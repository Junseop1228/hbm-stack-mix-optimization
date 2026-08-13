# -*- coding: utf-8 -*-
"""
robustness_evppi.py — M12(층별 수율 저하)와 M7(EVPPI) 처리

M12 — i.i.d. 가정의 검사
------------------------
가정 1 은 층별 접합 실패를 i.i.d. 로 둔다. 실제 TC 접합은 적층 누적 warpage 로
**상단으로 갈수록 수율이 저하**될 수 있다. x_i = x_0 − δ(i−1) 로 두고
주요 결론이 버티는지 본다. 특히 dppm_floor.py 의 '상단 집중' 과 결합하면
상단 수율 저하는 그 집중을 **강화**하는 방향이므로, 비균일 스케줄 결론은
오히려 강해질 것으로 예측된다. 검정한다.

M7 — EVPPI
----------
Table XII 는 Pearson 상관이며 정보가치가 아니다. EVPPI(expected value of
partial perfect information)는 특정 파라미터의 불확실성만 해소했을 때
목적함수의 기대 개선분이다. 상관계수와 순위가 다를 수 있다는 지적을 검정한다.

  단순화: 결정을 '어느 (L,k) 구성을 택할 것인가' 로 두고 성과를 설비시간
  단위당 이익으로 잡는다. 캐파·수요 제약의 실행가능성 변동을 배제해
  EVPPI 계산을 정의 가능하게 만든 것이며, 이 단순화를 명시한다.

산출물: data/robustness_evppi_log.txt
"""

import math
import os
import random
import sys

from hbm_model import Params, coefficients, block_y, L_SET, K_SET

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DIST = {
    "x":         (0.940, 0.965, 0.990),
    "beta":      (0.840, 0.950, 0.990),
    "beta_f":    (0.870, 0.950, 0.990),
    "phi_final": (1.0,   3.0,  10.0),
    "a":         (0.0,   3.0,   8.0),
    "theta":     (1.0,   3.0,  10.0),
    "r":         (3.0,   5.0,   8.0),
    "c_base":    (0.5,   1.5,   2.0),
    "c_fix_b":   (1.0,   4.5,   8.0),
    "c_test":    (0.007, 0.012, 0.017),
}


# ══════════════════════════════════════════════════════════
# M12 — 층별 수율 저하
# ══════════════════════════════════════════════════════════

def block_y_graded(L, positions, x0, delta, beta, beta_f=0.0):
    """층별 수율 x_i = x0 - delta*(i-1). positions 는 검사 위치 집합."""
    pos = sorted(positions)
    m = len(pos)
    xs = [max(1e-9, x0 - delta * (i - 1)) for i in range(1, L + 1)]
    # 무결점 확률
    p_good = 1.0
    for v in xs:
        p_good *= v
    e_layer = p_good * L
    e_test = p_good * m
    esc_raw = 0.0
    surv = 1.0                          # 층 i-1 까지 무결점 확률
    for i in range(1, L + 1):
        p_i = surv * (1.0 - xs[i - 1])   # 층 i 에서 첫 결함
        surv *= xs[i - 1]
        j0 = 0
        while j0 < m and pos[j0] < i:
            j0 += 1
        rem = m - j0
        for t in range(1, rem + 1):
            prob = p_i * ((1.0 - beta) ** (t - 1)) * beta
            e_layer += prob * pos[j0 + t - 1]
            e_test += prob * (j0 + t)
        miss = p_i * ((1.0 - beta) ** rem)
        esc_raw += miss
        e_layer += miss * L
        e_test += miss * m
    esc = esc_raw * (1.0 - beta_f)
    ship = p_good + esc
    return {"p_good": p_good, "e_layer": e_layer, "e_test": e_test,
            "p_escape": esc, "p_ship": ship,
            "dppm": esc / ship * 1e6 if ship > 0 else 0.0}


def m12(P):
    p = Params()
    beta = p.beta
    P("=" * 84)
    P("M12 — 층별 수율 저하 시나리오 (i.i.d. 가정의 검사)")
    P("=" * 84)
    P("x_i = x_0 − δ(i−1).  δ=0 이 종전 i.i.d. 가정이다.")
    P("x_0 는 평균 수율을 0.965 로 유지하도록 보정한다: x_0 = 0.965 + δ(L−1)/2")
    P("")
    P("[1] DPPM 하한 (균일 k=1, β=0.95, β_f=0)")
    P("      δ    │   L=8      L=12     L=16   │ L 무의존성")
    for delta in (0.0, 0.001, 0.002, 0.005):
        vals = []
        for L in L_SET:
            x0 = 0.965 + delta * (L - 1) / 2.0
            y = block_y_graded(L, range(1, L + 1), x0, delta, beta, 0.0)
            vals.append(y["dppm"])
        spread = (max(vals) - min(vals)) / min(vals) * 100
        P("  %.4f  │ %8.1f %8.1f %8.1f  │ 편차 %.2f %%"
          % (delta, vals[0], vals[1], vals[2], spread))
    P("")
    P("  δ>0 이면 상단 수율이 더 나쁘고, 상단 층은 검사 기회가 1회뿐이므로")
    P("  하한이 상승한다. 그리고 L 무의존성이 깨진다 — 층수가 많을수록 상단이")
    P("  더 나빠지기 때문이다. **δ=0 에서만 성립하는 결과임을 명시해야 한다.**")
    P("")
    P("[2] 비균일 스케줄 우위는 유지되는가 (L=16, 검사 5회)")
    P("      δ    │ 상단 5개(12~16)  균일 k=4(4,8,12,16)  개선")
    for delta in (0.0, 0.001, 0.002, 0.005):
        x0 = 0.965 + delta * 15 / 2.0
        top = block_y_graded(16, [12, 13, 14, 15, 16], x0, delta, beta, 0.0)["dppm"]
        uni = block_y_graded(16, [4, 8, 12, 16], x0, delta, beta, 0.0)["dppm"]
        P("  %.4f  │    %8.1f          %8.1f       %.1f %% 개선"
          % (delta, top, uni, (uni - top) / uni * 100))
    P("")
    P("  ★ 비균일 스케줄의 우위는 δ 전 구간에서 유지된다 (74~76 % 개선).")
    P("")
    P("  ⚠️ 사전 예측 정정 — 예측이 절반만 맞았다.")
    P("     예측: 'δ 가 커질수록 비균일 스케줄의 우위가 커진다'")
    P("     실제: 절대 개선폭은 커지지만(6,152 → 11,757 ppm) 상대 개선율은")
    P("           소폭 감소한다(76.3 → 74.2 %). 두 스케줄의 하한이 함께")
    P("           올라가기 때문이다. 예측과 어긋난 부분을 그대로 남긴다.")
    P("")


# ══════════════════════════════════════════════════════════
# M7 — EVPPI
# ══════════════════════════════════════════════════════════

def tri_ppf(u, lo, mode, hi):
    """삼각분포 역CDF. 외부 격자를 실제 marginal 에서 뽑기 위해 필요하다."""
    fc = (mode - lo) / (hi - lo)
    if u < fc:
        return lo + math.sqrt(u * (hi - lo) * (mode - lo))
    return hi - math.sqrt((1.0 - u) * (hi - lo) * (hi - mode))


def ratios(params, configs):
    """샘플 1개에 대한 전 구성의 설비시간 단위당 이익.
    종전 payoff() 는 구성마다 coefficients() 를 다시 호출해 9배 낭비했다."""
    coef = coefficients(Params(**params))
    return [coef[c]["ratio"] for c in configs]


def evppi(P, n_outer=40, n_inner=250, seed=7):
    rnd = random.Random(seed)
    P("=" * 84)
    P("M7 — EVPPI (기대 부분정보가치)")
    P("=" * 84)
    P("결정 = 어느 (L,k) 구성을 택할 것인가.  성과 = 설비시간 단위당 이익.")
    P("캐파·수요 제약의 실행가능성 변동을 배제한 단순화이며, 이를 명시한다.")
    P("표본: 외부 %d × 내부 %d (파라미터당 %d회 평가)" % (n_outer, n_inner, n_outer * n_inner))
    P("분산감소: **공통 난수(CRN)**. 내부 표본을 한 번만 뽑아 모든 외부 격자점과")
    P("모든 파라미터에 재사용한다. 격자점 간 비교에서 표본 변동이 상쇄된다.")
    P("외부 격자: **삼각분포의 층화 분위수**(역CDF). 균등 분할을 쓰면 분포가")
    P("어긋나 EVPPI 가 체계적으로 음수가 된다 — 실제로 그 오류를 겪고 정정했다.")
    P("")

    def draw():
        return {kk: rnd.triangular(v[0], v[2], v[1]) for kk, v in DIST.items()}

    configs = [(L, k) for L in L_SET for k in K_SET]
    # ★ CRN — 내부 표본을 한 번만 뽑아 전 격자점·전 파라미터에 재사용
    pool = [draw() for _ in range(n_inner)]

    # 기준: 정보 없음 — 전체 분포 평균에서 최선 구성 1개 고정
    # 기준도 동일 표본 풀로 계산해 편향을 없앤다
    acc = [0.0] * len(configs)
    for s in pool:
        for j, v in enumerate(ratios(s, configs)):
            acc[j] += v
    mean_pay = {c: acc[j] / n_inner for j, c in enumerate(configs)}
    ev_no_info = max(mean_pay.values())
    best_cfg = max(mean_pay, key=mean_pay.get)
    P("  정보 없음: 구성 %d단 k=%d 고정, 기대 성과 %.5f"
      % (best_cfg[0], best_cfg[1], ev_no_info))
    P("")

    rows = []
    for name in DIST:
        lo, mode, hi = DIST[name]
        total = 0.0
        for q in range(n_outer):
            fixed = tri_ppf((q + 0.5) / n_outer, lo, mode, hi)   # 삼각분포 층화 분위수
            acc2 = [0.0] * len(configs)
            for base in pool:                      # CRN: 공통 표본 재사용
                s = dict(base)
                s[name] = fixed
                for j, v in enumerate(ratios(s, configs)):
                    acc2[j] += v
            total += max(v / n_inner for v in acc2)
        ev_partial = total / n_outer
        gain = ev_partial - ev_no_info
        rows.append((name, gain, gain / ev_no_info * 100))

    rows.sort(key=lambda r: -r[1])
    noise = max(0.0, -min(r[1] for r in rows))   # 음수 최대치 = 추정 노이즈 하한
    P("  파라미터   │  EVPPI      기준 대비 │ 판정")
    for name, g, pct in rows:
        if g > 2 * noise and noise > 0:
            mark = "유의"
        elif g > noise:
            mark = "노이즈 경계"
        else:
            mark = "0 과 구분 불가"
        P("  %-10s │ %+.6f   %+6.3f %%  │  %s" % (name, g, pct, mark))
    P("")
    P("  ⚠️ EVPPI 는 이론상 항상 0 이상이다. 음수 추정치는 표본 노이즈이며,")
    P("     그 최대 크기 %.6f 가 추정기의 노이즈 하한이다. 이보다 작은" % noise)
    P("     추정치는 0 과 구분할 수 없으므로 순위를 부여하지 않는다.")
    P("")
    P("  ⚠️ r(층당 매출) 이 상위인 것은 정보가치가 아니라 스케일 효과일 수 있다.")
    P("     성과가 이익이므로 r 을 알면 이익 예측이 좋아지지만, 그것이 '어느")
    P("     구성을 택하는가' 를 바꾸지 않으면 의사결정 가치는 없다. 상관계수")
    P("     분석에서 r 에 붙인 caveat 와 같은 성질의 문제다.")
    P("")
    P("  ★ 상관계수 순위와 대조 (07_Results 5.2 — 16단 비중 기준)")
    corr_rank = ["x", "theta", "phi_final", "beta", "c_fix_b", "rho",
                 "beta_f", "a", "r", "c_base", "c_test"]
    evppi_rank = [r[0] for r in rows]
    P("    상관 상위 3 (16단 비중): %s"
      % ", ".join([c for c in corr_rank if c in DIST][:3]))
    P("    EVPPI 상위 3          : %s" % ", ".join(evppi_rank[:3]))
    P("")
    P("  EVPPI 가 상관계수와 다른 순위를 주면 심사자 지적(상관 ≠ 정보가치)이")
    P("  수치로 확인되는 것이다. 같은 순위를 주면 종전 해석이 우연히 옳았던 것이다.")
    P("  어느 쪽이든 **'정보가치 분석' 이라는 명칭은 상관계수에 붙일 수 없다.**")
    P("")


def main():
    out = []
    P = out.append
    m12(P)
    evppi(P)
    text = "\n".join(out)
    print(text)
    with open(os.path.join(ROOT, "data", "robustness_evppi_log.txt"), "w",
              encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    main()
