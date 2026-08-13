# -*- coding: utf-8 -*-
"""
S-1A 추가 : single_k 가 대표 결과 ②(x 스윕에서 16단 0%→100%)에도 영향하는가
2026.08.12

배경
----
반증 테스트에서 single_k 를 풀면 **16단이 사라졌다**(32%→0%, C4 유무 무관).
그렇다면 Phase 3 대표 결과 ②("x 가 0.955→0.980 이면 16단 비중 0%→100%")가
층수당 단일 주기 제약의 산물일 가능성이 있다. 대표 그림 2번의 근거이므로
확인 없이 넘어가면 안 된다.

방법 : 시나리오 A(x 스윕)를 single_k True / False 로 각각 돌려 16단 비중을 대조한다.
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run(p, single_k=True):
    return solve(coefficients(p), SC.H_B, SC.H_B * SC.RHO_BASE,
                 segments=SC.SEG, wafer_dies=SC.WAFER,
                 dppm_cap=SC.DPPM_CAP, single_k=single_k, need_duals=False)


def sh(res):
    if res["status"] != "Optimal":
        return None
    tot = sum(res["q"].values())
    byL = {L: 0.0 for L in L_SET}
    for (L, k), v in res["q"].items():
        byL[L] += v / tot
    return byL


def main():
    out = []
    W = out.append
    W("=" * 88)
    W("S-1A 추가 : 대표 결과 ②가 single_k 의 산물인가")
    W("=" * 88)
    W("")
    W("            single_k=True (현행)          single_k=False (해제)")
    W("     x      8단   12단   16단        8단   12단   16단")
    W("-" * 88)
    rows = []
    for x in [0.940, 0.950, 0.955, 0.960, 0.965, 0.970, 0.975, 0.980, 0.985, 0.990]:
        a = sh(run(Params(x=x), True))
        b = sh(run(Params(x=x), False))
        fa = ("%5.0f%% %5.0f%% %5.0f%%" % (a[8] * 100, a[12] * 100, a[16] * 100)
              if a else "    infeasible    ")
        fb = ("%5.0f%% %5.0f%% %5.0f%%" % (b[8] * 100, b[12] * 100, b[16] * 100)
              if b else "    infeasible    ")
        W("  %.3f   %s      %s" % (x, fa, fb))
        rows.append((x, a, b))
    W("")
    W("=" * 88)
    W("[판정]")
    W("=" * 88)
    hi_true = [r for r in rows if r[1] and r[1][16] > 0.99]
    hi_false = [r for r in rows if r[2] and r[2][16] > 0.99]
    W("  16단 100% 도달 구간")
    W("    single_k=True  : %s"
      % (", ".join("x=%.3f" % r[0] for r in hi_true) if hi_true else "없음"))
    W("    single_k=False : %s"
      % (", ".join("x=%.3f" % r[0] for r in hi_false) if hi_false else "없음"))
    W("")
    if hi_false:
        W("  → 대표 결과 ②는 single_k 와 무관하게 성립한다. 층수 경제성이 실제 원인이다.")
    else:
        W("  → **경고. 16단 지배가 single_k 해제 시 사라진다.**")
        W("    대표 결과 ②와 대표 그림 2번이 모델링 선택의 산물일 수 있다.")
        W("    01_Spec 8.2 한계에 명시하고, single_k 의 실무적 정당화를 보강해야 한다.")

    text = "\n".join(out)
    print(text)
    with open(os.path.join(ROOT, "data", "single_k_xsweep_log.txt"),
              "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    main()
