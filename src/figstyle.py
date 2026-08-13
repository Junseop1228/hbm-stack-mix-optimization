# -*- coding: utf-8 -*-
"""
figstyle.py — 그림 공통 스타일
2026.08.12 | HBM Stack Mix Optimization

레퍼런스
--------
Rougier, N.P., Droettboom, M., Bourne, P.E. (2014)
"Ten Simple Rules for Better Figures"
PLOS Computational Biology 10(9): e1003833
DOI 10.1371/journal.pcbi.1003833   (CC0, 스크립트 공개: github.com/rougier/ten-rules)

이 논문의 그림은 전부 matplotlib 으로 제작됐고 스크립트가 공개돼 있어
스타일을 직접 대조할 수 있다. 아래 규칙을 그대로 적용한다.

  Rule 2  Identify your message   — 그림 1장 = 메시지 1개. 제목에 메시지를 쓴다
  Rule 5  Do not trust the defaults — 기본 설정을 그대로 쓰지 않는다
  Rule 6  Use color effectively   — 강조할 요소만 색, 나머지는 회색/검정.
                                    색맹 안전 팔레트 사용 (Okabe & Ito 2008)
  Rule 7  Do not mislead          — 누적 영역 차트로 상단 계열을 읽게 하지 않는다.
                                    축 범위·눈금을 명시한다
  Rule 8  Avoid chartjunk         — 범례 상자 대신 직접 라벨링, 눈금 수 축소,
                                    불필요한 격자·테두리 제거
                                    (논문 Figure 7 오른쪽 패널의 방식)
  Rule 4  Captions are not optional — 조건을 캡션에 전부 명시

색상: Okabe, M. & Ito, K. (2008) "Color Universal Design"
      https://jfly.uni-koeln.de/color/
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── Okabe–Ito 색맹 안전 팔레트 ────────────────────────────────────
BLACK = "#000000"
ORANGE = "#E69F00"
SKY = "#56B4E9"
GREEN = "#009E73"
YELLOW = "#F0E442"
BLUE = "#0072B2"
VERMILLION = "#D55E00"
PURPLE = "#CC79A7"

# 보조 회색 (Rule 6: 강조하지 않는 요소)
GREY_D = "#4D4D4D"
GREY_M = "#808080"
GREY_L = "#BFBFBF"
GREY_BG = "#E8E8E8"


def apply_style():
    """Rule 5 — 기본 설정을 쓰지 않는다."""
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "font.size": 9.5,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "axes.linewidth": 0.9,
        "axes.edgecolor": GREY_D,
        "axes.labelcolor": BLACK,
        "axes.grid": False,          # Rule 8 — 격자는 기본 제거
        "xtick.direction": "out",
        "ytick.direction": "out",
        "xtick.color": GREY_D,
        "ytick.color": GREY_D,
        "xtick.major.size": 4,
        "ytick.major.size": 4,
        "xtick.major.width": 0.9,
        "ytick.major.width": 0.9,
        "legend.frameon": False,
        "figure.dpi": 200,
        "savefig.dpi": 200,
        "savefig.bbox": "tight",
        "savefig.pad_inches": 0.12,
    })


def despine(ax, keep=("left", "bottom")):
    """Rule 8 — 상·우 테두리 제거."""
    for side in ("top", "right", "left", "bottom"):
        ax.spines[side].set_visible(side in keep)


def hgrid(ax, color=GREY_L, lw=0.6):
    """가로 보조선만 아주 옅게. 값 읽기에 필요한 최소한만 남긴다."""
    ax.set_axisbelow(True)
    ax.yaxis.grid(True, color=color, lw=lw, alpha=0.55)
    ax.xaxis.grid(False)


def label_line(ax, x, y, text, color, ha="left", va="center", size=9.5,
               weight="bold", box=False):
    """Rule 8 — 범례 상자 대신 선 옆에 직접 라벨링
    (Rougier et al. Figure 7 오른쪽 패널의 방식)."""
    kw = dict(color=color, ha=ha, va=va, fontsize=size, fontweight=weight,
              zorder=6)
    if box:
        kw["bbox"] = dict(boxstyle="round,pad=0.25", facecolor="white",
                          edgecolor="none", alpha=0.88)
    return ax.text(x, y, text, **kw)


def note(ax, x, y, text, color=GREY_D, ha="left", va="top", size=8.5,
         box=True):
    """주석 — 데이터 위에 얹힐 때는 흰 배경 상자로 대비를 확보한다."""
    kw = dict(color=color, ha=ha, va=va, fontsize=size, zorder=6, linespacing=1.35)
    if box:
        kw["bbox"] = dict(boxstyle="round,pad=0.3", facecolor="white",
                          edgecolor="none", alpha=0.90)
    return ax.text(x, y, text, **kw)


def caption(fig, text):
    """Rule 4 — 조건을 캡션에 전부 적는다."""
    fig.text(0.5, -0.02, text, ha="center", va="top",
             fontsize=7.5, color=GREY_M, wrap=True)


REFERENCE = ("Figure style follows Rougier NP, Droettboom M, Bourne PE (2014) "
             "Ten Simple Rules for Better Figures, PLOS Comput Biol 10(9): e1003833. "
             "Colors: Okabe & Ito colorblind-safe palette.")
