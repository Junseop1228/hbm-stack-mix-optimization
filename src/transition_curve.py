# -*- coding: utf-8 -*-
"""전환점 궤적 무릎 구간 보강 — 400~500 ppm 사이."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from transition_point import transition, SEG_NEW
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

print("  DPPM 상한   전환 H_t/H_b")
rows = []
for cap in (200, 250, 300, 350, 400, 425, 450, 475, 500, 600, 1000, 5000):
    t = transition(cap, SEG_NEW, 0.95)
    print("  %7d      %s" % (cap, "실행 불가" if t is None else "%.4f" % t))
    rows.append((cap, t))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "data", "fig1_transition_curve.csv"), "w",
          newline="", encoding="utf-8") as f:
    f.write("dppm_cap,transition_Ht_over_Hb\n")
    for c, t in rows:
        f.write("%d,%s\n" % (c, "" if t is None else "%.6f" % t))
print("\n[기록] data/fig1_transition_curve.csv — 대표 그림 1번 데이터")
