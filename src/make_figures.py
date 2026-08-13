# -*- coding: utf-8 -*-
"""
Phase 4 — 대표 그림 3장 (v2, 재작성)
2026.08.12 | HBM Stack Mix Optimization

스타일 레퍼런스
--------------
Rougier NP, Droettboom M, Bourne PE (2014) "Ten Simple Rules for Better Figures",
PLOS Computational Biology 10(9): e1003833, DOI 10.1371/journal.pcbi.1003833

v1 대비 변경 (지적 3건 반영)
--------------------------
fig1  로그축 major tick 이 10^3 하나뿐이라 425 ppm 무릎 위치를 축에서 읽을 수 없었다.
      → 데이터 지점에 명시 눈금. 계열 1개짜리 범례 제거. 두 체제를 음영으로 구분.

fig2  ★ 차트 종류 자체를 교체했다.
      누적 영역 차트는 맨 위 밴드(16단)의 두께를 눈으로 읽을 수 없다 — 바닥이
      아래 두 계열의 합에 따라 계속 움직이기 때문이다 (Rule 7: do not mislead).
      메시지가 "16단이 언제 왜 나타나는가" 이므로 16단 단일 선으로 바꾼다.
      8/12단은 배경에 옅은 회색으로 남긴다 (논문 Figure 7 오른쪽 패널의 방식).
      + C2(수요) 구속 여부를 마커 채움으로 직접 인코딩 — 두 체제가 데이터에서 보인다.

fig3  "no final test" 주석이 k=4 곡선을 관통했다.
      → 빈 영역(277~1,000 ppm 띠)으로 이동. 범례 상자 제거하고 곡선 옆 직접 라벨링.
"""

import csv
import os
import sys

import matplotlib.pyplot as plt
from matplotlib.ticker import FixedLocator, FixedFormatter, NullFormatter
from matplotlib.lines import Line2D

import figstyle as FS
from figstyle import (BLUE, VERMILLION, GREEN, ORANGE, PURPLE,
                      GREY_D, GREY_M, GREY_L, GREY_BG, BLACK)
from hbm_model import Params, block_y

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIGS = os.path.join(ROOT, "figures")
DATA = os.path.join(ROOT, "data")
os.makedirs(FIGS, exist_ok=True)

FS.apply_style()

COND = ("Conditions: x = 0.965, beta = 0.95, beta_f = 0.95, a = 3, theta = 3, "
        "DPPM cap = 200 ppm, demand share (>=12-Hi) = 0.70, H_t/H_b = 0.90, "
        "one inspection period per stack height.")


def save(fig, name):
    out = os.path.join(FIGS, name)
    fig.savefig(out)
    plt.close(fig)
    print("  saved  %s" % name)
    return out


# ======================================================================
# Figure 1 — 병목 전환점 vs 출하 품질 목표
#   메시지: 품질 목표가 425 ppm 보다 느슨하면 설비 증설 우선순위는 품질과 무관하다.
#           조이면 품질이 결정하며, 200 ppm 에서는 테스터가 본더보다 많아야 한다.
# ======================================================================

def fig1():
    caps, vals = [], []
    with open(os.path.join(DATA, "fig1_transition_curve.csv"),
              newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["transition_Ht_over_Hb"]:
                caps.append(float(row["dppm_cap"]))
                vals.append(float(row["transition_Ht_over_Hb"]))

    KNEE = 425.0
    XMIN, XMAX = 175.0, 6500.0
    fig, ax = plt.subplots(figsize=(7.0, 4.2))

    # Rule 6 — 평탄 구간은 회색 배경으로 눌러두고, 민감 구간만 색으로 강조
    ax.axvspan(KNEE, XMAX, color=GREY_BG, alpha=0.85, lw=0, zorder=0)

    ax.axhline(1.0, color=GREY_M, ls=(0, (5, 4)), lw=1.0, zorder=1)

    # 전체 곡선은 회색, 민감 구간만 컬러로 덮어씌운다
    ax.plot(caps, vals, color=GREY_M, lw=1.6, zorder=2)
    ax.plot(caps, vals, ls="none", marker="o", ms=4.5, mfc="white",
            mec=GREY_M, mew=1.2, zorder=3)
    sens = [(c, v) for c, v in zip(caps, vals) if c <= KNEE]
    ax.plot([c for c, _ in sens], [v for _, v in sens], color=VERMILLION,
            lw=2.4, zorder=4)
    ax.plot([c for c, _ in sens], [v for _, v in sens], ls="none", marker="o",
            ms=5.2, mfc=VERMILLION, mec="white", mew=1.0, zorder=5)

    ax.axvline(KNEE, color=GREY_D, ls=":", lw=1.1, zorder=1)

    # 체제 라벨 — 범례 대신 직접 라벨링 (Rule 8)
    ax.text(290, 1.295, "quality-driven", color=VERMILLION, fontsize=9.5,
            fontweight="bold", ha="center", va="center")
    ax.text(1900, 1.295, "quality-insensitive", color=GREY_D, fontsize=9.5,
            fontweight="bold", ha="center", va="center")

    FS.note(ax, 235, 1.135,
            "200 ppm :  $H_t/H_b$ = 1.14\ntester capacity must exceed bonder",
            color=VERMILLION, va="center", size=9, box=True)
    FS.note(ax, 1000, 0.655,
            "plateau  $H_t/H_b$ = 0.584\nquality target no longer matters",
            color=GREY_D, va="bottom", size=9, box=True)
    ax.text(XMIN * 1.06, 1.012, "tester capacity  =  bonder capacity",
            color=GREY_M, fontsize=8.5, va="bottom", ha="left")
    ax.text(KNEE * 1.06, 0.505, "knee\n425 ppm", color=GREY_D, fontsize=8.5,
            va="bottom", ha="left", linespacing=1.3)

    ax.set_xscale("log")
    ax.set_xlim(XMIN, XMAX)
    ax.set_ylim(0.48, 1.34)
    # Rule 8 — 눈금 수를 줄이되 반드시 읽어야 할 값은 명시한다
    ax.xaxis.set_major_locator(FixedLocator([200, 425, 1000, 5000]))
    ax.xaxis.set_major_formatter(FixedFormatter(["200", "425", "1,000", "5,000"]))
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.xaxis.set_minor_locator(FixedLocator([250, 300, 350, 500, 600, 2000, 3000]))
    ax.set_yticks([0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2])
    ax.set_xlabel("Outgoing quality limit,  DPPM cap  (ppm, log scale)")
    ax.set_ylabel("Bottleneck transition,  $H_t / H_b$")
    ax.set_title("Equipment expansion priority is set by the quality target",
                 loc="left", pad=26, fontweight="bold", color=BLACK)
    FS.hgrid(ax)
    FS.despine(ax)
    FS.caption(fig, "Figure 1.  Bottleneck transition point versus outgoing "
                    "quality limit.  Below the transition ratio the tester is "
                    "the bottleneck; above it the bonder is.\n" + COND)
    return save(fig, "fig1_bottleneck_vs_quality.png")


# ======================================================================
# Figure 2 — 층당 수율에 따른 16단 비중  ★ 차트 종류 교체
#   메시지: 16단은 두 가지 이유로 등장한다. 수율이 낮을 때는 수요 제약이 강제해서,
#           높을 때는 설비 경제성이 선택해서. 그 사이에는 0% 다.
# ======================================================================

def fig2():
    xs, s8, s12, s16, binds = [], [], [], [], []
    with open(os.path.join(DATA, "fig2_mix_vs_yield.csv"),
              newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            xs.append(float(row["x"]))
            s8.append(float(row["share_8Hi"]))
            s12.append(float(row["share_12Hi"]))
            s16.append(float(row["share_16Hi"]))
            binds.append(row["binding"])

    c2 = ["C2_seg1" in b for b in binds]
    XMIN, XMAX = 0.9415, 0.9910
    fig, ax = plt.subplots(figsize=(7.0, 4.4))

    # 체제 음영은 데이터 아래로 (zorder 0) — 데이터 색을 오염시키지 않는다
    ax.axvspan(XMIN, 0.9513, color=VERMILLION, alpha=0.09, lw=0, zorder=0)
    ax.axvspan(0.9513, 0.9638, color=GREY_BG, alpha=0.85, lw=0, zorder=0)
    ax.axvspan(0.9813, XMAX, color=GREEN, alpha=0.10, lw=0, zorder=0)

    # 보조 계열 — 옅은 회색으로 배경에 (Rougier Fig 7 오른쪽 패널)
    ax.plot(xs, s8, color=GREY_L, lw=1.3, ls="-", zorder=2)
    ax.plot(xs, s12, color=GREY_L, lw=1.3, ls=(0, (4, 3)), zorder=2)
    # 라벨은 반드시 해당 계열 위에 — 8-Hi 는 실선, 12-Hi 는 점선
    FS.label_line(ax, 0.9693, 84, "8-Hi", GREY_M, ha="center", size=8.5,
                  weight="normal")          # x=0.9675 에서 8-Hi = 77.0
    FS.label_line(ax, 0.9598, 90, "12-Hi", GREY_M, ha="center", size=8.5,
                  weight="normal")          # x=0.9600 에서 12-Hi = 81.0

    # 주인공 — 16단 비중
    ax.plot(xs, s16, color=BLUE, lw=2.4, zorder=4)
    for xi, yi, flag in zip(xs, s16, c2):
        ax.plot([xi], [yi], marker="o", ms=6.0, zorder=5,
                mfc=BLUE if flag else "white", mec=BLUE, mew=1.5, ls="none")

    # 체제 라벨
    for xc, txt, col, ha in ((0.9464, "demand-forced", VERMILLION, "center"),
                             (0.9576, "16-Hi absent", GREY_D, "center"),
                             (0.9726, "transition", GREY_D, "center"),
                             (0.9903, "economics-driven", "#1B7A5A", "right")):
        ax.text(xc, 110, txt, color=col, fontsize=8.8, fontweight="bold",
                ha=ha, va="center")

    FS.note(ax, 0.9432, 74,
            "capacity target forces tall stacks\ndespite low yield\n"
            "(demand constraint binding)",
            color=VERMILLION, va="top", size=8.5)
    ax.annotate("", xy=(0.9473, 46), xytext=(0.9497, 62),
                arrowprops=dict(arrowstyle="->", color=VERMILLION, lw=1.1),
                zorder=6)
    FS.note(ax, 0.9808, 62,
            "only bonder capacity binds\n16-Hi wins on equipment economics",
            color="#1B7A5A", va="top", ha="right", size=8.5)
    ax.annotate("", xy=(0.9830, 96), xytext=(0.9820, 66),
                arrowprops=dict(arrowstyle="->", color="#1B7A5A", lw=1.1),
                zorder=6)

    # 마커 채움의 의미 — 상자 없는 직접 설명
    handles = [Line2D([], [], marker="o", ls="none", ms=6, mfc=BLUE,
                      mec=BLUE, mew=1.5, label="demand constraint binding"),
               Line2D([], [], marker="o", ls="none", ms=6, mfc="white",
                      mec=BLUE, mew=1.5, label="not binding")]
    leg = ax.legend(handles=handles, loc="lower left", fontsize=8.5,
                    handletextpad=0.5, borderaxespad=0.8, labelcolor=GREY_D,
                    frameon=True, facecolor="white", edgecolor="none",
                    framealpha=0.92)
    leg.set_zorder(7)

    ax.set_xlim(XMIN, XMAX)
    ax.set_ylim(-4, 118)
    ax.set_yticks([0, 20, 40, 60, 80, 100])
    ax.set_xticks([0.945, 0.955, 0.965, 0.975, 0.985])
    ax.set_xlabel("Per-layer bonding yield,  $x$")
    ax.set_ylabel("16-Hi share of production  (%)")
    ax.set_title("16-Hi appears for two different reasons:\n"
                 "demand forces it at low yield, economics chooses it at high yield",
                 loc="left", pad=24, fontweight="bold", color=BLACK)
    FS.hgrid(ax)
    FS.despine(ax)
    FS.caption(fig, "Figure 2.  Share of 16-Hi stacks in the optimal production "
                    "mix versus per-layer bonding yield.  Grey lines show 8-Hi "
                    "and 12-Hi shares for context.  Filled markers indicate that "
                    "the customer capacity constraint is binding.\n" + COND)
    return save(fig, "fig2_mix_vs_yield.png")


# ======================================================================
# Figure 3 — 달성 가능 DPPM 하한 vs 최종 검사 검출률
#   메시지: 최종 검사 없이는 어떤 검사 빈도로도 1,000 ppm 아래로 갈 수 없다.
# ======================================================================

def fig3():
    p = Params()
    bfs = [i / 200.0 for i in range(0, 199)]
    curves = {k: [block_y(12, k, p.x, p.beta, bf)["dppm"] for bf in bfs]
              for k in (1, 2, 4)}

    fig, ax = plt.subplots(figsize=(7.0, 4.4))

    # 기준선 — 회색으로 눌러둔다
    ax.axhline(1000, color=GREY_M, ls=(0, (5, 4)), lw=1.0, zorder=1)
    ax.axhline(277, color=GREY_M, ls=(0, (1, 3)), lw=1.0, zorder=1)
    ax.text(0.985, 1120, "1,000 ppm", color=GREY_D, fontsize=8.5,
            ha="right", va="bottom")
    ax.text(0.008, 312, "277 ppm  (quality constraint becomes binding)",
            color=GREY_D, fontsize=8.5, ha="left", va="bottom")

    style = {1: (BLUE, "-", 2.4), 2: (ORANGE, (0, (6, 3)), 2.2),
             4: (VERMILLION, (0, (2, 2.5)), 2.2)}
    for k in (1, 2, 4):
        col, ls, lw = style[k]
        ax.plot(bfs, curves[k], color=col, ls=ls, lw=lw, zorder=4)

    # Rule 8 — 범례 상자 대신 곡선 옆 직접 라벨링
    xlab = 0.32
    i = bfs.index(0.32)
    for k, dy in ((1, 1.30), (2, 1.28), (4, 1.26)):
        col = style[k][0]
        FS.label_line(ax, xlab, curves[k][i] * dy, "k = %d" % k, col,
                      ha="center", size=10)
    ax.text(0.60, 6200, "k  =  inspect every k layers", color=GREY_D,
            fontsize=8.5, ha="center", va="center")

    # β_f = 0 강조 — 이 점이 메시지의 핵심이다
    for k in (1, 2, 4):
        ax.plot([0], [curves[k][0]], marker="o", ms=6.5, mfc="white",
                mec=style[k][0], mew=1.8, zorder=6, clip_on=False)
    FS.note(ax, 0.085, 560,
            "no final test :  floor is 1,909 ppm even at k = 1",
            color=BLACK, va="center", size=9)
    ax.annotate("", xy=(0.004, 1830), xytext=(0.075, 620),
                arrowprops=dict(arrowstyle="->", color=GREY_D, lw=1.1),
                zorder=5)

    ax.axvline(0.95, color=GREY_D, ls=":", lw=1.0, zorder=1)
    ax.text(0.941, 11, "adopted\n$\\beta_f$ = 0.95", color=GREY_D,
            fontsize=8.5, ha="right", va="bottom", linespacing=1.3)

    ax.set_yscale("log")
    ax.set_xlim(-0.005, 0.995)
    ax.set_ylim(8, 13000)
    ax.set_xticks([0.0, 0.2, 0.4, 0.6, 0.8, 0.95])
    ax.set_xticklabels(["0", "0.2", "0.4", "0.6", "0.8", "0.95"])
    ax.set_xlabel("Final-test detection rate,  $\\beta_f$")
    ax.set_ylabel("Achievable outgoing DPPM floor  (log scale)")
    ax.set_title("Without a final test, no inspection frequency reaches 1,000 ppm",
                 loc="left", pad=16, fontweight="bold", color=BLACK)
    FS.hgrid(ax)
    FS.despine(ax)
    FS.caption(fig, "Figure 3.  Lowest outgoing DPPM attainable for a 12-Hi stack "
                    "when every eligible in-line inspection is used, as a function "
                    "of final-test detection rate.  Open circles mark the no-final-test "
                    "case.\nConditions: x = 0.965, beta = 0.95, 12-Hi stack.  "
                    + FS.REFERENCE)
    return save(fig, "fig3_dppm_floor_vs_final_test.png")


if __name__ == "__main__":
    print("Phase 4 figures (v2)")
    fig1()
    fig2()
    fig3()
    print("\ndone - figures/ 3 files")
    print(FS.REFERENCE)
