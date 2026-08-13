# -*- coding: utf-8 -*-
"""
S-1A : 발견 2 반증 테스트 — 8단의 등장은 single_k 제약의 부산물인가
2026.08.12

가설
----
C4 가 k2 비중을 밀어올릴 때, 층수마다 검사 주기를 하나만 고를 수 있으므로
(single_k) 늘어난 k2 물량을 받을 새 층수가 필요해지고 그 자리를 8단이 떠맡는다.

반증 방법
--------
single_k=False 로 풀면 같은 층수가 k2 와 k4 를 동시에 가질 수 있다.

  8단이 사라지고 12단k2 + 12단k4 형태가 나온다  → 가설 확증
  8단이 그대로 남는다                          → 가설 기각

single_k=False 이면 이진변수가 없어 순수 LP 가 된다(milp.solve 참조).
"""

import os
import sys

from hbm_model import Params, coefficients, L_SET, K_SET
from milp import solve, BIG
import scenarios as SC

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

P = Params()
COEF = coefficients(P)
H_B = SC.H_B
H_T = SC.H_B * SC.RHO_BASE
SEG = SC.SEG
WAFER = SC.WAFER
CAP = SC.DPPM_CAP


def run(single_k=True, c1a=True, c1b=True, c2=True, c4=True):
    return solve(COEF,
                 H_bond=H_B if c1a else BIG,
                 H_test=H_T if c1b else BIG,
                 segments=SEG if c2 else (),
                 wafer_dies=WAFER,
                 dppm_cap=CAP if c4 else BIG,
                 single_k=single_k)


def report(tag, res, W):
    if res["status"] != "Optimal":
        W("  %-28s %s" % (tag, res["status"]))
        return None
    tot = sum(res["q"].values())
    byL = {L: 0.0 for L in L_SET}
    byK = {k: 0.0 for k in K_SET}
    for (L, k), v in res["q"].items():
        byL[L] += v / tot
        byK[k] += v / tot
    mix = " + ".join("%d단k%d %.0f%%" % (L, k, v / tot * 100)
                     for (L, k), v in sorted(res["q"].items()))
    binding = [n for n, v in res["duals"].items() if abs(v) > 1e-9]
    W("  %-28s %s" % (tag, mix))
    W("  %-28s   층수 8/12/16 = %.0f/%.0f/%.0f %%   주기 k1/k2/k4 = %.0f/%.0f/%.0f %%"
      % ("", byL[8] * 100, byL[12] * 100, byL[16] * 100,
         byK[1] * 100, byK[2] * 100, byK[4] * 100))
    W("  %-28s   DPPM %.0f   이익 %.4e   구속 %s"
      % ("", res["dppm"], res["profit"], ",".join(sorted(binding))))
    W("")
    return dict(byL=byL, byK=byK, mix=mix, profit=res["profit"],
                n8=byL[8], nvar=len(res["q"]))


def main():
    out = []
    W = out.append

    W("=" * 92)
    W("S-1A : 발견 2 반증 테스트 — single_k 해제")
    W("=" * 92)
    W("기준선 : x=%.3f β=%.2f a=%.1f θ=%.1f  H_t/H_b=%.2f  cap=%.0f ppm"
      % (P.x, P.beta, P.a, P.theta, SC.RHO_BASE, CAP))
    W("")
    W("-" * 92)
    W("[1] 전체 제약 + C4 적용")
    W("-" * 92)
    on = report("single_k=True  (현행)", run(True), W)
    off = report("single_k=False (해제)", run(False), W)

    W("-" * 92)
    W("[2] C4 해제 — 대조군")
    W("-" * 92)
    report("single_k=True,  −C4", run(True, c4=False), W)
    report("single_k=False, −C4", run(False, c4=False), W)

    W("=" * 92)
    W("[판정]")
    W("=" * 92)
    if on and off:
        W("  single_k=True  일 때 8단 비중 : %.1f%%" % (on["n8"] * 100))
        W("  single_k=False 일 때 8단 비중 : %.1f%%" % (off["n8"] * 100))
        W("")
        if off["n8"] < 1e-4:
            W("  → **가설 확증.** single_k 를 풀면 8단이 사라진다.")
            W("    8단의 등장은 층수 경제성이 아니라 층수당 단일 주기 제약의 부산물이다.")
        elif off["n8"] < on["n8"] - 1e-4:
            W("  → **부분 확증.** 8단이 줄지만 완전히 사라지지는 않는다.")
            W("    single_k 가 원인의 일부이며, 다른 요인이 함께 작동한다.")
        else:
            W("  → **가설 기각.** single_k 를 풀어도 8단이 남는다.")
            W("    8단 등장에는 다른 이유가 있다. 문서에 확정 서술로 넣으면 안 된다.")
        W("")
        W("  이익 비교 : single_k=True %.6e / False %.6e  (해제 시 %+.3f%%)"
          % (on["profit"], off["profit"],
             (off["profit"] / on["profit"] - 1) * 100))
        W("  비영 변수 개수 : True %d개 / False %d개" % (on["nvar"], off["nvar"]))

    text = "\n".join(out)
    print(text)
    with open(os.path.join(ROOT, "data", "single_k_log.txt"),
              "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    main()
