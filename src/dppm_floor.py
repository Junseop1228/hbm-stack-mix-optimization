# -*- coding: utf-8 -*-
"""
dppm_floor.py — 출하 DPPM 하한의 일반 닫힌형과 층수 무의존성

배경
----
종전에는 하한을 MILP 이분탐색으로 구했고, 닫힌형은 k=1, β=1 특수해만 알고 있었다.
그런데 일반 (L, k, β, β_f) 에 대해 두 줄로 닫힌형이 나오며, 더 중요하게는
**하한이 층수 L 에 거의 무의존**이다.

유도
----
층 i 의 결함은 i 이상의 검사 지점에서만 검출된다. L = nk 라 하고 블록
b = ⌈i/k⌉ 로 묶으면, 블록 b 의 남은 검사 기회는 m = n − b + 1 이다.

  Σ_{i∈블록 b} x^(i−1)(1−x) = x^((b−1)k) (1 − x^k)

s = n − b + 1 로 치환하면 (b−1)k = L − sk 이므로

  p_escape = (1−β_f)(1−x^k) · x^L · Σ_{s=1..n} r^s ,   r = (1−β) / x^k     … (1)

  DPPM_floor = 10^6 · Q/(1+Q) ,   Q = p_escape / x^L = (1−β_f)(1−x^k) Σ r^s   … (2)

**Q 는 L 을 n = L/k 로만 포함한다.** r < 1 이면 등비급수가 수렴하므로

  Q(L→∞) = (1−β_f)(1−x^k) · r/(1−r)                                        … (3)

즉 하한은 L 에 대해 상수로 수렴한다. 8단이든 16단이든 같은 값이다.

구조적 함의
-----------
(1) 에서 s=1 항, 즉 **최상단 블록(상단 k개 층)** 이 지배적이다. 이 층들은
검사 기회가 구조적으로 1회뿐이기 때문이다. 종전 서술("한 번 놓친 불량은
이후에도 같은 확률로 놓친다")은 검출 실패가 상관된 모델의 설명이며 본 모델의
독립 가정과 어긋난다. **하한의 진짜 원인은 상단 블록의 기회 부족이다.**

따라서 escape 는 상단에 집중되고 조기 폐기 이득은 하단에서 최대이므로,
**최적 검사 스케줄은 균일 주기가 아니라 위로 갈수록 촘촘해야 한다.**
균일 주기(가정 3)의 기회비용은 다중 주기 허용만으로 측정할 수 없다.

산출물: data/dppm_floor_log.txt
"""

import os
import sys

from hbm_model import block_y, L_SET, K_SET, Params

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def q_exact(L, k, x, beta, beta_f):
    """식 (2) 의 Q — 유한 n. 해석식과 기계정밀도로 일치해야 한다."""
    n = L // k
    r = (1.0 - beta) / (x ** k)
    s = sum(r ** j for j in range(1, n + 1))
    return (1.0 - beta_f) * (1.0 - x ** k) * s


def q_asymptotic(k, x, beta, beta_f):
    """식 (3) — L 무의존 극한."""
    r = (1.0 - beta) / (x ** k)
    if r >= 1.0:
        return float("inf")
    return (1.0 - beta_f) * (1.0 - x ** k) * r / (1.0 - r)


def floor_ppm(q):
    return 1e6 * q / (1.0 + q)


def top_block_share(L, k, x, beta, beta_f):
    """최상단 블록(s=1)이 escape 에서 차지하는 비중."""
    n = L // k
    r = (1.0 - beta) / (x ** k)
    tot = sum(r ** j for j in range(1, n + 1))
    return r / tot if tot > 0 else 0.0


def main():
    out = []
    P = out.append
    p = Params()
    x = p.x

    P("=" * 82)
    P("출하 DPPM 하한 — 일반 닫힌형과 층수 무의존성")
    P("=" * 82)
    P("Q = (1−β_f)(1−x^k) Σ_{s=1..L/k} r^s ,  r = (1−β)/x^k ,  DPPM = 1e6·Q/(1+Q)")
    P("")

    # ── 1. 닫힌형 대 해석식 (기계정밀도) ──────────────────────
    P("[1] 닫힌형 대 Block Y 해석식 — 전 조합 대조")
    P("   L  k    β    β_f │  닫힌형 ppm    해석식 ppm     상대오차")
    worst = 0.0
    for L in L_SET:
        for k in K_SET:
            for beta, bf in ((0.95, 0.0), (0.95, 0.95), (0.84, 0.95), (0.99, 0.95)):
                cf = floor_ppm(q_exact(L, k, x, beta, bf))
                an = block_y(L, k, x, beta, bf)["dppm"]
                rel = abs(cf - an) / max(an, 1e-12)
                worst = max(worst, rel)
                P("  %2d %2d  %.2f  %.2f │ %11.3f  %11.3f   %.2e"
                  % (L, k, beta, bf, cf, an, rel))
    P("")
    P("  최대 상대오차 %.2e → %s" % (worst, "일치 (기계정밀도)" if worst < 1e-9 else "불일치"))
    P("")

    # ── 2. 층수 무의존성 ──────────────────────────────────────
    P("[2] ★ 층수 무의존성 — 같은 k 에서 L 을 바꿔도 하한이 거의 같다")
    P("      (x=%.3f, β=0.95, β_f=0 — 최종 검사 없는 경우)" % x)
    P("   k │    L=8       L=12      L=16   │  L→∞ 극한   │ L=8~16 편차")
    for k in K_SET:
        vals = [floor_ppm(q_exact(L, k, x, 0.95, 0.0)) for L in L_SET]
        lim = floor_ppm(q_asymptotic(k, x, 0.95, 0.0))
        spread = (max(vals) - min(vals)) / lim * 100
        P("  %2d │ %8.1f  %8.1f  %8.1f  │ %8.1f    │  %.3f %%"
          % (k, vals[0], vals[1], vals[2], lim, spread))
    P("")
    P("  L 은 등비급수의 항 수 n = L/k 로만 들어오고, r < 1 이므로 급수가 수렴한다.")
    P("  따라서 하한은 L 에 대해 상수로 수렴한다.")
    P("")
    P("  ★ 이것이 본 연구의 헤드라인 수치 중 유일하게 파라미터 구조에서 직접 나오는")
    P("    결과다. 나머지(병목 전환점, knee, 임계 a)는 특정 파라미터 점에서의 값이다.")
    P("")

    # ── 3. 상단 블록 지배 ────────────────────────────────────
    P("[3] ★ 하한의 원인 — 최상단 블록의 검사 기회 부족")
    P("      상단 k개 층은 검사 지점이 1회뿐이므로 escape 가 거기 집중된다.")
    P("   L  k │ 최상단 블록이 escape 에서 차지하는 비중")
    for L in L_SET:
        for k in K_SET:
            P("  %2d %2d │  %6.2f %%" % (L, k, top_block_share(L, k, x, 0.95, 0.0) * 100))
    P("")
    P("  종전 서술 \"한 번 놓친 불량은 이후 검사에서도 같은 확률로 놓친다\" 는")
    P("  검출 실패가 상관된 모델의 설명이며, 본 모델의 독립 가정 (1−β)^m 과 어긋난다.")
    P("  독립이면 기회가 늘수록 escape 는 지수적으로 감소하므로 그 설명은 하한을")
    P("  설명하지 못한다. 진짜 원인은 상단 블록의 기회 부족이다.")
    P("")

    # ── 4. 12단 k=1 상세 분해 ────────────────────────────────
    P("[4] 12단 k=1, β=0.95, β_f=0 층별 기여 분해")
    P("   층 i │ 검사 기회 m │  escape 기여      누적 비중")
    n = 12
    terms = []
    for i in range(1, 13):
        m = 12 - i + 1
        c = x ** (i - 1) * (1 - x) * (0.05 ** m)
        terms.append((i, m, c))
    tot = sum(c for _, _, c in terms)
    acc = 0.0
    for i, m, c in reversed(terms):
        acc += c
        P("  %3d  │     %2d      │  %.6e    %6.2f %%" % (i, m, c, acc / tot * 100))
        if acc / tot > 0.9999:
            break
    P("")
    P("  최상단 1개 층이 %.1f %% 를 차지한다." % (terms[-1][2] / tot * 100))
    P("  p_escape = %.6e , p_ship = %.6f → %.1f ppm" % (tot, x ** 12 + tot,
                                                        tot / (x ** 12 + tot) * 1e6))
    P("")

    # ── 5. 비균일 스케줄의 여지 ──────────────────────────────
    P("[5] 구조적 함의 — 균일 주기 제약의 진짜 기회비용")
    P("  escape 는 상단에 집중되고 조기 폐기 이득은 하단에서 최대다.")
    P("  따라서 최적 검사 스케줄은 위로 갈수록 촘촘해야 한다.")
    P("  종전 VII-H 는 '층수당 다중 주기 허용' 만 측정했고 '비균일 위치' 는")
    P("  시험하지 않았으므로, '라인 운영 현실 반영 비용 1.5 %% 이내' 라는 주장은")
    P("  균일-주기 계열 안에서만 유효하다. 범위를 명시해야 한다.")

    text = "\n".join(out)
    print(text)
    with open(os.path.join(ROOT, "data", "dppm_floor_log.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    return 0 if worst < 1e-9 else 1


if __name__ == "__main__":
    sys.exit(main())
