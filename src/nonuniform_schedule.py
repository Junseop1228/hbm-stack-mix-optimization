# -*- coding: utf-8 -*-
"""
nonuniform_schedule.py — 비균일 검사 위치의 최적성 (M3 파생 지적)

배경
----
`dppm_floor.py` 에서 escape 가 상단 블록에 집중된다는 것이 드러났다
(최상단 1개 층이 94.8%). 조기 폐기 이득은 반대로 하단에서 최대다.
따라서 최적 검사 스케줄은 균일 주기가 아니라 **위로 갈수록 촘촘해야** 한다.

종전 VII-H 는 '층수당 다중 주기 허용' 만 측정했고 **비균일 위치는 시험하지
않았다.** 이 스크립트가 그 공백을 메운다.

방법
----
검사 위치 집합 S ⊆ {1..L} (L ∈ S 고정) 을 전수 열거한다.
  L=8  : 2^7  =    128
  L=12 : 2^11 =  2,048
  L=16 : 2^15 = 32,768
검사 예산 m = |S| 별로 최적 위치를 찾고 균일 주기와 대조한다.

측정
----
  ① 고정 예산 m 에서 출하 DPPM 을 최소화하는 위치 → 상단 집중 가설 검정
  ② 균일 주기 대비 개선폭 → VII-H 가 놓친 기회비용
  ③ 최적 위치의 상단 편중도 (상반부 검사 수 / 전체)

산출물: data/nonuniform_schedule_log.txt, nonuniform_schedule.csv
"""

import csv
import itertools
import os
import sys

from hbm_model import Params, L_SET, K_SET

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def block_y_positions(L, positions, x, beta, beta_f=0.0):
    """임의 검사 위치 집합에 대한 Block Y. positions 는 정렬된 튜플, L 포함."""
    pos = list(positions)
    m = len(pos)
    p_good = x ** L
    e_layer = p_good * L
    e_test = p_good * m
    p_escape_raw = 0.0

    for i in range(1, L + 1):
        p_i = x ** (i - 1) * (1.0 - x)
        # 층 i 이후(포함)의 검사 지점 인덱스
        j0 = 0
        while j0 < m and pos[j0] < i:
            j0 += 1
        rem = m - j0
        for t in range(1, rem + 1):
            prob = p_i * ((1.0 - beta) ** (t - 1)) * beta
            stop = pos[j0 + t - 1]
            e_layer += prob * stop
            e_test += prob * (j0 + t)          # stop 이하 검사 횟수
        miss = p_i * ((1.0 - beta) ** rem)
        p_escape_raw += miss
        e_layer += miss * L
        e_test += miss * m

    p_escape = p_escape_raw * (1.0 - beta_f)
    p_ship = p_good + p_escape
    return {
        "e_layer": e_layer, "e_test": e_test,
        "p_good": p_good, "p_escape": p_escape, "p_ship": p_ship,
        "dppm": p_escape / p_ship * 1e6 if p_ship > 0 else 0.0,
    }


def enumerate_best(L, x, beta, beta_f):
    """예산 m 별 DPPM 최소 위치. L 은 항상 포함."""
    best = {}
    others = list(range(1, L))
    for r in range(0, L):
        for combo in itertools.combinations(others, r):
            pos = tuple(sorted(combo + (L,)))
            m = len(pos)
            y = block_y_positions(L, pos, x, beta, beta_f)
            cur = best.get(m)
            if cur is None or y["dppm"] < cur[0]["dppm"] - 1e-12:
                best[m] = (y, pos)
    return best


def uniform(L, k, x, beta, beta_f):
    pos = tuple(range(k, L + 1, k))
    return block_y_positions(L, pos, x, beta, beta_f), pos


def top_bias(L, pos):
    """상반부(층 > L/2) 검사 비중."""
    return sum(1 for p in pos if p > L / 2) / len(pos)


def main():
    p = Params()
    x, beta, bf = p.x, p.beta, 0.0     # β_f=0 : 하한 구조를 그대로 보기 위해
    out, rows = [], []
    P = out.append

    P("=" * 86)
    P("비균일 검사 위치의 최적성 — 균일 주기 제약이 실제로 얼마를 잃는가")
    P("=" * 86)
    P("x=%.3f  β=%.2f  β_f=%.2f (하한 구조를 그대로 보기 위해 최종 검사 제외)" % (x, beta, bf))
    P("검사 위치 집합 S ⊆ {1..L}, L ∈ S 고정. 전수 열거.")
    P("")

    for L in L_SET:
        best = enumerate_best(L, x, beta, bf)
        P("─" * 86)
        P("[L = %d단]  열거한 위치 집합 %d개" % (L, 2 ** (L - 1)))
        P("  예산 m │ 최적 위치                       DPPM     E[layer] │ 균일 k  균일 DPPM  개선")
        for m in sorted(best):
            y, pos = best[m]
            uni_txt, uni_dppm, imp = "—", None, ""
            if L % m == 0:
                k = L // m
                if k in K_SET:
                    uy, upos = uniform(L, k, x, beta, bf)
                    uni_txt = "k=%d" % k
                    uni_dppm = uy["dppm"]
                    imp = "%+.2f %%" % ((y["dppm"] - uni_dppm) / uni_dppm * 100)
            P("    %2d   │ %-32s %8.1f  %7.3f  │ %-6s %9s  %s"
              % (m, ",".join(str(v) for v in pos), y["dppm"], y["e_layer"],
                 uni_txt, "%.1f" % uni_dppm if uni_dppm else "—", imp))
            rows.append(dict(L=L, m=m, positions="|".join(map(str, pos)),
                             dppm=round(y["dppm"], 4),
                             e_layer=round(y["e_layer"], 5),
                             uniform_k=(L // m if L % m == 0 and L // m in K_SET else ""),
                             uniform_dppm=round(uni_dppm, 4) if uni_dppm else "",
                             top_half_share=round(top_bias(L, pos), 4)))
        P("")

    # ── 해석 ────────────────────────────────────────────────
    P("=" * 86)
    P("해석")
    P("=" * 86)
    P("[1] ★ 상단 집중 가설 검정")
    P("  고정 예산에서 DPPM 을 최소화하는 위치의 상반부(층 > L/2) 검사 비중:")
    P("   L  m │ 상반부 비중 │ 균일 주기라면")
    for r in rows:
        if r["uniform_k"] == "":
            continue
        L, m, k = r["L"], r["m"], r["uniform_k"]
        upos = tuple(range(k, L + 1, k))
        P("  %2d %2d │   %5.1f %%   │   %5.1f %%"
          % (L, m, r["top_half_share"] * 100, top_bias(L, upos) * 100))
    P("")
    P("  균일 주기는 정의상 상반부 비중이 50 %% 다. 최적 위치가 그보다 높으면")
    P("  '위로 갈수록 촘촘해야 한다' 는 구조적 예측이 확인된다.")
    P("")
    P("[2] ★ 균일 주기 제약의 실제 기회비용 (DPPM 기준)")
    cmp_rows = [r for r in rows if r["uniform_dppm"] != ""]
    if cmp_rows:
        worst = max(cmp_rows, key=lambda r: (r["uniform_dppm"] - r["dppm"]) / r["uniform_dppm"])
        P("  같은 검사 예산에서 최적 위치가 균일 주기보다 DPPM 을 얼마나 낮추는가:")
        for r in cmp_rows:
            gain = (r["uniform_dppm"] - r["dppm"]) / r["uniform_dppm"] * 100
            P("   L=%2d m=%2d  균일 %8.1f → 최적 %8.1f  (%.2f %% 개선)"
              % (r["L"], r["m"], r["uniform_dppm"], r["dppm"], gain))
        P("")
        P("  최대 개선: L=%d, m=%d — %.2f %%"
          % (worst["L"], worst["m"],
             (worst["uniform_dppm"] - worst["dppm"]) / worst["uniform_dppm"] * 100))
    P("")
    P("  종전 VII-H 는 '층수당 다중 주기 허용' 만 측정해 기회비용 0.000 %% 를 얻었고,")
    P("  이는 균일-주기 계열 안에서만 유효한 값이었다. 위치를 풀면 결과가 다르다.")

    # ── [3] 최소 검사 예산 — 하한 도달에 필요한 검사 횟수 ──────
    P("")
    P("[3] ★★ 최소 검사 예산 — 같은 품질을 몇 번의 검사로 달성하는가")
    P("  균일 k=1 은 L 회 검사해 하한에 도달한다. 최적 위치는 몇 회면 되는가?")
    P("  (판정 기준: 하한의 100.1 % 이내)")
    P("   L │ 균일 k=1  하한 DPPM │ 최적 최소 검사수  위치              │ 테스터 시간")
    for L in L_SET:
        base = [r for r in rows if r["L"] == L and r["m"] == L][0]["dppm"]
        cand = [r for r in rows if r["L"] == L and r["dppm"] <= base * 1.001]
        mmin = min(cand, key=lambda r: r["m"])
        P("  %2d │   %2d회    %8.1f │       %2d회        %-18s │  %5.1f %% 절감"
          % (L, L, base, mmin["m"], mmin["positions"].replace("|", ","),
             (1 - mmin["m"] / L) * 100))
    P("")
    P("  ★ 상단에 몰아서 검사하면 균일 매층 검사와 같은 출하 품질을 절반 이하의")
    P("    검사 횟수로 달성한다. 테스터가 병목인 본 모델에서 이는 곧 캐파 확보다.")
    P("    하한의 원인이 상단 층의 검사 기회 부족(dppm_floor.py)이므로, 그 기회를")
    P("    채우는 것이 가장 효율적인 검사 배치다.")
    P("")
    P("  ⚠️ 단 이 결과는 가정 3(균일 주기)을 푼 것이며, 현장이 규칙적 패턴만")
    P("    운용한다는 근거(01_Spec 2.1)와 충돌한다. 실행 가능성은 별도 문제다.")

    text = "\n".join(out)
    print(text)
    with open(os.path.join(ROOT, "data", "nonuniform_schedule_log.txt"), "w",
              encoding="utf-8") as f:
        f.write(text)
    with open(os.path.join(ROOT, "data", "nonuniform_schedule.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["L", "m", "positions", "dppm", "e_layer",
                                          "uniform_k", "uniform_dppm", "top_half_share"])
        w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main()
