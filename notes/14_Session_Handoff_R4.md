# 세션 인계 — Round 4 대응 (STEP 1 진행 중)
**작성 2026.08.18**

---

## 0. 이어받으면 먼저 할 일

```powershell
cd "C:\Users\userPC\Desktop\Workspace\00_Active\2026_Summer\semconductor\HBM_Stack_Mix_Optimization"
Get-Process python -ErrorAction SilentlyContinue      # 비어야 정상
Get-Item data\phi_final_wide_log.txt | Select LastWriteTime
Select-String -Path data\phi_final_wide_log.txt -Pattern "knee \(ppm\)" -Context 0,5
```

**phi_final_wide.py 2차 실행이 끝났는지 반드시 확인하라.** 로그의 knee 열이
전부 **410** 이어야 한다. 425 면 아직 1차 실행 산출물이므로 재실행할 것
(약 4분, 백그라운드 권장).

그 다음 `python src\check_manuscript.py` — **현재 8건 실패가 정상이다.**
새 규칙이 원고의 옛 값을 잡고 있는 상태이고, STEP 1-2 에서 원고를 고치면 0 이 된다.

---

## 1. STEP 1 에서 확정된 계산 결과 (재계산 불필요)

| 항목 | 결과 |
|---|---|
| **F1 DPPM floor** | 12단 k=2 = **195.1 ppm**, 16단 k=4 = **406.2 ppm**. 원고의 371.0 / 770.1 은 **어떤 스크립트도 산출한 적 없는 손입력 값**이다(src·data 전수 검색 확인). A.2 닫힌형과 block_y 출력 두 경로로 독립 확인 |
| **M-d knee** | 25 ppm 격자의 425 는 **격자 인공물**. 5 ppm 에서 **410 ppm**. 직전 격자점 405 는 plateau 와 0.0019 차 |
| **S4 knee 불변성** | 5 ppm 해상도에서도 φ_f = 1/3/8/20 전부 410. **주장이 강해졌다** |
| **S1 gate0 임계 a** | 현행 1.39 / 10.26 은 φ_f 항이 빠진 값. φ_f=1 → **0.0 / 6.68**, φ_f=2.03 → 0.0 / 2.995, φ_f≥3 → 0.0 / 0.0. Check 8(b) 의 "φ_f < 2.03 에서만 내부최적" 과 정확히 맞물린다 |
| **F3 event-MC** | `data/block_y_mc_verify_log.txt` 에 400,000회 표본·4×SE 판정·전건 OK. **계산 완비, 원고 보고만 없음** |
| **S6 EVPPI** | `data/robustness_evppi_log.txt` 완비. 음수 추정치 노이즈 하한까지 논의됨. **보고만 없음** |

**S1 해석 (원고에 쓸 것):** 최종 검사 시간이 p_ship 에 비례하는데 고층수일수록
조기 폐기로 p_ship 이 작다. 즉 최종 검사 시간이 고층수에 덜 부과된다.
VII-F 의 k=1/k=4 반전 메커니즘("조기폐기가 최종테스트 시간까지 절약")의
**층수 버전**이며 논문 내부에서 이미 확립된 기제다.

---

## 2. 코드 변경 (완료, 미커밋)

- `src/transition_curve.py` — 350~500 을 5 ppm 격자로. knee·plateau·직전 격자점 출력
- `src/phi_final_wide.py` — `_ratio()` 분리 + `knee()` 를 거친격자 브래킷 + 5 ppm 이분탐색으로.
  전 구간 5 ppm 은 비용 3배라 회피했다 (추가 약 5회)
- `src/canonical.py` — `out["dppm_floors"]` 신설. A.2 닫힌형 직접 계산
- `src/check_manuscript.py` — knee 필수/옛 knee 금지, floor 필수, 371.0·770.1 금지

---

## 3. 다음 작업 — STEP 1-2 (원고 전파)

**425 → 410 을 전 파일에 반영.** 등장 위치 25곳:
paper_en.html 10곳(**초록 포함**), 07_Results.md 2, 11_Report.md 1, README.md 1,
make_figures.py 5(**그림에 하드코딩**), mix_vs_yield.py 2, phi_final_wide.py 3,
transition_curve.py 1.

주의 — 단순 치환 금지. `make_figures.py` 수정 후 **그림 재생성 필수**이고,
`phi_final_wide.py` 의 425 는 독스트링·헤더 문구다.
07_Results.md L169 는 "knee 는 400~425 ppm" 형태라 문장을 다시 써야 한다.

전파 후 `python src\check_manuscript.py` 가 0 이 되어야 한다.

---

## 4. 이번 세션의 자체 오류 (기록)

**패치 스크립트가 "OK" 를 출력했는데 파일이 안 바뀌어 있었다.** 두 건
(`canonical.py`, `phi_final_wide.py`). 원인은 `phi_final_wide.py` 가 CRLF 인데
앵커를 LF 로 만든 것이고, PowerShell 이 stderr 를 삼켜 AssertionError 가
보이지 않았다. **출력의 OK 를 믿고 산출물을 확인하지 않은 것**이 실질 원인이며,
심사자가 F1 에서 지적한 실패("인쇄된 것을 신뢰")와 같은 계열이다.

처방: 패처는 **쓰기 후 파일을 다시 읽어 새 내용이 있는지 검증**한다.
`must_appear` 인자를 받는 형태로 이미 전환했다. 이 방식을 유지할 것.

---

## 5. Round 4 잔여 계획

STEP 1-3 (gate0 에 φ_f 정식 반영 + 파이프라인 편입), STEP 2 (상호참조 검증기
`check_crossref.py` — F3·F4·M-b·S6 를 한 번에), STEP 3 (F1~F5), STEP 4 (M-a~M-f),
STEP 5 (S 항목 + 마감), STEP 6 (VIII-E 네 번째 항목).

상세는 직전 세션의 계획 참조. **재계산이 남은 것은 M-c 의 비균일 family 전환비 1점뿐이다.**