# -*- coding: utf-8 -*-
"""
check_degeneracy.py — 최적해의 유일성과 축퇴 검증

배경 (3라운드 T-1 #20)
----------------------
원고는 기준 믹스를 "12단 97.3 % / 16단 2.68 %" 처럼 소수 첫째 자리까지 보고하면서
그 해가 유일한지는 검증하지 않았다. 대체최적해가 존재하면 97.3 이라는 자릿수는
의미가 없고, 결론의 정밀도 주장 전체가 흔들린다.

두 층위를 따로 본다.

  [1] 정수 층위 — k 배정(층수별 검사주기)의 대체최적해
      L 마다 k in {1,2,4} 또는 미사용 → 4^3 = 64 조합을 전수 열거하고
      각각을 순수 LP 로 풀어 최적값에 도달하는 조합이 몇 개인지 센다.

  [2] 연속 층위 — 목적함수 값을 최적값에 고정한 뒤 각 q 의 min/max 를 LP 로 푼다.
      구간 폭이 0 이면 유일해, 아니면 그 폭이 보고 가능한 정밀도의 상한이다.

[1] 의 열거 LP 가 milp.solve 의 정식화와 어긋나면 결과가 무의미하므로,
최적 k 배정을 넣었을 때 milp 의 최적값을 재현하는지 먼저 자가검증한다.
"""

import os
import sys
import itertools
import pulp

from hbm_model import (Params, coefficients, L_SET, K_SET,
                       DEMAND_SEG, DEMAND_WAFER_DIES,
                       H_BONDER, H_TESTER, RHO_BASE)
from milp import solve, DPPM_CAP, BIG

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LOG = os.path.join(ROOT, "data", "degeneracy_log.txt")
_buf = []


def P(s=""):
    print(s)
    _buf.append(s)


def build_lp(coef, sel, H_bond, H_test, segments, wafer_dies, dppm_cap,
             sense=pulp.LpMaximize, name="lp"):
    """sel 로 고정된 (L,k) 집합 위의 순수 LP. milp.solve 의 제약을 그대로 옮긴다."""
    lp = pulp.LpProblem(name, sense)
    q = {key: pulp.LpVariable("q_%d_%d" % key, lowBound=0) for key in sel}
    lp += pulp.lpSum(coef[key]["tau_bond"] * q[key] for key in sel) <= H_bond, "C1a"
    lp += pulp.lpSum(coef[key]["tau_test"] * q[key] for key in sel) <= H_test, "C1b"
    for idx, (L_min, gb_req) in enumerate(segments):
        lp += pulp.lpSum(coef[key]["gb_good"] * q[key]
                         for key in sel if key[0] >= L_min) >= gb_req, "C2_%d" % idx
    lp += pulp.lpSum(coef[key]["e_die"] * q[key] for key in sel) <= wafer_dies, "C3"
    cap = dppm_cap * 1e-6
    lp += pulp.lpSum((coef[key]["p_escape"] - cap * coef[key]["p_ship"]) * q[key]
                     for key in sel) <= 0, "C4"
    return lp, q


def main():
    p = Params()
    coef = coefficients(p)
    H_b, H_t = H_BONDER, H_TESTER
    seg, W = DEMAND_SEG, DEMAND_WAFER_DIES
    A = dict(H_bond=H_b, H_test=H_t, segments=seg, wafer_dies=W, dppm_cap=DPPM_CAP)

    P("=" * 86)
    P("최적해 유일성·축퇴 검증 — 보고 가능한 자릿수의 상한")
    P("=" * 86)

    base = solve(coef, H_b, H_t, segments=seg, wafer_dies=W, dppm_cap=DPPM_CAP)
    Pstar = base["profit"]
    sel_star = sorted(base["q"].keys())
    tot_star = sum(base["q"].values())
    P("  MILP 최적값  : %.10e" % Pstar)
    P("  선택 구성    : %s" % ", ".join("%d단 k=%d" % k for k in sel_star))
    P("")

    # ---- 자가검증 : 열거 LP 가 MILP 최적값을 재현하는가 -------------------
    lp, q = build_lp(coef, sel_star, name="selfcheck", **A)
    lp += pulp.lpSum(coef[k]["profit"] * q[k] for k in sel_star)
    lp.solve(pulp.PULP_CBC_CMD(msg=0))
    got = pulp.value(lp.objective)
    ok = abs(got - Pstar) / Pstar < 1e-9
    P("  [자가검증] 열거 LP 재현값 %.10e  →  %s" % (got, "일치" if ok else "**불일치**"))
    if not ok:
        P("  !! 열거 LP 가 milp.solve 와 다른 문제를 푼다. 이하 결과는 무효다.")
        open(LOG, "w", encoding="utf-8").write("\n".join(_buf))
        return 1
    P("")

    # ---- [1] 정수 층위 : k 배정 전수 열거 --------------------------------
    P("-" * 86)
    P("[1] 정수 층위 — k 배정 4^3 = 64 조합 전수 열거")
    P("-" * 86)
    TOL = 1e-7
    ties, feas = [], 0
    for combo in itertools.product([None] + list(K_SET), repeat=len(L_SET)):
        sel = [(L, k) for L, k in zip(sorted(L_SET), combo) if k is not None]
        if not sel:
            continue
        lp, q = build_lp(coef, sel, name="enum", **A)
        lp += pulp.lpSum(coef[k]["profit"] * q[k] for k in sel)
        st = lp.solve(pulp.PULP_CBC_CMD(msg=0))
        if pulp.LpStatus[st] != "Optimal":
            continue
        feas += 1
        v = pulp.value(lp.objective)
        if v > Pstar * (1 - TOL):
            ties.append((sel, v, {k: q[k].value() for k in sel}))
    P("  실행가능 조합 %d개 / 최적값 도달 조합 **%d개**" % (feas, len(ties)))
    for sel, v, qq in ties:
        tot = sum(qq.values())
        mix = ", ".join("%d단k=%d %.4f %%" % (L, k, 100.0 * qq[(L, k)] / tot)
                        for (L, k) in sel if qq[(L, k)] / tot > 1e-9)
        P("    %-28s 이익 %.10e   %s"
          % (", ".join("%dk%d" % s for s in sel), v, mix))
    # 대체최적해가 "생산 믹스가 다른 해"인지 "쓰이지 않는 구성의 라벨만 다른 해"인지
    # 구분한다. 후자는 y 의 축퇴이지 믹스의 축퇴가 아니며 보고 정밀도를 위협하지 않는다.
    def mixvec(qq):
        tot = sum(qq.values())
        return tuple(sorted((key, round(100.0 * v / tot, 6))
                            for key, v in qq.items() if v / tot > 1e-9))
    mixes = {mixvec(qq) for _, _, qq in ties}
    uniq_int = len(ties) == 1
    uniq_mix = len(mixes) == 1
    if uniq_int:
        P("  → 정수 층위 **유일**")
    elif uniq_mix:
        P("  → 대체최적해 %d개는 전부 **동일한 생산 믹스**를 준다."
          % len(ties))
        P("    차이는 생산량이 0 인 구성에 붙는 k 라벨뿐이다. 즉 y 의 축퇴이지")
        P("    믹스의 축퇴가 아니며, 보고 정밀도를 위협하지 않는다.")
        P("    (제약 Sigma_k y_Lk <= 1 은 미사용 L 의 k 를 고정하지 않는다.)")
    else:
        P("  → **서로 다른 생산 믹스의 대체최적해 %d개**. 자릿수 주장 불가." % len(mixes))
    P("")

    # ---- [2] 연속 층위 : 목적함수 고정 후 각 변수 min/max -----------------
    P("-" * 86)
    P("[2] 연속 층위 — 목적함수를 최적값에 고정하고 각 q 의 가동범위를 푼다")
    P("-" * 86)
    P("  구성            q_min          q_max        비중 min    비중 max     폭")
    widths = []
    for tgt in sel_star:
        rng = []
        for sense in (pulp.LpMinimize, pulp.LpMaximize):
            lp, q = build_lp(coef, sel_star, sense=sense, name="rng", **A)
            lp += q[tgt]
            lp += pulp.lpSum(coef[k]["profit"] * q[k]
                             for k in sel_star) >= Pstar * (1 - TOL), "opt_fix"
            st = lp.solve(pulp.PULP_CBC_CMD(msg=0))
            rng.append(pulp.value(lp.objective) if pulp.LpStatus[st] == "Optimal" else None)
        lo, hi = rng
        s_lo, s_hi = 100.0 * lo / tot_star, 100.0 * hi / tot_star
        widths.append(s_hi - s_lo)
        P("  %d단 k=%d   %12.4e  %12.4e   %8.4f %%  %8.4f %%  %8.5f %%p"
          % (tgt[0], tgt[1], lo, hi, s_lo, s_hi, s_hi - s_lo))
    wmax = max(widths)
    P("")
    P("  최대 폭 %.6f %%p" % wmax)
    if wmax < 5e-4:
        P("  → 연속 층위 **유일**. 소수 둘째 자리까지 보고 가능하다.")
    elif wmax < 5e-2:
        P("  → 폭이 0.05 %%p 미만. 소수 첫째 자리 보고는 정당하다.")
    else:
        P("  → 폭이 %.3f %%p. **이 자릿수 아래는 보고하지 말 것.**" % wmax)
    P("")
    P("=" * 86)
    verdict = ("유일" if uniq_int else
               ("라벨 축퇴만 존재(믹스는 유일)" if uniq_mix else "믹스 축퇴"))
    P("[판정] 정수 층위 %s / 연속 층위 최대 폭 %.6f %%p" % (verdict, wmax))
    P("  보고 권장 정밀도 : %s"
      % ("소수 첫째 자리" if wmax < 5e-2 else "정수 자리"))
    P("=" * 86)
    open(LOG, "w", encoding="utf-8").write("\n".join(_buf))
    print("\n[저장] data/degeneracy_log.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())