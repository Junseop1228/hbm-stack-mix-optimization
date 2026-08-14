# -*- coding: utf-8 -*-
"""
phi_final_sweep.py — STEP 3 / N3·N4

N3 (심사자 요구)
----------------
"φf ∈ [1, 20] 에 대해 (a) knee 위치, (b) 전환비, (c) 최적 mix, (d) **VII-F 반전
여부**를 스윕한 표/그림 1개. baseline 은 최소가 아니라 mode 로 옮기고, 최소값
케이스는 lower bound 시나리오로 별도 보고."

특히 (d) 가 핵심이다. 심사자 논거:
  "φf 가 크면 τ_test 가 k 에 거의 무의존한 바닥 항에 지배되고, 조기폐기는 그 바닥
   항까지 절약한다. 즉 '테스터 병목 → k=4' 의 유인이 약화되거나 반전할 수 있다."

이건 확인 없이 넘길 수 없다. 반전하면 VII-F 가 조건부 결론이 된다.

또한 R2 는 φf 가 물리적으로 5–20 이 현실적이라고 본다. in-line 은 개방/단락·연속성
위주의 짧은 검사이고 HBM 최종테스트는 full-speed·전 채널·soak/burn-in 을 포함한다.

N4 (심사자 요구)
----------------
"실행가능률이 47.6% → 28.3% 로 떨어졌는데 VII-E 는 여전히 'β 또는 βf 가 낮아
200 ppm 을 못 맞춤' 이라 쓴다. β, βf 분포는 안 바뀌었고 τ_test 만 늘었다.
품질 실행불가능성은 τ_test 와 무관하므로 새로 생긴 19.3%p 는 다른 메커니즘이다 —
거의 확실히 C2 다."

실행불가 사유를 분해해 확인한다.

산출물: data/phi_final_sweep_log.txt, phi_final_sweep.csv
"""

import csv
import math
import os
import random
import sys

from hbm_model import (Params, coefficients, block_y, L_SET, K_SET,
                       DEMAND_SEG, DEMAND_WAFER_DIES,
                       H_BONDER, H_TESTER, RHO_BASE, DPPM_CAP)
from milp import solve, BIG

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PHI_GRID = [1.0, 2.0, 3.0, 5.0, 8.0, 12.0, 16.0, 20.0]


def run(pf=None, rho=RHO_BASE, cap=DPPM_CAP, H_b=H_BONDER, **kw):
    p = Params(phi_final=pf if pf is not None else Params().phi_final, **kw)
    return solve(coefficients(p), H_b, H_b * rho, segments=DEMAND_SEG,
                 wafer_dies=DEMAND_WAFER_DIES, dppm_cap=cap)


def mix_of(s):
    if "q" not in s or not s["q"]:
        return "-", {}
    tot = sum(s["q"].values())
    by = {L: 0.0 for L in L_SET}
    byk = {k: 0.0 for k in K_SET}
    for (L, k), v in s["q"].items():
        by[L] += v / tot * 100
        byk[k] += v / tot * 100
    return " ".join("%dL:%.0f%%" % (L, v) for L, v in by.items() if v > 0.05), byk


def transition(pf, lo=0.3, hi=4.0, iters=32):
    for _ in range(iters):
        mid = (lo + hi) / 2
        s = run(pf, rho=mid)
        if s["status"] != "Optimal":
            lo = mid
            continue
        if s["dual_test"] > s["dual_bond"]:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def knee(pf, caps=(200, 250, 300, 350, 400, 425, 500, 1000, 5000)):
    """품질 상한별 전환점에서 평탄 구간이 시작되는 지점."""
    tr = {}
    for c in caps:
        lo, hi = 0.3, 4.0
        for _ in range(26):
            mid = (lo + hi) / 2
            s = run(pf, rho=mid, cap=c)
            if s["status"] != "Optimal":
                lo = mid; continue
            if s["dual_test"] > s["dual_bond"]:
                lo = mid
            else:
                hi = mid
        tr[c] = (lo + hi) / 2
    vals = list(tr.values())
    plateau = min(vals)
    k = min((c for c, v in tr.items() if abs(v - plateau) < 2e-3), default=None)
    return k, plateau, tr


def vii_f(pf):
    """VII-F 반전 검정 — 제약을 하나만 활성화했을 때의 최적 k."""
    out = {}
    for tag, kwargs in (("C1a_only", dict(H_t=BIG)), ("C1b_only", dict(H_b_free=True))):
        p = Params(phi_final=pf)
        coef = coefficients(p)
        if tag == "C1a_only":
            s = solve(coef, H_BONDER, BIG, wafer_dies=DEMAND_WAFER_DIES)
        else:
            s = solve(coef, BIG, H_TESTER, wafer_dies=DEMAND_WAFER_DIES)
        if s["status"] != "Optimal" or not s["q"]:
            out[tag] = None
            continue
        tot = sum(s["q"].values())
        byk = {k: 0.0 for k in K_SET}
        for (L, k), v in s["q"].items():
            byk[k] += v / tot * 100
        out[tag] = max(byk, key=byk.get), byk
    return out


def main():
    out, rows = [], []
    P = out.append
    P("=" * 92)
    P("N3 — 최종 검사 시간비 φ_f 스윕 (심사자 요구 범위 [1, 20])")
    P("=" * 92)
    P("R2 판단: in-line 은 개방/단락·연속성 위주의 짧은 검사, HBM 최종테스트는")
    P("full-speed·전 채널·soak/burn-in 포함 → φ_f 는 5~20 이 현실적.")
    P("본 연구 기준값 1.0 은 M1 을 정정하는 최소값이며 **하한 시나리오**다.")
    P("")

    # ── (a)(b)(c) ────────────────────────────────────────────
    P("[1] 전환비 · 최적 믹스 · knee")
    P("   φ_f │ 전환 H_t/H_b │ knee(ppm) │ 평탄값  │ 기준 시나리오 믹스        │ 병목    J")
    for pf in PHI_GRID:
        tr = transition(pf)
        kn, pl, _ = knee(pf)
        s = run(pf)
        if s["status"] != "Optimal":
            P("  %5.1f │   %8.4f   │    %4s   │ %6.4f  │  실행 불가                │ —"
              % (pf, tr, kn, pl))
            rows.append(dict(phi_final=pf, transition=round(tr, 4), knee_ppm=kn,
                             plateau=round(pl, 4), mix="infeasible", bottleneck="",
                             J="", k_C1a="", k_C1b="", inversion=""))
            continue
        mx, byk = mix_of(s)
        P("  %5.1f │   %8.4f   │    %4s   │ %6.4f  │  %-24s │ %-5s  %.5f"
          % (pf, tr, kn, pl, mx, s["bottleneck"], s["J"]))
        rows.append(dict(phi_final=pf, transition=round(tr, 4), knee_ppm=kn,
                         plateau=round(pl, 4), mix=mx, bottleneck=s["bottleneck"],
                         J=round(s["J"], 5), k_C1a="", k_C1b="", inversion=""))
    P("")
    P("  ★ knee 는 φ_f 에 따라 이동한다. 종전 '425 ppm' 은 φ_f = 1.0 한 점의 값이다.")
    P("")

    # ── (d) VII-F 반전 검정 ─────────────────────────────────
    P("[2] ★★ VII-F 반전 검정 — '본더 병목 → k 최대 / 테스터 병목 → k 최소' 가 유지되는가")
    P("  심사자 논거: φ_f 가 크면 τ_test 가 k 무의존 바닥 항에 지배되고, 조기 폐기가")
    P("  그 바닥 항까지 절약하므로 '테스터 병목 → k=4' 의 유인이 약화·반전할 수 있다.")
    P("")
    P("   φ_f │ C1a 단독(본더 병목) │ C1b 단독(테스터 병목) │ VII-F 방향")
    for i, pf in enumerate(PHI_GRID):
        v = vii_f(pf)
        a, bb = v.get("C1a_only"), v.get("C1b_only")
        ka = ("k=%d (%.0f%%)" % (a[0], a[1][a[0]])) if a else "실행불가"
        kb = ("k=%d (%.0f%%)" % (bb[0], bb[1][bb[0]])) if bb else "실행불가"
        if a and bb:
            keep = a[0] < bb[0]
            verdict = "유지" if keep else ("동일" if a[0] == bb[0] else "**반전**")
        else:
            verdict = "판정불가"
        P("  %5.1f │  %-17s │  %-19s │ %s" % (pf, ka, kb, verdict))
        rows[i]["k_C1a"] = a[0] if a else ""
        rows[i]["k_C1b"] = bb[0] if bb else ""
        rows[i]["inversion"] = verdict
    P("")

    # ── N4 실행불가 사유 분해 ───────────────────────────────
    P("=" * 92)
    P("N4 — 몬테카를로 실행불가 사유 분해")
    P("=" * 92)
    P("심사자 지적: 실행가능률 47.6% → 28.3% 인데 VII-E 는 여전히 'β·β_f 가 낮아")
    P("200 ppm 미달' 이라 쓴다. 그러나 β·β_f 분포는 불변이고 τ_test 만 늘었다.")
    P("품질 실행불가는 τ_test 와 무관하므로 새 19.3%p 는 다른 메커니즘이다.")
    P("")
    DIST = {
        "x": (0.940, 0.965, 0.990), "beta": (0.840, 0.950, 0.990),
        "beta_f": (0.870, 0.950, 0.990), "phi_final": (1.0, 3.0, 10.0),
        "a": (0.0, 3.0, 8.0), "theta": (1.0, 3.0, 10.0),
        "r": (3.0, 5.0, 8.0), "c_base": (0.5, 1.5, 2.0),
        "c_fix_b": (1.0, 4.5, 8.0), "c_test": (0.007, 0.012, 0.017),
        "rho": (0.6, 0.9, 1.4),
    }
    rnd = random.Random(42)
    N = 1500
    cnt = {"feasible": 0, "quality": 0, "capacity_demand": 0, "other": 0}
    for _ in range(N):
        d = {k: rnd.triangular(v[0], v[2], v[1]) for k, v in DIST.items()}
        rho = d.pop("rho")
        p = Params(**d)
        coef = coefficients(p)
        s = run(rho=rho, **d)
        if s["status"] == "Optimal":
            cnt["feasible"] += 1
            continue
        # 사유 판정 1 — 어떤 구성으로도 cap 을 못 맞추는가 (품질)
        best = min(coef[(L, k)]["dppm"] for L in L_SET for k in K_SET)
        if best > DPPM_CAP:
            cnt["quality"] += 1
            continue
        # 사유 판정 2 — 수요 제약을 풀면 실행 가능해지는가 (캐파-수요)
        s2 = solve(coef, H_BONDER, H_BONDER * rho, segments=(),
                   wafer_dies=DEMAND_WAFER_DIES, dppm_cap=DPPM_CAP)
        cnt["capacity_demand" if s2["status"] == "Optimal" else "other"] += 1

    P("  표본 %d회" % N)
    P("   사유                          건수      비율")
    P("   실행 가능                   %5d   %6.1f %%" % (cnt["feasible"], cnt["feasible"] / N * 100))
    P("   품질 — 어떤 (L,k)로도 cap 미달  %5d   %6.1f %%" % (cnt["quality"], cnt["quality"] / N * 100))
    P("   ★ 캐파-수요 — C2 를 풀면 가능  %5d   %6.1f %%"
      % (cnt["capacity_demand"], cnt["capacity_demand"] / N * 100))
    P("   기타                        %5d   %6.1f %%" % (cnt["other"], cnt["other"] / N * 100))
    P("")
    if cnt["capacity_demand"] > 0:
        P("  ★ 심사자 추정이 확인됐다. 실행불가의 상당 부분이 품질이 아니라")
        P("    **테스터 시간 증가로 산출이 줄어 수요 제약 C2 를 못 맞추는 것**이다.")
        P("    VII-E 의 'β 또는 β_f 가 낮아 200 ppm 미달' 서술은 불완전하다.")
    P("")
    P("  ⚠️ 절단 편향 — 상관계수는 실행 가능 표본 위에서만 계산된다. 절단 기준이")
    P("     이제 품질과 캐파-수요 두 축이며, φ_f 가 후자에 직접 관여한다. 따라서")
    P("     φ_f 의 상관계수는 절단 편향을 포함한다. 해석 시 명시해야 한다.")

    text = "\n".join(out)
    print(text)
    with open(os.path.join(ROOT, "data", "phi_final_sweep_log.txt"), "w",
              encoding="utf-8") as f:
        f.write(text)
    with open(os.path.join(ROOT, "data", "phi_final_sweep.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["phi_final", "transition", "knee_ppm",
                                          "plateau", "mix", "bottleneck", "J",
                                          "k_C1a", "k_C1b", "inversion"])
        w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main()
