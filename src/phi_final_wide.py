# -*- coding: utf-8 -*-
"""
phi_final_wide.py — N3: φ_f ∈ [1, 20] 광역 스윕

2라운드 지적 (N3)
-----------------
"φ_f = 1.0 은 물리적으로 매우 낮다. in-line 검사는 개방/단락·연속성 위주의 짧은
검사이고 HBM 최종테스트는 full-speed·전 채널·soak/burn-in 을 포함한다. R2 판단으로
φ_f 는 5–20 범위가 현실적이다. 따라서 Table IX 의 1.2872/0.7284, 425 ppm knee,
Table VIII 전체가 모두 **하한**이다."

그리고 가장 중요한 지적:

"φ_f 가 크면 τ_test 가 k 에 거의 무의존한 바닥 항에 지배되고, 조기폐기는 그 바닥
항까지 절약한다. 즉 '테스터 병목 → k=4' 의 유인이 약화되거나 반전할 수 있다.
**φ_f 스윕에서 VII-F 반전이 살아있는지 확인은 선택이 아니라 필수다.**"

이 스크립트가 그 확인이다. 네 가지를 φ_f 축에서 보고한다.
  (a) knee 위치          (b) 병목 전환 비율
  (c) 최적 믹스          (d) ★ VII-F 반전(본더 병목→k=1 / 테스터 병목→k=4) 생존 여부

산출물: data/phi_final_wide_log.txt, phi_final_wide.csv
"""

import csv
import os
import sys

from hbm_model import (Params, coefficients, L_SET, K_SET,
                       DEMAND_SEG, DEMAND_WAFER_DIES,
                       H_BONDER, H_TESTER, RHO_BASE, DPPM_CAP)
from milp import solve, BIG

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PHIS = [1.0, 2.0, 3.0, 5.0, 8.0, 12.0, 16.0, 20.0]


def base(pf, rho=RHO_BASE, cap=DPPM_CAP):
    return solve(coefficients(Params(phi_final=pf)), H_BONDER, H_BONDER * rho,
                 segments=DEMAND_SEG, wafer_dies=DEMAND_WAFER_DIES, dppm_cap=cap)


def mix_of(s):
    if s["status"] != "Optimal" or not s["q"]:
        return None, None
    tot = sum(s["q"].values())
    byL = {L: 0.0 for L in L_SET}
    byK = {k: 0.0 for k in K_SET}
    for (L, k), v in s["q"].items():
        byL[L] += v / tot * 100
        byK[k] += v / tot * 100
    return byL, byK


def transition(pf, lo=0.2, hi=6.0, iters=34):
    coef = coefficients(Params(phi_final=pf))
    for _ in range(iters):
        mid = (lo + hi) / 2
        s = solve(coef, H_BONDER, H_BONDER * mid, segments=DEMAND_SEG,
                  wafer_dies=DEMAND_WAFER_DIES, dppm_cap=DPPM_CAP)
        if s["status"] != "Optimal":
            lo = mid
            continue
        if s["dual_test"] > s["dual_bond"]:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def _ratio(pf, cap):
    """주어진 cap 에서 병목이 뒤바뀌는 H_t/H_b 를 이분탐색한다."""
    coef = coefficients(Params(phi_final=pf))
    lo, hi = 0.2, 6.0
    for _ in range(28):
        mid = (lo + hi) / 2
        s = solve(coef, H_BONDER, H_BONDER * mid, segments=DEMAND_SEG,
                  wafer_dies=DEMAND_WAFER_DIES, dppm_cap=cap)
        if s["status"] != "Optimal":
            lo = mid; continue
        if s["dual_test"] > s["dual_bond"]:
            lo = mid
        else:
            hi = mid
    return round((lo + hi) / 2, 4)


def knee(pf, caps=(200, 250, 300, 350, 400, 450, 500, 700, 1000, 2000, 5000),
         grid=5, tol=1e-3):
    """전환 비율이 평탄해지기 시작하는 cap. 격자 해상도 5 ppm.

    3라운드 S4/M-d: knee 를 격자점으로 보고하면 값이 해상도의 인공물이 된다.
    실제로 25 ppm 격자의 425 ppm 은 5 ppm 에서 410 ppm 으로 이동했다.
    전 구간을 5 ppm 으로 훑으면 비용이 3배가 되므로, 거친 격자로 구간을
    좁힌 뒤 그 안에서만 5 ppm 이분탐색한다 (추가 약 5회).
    """
    vals = {c: _ratio(pf, c) for c in caps}
    plateau = vals[max(caps)]
    flat = [c for c in caps if abs(vals[c] - plateau) < tol]
    if not flat:
        return None, plateau, vals
    hi = min(flat)
    below = [c for c in caps if c < hi]
    if not below:
        return hi, plateau, vals
    lo = max(below)
    while hi - lo > grid:
        mid = int(round((lo + hi) / 2.0 / grid) * grid)
        if mid <= lo or mid >= hi:
            break
        v = _ratio(pf, mid)
        vals[mid] = v
        if abs(v - plateau) < tol:
            hi = mid
        else:
            lo = mid
    return hi, plateau, vals


def single_constraint(pf, which):
    """제약 하나만 활성화 — VII-F 검정. C3 는 발산 방지용으로 항상 켠다."""
    coef = coefficients(Params(phi_final=pf))
    kw = dict(H_bond=BIG, H_test=BIG, wafer_dies=DEMAND_WAFER_DIES)
    if which == "bonder":
        kw["H_bond"] = H_BONDER
    else:
        kw["H_test"] = H_TESTER
    s = solve(coef, **kw)
    if s["status"] != "Optimal" or not s["q"]:
        return None
    tot = sum(s["q"].values())
    byK = {k: 0.0 for k in K_SET}
    for (L, k), v in s["q"].items():
        byK[k] += v / tot * 100
    return byK


def main():
    out, rows = [], []
    P = out.append
    P("=" * 92)
    P("N3 — 최종 검사 시간비 φ_f 광역 스윕 [1, 20]")
    P("=" * 92)
    P("심사자 판단: φ_f 는 5~20 이 현실적. 기준값 1.0 은 분포 최소값이므로")
    P("보고된 모든 값이 하한이다. 그 사실을 곡면으로 확인한다.")
    P("")

    # ── (d) VII-F 반전 생존 — 가장 중요 ────────────────────
    P("[1] ★★ VII-F 반전의 생존 여부 — 이번 스윕의 핵심")
    P("  주장: '본더가 병목이면 검사를 최대로, 테스터가 병목이면 최소로'")
    P("  우려: φ_f 가 크면 τ_test 가 k 무의존 바닥 항에 지배되어 반전이 약화/역전")
    P("")
    P("   φ_f │ 본더만 활성 (k1/k2/k4 %)   │ 테스터만 활성 (k1/k2/k4 %)  │ 반전")
    for pf in PHIS:
        b = single_constraint(pf, "bonder")
        t = single_constraint(pf, "tester")
        if b is None or t is None:
            P("  %5.1f │ (해 없음)" % pf); continue
        # 반전 성립 = 본더 병목에서 k 가 작고, 테스터 병목에서 k 가 큼
        kb = sum(k * v for k, v in b.items()) / 100.0
        kt = sum(k * v for k, v in t.items()) / 100.0
        ok = "유지" if kb < kt - 1e-6 else ("소멸" if abs(kb - kt) < 1e-6 else "★역전")
        P("  %5.1f │  %5.1f/%5.1f/%5.1f  (k̄=%.2f) │  %5.1f/%5.1f/%5.1f  (k̄=%.2f) │ %s"
          % (pf, b[1], b[2], b[4], kb, t[1], t[2], t[4], kt, ok))
        rows.append(dict(axis="viif", phi_final=pf, k_bar_bonder=round(kb, 3),
                         k_bar_tester=round(kt, 3), verdict=ok))
    P("")

    # ── (b)(c) 전환점·믹스 ────────────────────────────────
    P("[2] 병목 전환 비율과 기준 시나리오 믹스")
    P("   φ_f │ 전환 H_t/H_b │ 8단/12단/16단 %      │ 병목    │ J")
    for pf in PHIS:
        tr = transition(pf)
        s = base(pf)
        if s["status"] != "Optimal":
            P("  %5.1f │   %8.4f   │ 실행 불가" % (pf, tr))
            rows.append(dict(axis="baseline", phi_final=pf, transition=round(tr, 4),
                             status="infeasible"))
            continue
        byL, byK = mix_of(s)
        P("  %5.1f │   %8.4f   │ %5.1f/%5.1f/%5.1f    │ %-5s │ %.5f"
          % (pf, tr, byL[8], byL[12], byL[16], s["bottleneck"], s["J"]))
        rows.append(dict(axis="baseline", phi_final=pf, transition=round(tr, 4),
                         status="ok", share_8=round(byL[8], 2),
                         share_12=round(byL[12], 2), share_16=round(byL[16], 2),
                         bottleneck=s["bottleneck"], J=round(s["J"], 5)))
    P("")

    # ── (a) knee ──────────────────────────────────────────
    P("[3] knee 위치의 φ_f 의존 — 425 ppm 은 φ_f=1 한 점의 값이다")
    P("   φ_f │ knee (ppm) │ 평탄값 H_t/H_b")
    for pf in (1.0, 3.0, 8.0, 20.0):
        kn, pl, vals = knee(pf)
        P("  %5.1f │    %5s    │  %.4f" % (pf, kn, pl))
        rows.append(dict(axis="knee", phi_final=pf, knee_ppm=kn, plateau=round(pl, 4)))
    P("")

    P("=" * 92)
    P("해석")
    P("=" * 92)
    P("[a] 기준값 1.0 은 분포 최소값이므로 보고된 전환 비율·knee 는 모두 하한이다.")
    P("    심사자가 현실적이라 본 5~20 구간에서 값이 어떻게 움직이는지 위 표로 확인된다.")
    P("[b] VII-F 반전의 생존 여부는 [1] 이 답한다. '유지' 가 아닌 행이 하나라도 있으면")
    P("    해당 φ_f 구간을 조건으로 명시해야 한다.")
    P("[c] baseline 을 분포 최소값에 두는 것과 mode 에 두는 것의 차이도 [2] 에서 읽힌다.")

    text = "\n".join(out)
    print(text)
    with open(os.path.join(ROOT, "data", "phi_final_wide_log.txt"), "w",
              encoding="utf-8") as f:
        f.write(text)
    keys = sorted({k for r_ in rows for k in r_})
    with open(os.path.join(ROOT, "data", "phi_final_wide.csv"), "w",
              newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader(); w.writerows(rows)


if __name__ == "__main__":
    main()
