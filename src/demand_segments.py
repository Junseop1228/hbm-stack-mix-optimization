# -*- coding: utf-8 -*-
"""
S3.5 (T5) : 수요 세그먼트 역산 + C2 구속 여부 판정
2026.08.12

역산 근거 (전부 공개 출처)
--------------------------
  슬롯 8개 고정                        Wing VC 2026-05-12          [A]
  층당 용량 3 GB                       24/8 = 36/12 일치            [A]
  B200/GB200   192GB = 24GB x 8  → 8단
  B300/GB300   288GB = 36GB x 8  → 12단 (HBM3E 12-Hi)              [B]
  Rubin        288GB HBM4 12-Hi                                    [B] NVIDIA 2026-07-21
  Rubin Ultra  12-Hi HBM4E 기준, 8-Hi 포함 4개 안 검토 중, 미확정    [B] TrendForce 2026-08-04

2026 고급 GPU 출하 믹스 (TrendForce 2026-04-08)
  Blackwell 71% (GB300/B300 주도, GB200/B200 은 상대적으로 소량)
  Rubin 22% (종전 29% 에서 하향)
  Hopper 나머지 (지정학 이슈로 감소 중)

⚠️ 16단 세그먼트 문제 — 그리고 슬롯 8개 전제의 붕괴 (2026.08.12 정정)
  Rubin Ultra 는 GTC 2025 발표 시점에 **1TB HBM4E · 스택 16개 · 16-Hi** 였다.
  즉 (a) 16단 수요는 원안에 실재했고, (b) **슬롯이 8개가 아니라 16개였다.**
  → 06_Parameters D1 "GPU당 HBM 슬롯 8개 고정"[A등급]은 **Blackwell·Rubin 세대에
    한정된 사실이며, Rubin Ultra 에는 적용되지 않는다.** 등급 조정 필요.

  그 뒤 사양이 계속 후퇴했다 (출처: TrendForce 2026-08-04, The Information 2026-08-06,
  SemiAnalysis, Tom's Hardware 2026-08-11).
     1TB HBM4E 16-Hi 4-die  →  HBM4E 12-Hi  →  4-die MCM 취소  →  2-die 패키지
     →  현재 192GB / 256GB 변형 시험 중, 주력 SKU 는 **HBM4 8-Hi 192GB** 유력
     →  **최종 사양 미확정**

  → 즉 16단 수요는 **원안에는 있었으나 현재 후퇴 중이고 확정 고객 제품이 없다.**
    16단 세그먼트는 0 으로 둔다. 억지로 만들지 않는다.
    ★ 이 후퇴 자체가 프로젝트 시의성의 직접 증거다 — 고객이 공급 제약 때문에
      층수를 낮추는 협상을 **지금** 하고 있고 답이 안 정해졌다.

⚠️ B300 대 B200 분리 비중은 미확보
  TrendForce 는 "GB300/B300 주도, GB200/B200 은 소량"이라는 정성 서술만 준다.
  따라서 ≥12단 비중을 **단일 점추정으로 쓰지 않고 스윕**한다. 그것이 이 프로젝트 방식이다.
"""

import os
import sys

from hbm_model import Params, coefficients, L_SET, K_SET, DEMAND_WAFER_DIES
from milp import solve
import scenarios as SC

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TOTAL = 5.666e6          # S1.5 동결 총 수요 (GB). 스케일은 캐파 대비 상대값이라 유지한다
CAP = SC.DPPM_CAP


def run(seg, seg16=0.0, p=None):
    p = p or Params()
    segs = [(8, TOTAL), (12, seg)]
    if seg16 > 0:
        segs.append((16, seg16))
    return solve(coefficients(p), SC.H_B, SC.H_B * SC.RHO_BASE,
                 segments=tuple(segs), wafer_dies=DEMAND_WAFER_DIES,
                 dppm_cap=CAP, need_duals=True)


def digest(res):
    if res["status"] != "Optimal":
        return None
    tot = sum(res["q"].values())
    byL = {L: 0.0 for L in L_SET}
    for (L, k), v in res["q"].items():
        byL[L] += v / tot
    d = res["duals"]
    return dict(byL=byL, gb=res["gb_total"], J=res["J"],
                c2a=d.get("C2_seg0", 0.0), c2b=d.get("C2_seg1", 0.0),
                c1a=d.get("C1a_bonder", 0.0), c1b=d.get("C1b_tester", 0.0),
                c4=d.get("C4_dppm", 0.0), dppm=res["dppm"],
                mix=" ".join("%d단k%d:%.0f%%" % (L, k, v / tot * 100)
                             for (L, k), v in sorted(res["q"].items())))


def main():
    out = []
    W = out.append

    W("=" * 96)
    W("S3.5 (T5) — 수요 세그먼트 역산 및 C2 구속 여부 판정")
    W("=" * 96)
    W("총 수요 %.3e GB (S1.5 동결 유지) / cap %.0f ppm / β_f %.2f"
      % (TOTAL, CAP, Params().beta_f))
    W("")
    W("[세그먼트 정의 — GPU 용량 목표에서 역산]")
    W("  슬롯 8개 고정이므로 스택당 용량 = 총용량 / 8, 층수 = 스택당용량 / 3GB")
    W("    192GB급 (B200/GB200, Hopper)      → 24GB/stack → **8단**")
    W("    288GB급 (B300/GB300, Rubin)       → 36GB/stack → **12단**")
    W("    Rubin Ultra : GTC 2025 원안은 1TB HBM4E · **스택 16개 · 16-Hi**")
    W("       → 슬롯 8개 전제(06_Parameters D1)가 이 제품에는 적용되지 않는다")
    W("       → 이후 12-Hi → 2-die 패키지 → 현재 HBM4 8-Hi 192GB 유력, **최종 미확정**")
    W("")
    W("  ★ 16단 수요는 원안에 실재했으나 **현재 후퇴 중이고 확정 제품이 없다.**")
    W("    16단 세그먼트 = 0 으로 둔다. 억지로 만들지 않는다.")
    W("")
    W("[≥12단 비중 스윕] — B300 대 B200 분리 비중이 미확보이므로 점추정하지 않는다")
    W("  TrendForce 2026-04-08 기준 추정 구간 : Blackwell 71%(B300 주도) + Rubin 22%")
    W("  → ≥12단 비중은 대략 0.65 ~ 0.75 로 본다. 아래에서 전 구간을 스윕한다.")
    W("")
    W("   ≥12단비중   상태     8단  12단  16단   C2듀얼(≥12단)  C1a     C1b      C4    믹스")
    thresh = None
    prev_bound = False
    for share in [0.30, 0.45, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00]:
        d = digest(run(TOTAL * share))
        if d is None:
            W("   %7.2f     실행 불가" % share)
            continue
        bound = abs(d["c2b"]) > 1e-9
        if bound and not prev_bound and thresh is None:
            thresh = share
        prev_bound = bound
        W("   %7.2f    OK    %4.0f%% %4.0f%% %4.0f%%   %11.4g  %6.4f  %6.4f  %7.4g  %s"
          % (share, d["byL"][8] * 100, d["byL"][12] * 100, d["byL"][16] * 100,
             d["c2b"], d["c1a"], d["c1b"], d["c4"], d["mix"]))
    W("")

    # 이분탐색으로 구속 전환점
    lo, hi = 0.30, 1.00
    if thresh is not None:
        lo, hi = thresh - 0.15, thresh
        for _ in range(30):
            mid = (lo + hi) / 2
            d = digest(run(TOTAL * mid))
            if d and abs(d["c2b"]) > 1e-9:
                hi = mid
            else:
                lo = mid
        W("  ★ C2 가 구속되기 시작하는 ≥12단 비중 : **%.4f**" % hi)
    else:
        W("  ★ 전 구간에서 C2 비구속")
    W("")

    # 기준 추정 구간 판정
    W("-" * 96)
    W("[판정] TrendForce 추정 구간(0.65~0.75)에서 C2 는 구속되는가")
    W("-" * 96)
    for share in (0.65, 0.70, 0.75):
        d = digest(run(TOTAL * share))
        W("   ≥12단 %.2f : C2 듀얼 %.6g → **%s**   믹스 %s"
          % (share, d["c2b"], "구속" if abs(d["c2b"]) > 1e-9 else "비구속", d["mix"]))
    W("")

    # 16단 세그먼트를 억지로 넣으면 어떻게 되는가 (참고용, 채택하지 않음)
    W("-" * 96)
    W("[참고] 16단 세그먼트를 넣으면 어떻게 되는가 — **채택하지 않는다**")
    W("  근거 없는 수요를 만들어 C2 를 구속시키는 것은 금지다. 감도만 본다.")
    W("-" * 96)
    for s16 in (0.05, 0.10, 0.20):
        d = digest(run(TOTAL * 0.70, TOTAL * s16))
        if d is None:
            W("   16단 %.2f : 실행 불가" % s16)
            continue
        W("   16단 %.2f : 8/12/16 = %.0f/%.0f/%.0f %%   믹스 %s"
          % (s16, d["byL"][8] * 100, d["byL"][12] * 100, d["byL"][16] * 100, d["mix"]))

    text = "\n".join(out)
    print(text)
    with open(os.path.join(ROOT, "data", "demand_segments_log.txt"), "w",
              encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    main()
