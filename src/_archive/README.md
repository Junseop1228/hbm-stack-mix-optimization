폐기 스크립트 아카이브

## phi_final_sweep.py (2026.08.17 동결)

2라운드 N3 대응의 1차 시도다. 심사자가 phi_f = 1.0 이 물리적으로 낮다고 지적해
스윕 범위를 [1, 20] 광역으로 다시 잡았고, 그 결과물이 `src/phi_final_wide.py` 다.
이 파일은 그 대체 이전 버전이며 `run_all.py` 의 STEPS·CHECKS 어디에도 없고
산출물을 참조하는 원고도 없다.

삭제하지 않는 이유는 스윕 범위를 좁게 잡았던 판단과 그것이 뒤집힌 경위가
`notes/12_Review_Response.md` N3 항목의 근거이기 때문이다.

**주의** — 현행 아님. phi_f 스윕의 정본은 `src/phi_final_wide.py` 와
`src/final_test_sweep.py` 다.
