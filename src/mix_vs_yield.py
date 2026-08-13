# -*- coding: utf-8 -*-
"""
mix_vs_yield.py — 층당 수율 스윕에 따른 생산 믹스 (대표 그림 2번 데이터)
HBM Stack Mix Optimization

층당 접합 수율 x 를 0.9425~0.9900 구간에서 0.0025 간격으로 훑으며
매 지점의 최적 믹스와 **구속 제약 집합**을 함께 기록한다.

구속 제약을 같이 남기는 이유
---------------------------
16단이 등장하는 원인이 구간마다 다르기 때문이다.

  x <= 0.9500       16단 15~44%   C2(수요) 구속 — **수요가 강제한다**
  0.9525 ~ 0.9625   16단 0%       C2 비구속 — 설비 경제성만으로는 못 이긴다
  0.9650 ~ 0.9800   16단 3~80%    전환 구간 — 구속 제약 조합이 계속 바뀐다
  x >= 0.9825       16단 100%     C1a(본더)만 구속 — **경제성이 선택한다**

같은 "16단 등장"이라도 왼쪽 끝과 오른쪽 끝은 원인이 정반대다.
01_Spec 8.3 의 결과 해석 지침("층수 상승이 고객 용량 요구가 강제한 것인지
설비 경제성 때문인지")이 한 그림 안에서 갈리는 지점이며, 마커 채움으로
그림에 직접 인코딩된다 (make_figures.py fig2).

산출물: data/fig2_mix_vs_yield.csv
"""

import os
import sys

from hbm_model import Params, coefficients, L_SET, DEMAND_WAFER_DIES
from milp import solve
import scenarios as SC

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

X_MIN, X_MAX, X_STEP = 0.9425, 0.9905, 0.0025


def sweep():
    rows = []
    x = X_MIN
    while x <= X_MAX:
        r = solve(coefficients(Params(x=x)), SC.H_B, SC.H_B * SC.RHO_BASE,
                  segments=SC.SEG, wafer_dies=DEMAND_WAFER_DIES,
                  dppm_cap=SC.DPPM_CAP)
        if r["status"] == "Optimal":
            tot = sum(r["q"].values())
            by = {L: 0.0 for L in L_SET}
            for (L, k), v in r["q"].items():
                by[L] += v / tot * 100
            binding = sorted(n for n, v in r["duals"].items() if abs(v) > 1e-9)
            rows.append((x, by[8], by[12], by[16], binding))
        x = round(x + X_STEP, 4)
    return rows


def main():
    rows = sweep()
    print("  층당수율    8단     12단    16단   구속 제약")
    for x, a, b, c, bind in rows:
        print("  %.4f  %6.2f  %6.2f  %6.2f   %s"
              % (x, a, b, c, ", ".join(n.replace("_", " ") for n in bind)))

    out = os.path.join(ROOT, "data", "fig2_mix_vs_yield.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        f.write("x,share_8Hi,share_12Hi,share_16Hi,binding\n")
        for x, a, b, c, bind in rows:
            f.write("%.4f,%.2f,%.2f,%.2f,%s\n" % (x, a, b, c, "|".join(bind)))

    s16 = [r[3] for r in rows]
    print("\n[기록] data/fig2_mix_vs_yield.csv — 대표 그림 2번 데이터 (%d점)" % len(rows))
    print("  16단 비중 : 최소 %.1f%% / 최대 %.1f%%" % (min(s16), max(s16)))
    print("  0%% 구간 : %d점 — 설비 경제성만으로는 16단이 선택되지 않는 구간"
          % sum(1 for v in s16 if v < 0.01))


if __name__ == "__main__":
    main()
