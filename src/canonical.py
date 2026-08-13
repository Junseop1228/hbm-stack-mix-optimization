# -*- coding: utf-8 -*-
"""
canonical.py — 정본 수치를 단일 JSON 으로 확정한다

배경
----
2라운드 심사에서 T-1 스테일 항목 24건이 지적됐고, 심사자 진단은 이렇다.

  "24개 중 절반 이상이 '숫자는 스크립트가 갱신했지만 산문은 사람이 갱신하지
   않았다' 는 하나의 원인에서 나온다."

실제로 그랬다. 예컨대 총이익을 기계 치환할 때 가수(1.0866 → 9.4182)만 바꾸고
지수(10^7)를 남겨 값이 8.7배로 부풀었다. 사람이 관리하는 체크리스트로는 막을 수
없는 종류의 오류다.

해결
----
파이프라인이 정본 수치를 **하나의 JSON** 으로 확정하고, 원고(논문 HTML·문서 MD)의
숫자를 그 JSON 과 기계적으로 대조한다(`check_manuscript.py`).

  data/*  (로그·CSV)  →  canonical.py  →  data/canonical_results.json
                                              ↓
                          check_manuscript.py ← paper/*.html, docs/*.md

이 스크립트는 로그를 파싱하지 않는다. **모델을 직접 재실행해 값을 얻는다.**
로그 파싱은 형식 변경에 취약하고, 무엇보다 로그 자체가 낡았을 때 낡은 값을
정본으로 승격시키기 때문이다.

산출물: data/canonical_results.json
"""

import json
import math
import os
import sys

from hbm_model import (Params, coefficients, block_y, L_SET, K_SET,
                       DEMAND_SEG, DEMAND_WAFER_DIES,
                       H_BONDER, H_TESTER, RHO_BASE, DPPM_CAP, N_BONDER)
from milp import solve
import scenarios as SC

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def r(v, n=6):
    return None if v is None else round(float(v), n)


def sig(v, n=4):
    """유효숫자 n 자리 문자열 + 가수/지수 분리. 지수 누락 오류를 원천 차단한다."""
    if v == 0:
        return {"value": 0.0, "mantissa": "0", "exponent": 0, "text": "0"}
    e = int(math.floor(math.log10(abs(v))))
    m = v / (10 ** e)
    return {"value": float(v), "mantissa": ("%%.%df" % (n - 1)) % m,
            "exponent": e, "text": ("%%.%df e%%+d" % (n - 1)) % (m, e)}


def build():
    p = Params()
    coef = coefficients(p)
    H_b, rho, H_t = H_BONDER, RHO_BASE, H_TESTER

    out = {
        "_meta": {
            "generated_by": "src/canonical.py",
            "purpose": "원고의 모든 수치는 이 파일과 일치해야 한다. "
                       "check_manuscript.py 가 대조한다.",
            "note": "값은 로그 파싱이 아니라 모델 재실행으로 얻는다.",
        },
        "parameters": {
            "x": p.x, "beta": p.beta, "beta_f": p.beta_f,
            "phi_final": p.phi_final, "a": p.a, "theta": p.theta,
            "t_stack_s": p.t_stack, "t_test_s": r(p.t_test, 3),
            "t_final_s": r(p.t_final, 3), "t_fix_a_s": r(p.t_fix_a, 3),
            "r": p.r, "c_base": p.c_base, "c_fix_b": p.c_fix_b,
            "c_test": p.c_test, "gb_per_layer": p.gb_per_layer,
            "phi_final_dist": [1.0, 3.0, 10.0],
            "phi_final_baseline_rationale":
                "미확보. 분포 최소값을 기준으로 두어 M1 정정 효과를 하한으로 보고한다.",
        },
        "instance": {
            "H_bonder_s": sig(H_b), "H_tester_s": sig(H_t),
            "rho_baseline": rho,
            "bonders": N_BONDER, "days": 30, "uptime": 0.85,
            "wafer_dies": sig(DEMAND_WAFER_DIES),
            "demand_seg_GB": {str(L): sig(D) for L, D in DEMAND_SEG},
            "demand_seg_ratio": r(DEMAND_SEG[1][1] / DEMAND_SEG[0][1], 4),
            "dppm_cap": DPPM_CAP,
            "J_definition": "J = (총이익) / (Σ τ_bond·q + Σ τ_test·q). "
                            "분모는 두 설비의 실사용 시간 합이며 가용 시간이 아니다.",
        },
    }

    # ── 기준 시나리오 ────────────────────────────────────────
    s = solve(coef, H_b, H_t, segments=DEMAND_SEG,
              wafer_dies=DEMAND_WAFER_DIES, dppm_cap=DPPM_CAP)
    tot = sum(s["q"].values())
    mix = {("%dL_k%d" % k_): r(v / tot * 100, 2) for k_, v in sorted(s["q"].items())}
    out["baseline"] = {
        "status": s["status"],
        "mix_percent": mix,
        "total_profit": sig(s["profit"]),
        "J": r(s["J"], 5),
        "util_bonder_pct": r(s["util_bond"] * 100, 1),
        "util_tester_pct": r(s["util_test"] * 100, 1),
        "bottleneck": s["bottleneck"],
        "outgoing_dppm": r(s["dppm"], 1),
        "good_GB": sig(s["gb_total"]),
        "dies_used": sig(s["dies"]),
        "duals": {k_: r(v, 6) for k_, v in sorted(s["duals"].items())},
        "binding": sorted(k_ for k_, v in s["duals"].items() if abs(v) > 1e-9),
    }

    # ── 검증 8 (단일 풀) ────────────────────────────────────
    per_L = {L: max(coef[(L, k)]["ratio"] for k in K_SET) for L in L_SET}
    arg = max(per_L, key=per_L.get)
    v8 = solve(coef, H_total=H_b)
    out["check8"] = {
        "best_L": arg,
        "interior_optimum": arg not in (min(L_SET), max(L_SET)),
        "unimodal": per_L[8] <= per_L[12] >= per_L[16],
        "single_pool_dual": r(v8["duals"].get("C1_single_pool", 0.0), 5),
        "direct_ratio": r(per_L[arg], 5),
        "ratio_per_L": {str(L): r(v, 5) for L, v in per_L.items()},
    }

    # ── DPPM 하한 (구조적 결과) ─────────────────────────────
    def q_exact(L, k, x, beta, bf):
        n = L // k
        rr = (1.0 - beta) / (x ** k)
        return (1.0 - bf) * (1.0 - x ** k) * sum(rr ** j for j in range(1, n + 1))

    floor = {}
    for bf, tag in ((0.0, "no_final_test"), (0.95, "beta_f_0.95")):
        floor[tag] = {}
        for k in K_SET:
            vals = {str(L): r(1e6 * q_exact(L, k, p.x, p.beta, bf)
                              / (1 + q_exact(L, k, p.x, p.beta, bf)), 1)
                    for L in L_SET}
            floor[tag]["k%d" % k] = vals
    out["dppm_floor"] = {
        "closed_form": "Q = (1-beta_f)(1-x^k) * sum_{s=1..floor(L/k)} rr^s, "
                       "rr = (1-beta)/x^k ;  DPPM = 1e6 * Q/(1+Q)",
        "values": floor,
        "L_independent": True,
        "top_block_share_pct": r(
            ((1 - p.beta) / p.x ** 1) / sum(((1 - p.beta) / p.x ** 1) ** j
                                            for j in range(1, 13)) * 100, 2),
    }

    # ── 층별 구성의 하한 (N6 — C4 blending 유도) ────────────
    blend = {}
    for (L, k) in ((12, 2), (16, 4)):
        qv = q_exact(L, k, p.x, p.beta, p.beta_f)
        blend["%dL_k%d" % (L, k)] = r(1e6 * qv / (1 + qv), 1)
    lo, hi = blend["12L_k2"], blend["16L_k4"]
    w = (DPPM_CAP - lo) / (hi - lo)
    out["c4_blending"] = {
        "floor_per_config_ppm": blend,
        "cap_ppm": DPPM_CAP,
        "predicted_16L_share_pct": r(w * 100, 2),
        "note": "C4 는 합산 제약이므로 두 구성의 하한을 cap 으로 블렌딩하면 "
                "16단 비중이 예측된다. baseline mix 와 대조하라.",
    }

    # ── Block Y 9조합 ───────────────────────────────────────
    out["block_y"] = {
        "%dL_k%d" % (L, k): {
            "e_layer": r(block_y(L, k, p.x, p.beta, p.beta_f)["e_layer"], 4),
            "e_test": r(block_y(L, k, p.x, p.beta, p.beta_f)["e_test"], 4),
            "p_good": r(block_y(L, k, p.x, p.beta, p.beta_f)["p_good"], 6),
            "dppm": r(block_y(L, k, p.x, p.beta, p.beta_f)["dppm"], 1),
        } for L in L_SET for k in K_SET
    }

    # ── 외부 로그에서 가져와야 하는 값 (재계산 비용이 큰 것) ──
    out["_external"] = {
        "note": "아래는 별도 스크립트의 산출물이다. 해당 로그가 갱신되면 "
                "이 절도 갱신해야 한다. check_manuscript 는 이 값들도 대조한다.",
        "sources": {
            "transition_curve": "data/fig1_transition_curve.csv",
            "monte_carlo": "data/phase3_log.txt",
            "nonuniform": "data/nonuniform_schedule.csv",
            "evppi": "data/robustness_evppi_log.txt",
            "phi_final_sweep": "data/final_test_sweep_log.txt",
        },
    }
    return out


def attach_external(out):
    """CSV·로그에서 파싱해야 하는 값을 붙인다."""
    import csv, re
    D = os.path.join(ROOT, "data")

    # 병목 전환점 궤적
    f = os.path.join(D, "fig1_transition_curve.csv")
    if os.path.exists(f):
        rows = [x for x in csv.DictReader(open(f, encoding="utf-8"))
                if x["transition_Ht_over_Hb"]]
        tr = {x["dppm_cap"]: r(float(x["transition_Ht_over_Hb"]), 4) for x in rows}
        vals = sorted({v for v in tr.values()})
        plateau = max(tr.values(), key=lambda v: sum(1 for u in tr.values() if u == v))
        knee = min((float(c) for c, v in tr.items() if v == plateau), default=None)
        out["transition"] = {"by_cap": tr, "plateau": plateau, "knee_ppm": knee,
                             "at_cap_200": tr.get("200")}

    # 몬테카를로
    f = os.path.join(D, "phase3_log.txt")
    if os.path.exists(f):
        t = open(f, encoding="utf-8").read()
        mc = {}
        m = re.search(r"실행 (\d+)회 중 실행가능 (\d+)회 \(([\d.]+)%\)", t)
        if m:
            mc["draws"] = int(m.group(1)); mc["feasible"] = int(m.group(2))
            mc["feasible_pct"] = float(m.group(3))
        for lab, key in (("8단 비중", "share_8"), ("12단 비중", "share_12"),
                         ("16단 비중", "share_16")):
            m = re.search(re.escape(lab) + r"\s+([\d.]+)%\s+\[([\d.]+)%, ([\d.]+)%\]", t)
            if m:
                mc[key] = {"median": float(m.group(1)),
                           "ci90": [float(m.group(2)), float(m.group(3))]}
        m = re.search(r"시간당 이익 J\s+([\d.]+)\s+\[([\d.]+), ([\d.]+)\]", t)
        if m:
            mc["J"] = {"median": float(m.group(1)),
                       "ci90": [float(m.group(2)), float(m.group(3))]}
        m = re.search(r"병목=테스터 확률\s+([\d.]+)%", t)
        if m:
            mc["p_bottleneck_tester_pct"] = float(m.group(1))
        # 상관계수
        corr = {}
        for line in t.split("\n"):
            m = re.match(r"\s+(x|theta|phi_final|beta_f|beta|rho|a|r|c_base|c_test|c_fix_b)"
                         r"\s+([+-][\d.]+)\s+([+-][\d.]+)\s+([+-][\d.]+)\s*$", line)
            if m:
                corr[m.group(1)] = {"share_16": float(m.group(2)),
                                    "profit_per_s": float(m.group(3)),
                                    "tester_bottleneck": float(m.group(4))}
        if corr:
            mc["correlation"] = corr
        out["monte_carlo"] = mc

    # 비균일 스케줄
    f = os.path.join(D, "nonuniform_schedule.csv")
    if os.path.exists(f):
        rows = list(csv.DictReader(open(f, encoding="utf-8")))
        nu = {}
        for L in (8, 12, 16):
            sub = [x for x in rows if int(x["L"]) == L]
            if not sub:
                continue
            base = [x for x in sub if int(x["m"]) == L][0]
            bd = float(base["dppm"])
            cand = [x for x in sub if float(x["dppm"]) <= bd * 1.001]
            mm = min(cand, key=lambda x: int(x["m"]))
            nu[str(L)] = {"uniform_k1_tests": L, "floor_ppm": r(bd, 1),
                          "min_tests": int(mm["m"]),
                          "positions": mm["positions"].replace("|", ","),
                          "tester_time_saving_pct": r((1 - int(mm["m"]) / L) * 100, 1)}
        gains = [(x, (float(x["uniform_dppm"]) - float(x["dppm"]))
                  / float(x["uniform_dppm"]) * 100)
                 for x in rows if x["uniform_dppm"]]
        if gains:
            best = max(gains, key=lambda g: g[1])
            nu["max_dppm_gain_pct"] = r(best[1], 2)
            nu["max_gain_case"] = "L=%s m=%s" % (best[0]["L"], best[0]["m"])
        out["nonuniform_schedule"] = nu

    # EVPPI
    f = os.path.join(D, "robustness_evppi_log.txt")
    if os.path.exists(f):
        t = open(f, encoding="utf-8").read()
        ev = {}
        for line in t.split("\n"):
            m = re.match(r"\s+(x|theta|phi_final|beta_f|beta|r|c_base|c_test|c_fix_b|a)"
                         r"\s+│\s+([+-][\d.]+)\s+([+-][\d.]+) %", line)
            if m:
                ev[m.group(1)] = r(float(m.group(2)), 6)
        if ev:
            out["evppi"] = {"values": ev,
                            "noise_floor": r(max(0.0, -min(ev.values())), 6)}

    # φ_f 임계값
    f = os.path.join(D, "final_test_sweep_log.txt")
    if os.path.exists(f):
        m = re.search(r"임계 φ_f = ([\d.]+)", open(f, encoding="utf-8").read())
        if m:
            out["phi_final_threshold"] = r(float(m.group(1)), 4)
    return out


def main():
    out = attach_external(build())
    path = os.path.join(ROOT, "data", "canonical_results.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    n = json.dumps(out, ensure_ascii=False)
    print("정본 수치 확정 → data/canonical_results.json  (%.1f KB)" % (len(n.encode()) / 1024))
    print()
    b = out["baseline"]
    print("  기준 시나리오")
    print("    믹스        : %s" % ", ".join("%s %.1f%%" % (k, v)
                                            for k, v in b["mix_percent"].items()))
    print("    총이익      : %s  (지수 %d — 기계 치환 시 지수 누락 방지)"
          % (b["total_profit"]["text"], b["total_profit"]["exponent"]))
    print("    J           : %s" % b["J"])
    print("    가동률      : 본더 %s%% / 테스터 %s%%"
          % (b["util_bonder_pct"], b["util_tester_pct"]))
    print("    병목        : %s" % b["bottleneck"])
    print("    구속 제약   : %s" % ", ".join(b["binding"]))
    print("    H_b / H_t   : %s / %s 초"
          % (out["instance"]["H_bonder_s"]["text"], out["instance"]["H_tester_s"]["text"]))
    print()
    c = out["c4_blending"]
    print("  C4 blending 예측 16단 비중 : %.2f %%  (baseline 실측과 대조)"
          % c["predicted_16L_share_pct"])
    print("  검증 8 : 최적 %d단 / 내부최적점 %s / 듀얼 %s = 직접계산 %s"
          % (out["check8"]["best_L"], out["check8"]["interior_optimum"],
             out["check8"]["single_pool_dual"], out["check8"]["direct_ratio"]))
    ext = [k for k in ("transition", "monte_carlo", "nonuniform_schedule",
                       "evppi", "phi_final_threshold") if k in out]
    print("  외부 산출물 연결 : %s" % ", ".join(ext))


if __name__ == "__main__":
    main()
