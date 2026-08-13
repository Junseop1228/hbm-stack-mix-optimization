# -*- coding: utf-8 -*-
"""
그림 자동 검수 — 텍스트가 축 밖으로 나가거나 데이터 선과 겹치는지 렌더러로 계산한다.
눈으로 볼 수 없는 환경에서의 대체 검증.
"""
import os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import make_figures as M
import figstyle as FS

FS.apply_style()


def audit(build, name):
    print("\n=== %s ===" % name)
    # 그림을 다시 만들되 저장 직전 상태를 잡기 위해 monkeypatch
    holder = {}
    orig_save = M.save
    def cap(fig, fname):
        holder["fig"] = fig
        return fname
    M.save = cap
    build()
    M.save = orig_save
    fig = holder["fig"]
    fig.canvas.draw()
    rend = fig.canvas.get_renderer()
    ax = fig.axes[0]
    abox = ax.get_window_extent(rend)

    texts = [t for t in ax.texts if t.get_text().strip()]
    problems = 0

    # 1) 축 밖으로 나가는 텍스트
    for t in texts:
        bb = t.get_window_extent(rend)
        out = []
        if bb.x0 < abox.x0 - 1: out.append("left %.0fpx" % (abox.x0 - bb.x0))
        if bb.x1 > abox.x1 + 1: out.append("right %.0fpx" % (bb.x1 - abox.x1))
        if bb.y0 < abox.y0 - 1: out.append("below %.0fpx" % (abox.y0 - bb.y0))
        if bb.y1 > abox.y1 + 1: out.append("above %.0fpx" % (bb.y1 - abox.y1))
        if out:
            problems += 1
            print("  [OUT ] %-42r  %s" % (t.get_text()[:40], ", ".join(out)))

    # 2) 텍스트끼리 겹침
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            a = texts[i].get_window_extent(rend)
            b = texts[j].get_window_extent(rend)
            ox = min(a.x1, b.x1) - max(a.x0, b.x0)
            oy = min(a.y1, b.y1) - max(a.y0, b.y0)
            if ox > 2 and oy > 2:
                problems += 1
                print("  [T-T ] %r  x  %r   (%.0f x %.0f px)"
                      % (texts[i].get_text()[:26], texts[j].get_text()[:26], ox, oy))

    # 3) 텍스트와 데이터 선 겹침 (흰 배경 상자가 없는 것만)
    lines = [ln for ln in ax.lines
             if ln.get_linestyle() not in ("None", "none")
             and len(ln.get_xdata()) > 2]
    for t in texts:
        if t.get_bbox_patch() is not None:
            continue  # 흰 상자로 대비 확보됨
        bb = t.get_window_extent(rend)
        for ln in lines:
            pts = ax.transData.transform(np.column_stack(
                [np.asarray(ln.get_xdata(), float), np.asarray(ln.get_ydata(), float)]))
            hit = ((pts[:, 0] >= bb.x0 - 1) & (pts[:, 0] <= bb.x1 + 1) &
                   (pts[:, 1] >= bb.y0 - 1) & (pts[:, 1] <= bb.y1 + 1))
            if hit.any():
                problems += 1
                print("  [T-L ] %-34r overlaps a data line (%d pts)"
                      % (t.get_text()[:32], int(hit.sum())))
                break

    print("  -> %s" % ("OK (0 problems)" if problems == 0 else "%d problem(s)" % problems))
    plt.close(fig)
    return problems


total = 0
total += audit(M.fig1, "fig1")
total += audit(M.fig2, "fig2")
total += audit(M.fig3, "fig3")
print("\nTOTAL: %d problem(s)" % total)
