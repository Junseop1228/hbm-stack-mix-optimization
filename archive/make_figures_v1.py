# -*- coding: utf-8 -*-
"""
Phase 4 — 대표 그림 3장 | 2026.08.12

한 줄 메시지를 먼저 고정하고 그린다.
  fig1  품질 목표가 425 ppm 보다 느슨하면 설비 증설 우선순위는 품질과 무관하다.
        조이면 품질이 결정하며, 200 ppm 에서는 테스터가 본더보다 많아야 한다.
  fig2  층당 수율 1.5%p 가 16단 비중을 0% 에서 100% 로 뒤집는다.
  fig3  최종 검사 없이는 어떤 검사 빈도로도 1,000 ppm 아래로 갈 수 없다.

라벨 전부 영문 (Windows matplotlib 한글 폰트 깨짐). 흑백 대비 : 색 + 선종류/마커 병용.
"""

import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from hbm_model import Params, coefficients, block_y, L_SET, K_SET, DEMAND_WAFER_DIES
from milp import solve
import scenarios as SC

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIGS = os.path.join(ROOT, "figures")
os.makedirs(FIGS, exist_ok=True)

CAPTION = ("Conditions: x=0.965, beta=0.95, beta_f=0.95, a=3, theta=3, "
           "cap=200 ppm, demand >=12-Hi share 0.70, H_t/H_b=0.90")

plt.rcParams.update({"font.size": 10, "axes.grid": True,
                     "grid.alpha": 0.3, "figure.dpi": 150})


def fig1():
    caps, vals = [], []
    with open(os.path.join(ROOT, "data", "fig1_transition_curve.csv"),
              newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["transition_Ht_over_Hb"]:
                caps.append(float(row["dppm_cap"]))
                vals.append(float(row["transition_Ht_over_Hb"]))

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.plot(caps, vals, marker="o", ms=5, lw=2, color="#1f4e79", ls="-",
            label="Bottleneck transition point")
    ax.axhline(1.0, color="#c00000", ls="--", lw=1.4)
    ax.text(5200, 1.02, "Tester capacity = Bonder capacity",
            color="#c00000", ha="right", fontsize=9)
    ax.axvline(425, color="#555555", ls=":", lw=1.4)
    ax.text(455, 1.02, "knee: 425 ppm", color="#333333", fontsize=9)
    ax.annotate("plateau  H_t/H_b = 0.5837\n(quality target does not matter)",
                xy=(2000, 0.5837), xytext=(900, 0.72), fontsize=9,
                arrowprops=dict(arrowstyle="->", color="#555555", lw=1))
    ax.annotate("200 ppm : 1.1398\ntester must exceed bonder",
                xy=(200, 1.1398), xytext=(255, 1.21), fontsize=9,
                arrowprops=dict(arrowstyle="->", color="#c00000", lw=1))
    ax.set_xscale("log")
    ax.set_xlabel("Outgoing quality limit  (DPPM cap, ppm, log scale)")
    ax.set_ylabel("Bottleneck transition  $H_t / H_b$")
    ax.set_title("Equipment expansion priority is set by the quality target",
                 fontsize=11.5, pad=10)
    ax.set_ylim(0.45, 1.32)
    ax.legend(loc="center right", fontsize=9)
    fig.text(0.5, 0.005, CAPTION, ha="center", fontsize=7, color="#555555")
    fig.tight_layout(rect=[0, 0.035, 1, 1])
    out = os.path.join(FIGS, "fig1_bottleneck_vs_quality.png")
    fig.savefig(out)
    plt.close(fig)
    print("[fig1] %s" % out)


def fig2():
    xs = [0.940, 0.945, 0.950, 0.955, 0.960, 0.965, 0.970, 0.975, 0.980, 0.985, 0.990]
    keep, s8, s12, s16 = [], [], [], []
    for x in xs:
        r = solve(coefficients(Params(x=x)), SC.H_B, SC.H_B * SC.RHO_BASE,
                  segments=SC.SEG, wafer_dies=DEMAND_WAFER_DIES,
                  dppm_cap=SC.DPPM_CAP, need_duals=False)
        if r["status"] != "Optimal":
            print("   (x=%.3f infeasible - skipped)" % x)
            continue
        tot = sum(r["q"].values())
        by = {L: 0.0 for L in L_SET}
        for (L, k), v in r["q"].items():
            by[L] += v / tot * 100
        keep.append(x)
        s8.append(by[8])
        s12.append(by[12])
        s16.append(by[16])

    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.stackplot(keep, s8, s12, s16, labels=["8-Hi", "12-Hi", "16-Hi"],
                 colors=["#dbe5f1", "#8db3e2", "#1f4e79"],
                 edgecolor="white", linewidth=0.6)
    ax.plot(keep, s8, color="#274e13", lw=1.2, ls="--", marker="o", ms=4,
            label="8-Hi boundary")
    ax.plot(keep, [a + b for a, b in zip(s8, s12)], color="#7f6000", lw=1.2,
            ls="-.", marker="s", ms=4, label="8+12-Hi boundary")
    ax.axvspan(0.965, 0.980, color="#c00000", alpha=0.10)
    ax.text(0.9725, 103, "transition band", ha="center", color="#c00000", fontsize=9)
    ax.set_xlabel("Per-layer bonding yield  $x$")
    ax.set_ylabel("Production mix by stack height  (%)")
    ax.set_title("A 1.5%p change in per-layer yield flips 16-Hi from 0% to 100%",
                 fontsize=11.5, pad=10)
    ax.set_ylim(0, 108)
    ax.set_xlim(min(keep), max(keep))
    ax.legend(loc="center left", fontsize=9, framealpha=0.9)
    fig.text(0.5, 0.005, CAPTION + "  |  single_k enabled (see report note)",
             ha="center", fontsize=7, color="#555555")
    fig.tight_layout(rect=[0, 0.035, 1, 1])
    out = os.path.join(FIGS, "fig2_mix_vs_yield.png")
    fig.savefig(out)
    plt.close(fig)
    print("[fig2] %s" % out)


def fig3():
    p = Params()
    bfs = [i / 100.0 for i in range(0, 100)]
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    styles = {1: ("-", "o", "#1f4e79"), 2: ("--", "s", "#c55a11"),
              4: (":", "^", "#548235")}
    for k in K_SET:
        ys = [block_y(12, k, p.x, p.beta, bf)["dppm"] for bf in bfs]
        ls, mk, c = styles[k]
        ax.plot(bfs, ys, ls=ls, color=c, lw=2, marker=mk, markevery=12, ms=5,
                label="k = %d  (test every %d layer%s)"
                      % (k, k, "" if k == 1 else "s"))
    ax.axhline(1000, color="#c00000", ls="--", lw=1.3)
    ax.text(0.02, 1150, "1,000 ppm", color="#c00000", fontsize=9)
    ax.axhline(277, color="#7030a0", ls="-.", lw=1.3)
    ax.text(0.02, 305, "277 ppm  (C4 binding threshold)", color="#7030a0", fontsize=9)
    ax.annotate("no final test:\n1,909 ppm (k=1)", xy=(0.0, 1908.9),
                xytext=(0.13, 4200), fontsize=9,
                arrowprops=dict(arrowstyle="->", color="#333333", lw=1))
    ax.axvline(0.95, color="#555555", ls=":", lw=1.2)
    ax.text(0.935, 12, "adopted\n$\\beta_f$ = 0.95", ha="right", fontsize=9,
            color="#333333")
    ax.set_yscale("log")
    ax.set_xlabel("Final-test detection rate  $\\beta_f$")
    ax.set_ylabel("Achievable outgoing DPPM floor  (log scale)")
    ax.set_title("Without a final test, no inspection frequency reaches 1,000 ppm",
                 fontsize=11.5, pad=10)
    ax.set_xlim(0, 0.99)
    ax.set_ylim(8, 12000)
    ax.legend(loc="lower left", fontsize=9)
    fig.text(0.5, 0.005, "Conditions: 12-Hi stack, x=0.965, beta=0.95. "
                         "Floor = outgoing DPPM with every eligible insertion used.",
             ha="center", fontsize=7, color="#555555")
    fig.tight_layout(rect=[0, 0.035, 1, 1])
    out = os.path.join(FIGS, "fig3_dppm_floor_vs_final_test.png")
    fig.savefig(out)
    plt.close(fig)
    print("[fig3] %s" % out)


if __name__ == "__main__":
    fig1()
    fig2()
    fig3()
    print("\n완료 - figures/ 3장")
