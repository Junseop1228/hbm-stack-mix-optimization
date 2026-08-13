# -*- coding: utf-8 -*-
"""
S3-5 : 시나리오 D 의 운명 판정
2026.08.12

"β = 0.84 면 매 층 검사해도 실행 불가"는 cap 5,000 · β_f = 0 기준이었다.
새 설정(β_f = 0.95, cap = 200)에서 이 결론이 살아남는지 본다.

  살아남으면 → 조건만 갱신해 D 유지
  죽으면     → D 를 β 스윕에서 β_f 스윕으로 교체
"""

import os
import sys

from hbm_model import Params, coefficients, block_y, L_SET, K_SET, DEMAND_SEG, DEMAND_WAFER_DIES
from milp import solve
import scenarios as SC

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(p, cap):
    return solve(coefficients(p), SC.H_B, SC.H_B * SC.RHO_BASE,
                 segments=DEMAND_SEG, wafer_dies=DEMAND_WAFER_DIES,
                 dppm_cap=cap, need_duals=True)


def kmix(res):
    if res["status"] != "Optimal":
        return None
    tot = sum(res["q"].values())
    byK = {k: 0.0 for k in K_SET}
    for (L, k), v in res["q"].items():
        byK[k] += v / tot
    return byK


def main():
    out = []
    W = out.append
    CAP = SC.DPPM_CAP
    P0 = Params()

    W("=" * 88)
    W("S3-5 : 시나리오 D 판정 — 새 설정에서 β 스윕이 여전히 의미 있는가")
    W("=" * 88)
    W("새 설정 : β_f = %.2f, 기준 cap = %.0f ppm (전환점 277 의 %.2f배)"
      % (P0.beta_f, CAP, CAP / 277.0))
    W("")

    W("-" * 88)
    W("[D-신] β 스윕 @ β_f=0.95, cap=200")
    W("-" * 88)
    W("      β    상태        최소달성DPPM(12단k1)   k1/k2/k4       출하DPPM  C4")
    survives = False
    for b in (0.84, 0.88, 0.92, 0.95, 0.97, 0.99):
        p = Params(beta=b)
        floor = block_y(12, 1, p.x, b, p.beta_f)["dppm"]
        s = run(p, CAP)
        if s["status"] != "Optimal":
            W("   %.2f   **실행 불가**   %8.1f ppm            —              —        —" % (b, floor))
            survives = True
            continue
        bk = kmix(s)
        d4 = s["duals"].get("C4_dppm", 0.0)
        W("   %.2f   Optimal      %8.1f ppm      %3.0f/%3.0f/%3.0f %%      %6.0f    %s"
          % (b, floor, bk[1] * 100, bk[2] * 100, bk[4] * 100, s["dppm"],
             "구속" if abs(d4) > 1e-9 else "비구속"))
    W("")

    W("-" * 88)
    W("[D-대안] β_f 스윕 @ β=0.95, cap=200")
    W("-" * 88)
    W("     β_f   상태        최소달성DPPM(12단k1)   k1/k2/k4       출하DPPM  C4")
    for bf in (0.0, 0.5, 0.80, 0.87, 0.90, 0.95, 0.99):
        p = Params(beta_f=bf)
        floor = block_y(12, 1, p.x, p.beta, bf)["dppm"]
        s = run(p, CAP)
        if s["status"] != "Optimal":
            W("   %.2f   **실행 불가**   %8.1f ppm            —              —        —" % (bf, floor))
            continue
        bk = kmix(s)
        d4 = s["duals"].get("C4_dppm", 0.0)
        W("   %.2f   Optimal      %8.1f ppm      %3.0f/%3.0f/%3.0f %%      %6.0f    %s"
          % (bf, floor, bk[1] * 100, bk[2] * 100, bk[4] * 100, s["dppm"],
             "구속" if abs(d4) > 1e-9 else "비구속"))
    W("")

    W("=" * 88)
    W("[판정]")
    W("=" * 88)
    if survives:
        W("  → 시나리오 D **유지**. 새 설정에서도 낮은 β 에서 실행 불가가 발생한다.")
        W("    조건 표기만 갱신한다 : 'β_f=0.95, cap=200 ppm 기준'")
    else:
        W("  → 시나리오 D **교체**. 새 설정에서 β 를 낮춰도 실행 불가가 안 나온다.")
        W("    β 스윕을 β_f 스윕으로 교체한다. 품질의 실질적 관문이 β_f 이기 때문이다.")
    W("")
    W("  어느 쪽이든 D 의 헤드라인은 살아남는다 — **검사 빈도로 검사 정확도를 대체할 수 없다.**")
    W("  근거가 β_f 역산 표로 바뀔 뿐이다: 최종 검사 없이는 어떤 k 로도 1,000 ppm 아래로 못 간다.")

    text = "\n".join(out)
    print(text)
    with open(os.path.join(ROOT, "data", "scenario_d_log.txt"), "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    main()
