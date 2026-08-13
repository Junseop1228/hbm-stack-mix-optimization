# -*- coding: utf-8 -*-
"""
Phase 3 — 시나리오 스윕 + 파라미터 몬테카를로
2026.08.12 | HBM Stack Mix Optimization

목적
----
파라미터가 추정치이므로 점추정 최적해가 목표가 아니다(01_Spec 5절).
**최적 구성이 전환되는 임계 조건**을 규명하고, 파라미터 불확실성 전체를
동시에 흔들었을 때 결론이 얼마나 버티는지를 신뢰구간으로 보고한다.

시나리오 (06_Parameters 7절)
---------------------------
  A  층당 수율 x            → 16단이 유리해지는 임계 x        [차별점 ③]
  B  고정시간 배수 a, θ     → 최적 층수의 이동                [차별점 ②]
  C  캐파 비율 H_t/H_b      → 병목 전환점                     [차별점 ①]
  D  검출률 β               → 최적 주기 k의 전환점
  F  층수 프리미엄 p(L)     → 매출 선형성 가정의 강건성
  MC 전체 동시 흔들기       → 90% 신뢰구간 + 정보가치 분석

몬테카를로는 **파라미터 불확실성**에 대한 것이다. 불량 발생 사건의 MC 가 아니다
(09_Roadmap 6.1.1). 조기 폐기는 닫힌형이라 사건 MC 는 불필요하다.
템플릿: Epoch AI (2026-03-12, CC BY), 01_Spec 5.1
"""

import csv
import math
import os
import random
import sys

from hbm_model import (Params, coefficients, L_SET, K_SET,
                       DEMAND_SEG, DEMAND_WAFER_DIES)
from milp import solve, BIG

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

SEC = 30 * 24 * 3600 * 0.85
H_B = SEC * 20                       # 본더 20대 · 30일 · 가동률 85%
# 기준 DPPM 상한 (2026.08.12 S3 확정)
#   200 ppm = C4 구속/비구속 **전환점 277 ppm 의 0.72배**
#   절대값 자체는 여전히 미확보다. 그래서 전환점 대비 위치로 표기한다.
#   300 ppm 이상이면 C4 가 비구속이 되어 기준선에서 아무 일도 하지 않는다.
#   C2 가 이미 비구속인 상태라 C4 까지 죽으면 제약 5개 중 2개가 장식이 된다.
DPPM_CAP = 200.0
RHO_BASE = 0.9


# ======================================================================
# 공통
# ======================================================================

# 수요는 hbm_model 의 절대 상수를 쓴다 (S1.5, 2026.08.12).
# 종전 make_demand() 는 기준 시나리오를 풀어 그 산출량의 비율로 수요를 만들었다.
# 폐기 근거와 동결 시점은 hbm_model.DEMAND_SEG 주석 참조.
SEG, WAFER = DEMAND_SEG, DEMAND_WAFER_DIES


def run(p: Params, rho=RHO_BASE, duals=True):
    return solve(coefficients(p), H_B, H_B * rho, segments=SEG,
                 wafer_dies=WAFER, dppm_cap=DPPM_CAP, need_duals=duals)


def shares(res):
    """층수별·주기별 생산 비중"""
    if "q" not in res or not res["q"]:
        return {}, {}
    tot = sum(res["q"].values())
    byL = {L: 0.0 for L in L_SET}
    byK = {k: 0.0 for k in K_SET}
    for (L, k), v in res["q"].items():
        byL[L] += v / tot
        byK[k] += v / tot
    return byL, byK


def mixstr(res):
    if "q" not in res or not res["q"]:
        return "-"
    tot = sum(res["q"].values())
    return " ".join("%d단k%d:%.0f%%" % (L, k, v / tot * 100)
                    for (L, k), v in sorted(res["q"].items()))


def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return 0.0
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((v - mx) ** 2 for v in xs))
    sy = math.sqrt(sum((v - my) ** 2 for v in ys))
    if sx == 0 or sy == 0:
        return 0.0
    return sum((a - mx) * (b - my) for a, b in zip(xs, ys)) / (sx * sy)


def pct(vals, q):
    s = sorted(vals)
    if not s:
        return float("nan")
    i = min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))
    return s[i]


# ======================================================================
# 실행
# ======================================================================

def main():
    out = []
    P = out.append
    rows_all = []

    P("=" * 78)
    P("Phase 3 — 시나리오 스윕 + 파라미터 몬테카를로")
    P("=" * 78)
    P("고정 조건 : 본더 H_b=%.3e s / 수요 전체 %.3e GB · 12단↑ %.3e GB"
      % (H_B, SEG[0][1], SEG[1][1]))
    P("           DPPM 상한 %.0f ppm / 기준 H_t/H_b=%.2f" % (DPPM_CAP, RHO_BASE))
    P("           수요는 절대 상수다 (S1.5 동결). 캐파가 변해도 고객 수요는 안 변한다")
    P("           ⚠️ 이 수요 수준에서 C2 는 **비구속**이다 (듀얼 0).")
    P("              01_Spec 1.1 상충 구조의 다섯 번째 힘(고객 용량 요구)이 작동하지 않는다.")
    P("              T5(S3.5)에서 GPU 용량 목표 역산값으로 교체 예정.")
    P("")

    # ---------------- 시나리오 C : 병목 전환점 ----------------
    P("-" * 78)
    P("[시나리오 C] 캐파 비율 H_t/H_b — 병목 전환점        ★ 차별점 ① / 대표 그림 1번")
    P("-" * 78)
    P("  H_t/H_b  본더%  테스터%   본더듀얼   테스터듀얼  병목    믹스")
    p0 = Params()
    for rho in [0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95, 1.0, 1.1, 1.3, 1.6, 2.0]:
        s = run(p0, rho)
        if s["status"] != "Optimal":
            P("  %6.2f   (infeasible)" % rho)
            continue
        P("  %6.2f  %5.1f  %6.1f  %9.5f  %9.5f  %-5s  %s"
          % (rho, s["util_bond"] * 100, s["util_test"] * 100,
             s["dual_bond"], s["dual_test"], s["bottleneck"], mixstr(s)))
        rows_all.append(dict(scenario="C", param="rho", value=rho,
                             J=s["J"], bottleneck=s["bottleneck"], mix=mixstr(s)))

    # 이분탐색으로 전환점 정밀화
    lo, hi = 0.5, 2.0
    for _ in range(30):
        mid = (lo + hi) / 2
        s = run(p0, mid)
        if s["status"] != "Optimal":
            lo = mid
            continue
        if s["dual_test"] > s["dual_bond"]:
            lo = mid          # 아직 테스터 병목
        else:
            hi = mid
    P("")
    P("  ★ 병목 전환점 : H_t/H_b = **%.4f**" % ((lo + hi) / 2))
    P("    이보다 테스터가 적으면 테스터가, 많으면 본더가 병목이다.")
    P("    → 설비 증설 우선순위를 이 한 숫자가 결정한다.")
    P("")

    # ---------------- 시나리오 A : 층당 수율 ----------------
    P("-" * 78)
    P("[시나리오 A] 층당 접합 수율 x — 층수 전환 임계        ★ 차별점 ③")
    P("-" * 78)
    P("      x     8단%   12단%   16단%   병목    시간당이익   믹스")
    for x in [0.940, 0.950, 0.955, 0.960, 0.965, 0.970, 0.975, 0.980, 0.985, 0.990]:
        s = run(Params(x=x))
        if s["status"] != "Optimal":
            P("  %.3f   (infeasible — 수율이 낮아 수요를 못 채움)" % x)
            rows_all.append(dict(scenario="A", param="x", value=x, J=None,
                                 bottleneck="infeasible", mix="-"))
            continue
        bL, _ = shares(s)
        P("  %.3f  %5.0f%%  %5.0f%%  %5.0f%%  %-5s  %9.5f  %s"
          % (x, bL[8] * 100, bL[12] * 100, bL[16] * 100,
             s["bottleneck"], s["J"], mixstr(s)))
        rows_all.append(dict(scenario="A", param="x", value=x, J=s["J"],
                             bottleneck=s["bottleneck"], mix=mixstr(s)))
    P("")

    # ---------------- 시나리오 B : 고정시간 배수 ----------------
    P("-" * 78)
    P("[시나리오 B] 고정시간 배수 a = t_fix_a/t_stack — 최적 층수 이동   ★ 차별점 ②")
    P("-" * 78)
    P("      a     8단%   12단%   16단%   병목    시간당이익   믹스")
    for a in [0, 1, 1.4, 2, 3, 4, 6, 8, 10, 12]:
        s = run(Params(a=a))
        if s["status"] != "Optimal":
            P("  %5.1f   (infeasible)" % a)
            continue
        bL, _ = shares(s)
        P("  %5.1f  %5.0f%%  %5.0f%%  %5.0f%%  %-5s  %9.5f  %s"
          % (a, bL[8] * 100, bL[12] * 100, bL[16] * 100,
             s["bottleneck"], s["J"], mixstr(s)))
        rows_all.append(dict(scenario="B", param="a", value=a, J=s["J"],
                             bottleneck=s["bottleneck"], mix=mixstr(s)))
    P("")
    P("  검사시간 배수 θ = t_test/t_stack")
    P("      θ     8단%   12단%   16단%   병목    믹스")
    for th in [1, 2, 3, 5, 8, 12]:
        s = run(Params(theta=th))
        if s["status"] != "Optimal":
            P("  %5.1f   (infeasible)" % th)
            continue
        bL, _ = shares(s)
        P("  %5.1f  %5.0f%%  %5.0f%%  %5.0f%%  %-5s  %s"
          % (th, bL[8] * 100, bL[12] * 100, bL[16] * 100,
             s["bottleneck"], mixstr(s)))
        rows_all.append(dict(scenario="B", param="theta", value=th, J=s["J"],
                             bottleneck=s["bottleneck"], mix=mixstr(s)))
    P("")

    # ---------------- 시나리오 D : 검출률 ----------------
    P("-" * 78)
    P("[시나리오 D] 검출률 β — 최적 검사 주기 k 의 전환")
    P("-" * 78)
    P("      β    k=1%   k=2%   k=4%   출하DPPM   시간당이익   믹스")
    for b in [0.84, 0.88, 0.92, 0.95, 0.97, 0.99]:
        s = run(Params(beta=b))
        if s["status"] != "Optimal":
            P("  %.2f   (infeasible — 검출률이 낮아 DPPM 상한을 못 맞춤)" % b)
            rows_all.append(dict(scenario="D", param="beta", value=b, J=None,
                                 bottleneck="infeasible", mix="-"))
            continue
        _, bK = shares(s)
        P("  %.2f  %5.0f%% %5.0f%% %5.0f%%  %8.0f  %9.5f  %s"
          % (b, bK[1] * 100, bK[2] * 100, bK[4] * 100,
             s["dppm"], s["J"], mixstr(s)))
        rows_all.append(dict(scenario="D", param="beta", value=b, J=s["J"],
                             bottleneck=s["bottleneck"], mix=mixstr(s)))
    P("")

    # ---------------- 시나리오 F : 층수 프리미엄 ----------------
    P("-" * 78)
    P("[시나리오 F] 층수 프리미엄 — 매출 선형성 가정의 강건성   (06_Parameters 5.3)")
    P("-" * 78)
    P("  16단 $/GB 프리미엄   8단%   12단%   16단%   시간당이익   믹스")
    base_mix = None
    for prem in [0.00, 0.05, 0.10, 0.15, 0.25]:
        s = run(Params(layer_premium=prem))
        if s["status"] != "Optimal":
            continue
        bL, _ = shares(s)
        if base_mix is None:
            base_mix = mixstr(s)
        P("       %4.0f%%          %5.0f%%  %5.0f%%  %5.0f%%  %9.5f  %s"
          % (prem * 100, bL[8] * 100, bL[12] * 100, bL[16] * 100,
             s["J"], mixstr(s)))
        rows_all.append(dict(scenario="F", param="layer_premium", value=prem,
                             J=s["J"], bottleneck=s["bottleneck"], mix=mixstr(s)))
    P("")

    # ---------------- 몬테카를로 ----------------
    P("-" * 78)
    P("[몬테카를로] 파라미터 불확실성 동시 반영 — 삼각분포 · 2,000회")
    P("-" * 78)
    P("  분포 (최소, 기준, 최대)  — 06_Parameters 근거")
    DIST = {
        "x":       (0.940, 0.965, 0.990),
        "beta":    (0.840, 0.950, 0.990),
        "a":       (0.0,   3.0,   8.0),
        "theta":   (1.0,   3.0,  10.0),
        "r":       (3.0,   5.0,   8.0),
        "c_base":  (0.5,   1.5,   2.0),
        "c_fix_b": (1.0,   4.5,   8.0),
        "c_test":  (0.007, 0.012, 0.017),
        "beta_f":  (0.87,  0.95,  0.99),
        "rho":     (0.6,   0.9,   1.4),
    }
    for k, (lo_, mo, hi_) in DIST.items():
        P("      %-8s (%.3f, %.3f, %.3f)" % (k, lo_, mo, hi_))
    P("")

    random.seed(42)
    N = 2000
    samples, Js, s16, s12, s8, bn_test, feas = [], [], [], [], [], [], 0
    kshare = {1: [], 2: [], 4: []}
    for _ in range(N):
        d = {k: random.triangular(v[0], v[2], v[1]) for k, v in DIST.items()}
        rho = d.pop("rho")
        s = run(Params(**d), rho)
        if s["status"] != "Optimal":
            continue
        feas += 1
        bL, bK = shares(s)
        samples.append(dict(d, rho=rho))
        Js.append(s["J"])
        s8.append(bL[8]); s12.append(bL[12]); s16.append(bL[16])
        for k in K_SET:
            kshare[k].append(bK[k])
        bn_test.append(1.0 if s["bottleneck"] == "테스터" else 0.0)

    P("  실행 %d회 중 실행가능 %d회 (%.1f%%)" % (N, feas, feas / N * 100))
    P("")
    P("  결과 분포            중앙값      90%% 신뢰구간")
    def line(name, vals, scale=100.0, unit="%"):
        P("    %-16s %8.1f%s   [%.1f%s, %.1f%s]"
          % (name, pct(vals, .5) * scale, unit,
             pct(vals, .05) * scale, unit, pct(vals, .95) * scale, unit))
    line("8단 비중", s8); line("12단 비중", s12); line("16단 비중", s16)
    P("")
    line("k=1 비중", kshare[1]); line("k=2 비중", kshare[2]); line("k=4 비중", kshare[4])
    P("")
    P("    %-16s %8.4f    [%.4f, %.4f]"
      % ("시간당 이익 J", pct(Js, .5), pct(Js, .05), pct(Js, .95)))
    P("    %-16s %8.1f%%" % ("병목=테스터 확률", sum(bn_test) / len(bn_test) * 100))
    P("")

    # ---------------- 정보가치 분석 ----------------
    P("-" * 78)
    P("[정보가치 분석] 어떤 파라미터를 가장 정확히 측정해야 하는가")
    P("-" * 78)
    P("  각 파라미터와 결과의 상관계수 (|r| 이 클수록 그 값을 정확히 알아야 한다)")
    P("")
    P("    파라미터    →16단비중   →시간당이익   →테스터병목")
    keys = list(DIST.keys())
    tornado = []
    for kname in keys:
        col = [smp[kname] for smp in samples]
        c16 = pearson(col, s16)
        cJ = pearson(col, Js)
        cB = pearson(col, bn_test)
        tornado.append((kname, c16, cJ, cB))
    tornado.sort(key=lambda t: -abs(t[1]))
    for kname, c16, cJ, cB in tornado:
        P("    %-10s  %+8.3f    %+8.3f     %+8.3f" % (kname, c16, cJ, cB))
    P("")
    top = tornado[0]
    P("  ★ 층수 구성을 가장 크게 좌우하는 것은 **%s** (상관 %+.3f)" % (top[0], top[1]))
    tornado.sort(key=lambda t: -abs(t[3]))
    P("  ★ 병목 위치를 가장 크게 좌우하는 것은 **%s** (상관 %+.3f)"
      % (tornado[0][0], tornado[0][3]))
    P("")

    text = "\n".join(out)
    print(text)
    with open(os.path.join(ROOT, "data", "phase3_log.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    with open(os.path.join(ROOT, "data", "phase3_scenarios.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["scenario", "param", "value", "J",
                                          "bottleneck", "mix"])
        w.writeheader()
        w.writerows(rows_all)
    with open(os.path.join(ROOT, "data", "phase3_montecarlo.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(keys + ["J", "share8", "share12", "share16", "bottleneck_tester"])
        for smp, j, a8, a12, a16, bt in zip(samples, Js, s8, s12, s16, bn_test):
            w.writerow([smp[k] for k in keys] + [j, a8, a12, a16, bt])


if __name__ == "__main__":
    main()
