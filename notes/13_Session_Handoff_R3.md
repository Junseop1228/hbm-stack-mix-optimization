# 세션 인계 — HBM Stack Mix Optimization
**작성 2026.08.17 | 3라운드 심사 대응 완료**

---

## 0. 먼저 할 일

```powershell
cd "C:\Users\userPC\Desktop\Workspace\00_Active\2026_Summer\semconductor\HBM_Stack_Mix_Optimization"
git status --short
python src\check_manuscript.py    # 0건이어야 정상
git log --oneline -3
```

프로젝트 전반은 `notes/08_Handoff.md`, 심사 대응 판정은 `notes/12_Review_Response.md`.

---

## 1. 상태

| 항목 | 값 |
|---|---|
| 파이프라인 | **24단계 / 446.8 s 완주 확인** |
| 원고 대조 | **0건** (금지 37 · 필수 9 규칙 / 대상 4원고) |
| 논문 | **영문 단일**. EN PDF 14 pages |
| 국문판 | `paper/_archive_ko/` 로 동결 (삭제 아님) |
| 심사 잔여 | **없음.** Major·Minor·T-1 전량 처리 |

## 2. 이번 라운드에 처리한 것

**T-1 #17~#20** — 표 X·XIII·XIV 스테일 정정, 유일성·축퇴 검증 신설
**Minor 21항목** — 정의·표기(B군) 5건, 주장 강도(C군) 9건, 재현성·인용(A군) 5건, 표 재번호
**자체 발견 5건** — `notes/12_Review_Response.md` 15절

핵심 결과 하나. **기준 믹스는 유일하다.** 정수 층위 동점 해 4개는 전부 같은
생산 믹스이며 차이는 생산량 0 인 8단의 k 라벨뿐이다(y 의 축퇴). 연속 층위
비중 구간 폭 2.6e-5 %p. 97.3 % 의 소수 자리 보고가 방어된다.

## 3. 반드시 유지할 규칙

- **수치를 바꿨으면 `canonical.py`, 원고를 고쳤으면 `check_manuscript.py`.**
  둘 다 파이프라인 23·24단계이므로 `run_all.py` 만 돌려도 된다
- **원고가 인용하는 값을 산출하는 스크립트는 반드시 STEPS 에 있어야 한다.**
  CHECKS(파이프라인 제외)에 두면 스테일이 시간문제다. 표 XIII 이 그렇게 깨졌다
- 문자열 치환은 Python 스크립트 파일로. 항목별 독립 적용 + count 단언 + SKIP 로그
- 긴 실행은 터미널에서 직접 `python -u src\run_all.py`. MCP 는 4분에 끊긴다

## 4. 남은 판단 — 논문 중심 이동 (미결)

심사자가 3라운드에서 강제하지 않았으나 계속 가리키는 방향.

> 지금 = "선행 cost 계보에 용량제약을 더했다"
> 옮기면 = "escape 확률의 층별 구조가 최적 검사 스케줄의 비균일성을 강제한다"

계산은 `src/nonuniform_schedule.py` 에 완비(테스터 시간 68.8 % 절감,
L=16 전수 32,768개). 현재 VII-H 의 한 절이다.

**이번 라운드 판단은 "옮기지 않는다".** 재구성은 서론·기여·결론·초록을 다시 쓰게
되고, 심사자가 요구하지 않은 재구성은 통과 확률을 낮춘다. 다음 논문의 중심으로 남긴다.

논문 3층위 재편(구조적 결과 -> 임계 조건 -> 점 시나리오)도 미완이다.
`docs/07_Results.md` 는 이미 이 구조이나 논문은 섞여 있다.