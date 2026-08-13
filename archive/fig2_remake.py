# -*- coding: utf-8 -*-
"""
fig2 재작성 — 원래 메시지가 현행 설정에서 성립하지 않아 정정한다.

폐기된 메시지 : "층당 수율 1.5%p 가 16단 비중을 0% 에서 100% 로 뒤집는다"
  → 이는 β_f=0 · cap=5,000 · C2 비구속 시점의 거동이었다.
    현행 설정(cap 200, C2 구속)에서는 x 스윕이 단조가 아니다.

확인된 실제 거동 (0.0025 간격, 20점)
  x ≤ 0.9500        16단 15~44%   — C2(수요)가 구속. **수요가 강제한다**
  0.9525 ~ 0.9625   16단 0%       — C2 비구속. 설비 경제성만으로는 못 이긴다
  0.9650 ~ 0.9800   16단 3~80%    — 전환 구간. 구속 제약 조합이 계속 바뀐다
  x ≥ 0.9825        16단 100%     — C1a(본더)만 구속. **경제성이 선택한다**

새 메시지
  **16단은 두 가지 이유로 등장한다. 수율이 낮을 때는 수요 제약이 강제해서,
    높을 때는 설비 경제성이 선택해서. 그 사이에는 0% 다.**

이것이 01_Spec 8.3 의 해석 지침과 정확히 맞는다 —
"층수 상승이 고객 용량 요구가 강제한 것인지 설비 경제성 때문인지"가 한 그림에서 갈린다.
"""

import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from hbm_model import Params, coefficients, L_SET, DEMAND_WAFER_DIES
from milp import solve
import scenarios as SC

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIGS = os.path.join(ROOT, "figures")
os.makedirs(FIGS, exist_ok=True)

plt.rcParams.update({"font.size": 10, "axes.grid": True,
                     "grid.alpha": 0.3, "figure.dpi": 150})

xs, s8, s12, s16, binds = [], [], [], [], []
x = 0.9425
while x <= 0.9905:
    r = solve(coefficients(Params(x=x)), SC.H_B, SC.H_B * SC.RHO_BASE,
              segments=SC.SEG, wafer_dies=DEMAND_WAFER_DIES,
              dppm_cap=SC.DPPM_CAP)
    if r["status"] == "Optimal":
        t = sum(r["q"].values())
        by = {L: 0.0 for L in L_SET}
        for (L, k), v in r["q"].items():
            by[L] += v / t * 100
        xs.append(x); s8.append(by[8]); s12.append(by[12]); s16.append(by[16])
        binds.append(set(n for n, v in r["duals"].items() if abs(v) > 1e-9))
    x = round(x + 0.0025, 4)

fig, ax = plt.subplots(figsize=(7.6, 4.8))
ax.stackplot(xs, s8, s12, s16, labels=["8-Hi", "12-Hi", "16-Hi"],
             colors=["#dbe5f1", "#8db3e2", "#1f4e79"],
             edgecolor="white", linewidth=0.6)
ax.plot(xs, [a + b for a, b in zip(s8, s12)], color="#7f6000", lw=1.3,
        ls="-.", marker="s", ms=3.5, label="8+12-Hi boundary")
ax.plot(xs, s8, color="#274e13", lw=1.3, ls="--", marker="o", ms=3.5,
        label="8-Hi boundary")

# 체제 구분
ax.axvspan(0.9415, 0.9513, color="#c00000", alpha=0.09)
ax.axvspan(0.9513, 0.9638, color="#7f7f7f", alpha=0.13)
ax.axvspan(0.9813, 0.9915, color="#548235", alpha=0.11)
ax.text(0.9463, 112, "demand-forced", ha="center", color="#c00000", fontsize=8.5)
ax.text(0.9575, 112, "16-Hi absent", ha="center", color="#404040", fontsize=8.5)
ax.text(0.9725, 112, "transition", ha="center", color="#404040", fontsize=8.5)
ax.text(0.9862, 112, "economics-driven", ha="center", color="#375623", fontsize=8.5)

ax.annotate("C2 (demand) binding:\ncapacity target forces tall stacks\ndespite poor yield",
            xy=(0.9475, 78), xytext=(0.9432, 40), fontsize=8.5, color="#333333",
            arrowprops=dict(arrowstyle="->", color="#c00000", lw=1))
ax.annotate("only C1a (bonder) binds:\n16-Hi wins on equipment economics",
            xy=(0.9862, 50), xytext=(0.9660, 62), fontsize=8.5, color="#333333",
            arrowprops=dict(arrowstyle="->", color="#375623", lw=1))

ax.set_xlabel("Per-layer bonding yield  $x$")
ax.set_ylabel("Production mix by stack height  (%)")
ax.set_title("16-Hi appears for two different reasons: demand forces it, "
             "or economics chooses it", fontsize=11, pad=14)
ax.set_ylim(0, 118)
ax.set_xlim(min(xs), max(xs))
ax.set_yticks([0, 20, 40, 60, 80, 100])
ax.legend(loc="lower left", fontsize=8.5, framealpha=0.92, ncol=2)
fig.text(0.5, 0.005,
         "Conditions: beta=0.95, beta_f=0.95, a=3, theta=3, cap=200 ppm, "
         "demand >=12-Hi share 0.70, H_t/H_b=0.90, single_k enabled",
         ha="center", fontsize=7, color="#555555")
fig.tight_layout(rect=[0, 0.035, 1, 1])
out = os.path.join(FIGS, "fig2_mix_vs_yield.png")
fig.savefig(out)
plt.close(fig)

with open(os.path.join(ROOT, "data", "fig2_mix_vs_yield.csv"), "w",
          newline="", encoding="utf-8") as f:
    f.write("x,share_8Hi,share_12Hi,share_16Hi,binding\n")
    for a, b, c, d, e in zip(xs, s8, s12, s16, binds):
        f.write("%.4f,%.2f,%.2f,%.2f,%s\n" % (a, b, c, d, "|".join(sorted(e))))

print("[fig2 재작성] %s" % out)
print("  구간별 16-Hi : x<=0.9500 → %.0f~%.0f%% / 0.9525~0.9625 → 0%% / x>=0.9825 → 100%%"
      % (min(s16[:4]), max(s16[:4])))
