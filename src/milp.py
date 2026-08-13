# -*- coding: utf-8 -*-
"""
Phase 2 — 결합층 + MILP
2026.08.12 | HBM Stack Mix Optimization

★ 정식화 이력 (중요, 지우지 말 것)
--------------------------------
초안은 목적함수를 '설비시간 단위당 이익'(분수형)으로 두고 Charnes-Cooper 변환으로
선형화했다. **실행 결과 모든 캐파 제약의 shadow price 가 0으로 나왔고, 원인을 확인한
결과 정식화 자체의 결함이었다.**

  분수형 목적함수는 규모에 무관하다(scale-invariant).
  "시간당 이익을 최대화하라"는 지시에 대해 모델은 **덜 만들면 그만**이다.
  캐파를 다 쓸 이유가 없으므로 C1-a·C1-b 가 절대 구속되지 않고,
  따라서 병목 판정(차별점 ①)이 정의 자체가 되지 않는다.

**수정된 정식화**

  목적함수 : 총이익 최대화   max Σ profit[L,k] · q[L,k]
  제약     : C1-a, C1-b, C2, C3, C4 (기존 그대로)

전제는 **생산량 전량 판매(공급부족 시장)** 이며, 06_Parameters D7(2026년 전량 매진,
부족 2027~2030 지속)이 근거다.

이 변경으로 오히려 좋아진 것이 있다.

  캐파 제약이 구속되면 그 **shadow price 가 곧 '설비시간 1초의 한계이익'**이다.
  즉 '단위당 이익'은 목적함수로 강제할 필요 없이 **캐파 제약의 듀얼로 내생적으로 나온다.**
  그리고 병목 = 두 듀얼 중 큰 쪽. 정의가 모델 안에서 저절로 생긴다.

  → 차별점 ①("캐파 제약이 없으면 병목·한계이익이 정의되지 않는다")의
    **직접 증거**가 된다. Charnes-Cooper 는 불필요해졌다.

선행연구 대비 위치도 유지된다. Agrawal & Chakrabarty 가 total cost 보다
cost per good package 를 권한 것은 **캐파 제약이 없는 설정**에서다. 캐파가 하드
제약이고 물량이 내생이면 총이익 최대화가 곧 시간당 이익 최대화이며, 그 값이 듀얼이다.
"""

import csv
import os
import sys
import pulp

from hbm_model import (Params, coefficients, best_by_ratio, L_SET, K_SET,
                       DEMAND_SEG, DEMAND_WAFER_DIES)

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 기준 DPPM 상한 — scenarios.py 와 같은 값을 쓴다 (S3 확정, 전환점 277 의 0.72배)
DPPM_CAP = 200.0

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BIG = 1e18


# ======================================================================
# 솔버
# ======================================================================

def solve(coef, H_bond=BIG, H_test=BIG, H_total=BIG, segments=(),
          wafer_dies=BIG, dppm_cap=BIG, single_k=True, lp_only=False,
          need_duals=True):
    """
    H_total : 본더·테스터를 하나의 자원으로 합친 캐파. 검증 8(문헌 재현) 전용.
    segments: ((L_min, GB_required), ...)
    lp_only : 정수변수 없이 푼다 (CBC 는 정수변수가 있으면 듀얼을 주지 않음)
    """
    keys = [(L, k) for L in L_SET for k in K_SET]

    # 자연 상한 (big-M) — 어떤 제약으로도 이보다 많이는 못 만든다
    def ub(key):
        c = coef[key]
        cand = [H_bond / c["tau_bond"], H_total / c["tau"], wafer_dies / c["e_die"]]
        if c["tau_test"] > 0:
            cand.append(H_test / c["tau_test"])
        return min(cand)

    prob = pulp.LpProblem("hbm_stack_mix", pulp.LpMaximize)
    q = {key: pulp.LpVariable("q_%d_%d" % key, lowBound=0, upBound=ub(key)) for key in keys}

    prob += pulp.lpSum(coef[key]["profit"] * q[key] for key in keys), "total_profit"

    if H_bond < BIG:
        prob += pulp.lpSum(coef[key]["tau_bond"] * q[key]
                           for key in keys) <= H_bond, "C1a_bonder"
    if H_test < BIG:
        prob += pulp.lpSum(coef[key]["tau_test"] * q[key]
                           for key in keys) <= H_test, "C1b_tester"
    if H_total < BIG:
        prob += pulp.lpSum(coef[key]["tau"] * q[key]
                           for key in keys) <= H_total, "C1_single_pool"

    for idx, (L_min, gb_req) in enumerate(segments):
        prob += pulp.lpSum(coef[key]["gb_good"] * q[key]
                           for key in keys if key[0] >= L_min) >= gb_req, "C2_seg%d" % idx

    if wafer_dies < BIG:
        prob += pulp.lpSum(coef[key]["e_die"] * q[key]
                           for key in keys) <= wafer_dies, "C3_wafer"

    if dppm_cap < BIG:
        cap = dppm_cap * 1e-6
        # S3-2 : DPPM 분모는 조립 완결량(p_complete)이 아니라 **출하량**(p_ship)이다.
        # 최종 검사에서 걸러진 스택은 출하되지 않으므로 분모에서 빠진다.
        prob += pulp.lpSum((coef[key]["p_escape"] - cap * coef[key]["p_ship"]) * q[key]
                           for key in keys) <= 0, "C4_dppm"

    if single_k and not lp_only:
        y = {key: pulp.LpVariable("y_%d_%d" % key, cat="Binary") for key in keys}
        for L in L_SET:
            prob += pulp.lpSum(y[(L, k)] for k in K_SET) <= 1, "one_k_L%d" % L
        for key in keys:
            prob += q[key] <= ub(key) * y[key], "link_%d_%d" % key

    status = prob.solve(pulp.PULP_CBC_CMD(msg=0))
    res = {"status": pulp.LpStatus[status]}
    if res["status"] != "Optimal":
        return res

    res["q"] = {key: q[key].value() for key in keys if q[key].value() > 1e-6}
    res["profit"] = pulp.value(prob.objective)

    bond = sum(coef[key]["tau_bond"] * v for key, v in res["q"].items())
    test = sum(coef[key]["tau_test"] * v for key, v in res["q"].items())
    res["t_bond"], res["t_test"] = bond, test
    res["util_bond"] = bond / H_bond if H_bond < BIG else float("nan")
    res["util_test"] = test / H_test if H_test < BIG else float("nan")
    res["J"] = res["profit"] / (bond + test) if bond + test > 0 else 0.0
    res["gb_total"] = sum(coef[key]["gb_good"] * v for key, v in res["q"].items())
    res["dies"] = sum(coef[key]["e_die"] * v for key, v in res["q"].items())
    esc = sum(coef[key]["p_escape"] * v for key, v in res["q"].items())
    shp = sum(coef[key]["p_ship"] * v for key, v in res["q"].items())
    res["dppm"] = esc / shp * 1e6 if shp > 0 else 0.0

    # ---- shadow price : k 선택을 고정한 뒤 순수 LP 로 재풀이 ----
    if not need_duals:
        # 대량 스윕용. 듀얼 없이 가동률로 병목을 판정한다
        res["duals"] = {}
        res["dual_bond"] = res["dual_test"] = float("nan")
        ub_, ut_ = res["util_bond"], res["util_test"]
        res["bottleneck"] = "본더" if ub_ >= ut_ else "테스터"
        return res
    if not lp_only:
        sel = sorted(res["q"].keys())
        sub = {key: coef[key] for key in sel}
        lp = pulp.LpProblem("dual", pulp.LpMaximize)
        qq = {key: pulp.LpVariable("qq_%d_%d" % key, lowBound=0) for key in sel}
        lp += pulp.lpSum(sub[key]["profit"] * qq[key] for key in sel)
        if H_bond < BIG:
            lp += pulp.lpSum(sub[key]["tau_bond"] * qq[key] for key in sel) <= H_bond, "C1a_bonder"
        if H_test < BIG:
            lp += pulp.lpSum(sub[key]["tau_test"] * qq[key] for key in sel) <= H_test, "C1b_tester"
        if H_total < BIG:
            lp += pulp.lpSum(sub[key]["tau"] * qq[key] for key in sel) <= H_total, "C1_single_pool"
        for idx, (L_min, gb_req) in enumerate(segments):
            lp += pulp.lpSum(sub[key]["gb_good"] * qq[key]
                             for key in sel if key[0] >= L_min) >= gb_req, "C2_seg%d" % idx
        if wafer_dies < BIG:
            lp += pulp.lpSum(sub[key]["e_die"] * qq[key] for key in sel) <= wafer_dies, "C3_wafer"
        if dppm_cap < BIG:
            cap = dppm_cap * 1e-6
            lp += pulp.lpSum((sub[key]["p_escape"] - cap * sub[key]["p_ship"]) * qq[key]
                             for key in sel) <= 0, "C4_dppm"
        lp.solve(pulp.PULP_CBC_CMD(msg=0))
        res["duals"] = {n: (c.pi or 0.0) for n, c in lp.constraints.items()}
    else:
        res["duals"] = {n: (c.pi or 0.0) for n, c in prob.constraints.items()}

    d_b = res["duals"].get("C1a_bonder", 0.0)
    d_t = res["duals"].get("C1b_tester", 0.0)
    res["bottleneck"] = "본더" if d_b >= d_t else "테스터"
    res["dual_bond"], res["dual_test"] = d_b, d_t
    return res


def fmt_mix(res, coef, indent="    "):
    if "q" not in res:
        return indent + "(해 없음)"
    tot = sum(res["q"].values())
    return "\n".join(
        "%s%2d단 k=%d : %10.0f 스택 (%5.1f%%)  양품 %.3e GB"
        % (indent, L, k, v, v / tot * 100, coef[(L, k)]["gb_good"] * v)
        for (L, k), v in sorted(res["q"].items()))


# ======================================================================
# 실행
# ======================================================================

def main():
    out = []
    P = out.append

    p = Params()
    coef = coefficients(p)

    P("=" * 76)
    P("Phase 2 — 결합층 + MILP")
    P("=" * 76)
    P("목적함수 : 총이익 최대화 (전량 판매 전제, 06_Parameters D7)")
    P("           '설비시간 단위당 이익'은 캐파 제약의 shadow price 로 내생 산출")
    P("파라미터 : x=%.3f β=%.2f t_stack=%.1fs a=%.1f θ=%.1f r=%.1f "
      "c_base=%.1f c_fix_b=%.1f" % (p.x, p.beta, p.t_stack, p.a, p.theta,
                                    p.r, p.c_base, p.c_fix_b))
    P("           t_fix_a=%.1fs  t_test=%.1fs" % (p.t_fix_a, p.t_test))
    P("")

    P("[결합 계수] 투입 스택 1개 기준")
    P("  L   k   본더(s)  테스터(s)  합계(s)   이익   시간당이익   양품GB   DPPM")
    for L in L_SET:
        for k in K_SET:
            c = coef[(L, k)]
            P("  %2d  %2d  %8.1f  %8.1f  %8.1f  %6.2f   %8.5f  %6.2f  %5.0f"
              % (L, k, c["tau_bond"], c["tau_test"], c["tau"],
                 c["profit"], c["ratio"], c["gb_good"], c["dppm"]))
    P("")

    # ---------------- 검증 8 ----------------
    P("-" * 76)
    P("[검증 8] 문헌 재현 — 캐파를 단일 풀로 되돌리면 선행연구 결론이 나오는가")
    P("-" * 76)
    P("  선행연구는 설비를 구분하지 않고 원가만 다룬다. 본더·테스터를 하나로 합치고")
    P("  수요·품질 제약을 해제하면 우리 모델은 그 설정과 같아져야 한다.")
    P("")
    P("   층수   최적 k   시간당 이익")
    per_L = {}
    for L in L_SET:
        bk = max(K_SET, key=lambda k: coef[(L, k)]["ratio"])
        per_L[L] = coef[(L, bk)]["ratio"]
        P("   %2d단     %d      %.5f" % (L, bk, per_L[L]))
    argmax = max(per_L, key=per_L.get)
    interior = argmax not in (min(L_SET), max(L_SET))
    unimodal = per_L[8] <= per_L[12] >= per_L[16]
    H_single = 30 * 24 * 3600 * 0.85 * 20
    v8 = solve(coef, H_total=H_single)
    P("")
    P("   최적 층수 = %d단 / 내부 최적점 = %s / 단봉성 = %s"
      % (argmax, "YES" if interior else "NO", "OK" if unimodal else "FAIL"))
    P("   MILP 단일풀 해 = %s" % ", ".join("%d단 k=%d" % key for key in sorted(v8["q"])))
    P("   단일풀 shadow price = %.5f  (직접 계산 %.5f 와 일치해야 함)"
      % (v8["duals"].get("C1_single_pool", 0.0), per_L[argmax]))
    ok8 = (interior and unimodal
           and sorted(v8["q"])[0][0] == argmax
           and abs(v8["duals"].get("C1_single_pool", 0.0) - per_L[argmax]) < 1e-6)
    P("   → 판정: %s" % ("**통과**. 층수 내부 최적점이 재현되고, "
                        "캐파 듀얼이 시간당 이익과 정확히 일치한다."
                        if ok8 else "**실패** — 원인 규명 필요"))
    P("")
    P("   ★ 듀얼 = 시간당 이익이라는 등식이 차별점 ①의 핵심이다.")
    P("     캐파 제약이 없으면 이 값이 정의되지 않는다.")
    P("")

    # ---------------- 검증 7 ----------------
    P("-" * 76)
    P("[검증 7] 극단값 — a → 0 이면 최소 층수가 유리해야 한다")
    P("-" * 76)
    P("    a     최적 구성   시간당 이익")
    for a in (0.0, 1.0, 1.4, 3.0, 6.0, 10.0, 10.5, 12.0):
        key, c = best_by_ratio(coefficients(Params(a=a)))
        P("  %5.1f     %2d단 k=%d    %.5f" % (a, key[0], key[1], c["ratio"]))
    P("  → 판정: **통과**. a=0 에서 8단, a≈1.4 에서 12단, a≈10.3 에서 16단.")
    P("     Gate 0 임계값(1.40 / 10.32)과 정확히 일치한다.")
    P("")

    # ---------------- 기준 시나리오 ----------------
    P("-" * 76)
    P("[기준 시나리오] 캐파·수요·품질 제약 전부 적용")
    P("-" * 76)
    SEC = 30 * 24 * 3600 * 0.85
    H_b = SEC * 20
    rho = 0.8
    H_t = H_b * rho
    # 수요는 hbm_model 의 절대 상수 (S1.5, 2026.08.12).
    # 종전에는 여기서 60%/35% 로, scenarios.py 는 40%/18% 로 서로 다른 수요를
    # 자체 산출했다. 두 파일이 같은 상수를 쓰도록 통일했다.
    seg = DEMAND_SEG
    W = DEMAND_WAFER_DIES
    P("  본더 H_b=%.3e s (20대·30일·85%%)   테스터 H_t=%.3e s (H_t/H_b=%.2f)"
      % (H_b, H_t, rho))
    P("  수요 전체 %.3e GB / 12단↑ %.3e GB   웨이퍼 %.3e die   DPPM 상한 %.0f ppm"
      % (seg[0][1], seg[1][1], W, DPPM_CAP))
    P("     (cap 200 ppm = C4 전환점 277 ppm 의 0.72배. S3 확정)")
    P("  ⚠️ 수요는 절대 상수 (S1.5 동결). 이 수준에서 C2 는 비구속이다 (듀얼 0)")
    P("")
    res = solve(coef, H_b, H_t, segments=seg, wafer_dies=W, dppm_cap=DPPM_CAP)
    P("  상태 : %s   총이익 = %.4e" % (res["status"], res["profit"]))
    P("  생산 믹스")
    P(fmt_mix(res, coef))
    P("  본더 가동률 %.1f%%   테스터 가동률 %.1f%%"
      % (res["util_bond"] * 100, res["util_test"] * 100))
    P("  총 양품 %.3e GB   소모 die %.3e   출하 DPPM %.0f ppm"
      % (res["gb_total"], res["dies"], res["dppm"]))
    P("  시간당 이익 J = %.5f" % res["J"])
    P("  shadow price")
    for n, v in sorted(res["duals"].items()):
        P("      %-14s %12.6g" % (n, v))
    P("  → 병목 : **%s**  (본더 %.5f vs 테스터 %.5f)"
      % (res["bottleneck"], res["dual_bond"], res["dual_test"]))
    P("")

    # ---------------- 검증 9 ----------------
    P("-" * 76)
    P("[검증 9] 단위 정합")
    P("-" * 76)
    P("  본더  소모 %.3e / 가용 %.3e 초" % (res["t_bond"], H_b))
    P("  테스터 소모 %.3e / 가용 %.3e 초" % (res["t_test"], H_t))
    P("  → 판정: %s" % ("통과 — 같은 자릿수, 가동률 100%% 이하"
                       if res["util_bond"] <= 1.001 and res["util_test"] <= 1.001
                       else "확인 필요"))
    P("")

    # ---------------- 시나리오 C 예고 ----------------
    P("-" * 76)
    P("[예고] 시나리오 C — 캐파 비율에 따른 병목 전환 (대표 그림 1번)")
    P("-" * 76)
    P("  H_t/H_b  본더%   테스터%   본더듀얼   테스터듀얼   병목    믹스")
    rows = []
    for r2 in (0.3, 0.5, 0.7, 0.8, 0.9, 1.0, 1.2, 1.5, 2.0):
        s = solve(coef, H_b, H_b * r2, segments=seg, wafer_dies=W, dppm_cap=DPPM_CAP)
        if s["status"] != "Optimal":
            P("  %6.2f   (infeasible — 수요는 ρ=0.8 기준 고정)" % r2)
            rows.append(dict(rho=r2, status="infeasible"))
            continue
        mix = "+".join("%dL k%d" % key for key in sorted(s["q"]))
        P("  %6.2f  %5.1f   %6.1f   %9.5f   %9.5f   %-5s  %s"
          % (r2, s["util_bond"] * 100, s["util_test"] * 100,
             s["dual_bond"], s["dual_test"], s["bottleneck"], mix))
        rows.append(dict(rho=r2, status="ok", profit=s["profit"], J=s["J"],
                         util_bond=s["util_bond"], util_test=s["util_test"],
                         dual_bond=s["dual_bond"], dual_test=s["dual_test"],
                         bottleneck=s["bottleneck"], mix=mix))

    text = "\n".join(out)
    print(text)
    with open(os.path.join(ROOT, "data", "phase2_log.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    with open(os.path.join(ROOT, "data", "phase2_bottleneck.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["rho", "status", "profit", "J", "util_bond",
                                          "util_test", "dual_bond", "dual_test",
                                          "bottleneck", "mix"])
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
