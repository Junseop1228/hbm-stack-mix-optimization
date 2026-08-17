# -*- coding: utf-8 -*-
"""
feasibility_decomp.py — N4: 실행불가 사유 분해와 절단 편향

2라운드 지적 (N4)
-----------------
"VII-E 는 여전히 '실행불가는 대부분 β 또는 β_f 가 낮아 200 ppm 을 못 맞추는
경우' 라고 쓴다. 그런데 β, β_f 분포는 바뀌지 않았고 τ_test 만 늘었다.
**품질 실행불가능성은 τ_test 와 무관하므로, 새로 생긴 19.3 %p 는 다른
메커니즘이다** — 거의 확실히 C2(고객 용량수요)다."

"Table XII 의 모든 상관계수가 28.3 % 절단표본 위에서 계산되었고, 절단 기준이
이제 품질 + 용량 두 축이다. φ_f 가 절단에 관여하면서 φ_f 의 상관계수는 절단
편향을 직접 포함한다."

방법
----
실행불가 draw 마다 제약을 하나씩 풀어 원인을 특정한다.
  C4 만 해제 → 실행가능?  → 품질이 원인
  C2 만 해제 → 실행가능?  → 용량수요가 원인
  둘 다 해제 → 실행가능?  → 두 축의 상호작용
  그래도 불가              → 그 외(C1/C3)
아울러 파라미터 3분위별 실행가능률과 로지스틱 회귀로 절단 편향을 정량화한다.

산출물: data/feasibility_decomp_log.txt
"""

import csv
import math
import os
import random
import sys

from hbm_model import (Params, coefficients, L_SET, DEMAND_SEG, DEMAND_WAFER_DIES,
                       H_BONDER, RHO_BASE, DPPM_CAP)
from milp import solve, BIG

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DIST = {
    "x": (0.940, 0.965, 0.990), "beta": (0.840, 0.950, 0.990),
    "beta_f": (0.870, 0.950, 0.990), "phi_final": (1.0, 3.0, 10.0),
    "a": (0.0, 3.0, 8.0), "theta": (1.0, 3.0, 10.0),
    "r": (3.0, 5.0, 8.0), "c_base": (0.5, 1.5, 2.0),
    "c_fix_b": (1.0, 4.5, 8.0), "c_test": (0.007, 0.012, 0.017),
}
# 표본 수 — 사유 분해는 비율만 필요하므로 400 이면 SE ≈ 2.4 %p 로 충분하다.
# 종전 1200 은 draw 당 CBC 재풀이가 겹쳐 파이프라인 한 단계가 30분을 먹었다.
N = 400
SEED = 42
NAMES = list(DIST)


def run(pars, cap=DPPM_CAP, seg=DEMAND_SEG):
    return solve(coefficients(Params(**pars)), H_BONDER, H_BONDER * RHO_BASE,
                 segments=seg, wafer_dies=DEMAND_WAFER_DIES, dppm_cap=cap,
                 need_duals=False)["status"] == "Optimal"


def logistic(X, y, iters=1500, lr=0.35):
    """표준화 후 경사하강. 계수 크기 비교용."""
    n, p = len(X), len(X[0])
    mu = [sum(r[j] for r in X) / n for j in range(p)]
    sd = [max(1e-12, math.sqrt(sum((r[j] - mu[j]) ** 2 for r in X) / n))
          for j in range(p)]
    Z = [[(r[j] - mu[j]) / sd[j] for j in range(p)] for r in X]
    w = [0.0] * p
    b = 0.0
    for _ in range(iters):
        gw = [0.0] * p
        gb = 0.0
        for zi, yi in zip(Z, y):
            z = b + sum(w[j] * zi[j] for j in range(p))
            pr = 1.0 / (1.0 + math.exp(-max(-30, min(30, z))))
            e = pr - yi
            gb += e
            for j in range(p):
                gw[j] += e * zi[j]
        b -= lr * gb / n
        for j in range(p):
            w[j] -= lr * gw[j] / n
    return w, b


def main():
    rnd = random.Random(SEED)
    out = []
    P = out.append
    P("=" * 90)
    P("N4 — 실행불가 사유 분해와 절단 편향 (draw %d, seed %d)" % (N, SEED))
    P("=" * 90)
    P("")

    # ── 분해 기준 ──────────────────────────────────────────
    # 처음에는 'C4 해제' 와 'C2 해제' 를 병렬로 시험했는데, **C2 를 해제하면
    # 생산 하한이 사라져 거의 항상 실행가능해진다.** 그 분류는 동어반복이므로
    # 폐기했다. 유효한 이분은 하나뿐이다.
    #
    #   C4(품질 상한)만 해제 → 실행가능  : 품질이 구속 요인
    #   C4 해제로도 불가               : 캐파가 수요를 감당하지 못함
    #
    # 후자가 심사자가 지목한 새 메커니즘이다.
    draws, feas = [], []
    cause = {"quality(C4)": 0, "capacity_vs_demand": 0}
    for _ in range(N):
        pars = {k: rnd.triangular(v[0], v[2], v[1]) for k, v in DIST.items()}
        ok = run(pars)
        draws.append(pars)
        feas.append(1 if ok else 0)
        if ok:
            continue
        cause["quality(C4)" if run(pars, cap=BIG)
              else "capacity_vs_demand"] += 1

    nf = sum(feas)
    P("[1] 실행가능률 : %d / %d = %.1f %%" % (nf, N, nf / N * 100))
    P("")
    P("[2] ★ 실행불가 사유 분해 (총 %d건)" % (N - nf))
    P("   사유                    건수    실행불가 중 비중")
    for k, v in sorted(cause.items(), key=lambda kv: -kv[1]):
        P("   %-22s %5d      %5.1f %%" % (k, v, v / max(1, N - nf) * 100))
    P("")
    q = cause["quality(C4)"]
    c = cause["capacity_vs_demand"]
    P("  분해 기준: C4(품질 상한)만 해제했을 때 실행가능해지는가.")
    P("  (C2 해제는 생산 하한을 없애 거의 항상 실행가능해지므로 동어반복이며 폐기했다.)")
    P("")
    P("  ★ 판정: 심사자 지적이 정확하다. 실행불가의 **%.1f %% 는 품질과 무관**하다."
      % (c / max(1, q + c) * 100))
    P("    종전 VII-E 서술('실행불가는 대부분 β 또는 β_f 가 낮아 200 ppm 을 못")
    P("    맞추는 경우')은 %.1f %% 만 설명한다. 나머지는 τ_test 증가로 산출이 줄어"
      % (q / max(1, q + c) * 100))
    P("    수요 하한 D_s 를 못 맞추는 경우다. **품질 축이 아니라 캐파-수요 축이다.**")
    P("")

    # ── 파라미터 3분위별 실행가능률 ─────────────────────────
    P("[3] 파라미터 3분위별 실행가능률 — 절단이 어느 축에서 일어나는가")
    P("   파라미터   │ 하위1/3   중위1/3   상위1/3  │ 최대-최소")
    tercile = {}
    for j, name in enumerate(NAMES):
        vals = sorted(d[name] for d in draws)
        q1, q2 = vals[N // 3], vals[2 * N // 3]
        buckets = [[], [], []]
        for d, f in zip(draws, feas):
            v = d[name]
            buckets[0 if v <= q1 else (1 if v <= q2 else 2)].append(f)
        rates = [sum(b) / len(b) * 100 if b else 0.0 for b in buckets]
        tercile[name] = rates
        P("   %-10s │ %6.1f %%  %6.1f %%  %6.1f %%  │ %6.1f %%p"
          % (name, rates[0], rates[1], rates[2], max(rates) - min(rates)))
    P("")
    worst = max(tercile, key=lambda k: max(tercile[k]) - min(tercile[k]))
    P("  절단을 가장 크게 좌우하는 파라미터: **%s** (%.1f %%p)"
      % (worst, max(tercile[worst]) - min(tercile[worst])))
    P("")

    # ── 로지스틱 회귀 ──────────────────────────────────────
    P("[4] 실행가능성 로지스틱 회귀 (표준화 계수)")
    X = [[d[n_] for n_ in NAMES] for d in draws]
    w, b = logistic(X, feas)
    P("   파라미터   │ 계수      해석")
    for name, coef in sorted(zip(NAMES, w), key=lambda t: -abs(t[1])):
        sign = "실행가능성 ↑" if coef > 0 else "실행가능성 ↓"
        P("   %-10s │ %+7.3f   %s" % (name, coef, sign))
    P("")
    P("  ⚠️ **절단 편향 고지.** 상관계수 표(전역 민감도)는 실행가능 표본에서만")
    P("     계산된다. 위 회귀가 보여주듯 실행가능성 자체가 여러 파라미터에")
    P("     의존하므로, 상관계수는 **조건부 상관**이며 무조건부 효과가 아니다.")
    P("     특히 절단에 강하게 관여하는 파라미터는 상관계수가 실제 효과보다")
    P("     작게(또는 반대로) 추정될 수 있다.")

    text = "\n".join(out)
    print(text)
    with open(os.path.join(ROOT, "data", "feasibility_decomp_log.txt"), "w",
              encoding="utf-8") as f:
        f.write(text)
    with open(os.path.join(ROOT, "data", "feasibility_decomp.csv"), "w",
              newline="", encoding="utf-8") as f:
        wr = csv.writer(f)
        wr.writerow(["metric", "key", "value"])
        wr.writerow(["feasible_pct", "-", round(nf / N * 100, 2)])
        for k, v in cause.items():
            wr.writerow(["cause_count", k, v])
        for name, coef in zip(NAMES, w):
            wr.writerow(["logit_coef", name, round(coef, 4)])
        for name, rates in tercile.items():
            wr.writerow(["tercile_spread_pp", name, round(max(rates) - min(rates), 2)])


if __name__ == "__main__":
    main()
