# -*- coding: utf-8 -*-
"""
run_all.py — 전체 파이프라인 재현
2026.08.12 | HBM Stack Mix Optimization

    python src/run_all.py            전체 실행
    python src/run_all.py --list     단계 목록만 출력

data/ 와 figures/ 의 모든 산출물이 이 스크립트 하나로 재생성된다.
저장소에 커밋된 결과와 재실행 결과가 일치해야 한다.
"""

import os
import subprocess
import sys
import time

try:  # Windows 콘솔 기본 인코딩(cp949)에서 한글·기호가 깨지는 것 방지
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))

# (스크립트, 설명, 산출물)
STEPS = [
    ("gate0_threshold.py", "Gate 0 — Block Y 검증 6종 + 층수 최적점 존재 조건(임계 a)",
     "data/gate0_log.txt, block_y_output.csv, gate0_thresholds.csv"),
    ("milp.py", "Phase 2 — 결합층 + MILP, 통합 검증 7·8·9",
     "data/phase2_log.txt, phase2_bottleneck.csv"),
    ("scenarios.py", "Phase 3 — 시나리오 A~F + 파라미터 몬테카를로 + 정보가치",
     "data/phase3_log.txt, phase3_scenarios.csv, phase3_montecarlo.csv"),
    ("scenario_g.py", "시나리오 G — DPPM 상한 스윕, 실행가능 하한, 최적 k 전환점",
     "data/scenario_g_log.txt"),
    ("demand_segments.py", "수요 세그먼트 — GPU 용량 목표 역산, C2 구속 판정",
     "data/demand_segments_log.txt"),
    ("transition_point.py", "병목 전환점 이분탐색 + J 하락 원인 분해",
     "data/transition_point_log.txt"),
    ("transition_curve.py", "전환점 궤적 무릎 구간 보강 (대표 그림 1번 데이터)",
     "data/fig1_transition_curve.csv"),
    ("mix_vs_yield.py", "층당 수율 스윕 — 믹스와 구속 제약 (대표 그림 2번 데이터)",
     "data/fig2_mix_vs_yield.csv"),
    ("make_figures.py", "대표 그림 3장",
     "figures/fig1~3.png"),
    ("make_figures.py --no-caption", "논문 조판용 그림 3장 (캡션 미포함)",
     "paper/fig/fig1~3.png"),
    ("fig_audit.py", "그림 자동 검수 — 축 이탈·텍스트 겹침·곡선 관통",
     "(콘솔)"),
    ("check_block_y_mc.py", "Block Y 일반식 독립 검증 — 이벤트 몬테카를로 108항목",
     "data/block_y_mc_verify_log.txt"),
    ("dppm_floor.py", "DPPM 하한 일반 닫힌형 · 층수 무의존성 · 층별 분해",
     "data/dppm_floor_log.txt"),
    ("final_test_sweep.py", "최종 검사 시간비 φ_f · θ 곡면, 임계 φ_f",
     "data/final_test_sweep_log.txt, final_test_sweep.csv"),
]

# 검증용 일회성 스크립트 — 파이프라인에는 포함하지 않는다
CHECKS = [
    ("check_constraint_attribution.py", "제약별 귀속 분해 (C1a/C1b/C2/C4)"),
    ("check_single_k.py", "층수당 단일 검사주기 제약의 영향"),
    ("check_single_k_xsweep.py", "동 제약의 수율 스윕 민감도"),
    ("check_scenario_d.py", "검출률 β 시나리오"),
]


def show():
    print("파이프라인")
    for i, (f, d, o) in enumerate(STEPS, 1):
        print("  %d. %-32s %s\n     -> %s" % (i, f, d, o))
    print("\n검증 스크립트 (개별 실행)")
    for f, d in CHECKS:
        print("  -  %-32s %s" % (f, d))


def main():
    if "--list" in sys.argv:
        show()
        return
    print("=" * 70)
    print("HBM Stack Mix Optimization — 전체 재현")
    print("=" * 70)
    t0 = time.time()
    for i, (f, d, _) in enumerate(STEPS, 1):
        print("\n[%d/%d] %s\n      %s" % (i, len(STEPS), f, d))
        t1 = time.time()
        parts = f.split()
        r = subprocess.run([sys.executable, os.path.join(HERE, parts[0])] + parts[1:],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        if r.returncode != 0:
            print("      FAILED (exit %d)" % r.returncode)
            print((r.stderr or "")[-1500:])
            sys.exit(1)
        print("      ok  (%.1fs)" % (time.time() - t1))
    print("\n" + "=" * 70)
    print("완료 — %.1fs" % (time.time() - t0))


if __name__ == "__main__":
    main()
