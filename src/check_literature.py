# -*- coding: utf-8 -*-
"""
check_literature.py — M5(품질 제약 구속 임계) + M10(검증 8 재정의)

M5 지적
-------
"Conclusion 의 네 threshold 중 하나가 '중간 검사의 성격이 277 ppm 에서 갈린다'
인데, 277 ppm 은 Fig 3 주석에만 한 번 등장하고 Section VII 어디에도 계산·정의·
유도가 없다."

정정: 이 값은 **C4 가 구속되기 시작하는 DPPM 상한**이다. 정의는 하나뿐이다.
C4 를 해제하고 푼 최적해의 출하 DPPM 이 그 임계값이다. 상한이 그보다 크면
품질 제약은 비구속이고, 검사는 품질 수단이 아니라 설비시간 절감 수단으로만
작동한다. 인스턴스가 바뀌었으므로 값을 재산출한다.

M10 지적
--------
"VI-B: 단일 pool 로 병합 → dual 0.20840, 직접계산 0.20840, '5자리까지 일치'.
이건 **항등식**이다. binding 자원이 하나이고 최적해가 단일 configuration 인
LP 에서 dual = profit/time 은 필연이다. 검증력이 0 이다. 게다가 stated purpose
는 '장비 제약을 제거하면 선행연구 문제로 환원'이었는데 실제로 한 건 제거가
아니라 **병합**이고, [1]의 어떤 published number 도 재현하지 않았다."

정정: 검증 8 을 세 성분으로 분해하고 각각의 검증력을 명시한다.
  (a) dual = profit/time  — 항등식. 검증력 없음. 구현 정합성 확인일 뿐이다.
  (b) 층수 내부 최적점 존재 — 선행연구의 정성적 결론. 검증력 있음.
  (c) [1]의 공표 주장 재현 — 목적함수 선택의 효과. 이번에 신설한다.

[1]은 2-die 예제에서 총원가를 목적함수로 쓰면 양품 스택당 이익률이 2 %
상쇄된다고 보고한다. 본 모델에서 같은 대조를 수행한다.

산출물: data/check_literature_log.txt
"""

import os
import sys

from hbm_model import (Params, coefficients, L_SET, K_SET,
                       DEMAND_SEG, DEMAND_WAFER_DIES,
                       H_BONDER, H_TESTER, DPPM_CAP)
from milp import solve, BIG

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def base(cap=DPPM_CAP, **kw):
    return solve(coefficients(Params(**kw)), H_BONDER, H_TESTER,
                 segments=DEMAND_SEG, wafer_dies=DEMAND_WAFER_DIES, dppm_cap=cap)


def main():
    out = []
    P = out.append
    p = Params()

    # ══════════════════════════════════════════════════════
    P("=" * 86)
    P("M5 — 품질 제약이 구속되기 시작하는 임계 DPPM")
    P("=" * 86)
    P("정의: C4 를 해제하고 푼 최적해의 출하 DPPM. 상한이 그보다 크면 C4 는")
    P("      비구속이며, 중간 검사는 품질 수단이 아니라 설비시간 절감 수단으로만")
    P("      작동한다. 그보다 작으면 검사 주기가 품질에 구속된다.")
    P("")

    free = base(cap=BIG)
    thr = free["dppm"]
    P("  C4 해제 시 최적해")
    P("    믹스        : %s" % ", ".join(
        "%d단 k=%d %.1f%%" % (L, k, v / sum(free["q"].values()) * 100)
        for (L, k), v in sorted(free["q"].items())))
    P("    출하 DPPM   : %.1f ppm   ← ★ 임계값" % thr)
    P("    병목        : %s" % free["bottleneck"])
    P("")
    P("  검산 — 상한을 임계값 좌우로 두고 C4 의 dual 을 본다")
    P("   DPPM 상한 │ C4 dual      │ 판정")
    for c in (thr * 0.8, thr * 0.95, thr * 1.05, thr * 1.5):
        s = base(cap=c)
        if s["status"] != "Optimal":
            P("  %8.1f  │ (실행 불가)" % c); continue
        d = s["duals"].get("C4_dppm", 0.0)
        P("  %8.1f  │ %11.1f  │ %s" % (c, d, "구속" if abs(d) > 1e-9 else "비구속"))
    P("")
    P("  ★ 임계값 = %.0f ppm. 종전 원고가 유도 없이 인용하던 277 ppm 은" % round(thr))
    P("    인스턴스 정정 전(ρ=0.8, φ_f=0) 값이므로 이 값으로 교체한다.")
    P("")

    # ══════════════════════════════════════════════════════
    P("=" * 86)
    P("M10 — 검증 8 의 재정의: 세 성분과 각각의 검증력")
    P("=" * 86)
    P("")

    coef = coefficients(p)
    per_L = {L: max(coef[(L, k)]["ratio"] for k in K_SET) for L in L_SET}
    arg = max(per_L, key=per_L.get)
    v8 = solve(coef, H_total=H_BONDER)
    dual = v8["duals"].get("C1_single_pool", 0.0)

    P("[a] dual = profit/time  — **항등식. 검증력 없음.**")
    P("    단일 풀 dual %.5f, 직접계산 %.5f" % (dual, per_L[arg]))
    P("    binding 자원이 하나이고 최적해가 단일 구성인 LP 에서 이 등식은")
    P("    필연이다. 심사자 지적대로 이것은 선행연구 재현이 아니라 **구현")
    P("    정합성 확인**이며, 그 이상으로 서술해서는 안 된다.")
    P("")

    P("[b] 층수 내부 최적점의 존재 — **검증력 있음.**")
    P("    구성별 설비시간 단위당 이익:")
    for L in L_SET:
        P("      %2d단 : %.5f%s" % (L, per_L[L], "  ← 최대" if L == arg else ""))
    interior = arg not in (min(L_SET), max(L_SET))
    P("    최적 %d단 / 내부 최적점 %s / 단봉성 %s"
      % (arg, "YES" if interior else "NO",
         "OK" if per_L[8] <= per_L[12] >= per_L[16] else "FAIL"))
    P("    이것이 선행연구의 정성적 결론(층수에 내부 최적점이 존재)이며,")
    P("    캐파 제약을 단일 풀로 되돌렸을 때 재현되는지가 실제 검증 대상이다.")
    P("    단 φ_f < 2.03 조건부다(VII-B).")
    P("")

    P("[c] [1]의 공표 주장 재현 — **신설.**")
    P("    [1]은 2-die 예제에서 총원가를 목적함수로 쓰면 양품 스택당 이익률이")
    P("    약 2 %% 상쇄된다고 보고한다. 본 모델에서 같은 대조를 수행한다.")
    P("")
    P("    비교 대상: 구성별로 (i) 총원가 최소 (ii) 양품당 원가 최소")
    P("    지표     : 선택된 구성의 양품 스택당 이익")
    P("")
    P("     층수 │ 총원가최소 k  양품당원가최소 k │ 양품당 이익 차")
    tot_gap = []
    for L in L_SET:
        by_total = min(K_SET, key=lambda k: coef[(L, k)]["cost"])
        by_unit = min(K_SET, key=lambda k: coef[(L, k)]["cost"] / coef[(L, k)]["p_good"])
        m_tot = ((coef[(L, by_total)]["revenue"] - coef[(L, by_total)]["cost"])
                 / coef[(L, by_total)]["p_good"])
        m_uni = ((coef[(L, by_unit)]["revenue"] - coef[(L, by_unit)]["cost"])
                 / coef[(L, by_unit)]["p_good"])
        gap = (m_uni - m_tot) / abs(m_uni) * 100 if m_uni else 0.0
        tot_gap.append(gap)
        P("      %2d  │      %d           %d          │  %+6.2f %%"
          % (L, by_total, by_unit, gap))
    P("")
    mx = max(tot_gap)
    P("    최대 상쇄 %.2f %%. **[1]의 2 %% 효과는 본 모델에서 재현되지 않는다.**" % mx)
    P("")
    P("    ★ 원인은 구조적이며 특정할 수 있다. 본 모델은 가정 2 에 따라 검사의")
    P("      효과를 **조기 폐기 하나로 한정**하므로 p_good = x^L 이 k 에 무의존이다")
    P("      (III-C 핵심 성질). 그러면 총원가와 양품당 원가는 k 에 대해 같은")
    P("      순서를 주고 두 목적함수가 항상 같은 검사 주기를 고른다.")
    P("")
    P("      [1]에서 두 목적함수가 갈리는 것은 그 모델이 **수리(repair)** 를 포함해")
    P("      테스트 흐름이 수율 자체를 바꾸기 때문이다. 가정 2 가 그 메커니즘을")
    P("      제거했으므로 재현될 수 없다.")
    P("")
    P("    → 따라서 이것은 **음성 재현**이며, 실패가 아니라 가정 2 의 범위를")
    P("      드러내는 결과다. 본 모델은 '검사 흐름이 수율을 바꾸는' 문제에는")
    P("      적용할 수 없다. 이를 VIII-A 에 한계로 명시한다.")
    P("")
    P("  결론: 검증 8 의 검증력은 [b]에 있다. [a]는 항등식이고 [c]는 정성적")
    P("  재현이다. 종전 원고가 [a]를 '유일한 치명 관문'의 근거로 제시한 것은")
    P("  과장이며 정정한다.")

    text = "\n".join(out)
    print(text)
    with open(os.path.join(ROOT, "data", "check_literature_log.txt"), "w",
              encoding="utf-8") as f:
        f.write(text)
    return round(thr)


if __name__ == "__main__":
    main()
