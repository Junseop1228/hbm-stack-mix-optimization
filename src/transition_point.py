# -*- coding: utf-8 -*-
"""
S3-6 : 병목 전환점 궤적 + J 하락 원인 분해
2026.08.12

(1) 전환점 궤적 — cap 별 병목 전환 H_t/H_b. 대표 그림 1번의 새 내용.
    "전환점이 여기다"(조건부 사실) → "전환점이 품질 목표의 함수다"(구조적 결과)

(2) J 하락 원인 분해 — 0.17289 → 0.15953 이 cap 단독 효과인지 확인한다.
    설정 3개(β_f, cap, 세그먼트)가 동시에 바뀌었으므로 하나씩 켠다.
    단독 효과가 아니면 "품질을 조이는 비용 7.7%" 문장은 쓰지 않는다.
"""

import os
import sys

from hbm_model import Params, coefficients, L_SET, K_SET, DEMAND_WAFER_DIES
from milp import solve
import scenarios as SC

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TOTAL = 5.666e6
SEG_OLD = ((8, TOTAL), (12, 2.550e6))    # 종전 : ≥12단 0.45
SEG_NEW = ((8, TOTAL), (12, 3.966e6))    # 현행 : ≥12단 0.70


def run(cap, seg, beta_f, rho, duals=True):
    p = Params(beta_f=beta_f)
    return solve(coefficients(p), SC.H_B, SC.H_B * rho, segments=seg,
                 wafer_dies=DEMAND_WAFER_DIES, dppm_cap=cap, need_duals=duals)


def transition(cap, seg, beta_f, lo=0.3, hi=3.0, n=34):
    """병목이 테스터→본더로 넘어가는 H_t/H_b (이분탐색)."""
    if run(cap, seg, beta_f, hi)["status"] != "Optimal":
        return None
    for _ in range(n):
        mid = (lo + hi) / 2
        s = run(cap, seg, beta_f, mid)
        if s["status"] != "Optimal":
            lo = mid
            continue
        if s["dual_test"] > s["dual_bond"]:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def main():
    out = []
    W = out.append

    W("=" * 88)
    W("S3-6 : 병목 전환점 궤적 + J 하락 원인 분해")
    W("=" * 88)
    W("")

    # ---------------- (1) 전환점 궤적 ----------------
    W("-" * 88)
    W("[1] 병목 전환점 궤적 — 대표 그림 1번 (가로축 cap, 세로축 전환 H_t/H_b)")
    W("-" * 88)
    W("  현행 설정 : β_f = 0.95, 세그먼트 ≥12단 0.70")
    W("")
    W("   DPPM 상한    전환 H_t/H_b    해석")
    rows = []
    for cap in (200, 250, 300, 400, 500, 1000, 2000, 5000, 8000):
        t = transition(cap, SEG_NEW, 0.95)
        if t is None:
            W("   %7d      실행 불가" % cap)
            continue
        note = "테스터 캐파가 본더보다 커야 함" if t > 1.0 else "테스터가 본더보다 작아도 됨"
        W("   %7d       %8.4f      %s" % (cap, t, note))
        rows.append((cap, t))
    W("")
    if rows:
        lo_c, lo_t = rows[0]
        hi_c, hi_t = rows[-1]
        W("  ★ cap %d ppm → %.4f / cap %d ppm → %.4f" % (lo_c, lo_t, hi_c, hi_t))
        W("    **병목 전환점은 품질 목표의 함수다.** 품질을 조이면 검사 부하가 늘어")
        W("    테스터 쪽으로 병목이 이동하고, 어느 지점에서는 테스터 캐파가 본더보다 커야 한다.")
        cross = [c for c, t in rows if t > 1.0]
        if cross:
            W("    테스터 캐파 > 본더 캐파가 필요해지는 구간 : cap ≤ %d ppm" % max(cross))
    W("")

    # ---------------- (2) J 분해 ----------------
    W("-" * 88)
    W("[2] J 하락 원인 분해 — 0.17289 → 0.15953 이 cap 단독 효과인가")
    W("-" * 88)
    W("  기준선(rho = %.2f)에서 설정을 하나씩 바꾼다." % SC.RHO_BASE)
    W("")
    W("   설정                                    상태        J        기준 대비")
    cases = [
        ("A 종전 전체 (β_f=0, cap=5000, seg0.45)", 5000.0, SEG_OLD, 0.0),
        ("B  cap 만 200 으로            ", 200.0, SEG_OLD, 0.0),
        ("C  β_f 만 0.95 로             ", 5000.0, SEG_OLD, 0.95),
        ("D  세그먼트만 0.70 으로        ", 5000.0, SEG_NEW, 0.0),
        ("E 현행 전체 (β_f=.95, cap=200, seg0.70)", 200.0, SEG_NEW, 0.95),
    ]
    base_J = None
    res_J = {}
    for tag, cap, seg, bf in cases:
        s = run(cap, seg, bf, SC.RHO_BASE)
        if s["status"] != "Optimal":
            W("   %-40s 실행 불가" % tag)
            res_J[tag[0]] = None
            continue
        if base_J is None:
            base_J = s["J"]
        res_J[tag[0]] = s["J"]
        W("   %-40s Optimal  %.5f    %+6.2f%%"
          % (tag, s["J"], (s["J"] / base_J - 1) * 100))
    W("")
    if res_J.get("B") and base_J:
        cap_only = (res_J["B"] / base_J - 1) * 100
        tot = (res_J["E"] / base_J - 1) * 100 if res_J.get("E") else float("nan")
        W("  cap 단독 효과 : %+.2f%%   /   전체 효과 : %+.2f%%" % (cap_only, tot))
        if abs(cap_only - tot) < 1.0:
            W("  → **cap 단독 효과로 봐도 된다.** '품질을 5,000→200 ppm 으로 조이는")
            W("    비용은 설비시간 단위당 이익 %.1f%%' 문장을 쓸 수 있다." % abs(cap_only))
        else:
            W("  → **cap 단독 효과가 아니다.** 다른 설정 변경이 %.2f%%p 를 설명한다."
              % abs(tot - cap_only))
            W("    '품질을 조이는 비용 7.7%' 문장은 **쓰지 않는다.**")

    text = "\n".join(out)
    print(text)
    with open(os.path.join(ROOT, "data", "transition_point_log.txt"), "w",
              encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    main()
