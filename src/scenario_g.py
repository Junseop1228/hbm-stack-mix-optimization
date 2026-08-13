# -*- coding: utf-8 -*-
"""
시나리오 G — DPPM 상한 스윕 + 최종 검사(beta_f) 판정
2026.08.12 | S3

구성
----
  S3-1  DPPM 상한 스윕 : 최적 k 의 전환점, 실행 불가 하한 이분탐색
  S3-4  beta_f 역산    : 업계 수준(수백 ppm)을 재현하려면 얼마여야 하는가
  S3-3  beta_f 도입 후 C4 가 여전히 구속되는가

★ S3-3 이 대표 그림 3번의 내용을 정한다.
  C4 가 계속 구속되면  → "검사 빈도로 DPPM 하한을 못 넘는다"가 유지된다
  C4 가 비구속이 되면  → "최종 검사가 있으면 중간 검사의 품질 기여는 미미하고,
                        중간 검사의 존재 이유는 품질이 아니라 조기 폐기다"
  **어느 쪽으로 나오든 결과다. 미리 어느 쪽을 원하지 않는다.**
"""

import os
import sys

from hbm_model import (Params, coefficients, block_y, L_SET, K_SET,
                       DEMAND_SEG, DEMAND_WAFER_DIES)
from milp import solve, BIG
import scenarios as SC

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H_B = SC.H_B
RHO = SC.RHO_BASE


def run(p, cap, rho=RHO, duals=True):
    return solve(coefficients(p), H_B, H_B * rho, segments=DEMAND_SEG,
                 wafer_dies=DEMAND_WAFER_DIES, dppm_cap=cap, need_duals=duals)


def digest(res):
    if res["status"] != "Optimal":
        return None
    tot = sum(res["q"].values())
    byL = {L: 0.0 for L in L_SET}
    byK = {k: 0.0 for k in K_SET}
    for (L, k), v in res["q"].items():
        byL[L] += v / tot
        byK[k] += v / tot
    d4 = res["duals"].get("C4_dppm", 0.0)
    return dict(byL=byL, byK=byK, dppm=res["dppm"], J=res["J"],
                profit=res["profit"], dual_c4=d4, bound=abs(d4) > 1e-9,
                mix=" ".join("%d단k%d:%.0f%%" % (L, k, v / tot * 100)
                             for (L, k), v in sorted(res["q"].items())))


def min_dppm(x, beta, beta_f, L=12):
    """매 층 검사(k=1)에서 달성 가능한 최소 출하 DPPM."""
    return block_y(L, 1, x, beta, beta_f)["dppm"]


def feas_floor(p, lo=1.0, hi=20000.0, n=40):
    """실행 가능해지는 DPPM 상한의 하한선 (이분탐색)."""
    if run(p, hi, duals=False)["status"] != "Optimal":
        return None
    for _ in range(n):
        mid = (lo + hi) / 2
        if run(p, mid, duals=False)["status"] == "Optimal":
            hi = mid
        else:
            lo = mid
    return hi


def main():
    out = []
    W = out.append
    P0 = Params()

    W("=" * 96)
    W("시나리오 G — DPPM 상한 + 최종 검사(beta_f)")
    W("=" * 96)
    W("기준선 : x=%.3f β=%.2f a=%.1f θ=%.1f  H_t/H_b=%.2f" % (P0.x, P0.beta, P0.a, P0.theta, RHO))
    W("수요   : 절대 상수 %.3e / %.3e GB (S1.5 동결). 이 수준에서 C2 는 비구속" % (DEMAND_SEG[0][1], DEMAND_SEG[1][1]))
    W("")

    # ================= S3-4 : beta_f 역산 =================
    W("-" * 96)
    W("[S3-4] beta_f 역산 — 업계 수준을 재현하려면 최종 검사 검출률이 얼마여야 하는가")
    W("-" * 96)
    W("  β=0.95, x=0.965 기준. 각 (L,k) 조합의 최종 검사 前 escape 에서 역산한다.")
    W("")
    W("  목표 DPPM   k=1 에 필요한 β_f   k=2 에 필요한 β_f   k=4 에 필요한 β_f")
    for target in (1000, 500, 300, 200, 100, 50):
        row = "  %6d ppm " % target
        for k in K_SET:
            y = block_y(12, k, P0.x, P0.beta, 0.0)
            e, g = y["p_escape_raw"], y["p_good"]
            # target = e(1-bf)/(g + e(1-bf)) * 1e6  →  (1-bf) = t*g / (e*(1e6 - t))
            t = target
            need = 1.0 - (t * g) / (e * (1e6 - t))
            row += "%18s" % ("%.4f" % need if need > 0 else "불필요")
        W(row)
    W("")
    W("  → **최종 검사 없이는(β_f=0) 어떤 k 로도 1,000 ppm 아래로 못 간다.**")
    W("    12단 k=1 의 최종 검사 前 DPPM 이 %.0f ppm 이기 때문이다."
      % block_y(12, 1, P0.x, P0.beta, 0.0)["dppm"])
    W("")

    # 기준값 채택
    BETA_F = 0.95
    W("  ★ β_f 기준값 채택 : **%.2f**" % BETA_F)
    W("    근거 — 위 역산표에서 k=2(현행 최적)로 수백 ppm 대에 진입하는 구간이며,")
    W("    임의 설정이 아니라 **모델 기반 추정**이다 (01_Spec 8.2 파라미터 공간 프레이밍).")
    W("    범위는 시나리오로 처리한다. 실측 미확보임을 문서에 명시한다.")
    W("")
    W("  β_f 별 달성 가능 최소 DPPM (12단, 매 층 검사)")
    W("     β_f      최소 DPPM")
    for bf in (0.0, 0.5, 0.8, 0.9, 0.95, 0.99):
        W("    %.2f    %9.1f ppm" % (bf, min_dppm(P0.x, P0.beta, bf)))
    W("")

    # ================= S3-1 : DPPM 상한 스윕 =================
    for tag, bf in (("β_f = 0 (최종 검사 없음 — 종전 모델)", 0.0),
                    ("β_f = %.2f (최종 검사 도입)" % BETA_F, BETA_F)):
        p = Params(beta_f=bf)
        W("=" * 96)
        W("[S3-1] DPPM 상한 스윕 — %s" % tag)
        W("=" * 96)
        W("   상한(ppm)   8단  12단  16단    k1   k2   k4   출하DPPM  C4구속  C4듀얼      믹스")
        caps = [100, 200, 300, 500, 800, 1200, 1500, 2000, 3000, 5000, 8000, 12000]
        for cap in caps:
            d = digest(run(p, cap))
            if d is None:
                W("  %8d     ---- 실행 불가 ----" % cap)
                continue
            W("  %8d   %4.0f%% %4.0f%% %4.0f%%  %4.0f%% %4.0f%% %4.0f%%  %8.0f  %-5s %9.4g  %s"
              % (cap, d["byL"][8] * 100, d["byL"][12] * 100, d["byL"][16] * 100,
                 d["byK"][1] * 100, d["byK"][2] * 100, d["byK"][4] * 100,
                 d["dppm"], "구속" if d["bound"] else "비구속",
                 d["dual_c4"], d["mix"]))
        floor = feas_floor(p)
        W("")
        W("  ★ 실행 가능 하한 : DPPM 상한 **%.1f ppm** 미만이면 해가 없다"
          % (floor if floor else float("nan")))

        # ---- S3-3 : C4 구속 여부 ----
        base = digest(run(p, 5000.0))
        W("  ★ 기준 cap 5,000 ppm 에서 C4 : **%s** (듀얼 %.4g, 출하 DPPM %.0f)"
          % ("구속" if base["bound"] else "비구속", base["dual_c4"], base["dppm"]))
        W("")

    # ================= S3-3 판정 =================
    W("=" * 96)
    W("[S3-3] 판정 — 최종 검사 도입 후 C4 가 여전히 구속되는가")
    W("=" * 96)
    p_new = Params(beta_f=BETA_F)
    rows = []
    for cap in (100, 200, 300, 500, 1000, 2000, 5000):
        d = digest(run(p_new, cap))
        rows.append((cap, d))
    W("  β_f = %.2f 에서 cap 별 C4 구속 여부" % BETA_F)
    for cap, d in rows:
        if d is None:
            W("    %6d ppm : 실행 불가" % cap)
        else:
            W("    %6d ppm : %-5s   k1/k2/k4 = %.0f/%.0f/%.0f %%   출하 DPPM %.0f"
              % (cap, "구속" if d["bound"] else "비구속",
                 d["byK"][1] * 100, d["byK"][2] * 100, d["byK"][4] * 100, d["dppm"]))
    bound_any = any(d and d["bound"] for _, d in rows)
    W("")
    if bound_any:
        W("  → **C4 는 여전히 구속된다.** 상한이 낮은 구간에서 k 를 여전히 제약한다.")
        W("    대표 그림 3번의 결론('검사 빈도로 DPPM 하한을 못 넘는다')이 유지된다.")
    else:
        W("  → **C4 가 전 구간에서 비구속이 됐다.**")
        W("    결론이 바뀐다 — 최종 검사가 있으면 중간 검사의 품질 기여는 미미하고,")
        W("    **중간 검사의 존재 이유는 품질이 아니라 조기 폐기에 의한 설비시간 절감이다.**")

    text = "\n".join(out)
    print(text)
    with open(os.path.join(ROOT, "data", "scenario_g_log.txt"), "w", encoding="utf-8") as f:
        f.write(text)


if __name__ == "__main__":
    main()
