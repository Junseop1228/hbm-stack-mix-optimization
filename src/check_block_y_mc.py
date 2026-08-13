# -*- coding: utf-8 -*-
"""
check_block_y_mc.py — Block Y 일반식의 독립 검증 (이벤트 몬테카를로)

배경
----
기존 검증(1~6)은 k=1, β=1 특수해의 닫힌형 대조뿐이었다.
`(1-β)^m` 분기가 들어간 **일반 (L, k, β) 식은 검증된 적이 없다.**

"조기 폐기가 닫힌형을 가지므로 사건 몬테카를로는 중복 계산"이라는 종전 판단은
**추정을 위한 중복**과 **검증을 위한 독립 경로**를 혼동한 것이다.
후자는 중복이 아니라 유일한 교차검증 수단이다.

방법
----
해석식을 전혀 참조하지 않고 적층 과정을 층 단위로 시뮬레이션한다.

  층 i 적층 → (아직 무결점이면) 확률 (1-x) 로 결함 발생
           → i 가 검사 지점이면 검사 1회, 결함 보유 시 확률 β 로 검출 → 즉시 폐기
  L 층까지 미검출 → 결함 보유면 escape, 무결점이면 양품

비교 대상: E[layer], E[test], p_good, p_escape
판정: |해석식 − MC| 가 MC 표준오차의 4배 이내
"""

import math
import os
import random
import sys

from hbm_model import block_y, L_SET, K_SET

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

N = 400_000
SEED = 20260812


def simulate(L, k, x, beta, beta_f, n=N, seed=SEED):
    """해석식을 참조하지 않는 층 단위 시뮬레이션."""
    rnd = random.Random(seed)
    s_layer = s_layer2 = 0.0
    s_test = s_test2 = 0.0
    n_good = n_escape = 0

    for _ in range(n):
        defective = False
        discarded = False
        layers = 0
        tests = 0
        for i in range(1, L + 1):
            layers = i
            if not defective and rnd.random() >= x:
                defective = True          # 층 i 에서 결함 발생
            if i % k == 0:                # 검사 지점
                tests += 1
                if defective and rnd.random() < beta:
                    discarded = True
                    break
        if not discarded:
            if defective:
                # 최종 검사에서 추가로 걸러진다 (가정 4)
                if rnd.random() >= beta_f:
                    n_escape += 1
            else:
                n_good += 1
        s_layer += layers; s_layer2 += layers * layers
        s_test += tests;   s_test2 += tests * tests

    def stat(s, s2):
        m = s / n
        v = max(0.0, s2 / n - m * m)
        return m, math.sqrt(v / n)

    e_layer, se_layer = stat(s_layer, s_layer2)
    e_test, se_test = stat(s_test, s_test2)
    p_good = n_good / n
    p_escape = n_escape / n
    return {
        "e_layer": e_layer, "se_layer": se_layer,
        "e_test": e_test, "se_test": se_test,
        "p_good": p_good, "se_good": math.sqrt(p_good * (1 - p_good) / n),
        "p_escape": p_escape, "se_escape": math.sqrt(max(p_escape, 1e-12) * (1 - p_escape) / n),
    }


def main():
    out = []
    P = out.append
    P("=" * 84)
    P("Block Y 일반식 독립 검증 — 이벤트 몬테카를로 (%s회, seed=%d)" % (f"{N:,}", SEED))
    P("=" * 84)
    P("판정 기준 : |해석식 - MC| <= 4 x SE")
    P("")

    cases = [(L, k, x, b, bf)
             for L in L_SET for k in K_SET
             for (x, b, bf) in ((0.965, 0.95, 0.0), (0.940, 0.84, 0.95), (0.990, 0.99, 0.95))]

    fails = []
    P("  L  k    x     β    β_f │      E[layer]              E[test]           p_escape")
    P("                          │  해석식 / MC (±4SE)   해석식 / MC        해석식 / MC")
    P("  " + "-" * 80)
    for L, k, x, b, bf in cases:
        a = block_y(L, k, x, b, bf)
        m = simulate(L, k, x, b, bf)
        row = []
        for key, tol_key in (("e_layer", "se_layer"), ("e_test", "se_test"),
                             ("p_escape", "se_escape"), ("p_good", "se_good")):
            diff = abs(a[key] - m[key])
            tol = 4 * m[tol_key] + 1e-9
            if diff > tol:
                fails.append((L, k, x, b, bf, key, a[key], m[key], tol))
            row.append("OK" if diff <= tol else "FAIL")
        P("  %2d %2d  %.3f %.2f %.2f │ %8.4f/%8.4f  %7.4f/%7.4f  %.5f/%.5f  %s"
          % (L, k, x, b, bf, a["e_layer"], m["e_layer"], a["e_test"], m["e_test"],
             a["p_escape"], m["p_escape"], " ".join(row)))

    P("")
    if fails:
        P("!! 불일치 %d건" % len(fails))
        for f in fails:
            P("   L=%d k=%d x=%.3f β=%.2f β_f=%.2f  %s  해석 %.6f vs MC %.6f (허용 %.6f)" % f)
    else:
        P("★ 전 케이스 통과 (%d 조합 x 4 지표 = %d 항목)" % (len(cases), len(cases) * 4))
        P("  일반 (L, k, β, β_f) 식이 해석식과 독립된 경로로 재현됐다.")
        P("  종전 검증은 k=1, β=1 특수해뿐이었으므로 이것이 첫 일반식 검증이다.")

    text = "\n".join(out)
    print(text)
    with open(os.path.join(ROOT, "data", "block_y_mc_verify_log.txt"), "w",
              encoding="utf-8") as f:
        f.write(text)
    return len(fails)


if __name__ == "__main__":
    sys.exit(1 if main() else 0)
