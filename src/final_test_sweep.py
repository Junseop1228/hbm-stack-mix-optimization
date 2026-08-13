# -*- coding: utf-8 -*-
"""
final_test_sweep.py — 최종 검사 시간비 φ_f 와 검사시간비 θ 에 대한 헤드라인 곡면

배경 (M1 + M8)
--------------
M1 정정으로 최종 검사의 테스터 시간을 τ_test 에 포함시킨 결과, 결론이 크게 바뀌었다.
그리고 φ_f 는 미확보 파라미터다. 따라서 헤드라인을 φ_f 한 점에서 보고하면
"절대값을 모르니 파라미터 공간으로 다룬다" 는 본 연구의 원칙에 어긋난다(M8).

이 스크립트는 φ_f 와 θ 를 축으로 다음을 보고한다.
  1. 단일 풀 최적 층수 — 내부 최적점인가 경계해인가 (검증 8 의 성립 조건)
  2. 병목 전환 비율
  3. 기준 시나리오 믹스와 실행 가능성

산출물: data/final_test_sweep_log.txt, data/final_test_sweep.csv
"""

import csv
import os
import sys

from hbm_model import Params, coefficients, L_SET, K_SET, DEMAND_SEG, DEMAND_WAFER_DIES
from milp import solve, BIG
import scenarios as SC

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

H_SINGLE = SC.H_B


def best_L_single_pool(**kw):
    """캐파를 단일 풀로 합쳤을 때의 최적 층수 (검증 8 설정)."""
    coef = coefficients(Params(**kw))
    per_L = {}
    for L in L_SET:
        per_L[L] = max(coef[(L, k)]["ratio"] for k in K_SET)
    arg = max(per_L, key=per_L.get)
    interior = arg not in (min(L_SET), max(L_SET))
    unimodal = per_L[8] <= per_L[12] >= per_L[16]
    return arg, interior, unimodal, per_L


def transition(rho_lo=0.3, rho_hi=3.0, iters=34, **kw):
    """병목 전환 비율 이분탐색."""
    coef = coefficients(Params(**kw))
    lo, hi = rho_lo, rho_hi
    for _ in range(iters):
        mid = (lo + hi) / 2
        s = solve(coef, SC.H_B, SC.H_B * mid, segments=DEMAND_SEG,
                  wafer_dies=DEMAND_WAFER_DIES, dppm_cap=SC.DPPM_CAP)
        if s["status"] != "Optimal":
            lo = mid
            continue
        if s["dual_test"] > s["dual_bond"]:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def baseline(**kw):
    s = solve(coefficients(Params(**kw)), SC.H_B, SC.H_B * SC.RHO_BASE,
              segments=DEMAND_SEG, wafer_dies=DEMAND_WAFER_DIES, dppm_cap=SC.DPPM_CAP)
    if s["status"] != "Optimal":
        return None
    tot = sum(s["q"].values())
    by = {L: 0.0 for L in L_SET}
    for (L, k), v in s["q"].items():
        by[L] += v / tot * 100
    return s, by


def main():
    out = []
    P = out.append
    rows = []

    P("=" * 88)
    P("최종 검사 시간비 φ_f 와 검사시간비 θ 에 대한 헤드라인 곡면")
    P("=" * 88)
    P("φ_f = t_final / t_test.  최종 검사는 완결 스택 전량이 거치므로 τ_test 에")
    P("p_ship(L,k)·t_final 로 들어간다. 절대값·비율 모두 공개 자료에 없다.")
    P("")

    # ── 1. 검증 8 의 성립 조건 ────────────────────────────────
    P("[1] ★ 검증 8(문헌 재현)의 성립 조건 — φ_f 에 따라 내부 최적점이 사라진다")
    P("  선행연구 결론은 '층수에 내부 최적점이 존재' 다. 캐파를 단일 풀로 합쳤을 때")
    P("  그것이 재현되는지가 검증 8 이다.")
    P("")
    P("   φ_f │ 최적 층수  내부최적점  단봉성 │  8단 ratio  12단 ratio  16단 ratio")
    thr = None
    prev_interior = None
    for pf in [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0, 5.0, 10.0]:
        arg, interior, uni, per = best_L_single_pool(phi_final=pf)
        P("  %5.2f │   %2d단      %-4s      %-4s   │  %.5f    %.5f    %.5f"
          % (pf, arg, "YES" if interior else "NO", "OK" if uni else "FAIL",
             per[8], per[12], per[16]))
        if prev_interior is None:
            prev_interior = interior
        elif prev_interior and not interior and thr is None:
            thr = pf
        prev_interior = interior
        rows.append(dict(axis="phi_final", value=pf, best_L=arg,
                         interior=int(interior), unimodal=int(uni)))
    P("")
    # 임계 φ_f 이분탐색
    lo, hi = 0.0, 3.0
    for _ in range(30):
        mid = (lo + hi) / 2
        _, interior, _, _ = best_L_single_pool(phi_final=mid)
        if interior:
            lo = mid
        else:
            hi = mid
    P("  ★ 임계 φ_f = %.4f" % ((lo + hi) / 2))
    P("    이보다 작으면 층수 내부 최적점이 존재하고(선행연구 결론 재현),")
    P("    크면 경계해(최대 후보 층수)가 되어 재현되지 않는다.")
    P("")
    P("  해석: 최종 검사 시간은 출하 스택당 층수와 무관하게 부과되므로 높은 층수가")
    P("  이를 분산한다. 이 힘이 수율의 지수적 하락을 넘어서면 내부 최적점이 소멸한다.")
    P("  φ_f ≥ 임계값 구간에서 모델은 '후보 중 가장 높이 쌓아라' 를 답하며, 이는")
    P("  참 최적점이 후보 집합 {8,12,16} 밖에 있을 수 있다는 뜻이다. 한계로 명시한다.")
    P("")

    # ── 2. 병목 전환 비율 ────────────────────────────────────
    P("[2] 병목 전환 비율의 φ_f 의존")
    P("   φ_f │ 전환 H_t/H_b │ 기준 시나리오 (ρ=0.90)")
    for pf in [0.0, 0.5, 1.0, 2.0, 3.0, 5.0]:
        tr = transition(phi_final=pf)
        b = baseline(phi_final=pf)
        if b is None:
            P("  %5.2f │   %8.4f   │  실행 불가" % (pf, tr))
            rows.append(dict(axis="phi_final_transition", value=pf, best_L=None,
                             interior=None, unimodal=None))
            continue
        s, by = b
        P("  %5.2f │   %8.4f   │  8/12/16 = %.0f/%.0f/%.0f %%   병목 %s  J=%.5f"
          % (pf, tr, by[8], by[12], by[16], s["bottleneck"], s["J"]))
        rows.append(dict(axis="phi_final_transition", value=pf, best_L=tr,
                         interior=None, unimodal=None))
    P("")
    P("  ★ 8단은 φ_f = 0 에서만 등장한다. 종전 모델의 '8단 등장 메커니즘 미규명'")
    P("    (VIII-A)은 최종 검사 시간 누락의 인공물이었다. M1 정정으로 해소됐다.")
    P("")

    # ── 3. θ 축 (M8) ─────────────────────────────────────────
    P("[3] ★ 병목 전환 비율의 θ 의존 (M8) — knee 를 한 점이 아니라 곡선으로")
    P("   θ  │ 전환 H_t/H_b │ 기준 시나리오")
    for th in [1.0, 2.0, 3.0, 5.0, 8.0]:
        tr = transition(theta=th)
        b = baseline(theta=th)
        if b is None:
            P("  %4.1f │   %8.4f   │  실행 불가" % (th, tr))
        else:
            s, by = b
            P("  %4.1f │   %8.4f   │  8/12/16 = %.0f/%.0f/%.0f %%   병목 %s"
              % (th, tr, by[8], by[12], by[16], s["bottleneck"]))
        rows.append(dict(axis="theta_transition", value=th, best_L=tr,
                         interior=None, unimodal=None))
    P("")
    P("  전환 비율은 θ 와 φ_f 두 축 모두에 강하게 의존한다. 둘 다 미확보이므로")
    P("  단일 수치(종전 1.1398)로 보고하는 것은 부적절하다. 곡면으로 보고한다.")

    text = "\n".join(out)
    print(text)
    with open(os.path.join(ROOT, "data", "final_test_sweep_log.txt"), "w",
              encoding="utf-8") as f:
        f.write(text)
    with open(os.path.join(ROOT, "data", "final_test_sweep.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["axis", "value", "best_L", "interior", "unimodal"])
        w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main()
