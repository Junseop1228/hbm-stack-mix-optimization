# -*- coding: utf-8 -*-
"""전환점 궤적 — 무릎 구간을 5 ppm 격자로 탐색한다.

3라운드 S4/M-d: knee 를 "plateau 와 같아지는 최소 cap" 으로 정의하므로
값이 격자 해상도에 그대로 종속된다. 25 ppm 격자에서 425 로 보고했으나
해상도 근거가 없었다. 350~500 을 5 ppm 으로 조여 knee 를 확정한다."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from transition_point import transition, SEG_NEW
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

print("  DPPM 상한   전환 H_t/H_b")
rows = []
CAPS = ([200, 250, 300] +
        [350 + 5 * i for i in range(31)] +      # 350~500, 5 ppm 격자
        [600, 1000, 5000])

for cap in CAPS:
    t = transition(cap, SEG_NEW, 0.95)
    print("  %7d      %s" % (cap, "실행 불가" if t is None else "%.4f" % t))
    rows.append((cap, t))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "data", "fig1_transition_curve.csv"), "w",
          newline="", encoding="utf-8") as f:
    f.write("dppm_cap,transition_Ht_over_Hb\n")
    for c, t in rows:
        f.write("%d,%s\n" % (c, "" if t is None else "%.6f" % t))
vals = [v for _, v in rows if v is not None]
if vals:
    plateau = max(vals, key=lambda v: sum(1 for u in vals if abs(u - v) < 1e-9))
    knee = min(c for c, v in rows if v is not None and abs(v - plateau) < 1e-9)
    prev = max((c for c, v in rows if v is not None and abs(v - plateau) >= 1e-9),
               default=None)
    print("")
    print("  plateau      : %.4f" % plateau)
    print("  knee         : %d ppm  (격자 해상도 5 ppm)" % knee)
    if prev is not None:
        print("  직전 격자점  : %d ppm -> %.4f  (plateau 와 차이 %.6f)"
              % (prev, dict(rows)[prev], dict(rows)[prev] - plateau))
print("\n[기록] data/fig1_transition_curve.csv — 대표 그림 1번 데이터")
