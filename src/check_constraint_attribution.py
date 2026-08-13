# -*- coding: utf-8 -*-
"""
S-1 : 제품 믹스 발생 원인 분해
2026.08.12 | HBM Stack Mix Optimization

목적
----
notes/08_Handoff 3.6 / 07_Results 3절 의 "제품 믹스를 만드는 것은 품질 제약(C4)이다"
라는 귀속이 옳은지 검증한다. 기존 보고는 **전체 해제 대 전체 적용**을 비교하고
차이를 C4 하나에 몰아 귀속시켰다. 통제 변수를 분리하지 않은 오류다.

방법
----
기준선(scenarios.py 조건)에서 C1a·C1b·C2·C4 를 하나씩 끄고(leave-one-out),
또 하나씩만 켜서(only-one) 각 제약이 **층수 믹스**와 **검사 주기**에 각각
무엇을 하는지 분리한다.

C3(웨이퍼)는 항상 켠다. 캐파를 풀면 상한이 사라져 발산하기 때문이며,
C3 를 통제 상수로 두어야 나머지 4개의 효과가 비교 가능해진다.

파라미터는 손대지 않는다. 현행 기준선에서 귀속만 바로잡는 작업이다.
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


def run(c1a=True, c1b=True, c2=True, c4=True):
    return solve(COEF,
                 H_bond=H_B if c1a else BIG,
                 H_test=H_T if c1b else BIG,
                 segments=SEG if c2 else (),
                 wafer_dies=WAFER,
                 dppm_cap=CAP if c4 else BIG)


def digest(res):
    """층수 믹스 / 검사주기 / 구속 제약을 한 줄로."""
    if res["status"] != "Optimal":
        return dict(status=res["status"])
    tot = sum(res["q"].values())
    byL = {L: 0.0 for L in L_SET}
    byK = {k: 0.0 for k in K_SET}
    for (L, k), v in res["q"].items():
        byL[L] += v / tot
        byK[k] += v / tot
    binding = [n for n, v in res["duals"].items() if abs(v) > 1e-9]
    return dict(status="Optimal",
                nL=sum(1 for L in L_SET if byL[L] > 1e-4),
                nK=sum(1 for k in K_SET if byK[k] > 1e-4),
                byL=byL, byK=byK,
                mix=" + ".join("%d단k%d %.0f%%" % (L, k, v / tot * 100)
                               for (L, k), v in sorted(res["q"].items())),
                binding=binding,
                duals=res["duals"],
                dppm=res["dppm"])


def line(tag, d):
    if d["status"] != "Optimal":
        return "  %-22s %s" % (tag, d["status"])
    return ("  %-22s L종수%d K종수%d   %-6s/%-6s/%-6s  %-6s/%-6s/%-6s  %6.0f ppm   %s"
            % (tag, d["nL"], d["nK"],
               "%.0f%%" % (d["byL"][8] * 100), "%.0f%%" % (d["byL"][12] * 100),
               "%.0f%%" % (d["byL"][16] * 100),
               "%.0f%%" % (d["byK"][1] * 100), "%.0f%%" % (d["byK"][2] * 100),
               "%.0f%%" % (d["byK"][4] * 100),
               d["dppm"], ",".join(sorted(d["binding"]))))


def main():
    out = []
    W = out.append

    W("=" * 100)
    W("S-1 : 제품 믹스 발생 원인 분해 — 제약별 귀속 검증")
    W("=" * 100)
    W("기준선 : x=%.3f β=%.2f a=%.1f θ=%.1f  H_t/H_b=%.2f  cap=%.0f ppm"
      % (P.x, P.beta, P.a, P.theta, SC.RHO_BASE, CAP))
    W("         SEG 전체 %.3e GB / 12단↑ %.3e GB   WAFER %.3e die"
      % (SEG[0][1], SEG[1][1], WAFER))
    W("C3(웨이퍼)는 전 케이스 상시 적용 — 캐파 해제 시 발산 방지용 통제 상수")
    W("")
    W("  케이스                 종수         층수 배분(8/12/16)      주기 배분(k1/k2/k4)   출하DPPM  구속제약")

    # ---------------- 기준선 ----------------
    base = digest(run())
    W("-" * 100)
    W("[A] 전체 제약 적용 (기준선)")
    W(line("all on", base))
    W("")

    # ---------------- leave-one-out ----------------
    W("-" * 100)
    W("[B] 하나씩 끄기 — 그 제약이 없으면 무엇이 사라지는가")
    loo = {}
    for tag, kw in (("−C4 (품질)", dict(c4=False)),
                    ("−C2 (수요)", dict(c2=False)),
                    ("−C1b (테스터)", dict(c1b=False)),
                    ("−C1a (본더)", dict(c1a=False))):
        d = digest(run(**kw))
        loo[tag] = d
        W(line(tag, d))
    W("")

    # ---------------- only-one ----------------
    W("-" * 100)
    W("[C] 하나씩만 켜기 — 그 제약 단독으로 믹스를 만들 수 있는가")
    only = {}
    for tag, kw in (("C4 단독", dict(c1a=False, c1b=False, c2=False)),
                    ("C2 단독", dict(c1a=False, c1b=False, c4=False)),
                    ("C1a+C1b 단독", dict(c2=False, c4=False)),
                    ("C1b 단독", dict(c1a=False, c2=False, c4=False)),
                    ("C1a 단독", dict(c1b=False, c2=False, c4=False)),
                    ("전부 해제 (C3만)", dict(c1a=False, c1b=False,
                                          c2=False, c4=False))):
        d = digest(run(**kw))
        only[tag] = d
        W(line(tag, d))
    W("")

    # ---------------- 판정 ----------------
    W("=" * 100)
    W("[판정]")
    W("=" * 100)

    d4 = loo["−C4 (품질)"]
    if d4["status"] == "Optimal":
        W("1) C4 를 끄면 층수 종수 %d → %d, 주기 배분 %s → %s"
          % (base["nL"], d4["nL"],
             "k1 %.0f/k2 %.0f/k4 %.0f" % tuple(base["byK"][k] * 100 for k in K_SET),
             "k1 %.0f/k2 %.0f/k4 %.0f" % tuple(d4["byK"][k] * 100 for k in K_SET)))
        W("   → C4 가 바꾸는 것은 %s"
          % ("주기(k)와 층수 둘 다" if d4["nL"] != base["nL"] else "주기(k)뿐. 층수 종수 불변"))
    d12 = only["C1a+C1b 단독"]
    if d12["status"] == "Optimal":
        W("2) 캐파 2제약만으로 층수 종수 %d 확보 여부 : %s (믹스 = %s)"
          % (d12["nL"], "가능" if d12["nL"] >= 2 else "불가", d12["mix"]))
    dall = only["전부 해제 (C3만)"]
    if dall["status"] == "Optimal":
        W("3) 전부 해제 시 : %s  (구속 = %s)"
          % (dall["mix"], ",".join(sorted(dall["binding"]))))
        W("   → 기존 보고가 이 케이스와 [A]를 직접 비교하고 차이를 C4 에 귀속시켰다.")
    W("")
    W("[듀얼 — 기준선]")
    for n, v in sorted(base["duals"].items()):
        W("    %-14s %14.6g   %s" % (n, v, "구속" if abs(v) > 1e-9 else "-"))

    text = "\n".join(out)
    print(text)
    with open(os.path.join(ROOT, "data", "constraint_attribution_log.txt"),
              "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    main()
