# Technical Specification

**HBM 후공정 설비 제약 하 층수 구성 믹스 및 검사 주기 최적화**
v2.0 | 2026.08.12 (S4 — β_f 도입, C2 구속으로 8.2 갱신, 3.5 강제 경로 2개, single_k 정당화·기회비용)

> 본 문서의 모든 수치는 출처를 명시한다. 출처 없는 값은 "가정"으로 표기하고 민감도 분석 대상에 포함한다.

---

## 1. 문제 정의

> **제한된 후공정 조립·테스트 설비 처리량에서, 층수 구성별(8/12/16단) 생산 배분과 층 단위 주기 검사 패턴(3/6/12회)을 동시에 결정하여 양품 단위당 이익을 최대화한다.**

부제: 설비 한 단위를 더 높이 쌓는 데 쓸 것인가, 더 자주 검사하는 데 쓸 것인가.

### 1.1 핵심 상충 구조

| 방향 | 힘 | 근거 절 |
|---|---|---|
| 층수 ↑ | 수율이 **지수적으로** 하락 | 3.1 |
| 층수 ↑ | 매출은 **선형으로만** 증가 | 3.2 |
| 층수 ↑ | 조립시간의 **층수무관 고정성분**이 분산 | 3.3 |
| 층수 ↑ | **base die 오버헤드**가 희석 | 3.4 |
| 층수 ↑ | 고객 **용량 요구** 충족 가능 | 3.5 |

**앞의 둘은 낮은 층수에, 뒤의 셋은 높은 층수에 유리하다. 따라서 내부 최적점이 존재한다.**

검사 주기 k의 상충은 별도 축이다. **검사는 설비시간을 소모하는 동시에 불량 스택의 잔여 설비시간을 절약한다**(3.6절).

### 1.2 왜 지금 이 문제인가

**★ 단일 제품의 층수 사양이 16단에서 8단까지 후퇴하는 과정이 공개 기록으로 남아 있다 (2026년 8월 기준).**

> 1TB HBM4E 16-Hi 4-die → HBM4E 12-Hi → 4-die MCM 취소 → 2-die 패키지 → 192GB/256GB 변형 시험 → **주력 SKU 는 HBM4 8-Hi 192GB 유력, 최종 미확정**

**이것이 본 연구가 다루는 문제 그 자체다.** 고객이 공급 제약 때문에 층수를 낮추는 협상을 **지금** 하고 있고 답이 안 정해졌다. 원안은 NVIDIA GTC 2025 의 1TB HBM4E · 스택 16개 · 16-Hi 였고, 후퇴 사유는 2027년 DRAM 부족과 12-Hi HBM4E 검증·수율 램프업 불확실성이다 (TrendForce 2026-08-04, The Information 2026-08-06, SemiAnalysis).

**⚠️ 이 사안은 계속 움직인다. 위 서술은 2026년 8월 기준이며 인용 시 시점을 반드시 병기한다.**

TrendForce (2026-08-04): 2026년 3분기부터 NVIDIA가 Rubin Ultra의 HBM 구성을 원래의 12단 HBM4e에서 8단 HBM4e·12단 HBM4·8단 HBM4까지 확대 검토하기 시작했으며 **최종 스펙은 미정**이다. 주 원인은 2027년 DRAM 부족으로 HBM에 배분 가능한 웨이퍼 캐파가 제한되는 것이다.

> https://www.trendforce.com/presscenter/news/20260804-13166.html

**고객이 공급 제약 때문에 층수를 낮춰 협상 중이고, 답이 아직 정해지지 않았다.**

### 1.3 선행연구가 남긴 자리

두 계보가 독립적으로 같은 결론에 도달했다.

**TU Delft 3D-COSTAR 공식 도구 페이지**
> "There is not a 'one-size-fits-all' test flow that covers all stacked-die products."
> https://www.tudelft.nl/en/eemcs/the-faculty/departments/quantum-computer-engineering/sections/computer-engineering/3d-costar

**Agrawal & Chakrabarty (Duke ECE-2015-01), Conclusion**
> "Because of the interplay of given parameter values, optimal choices of tests and test insertions are dependent on problem instances; therefore, **a generic set of rules cannot be specified for minimizing cost**."

**둘 다 "조건별 최적해"를 후속 과제로 남겼다.** 본 연구가 그 요청에 응답한다.

---

## 2. 결정변수

| 기호 | 정의 | 정의역 |
|---|---|---|
| q_L | 층수 구성 L의 생산량 | L ∈ {8, 12, 16}, q_L ≥ 0 |
| k_L | 층수 구성 L의 검사 주기 | k ∈ {1, 2, 4} (매층/2층/4층마다) |

**검사 횟수 = 층수 ÷ 주기.** 12단 기준 k=1이면 12회, k=2면 6회, k=4면 3회.

### 2.1 왜 주기 패턴으로 제약하는가 — 이것이 기여 ④의 핵심

**계산 불가능성이 실재한다.** Agrawal & Chakrabarty가 수식으로 제시했다.

| 항목 | 수식 |
|---|---|
| 가능한 test insertion 수 | (l² + 3l − 2) / 2 |
| 가능한 test flow 수 | O(N^(l²)), N = insertion당 가용 test 수 |

l에 대입하면 이렇게 된다.

| 스택 | insertion 수 | 탐색공간 (N=3) | 논문 실측 |
|---|---|---|---|
| 4-die | 13 | 8.95×10⁷ | 전수탐색 73초 / A* 73,063 노드 |
| 4-die (N=6) | 13 | 1.13×10¹¹ | **전수탐색 28시간 9분** / A* 7분 10초 |
| 5-die (N=3) | 19 | — | **전수탐색 72시간** / A* 40분 |
| **9-die (8단 HBM)** | **53** | 3⁵³ ≈ 2×10²⁵ | **미실험** |
| **13-die (12단 HBM)** | **104** | 3¹⁰⁴ ≈ 10⁵⁰ | **미실험** |

**선행연구 실험 최대치가 5-die다. HBM 규모는 A*로도 불가능하다.**

### 2.2 주기 제약의 산업적 근거

SemiEngineering (2026-05-12, Anne Meixner): DRAM die는 로직 base die 웨이퍼 위에 적층되며 일련의 test insertion을 거친다. **조립업체의 공정에 따라 DRAM die 한 장을 쌓을 때마다, 또는 2장·4장을 쌓은 후에** 테스트할 수 있다. 그리고 **12단 die의 test insertion 수는 조립업체의 품질 수준에 따라 3회에서 12회까지 범위를 가진다.**

> https://semiengineering.com/hbm-shifts-testing-left-to-preserve-ai-chip-yield/

**관측된 하한 3과 상한 12가 정확히 12÷4와 12÷1이다.** 즉 현장은 이미 주기 패턴으로만 검사하며, 임의 조합을 쓰지 않는다.

**따라서 주기 제약은 계산 편의를 위한 임의 축소가 아니라 공정 현실의 반영이다.** 이것이 O(N^(l²))를 O(|K| × |L|)로 축소하면서도 정당성을 유지하는 근거다.

---

## 3. 모델 구조

### 3.1 수율 모델 — 복합수율 (교차 검증 완료)

**SemiAnalysis (2025-10-03), "Scaling the Memory Wall"**
> 한 층의 적층 수율이 x%일 때 전체 수율은 x%의 (전체 층수 − 1) 제곱으로 누적된다. 층당 99%인 8층 스택의 전체 수율은 92%가 된다. HBM은 후단에서 총 9층 또는 13층으로 적층된다 — 로직 base die 위에 DRAM 8층 또는 12층.
> https://newsletter.semianalysis.com/p/scaling-the-memory-wall-the-rise-and-roadmap-of-hbm

**nomadsemi (2025-06-03), "Deep Dive on HBM"**
> 수율 95%일 때 최종 수율은 8-Hi에서 66%, 16-Hi에서 44%가 된다.
> https://www.nomadsemi.com/p/deep-dive-on-hbm

**공식**

> Y_stack(L) = x^L
> x = 층당 접합 수율, L = DRAM 층수 (= bond step 수)

**검산 — 두 출처가 정확히 일치한다**

| 계산 | 값 | 출처 서술값 |
|---|---|---|
| 0.99⁸ | 92.3% | 92% |
| 0.95⁸ | 66.3% | 66% |
| 0.95¹⁶ | 44.0% | 44% |

**역산 검증 — 실제 수율 추정치와도 정합한다**

| 근거 | 값 | 역산 층당 수율 |
|---|---|---|
| HBM3E 12-hi 수율 65% 가정 사례 (ravikant.dev, 2026-04-23) | 65% | 0.65^(1/12) = **96.5%** |
| HBM4 제조 수율 60~70% 업계 추정 (PatSnap, 2025-09) | 60~70% | **96.0~97.0%** |

**보조 근거**: PatSnap 리포트는 8-Hi → 12-Hi 전환 시 수율이 15~20% 감소하고 16-Hi에서는 더 클 수 있다고 서술한다. 층당 96.5% 가정 시 계산값은 0.965⁸ = 75.4% → 0.965¹² = 65.4%로 약 13% 감소이며, 근사적으로 부합한다.

**시나리오 변수**: x (층당 접합 수율). 범위 0.94 ~ 0.99.

### 3.2 매출 모델 — 층수에 선형

**Silicon Analysts (2026-08 갱신)**
> HBM3는 GB당 약 8~10달러(24GB 스택 200달러), HBM3E도 GB당 약 8~10달러(36GB 스택 300달러). HBM4는 48GB 스택 약 500달러(추정).
> https://siliconanalysts.com/data/hbm-pricing

**비트당 단가가 층수·세대와 거의 무관하게 일정하다.** 8-Hi 24GB, 12-Hi 36GB, 16-Hi 48GB가 각각 동일 $/GB로 거래된다.

> R(L) = p × c × L
> p = 비트당 단가 ($/GB), c = 층당 용량 (GB/layer), L = 층수

HBM3E 기준 c = 3 GB/layer (36GB ÷ 12층). 24GB ÷ 8층 = 3 GB/layer로 일관.

**단, HBM4는 $10.4/GB로 소폭 상승한다.** 세대 프리미엄이므로 동일 세대 내 층수 비교에서는 p를 상수로 둔다.

### 3.3 조립 시간 모델 — 고정 + 변동 (이것이 프로젝트의 심장)

#### 3.3.1 구조적 근거

**접합 방식별 공정 구조** (Tom Hsu, "DRAM-301-1", Future Memory & Storage 2025, 2025-08-07)

| 공정 | 층마다 | 최종 |
|---|---|---|
| TC-NCF | 고온·고응력 열압착 → **접합 완성** | 없음 |
| MR-MUF (원조) | 배치만 | 전체 저온 mass reflow |
| **Advanced MR-MUF** | 저온·저응력 열압착(가고정) | 전체 mass reflow |

> https://files.futurememorystorage.com/proceedings/2025/20250807_DRAM-301-1_Tom-Hsu.pdf

**SemiAnalysis 보조 확인**: MR-MUF는 접합부 형성에 **배치 mass reflow + 단일 오버몰드**를 쓰는 반면, TC-NCF는 모든 층 각각에 완전한 TCB 단계로 접합부를 형성한다.

**→ MR-MUF 계열은 mass reflow와 몰딩이 층수와 무관하게 1회다. 명백한 고정 성분이다.**

#### 3.3.2 gang bonding — 고정/변동 구조의 정량적 근거

US 9524958 (Semiconductor device and method of individual die bonding followed by simultaneous multiple die thermal compression bonding):
> 각 die를 낮은 압력으로 짧게(1초) 개별 본딩한 뒤, 여러 die를 더 높은 온도·압력으로 더 긴 시간(5~10초) 동시에 열압착한다. chuck head가 3개 die를 수용하면 본딩 사이클 10초에 단위당 평균 3.3초, 1,080 UPH. 9개를 수용하면 총 사이클이 120초에서 40초로 감소.

**열압착 본더 UPH 수식** (US 8967452):
> UPH = (1/t₄) × 3600, gang bonding으로 n개 처리 시 UPH = (n/t₄) × 3600

**→ 개별 단계는 층수 비례, 동시 처리 단계는 묶음으로 분산. 2층 구조가 확인된다.**

#### 3.3.3 모델식

> T(L, k) = T_fix + t_stack × L + t_test × (L / k)

| 항목 | 의미 | 성격 |
|---|---|---|
| T_fix | mass reflow + 몰딩 + 로딩/언로딩 | **층수 무관** |
| t_stack × L | 층별 배치·가고정 | 층수 비례 |
| t_test × (L/k) | 검사 인서션 | 검사 횟수 비례 |

**★ 핵심 파라미터는 두 개로 분리된다** (06_Parameters 3.3). 리플로우·몰딩은 저가·고처리량 배치 설비라 **제약 자원이 아니므로**, 캐파와 원가에 같은 지표를 쓸 수 없다.

| 기호 | 정의 | 범위 | 쓰이는 곳 |
|---|---|---|---|
| **a** | **t_fix_a / t_stack** — 적층 전 고정시간이 층 1장 쌓는 시간의 몇 배인가 | 0 ~ 8 (기준 3) | **C1-a 캐파, 시나리오 B 축** |
| φ_cost | 원가에서 고정성분이 차지하는 비율. 리플로우·몰딩 **포함** | 0.1 ~ 0.6 | 원가식 |
| ψ | T_fix(a) / T_fix — 고정시간의 적층 전/후 분해비 | 0.1 ~ 0.4 (기준 0.2) | a의 산출 근거 |

**왜 φ_capacity가 아니라 a인가.** φ_capacity는 정의에 기준 층수 L_ref가 들어가 있어 **층수를 비교하는 목적함수에 쓰면 순환한다.** a는 무차원이고 L에 독립이며, 층수 최적점의 임계값이 이 단위로 직접 떨어진다.

**a가 클수록 높은 층수가 유리해진다.** Gate 0 계산으로 임계값이 확정됐다 (`src/gate0_threshold.py`, 2026.08.12).

| 기준 시나리오 (r=5, F=6, θ=3, x=0.965, β=0.95) | 임계 a | t_stack=5.4초 환산 |
|---|---|---|
| 8단 → 12단 전환 | **1.40** | t_fix_a ≈ 7.6초 |
| 12단 → 16단 전환 | **10.32** | t_fix_a ≈ 56초 |

**판정: 차별점 ③ 성립.** 8→12 임계가 현실 범위(a = 0~8) 한참 안쪽이다. 반면 16단 임계는 범위 밖이므로, **16단은 설비 경제성이 아니라 C2(고객 용량 수요)가 강제할 때만 선택된다** — 8.3의 해석 경로가 실제로 발동한다.

**층수무관 고정원가 F가 같은 방향으로 작용한다.** F ≥ 9면 **a = 0에서도** 12단이 최적이 된다. 즉 v1.2에서 t_fix_b를 캐파식에서 뺀 것은 고정성분 분산 효과를 없앤 것이 아니라 **분모에서 분자로 이동시킨 것**이다.

**민감도 순위** (임계 a의 이동 폭)

| 파라미터 | 범위 | 임계 a 이동 | 판정 |
|---|---|---|---|
| **x (층당 수율)** | 0.94 ~ 0.98 | **11.88 → 0.00** | **지배적. 시나리오 A가 주축인 이유** |
| F (고정원가) | 0 ~ 12 | 5.53 → 0.00 | 강함 |
| θ (검사시간 배수) | 1 ~ 30 | 0.94 → 6.41 | 중간 |
| **β (검출률)** | 0.84 ~ 1.0 | **1.61 → 1.32** | **미미. 미확보여도 무해** |

**β의 둔감성은 결론의 일부다.** 06_Parameters 6절이 β를 미확보로 남겼는데, 그 불확실성이 층수 결정에 거의 영향하지 않음이 확인됐다.

#### 3.3.4 확보된 처리량 수치

| 항목 | 값 | 출처 |
|---|---|---|
| TC-NCF 처리량 | 1,500~2,000 UPH 달성 가능. 이송 온도 개선으로 약 40% 향상 | Strothmann/Rezvani 외, C2W Collective Bonding, ECTC 계열 |
| Hybrid bonding | CMP 공정의 시간 소모로 UPH가 심각하게 병목 | aminext.blog (2026-03-04) |
| pick&place 시간 | 10초/스텝 | CATCH `assembly_process_definitions.xml`, 저자 주석 "Krutikesh와의 논의 근거" |
| bonding 시간 | 20초/스텝 | 동일 |
| bonding 동시처리 그룹 | 1 / 10 / 64 / 1,000 | 동일 |

**⚠️ 미확보: MR-MUF의 mass reflow·몰딩 사이클 타임 절대값.** SK하이닉스 고유 공정으로 비공개. **φ를 무차원 시나리오 변수로 두고 0.1~0.6 범위로 흔든다.**

### 3.4 base die 오버헤드

**Aehr Test, Vernon Rodgers** (SemiEngineering 2026-05-12):
> base logic die 하나와 8~16개 HBM을 생각해보라. base logic이 불량이면 16개 die가 함께 폐기되므로 수율 곡선에서 거대한 승수다.

**구조적 사실**: "12단 HBM"의 12는 core DRAM die 수이며 base die는 별도 1장이다. 즉 8-Hi = 총 9층, 12-Hi = 총 13층.

> 스택당 base die 원가 부담 = C_base / L

**L이 클수록 die당 오버헤드가 작아진다.** 높은 층수에 유리한 두 번째 힘.

**추가 역할**: base die는 적층 후 상부 core die에 접근하는 **유일한 경로**다(JEDEC Direct Access, IEEE 1500, MBiST 탑재). 본 모델에서는 base die 수율을 상수로 두되, 민감도 대상에 포함한다.

### 3.5 고객 수요 제약 — 층수를 강제하는 힘

> **⚠️ 2026.08.12 정정 — 강제 경로는 두 개다.** 이 절은 "슬롯이 8개로 고정이므로 총 용량 목표가 층수를 강제한다"를 전제해 왔다. 그런데 **스택 수는 세대 불변 상수가 아니다**(06_Parameters D1-b). Rubin Ultra 원안은 스택 **16개**였다. 따라서 총 용량 목표를 맞추는 경로는 **층수를 올리거나 스택 수를 늘리거나** 두 가지이며, **Rubin Ultra 는 후자를 시도했다가 후퇴한 실사례다.**
>
> **본 모델은 스택 수를 8개 고정으로 둔다. 이는 범위 한계이며 8.2 에 명시한다.** 스택 수를 결정변수로 넣으면 고객 패키지 설계까지 모델에 들어와 5주 범위를 벗어난다.

**Wing Venture Capital, "The Memory Triopoly" (2026-05-12)**
> B200은 24GB 스택 8개로 총 192GB, B300(Blackwell Ultra)은 HBM3E 12-Hi로 288GB.
> https://www.wing.vc/content/the-memory-triopoly

**GPU당 슬롯 수가 8개로 고정이다.** 총 용량 목표 G를 만족하려면 스택당 용량이 G/8 이상이어야 하고, 이것이 층수를 결정한다.

> 제약: Σ_L (q_L × c × L) ≥ 수요 세그먼트별 용량 요구
> 제품 세그먼트가 요구하는 최소 층수 L_min(segment)를 만족하는 구성만 해당 수요에 배정 가능

**즉 낮은 층수 제품이 자원 효율이 좋더라도 고용량 수요를 대체할 수 없다.**

### 3.6 검사 효과 모델 — 조기 폐기 (2026.08.11 확정)

k가 결정변수이려면 "검사를 늘리면 무엇이 좋아지는가"가 정의되어야 한다. 후보 3안 중 **① 조기 폐기**를 채택한다.

| 안 | 내용 | 판정 |
|---|---|---|
| **① 조기 폐기** | 불량 스택을 일찍 발견해 남은 층의 설비시간·재료를 아낀다 | **채택** |
| ② 수율 회복 | 검사 후 repair로 수율을 올린다 | 기각 |
| ③ 출하 품질 | escape를 줄여 DPPM 제약을 만족한다 | 목적함수에서는 기각, **C4 제약으로 유지** |

**채택 근거 3가지**

1. **목적함수와 단위가 일치한다.** 검사는 설비시간을 소모하는 동시에 설비시간을 절약한다. 같은 단위로 상충하므로 k의 내부 최적점이 형성된다. ③은 제약으로만 작동해 최적점을 만들지 못한다.
2. **MILP 선형성을 보존한다.** (L, k) 조합이 3×3 = 9개로 유한하므로, 조합별 기대 소모 층수·기대 검사 횟수를 **사전 계산해 상수 계수로 투입**할 수 있다. 최적화 문제에는 q_L만 변수로 남고 모델은 순수 선형을 유지한다. ②(repair)는 수리 성공 여부에 따라 이후 층의 상태가 갈려 계수가 상태 의존적이 되고, 시나리오 분기 또는 비선형이 유입된다. 5주 일정에서 감당 불가.
3. **파라미터 확보 가능성.** repair 성공률은 공개 자료가 사실상 없어 8.2의 "파라미터 공간" 원칙에 어긋난다. 조기 폐기는 층당 수율 x와 검출률 β만 요구하며 둘 다 근거 확보 경로가 있다.

#### 3.6.1 계산식

> 층 i에서 첫 불량이 발생할 확률: P(i) = x^(i−1) × (1 − x)
> 검사 지점: k, 2k, 3k, …, L / 각 지점의 검출률 β
> 층 i에서 불량 발생 시 검출되는 최초 지점: ⌈i/k⌉ × k

기대 소모 층수와 기대 검사 횟수는 다음 형태로 정의된다.

> E[layer](L, k) = Σ_i P(i) × d(i) + x^L × L
> E[test](L, k) = 폐기 이전까지 통과한 검사 지점 수의 기대값
> d(i) = 층 i 불량이 검출되어 폐기될 때까지 소모한 층수

β = 1이면 d(i) = ⌈i/k⌉ × k로 단순해진다. β < 1이면 첫 검사에서 놓친 불량이 다음 지점에서 잡히므로 d(i)는 기하분포 가중 평균이 되고, 마지막 지점까지 미검출된 분량이 **escape**로 출하되어 C4에 걸린다.

**closed form으로 떨어지며 몬테카를로가 불필요하다.** 이것이 (L, k) 9개 조합의 계수 사전 계산을 가능하게 한다.

투입 스택 1개당 기대 설비 점유시간은 Block T 의 T(L, k)와 결합해 다음이 된다.

> E[T](L, k) = T_fix(a) + t_stack × E[layer] + t_test × E[test] + P_complete(L,k) × T_fix(b)

**주의**: T_fix(b)를 소모하는 것은 양품이 아니라 **폐기되지 않고 끝까지 간 스택 전체**다. β < 1이면 미검출 불량(escape)도 몰딩까지 간다. 따라서 계수는 x^L이 아니라 P_complete = x^L + P_escape다. (04_Interface.md 5절에서 확정)

#### 3.6.2 파생 요구사항 — T_fix의 분해

3.3.3의 T_fix는 mass reflow와 몰딩이 주성분이며 **공정 최종 단계에 몰려 있다.** 중도 폐기된 스택은 이 시간을 쓰지 않는다. 따라서 T_fix를 두 성분으로 쪼개야 한다.

| 성분 | 내용 | 폐기 스택의 소모 여부 |
|---|---|---|
| T_fix(a) | 로딩·정렬 등 적층 이전 | 소모함 |
| T_fix(b) | mass reflow·몰딩 등 적층 이후 | 소모하지 않음 |

**분해 비율 미확정 → φ와 함께 Block T 파라미터로 남는다(10절 1·2번과 통합).**

#### 3.6.3 확정되는 귀결 3가지

1. **Y_stack은 k에 의존하지 않는다.** 검출률이 완전하면 k를 바꿔도 최종 양품 수는 동일하고, 달라지는 것은 불량 스택에 낭비한 설비시간과 die뿐이다. 따라서 Block Y 산출물은 Y_stack(L)과 E[layer](L,k) · E[test](L,k)로 **분리 표기한다**(7절 반영).
2. **DPPM은 k에 의존한다.** β < 1에서 발생하는 escape 경로를 통해서다. C4가 살아있는 이유이며 Block Y 산출물로 유지된다.
3. **목적함수 분모는 설비시간으로 확정된다**(10절 5번 해소). 양품 단위당으로 잡으면 조기 폐기의 이득이 재료비로만 나타나 메커니즘이 약해진다.

---
### 3.7 목적함수 (v1.4 정정, 2026.08.12)

> **maximize Σ_(L,k) [ R(L) − E[C](L,k) ] × q_(L,k)**
> = **총이익 최대화**, 캐파는 제약으로. 전제는 **생산량 전량 판매**(06_Parameters D7)

#### 3.7.1 ⚠️ 초안(분수형)을 폐기한 이유 — Phase 2에서 발견

초안은 **설비시간 단위당 이익**(분수형)을 목적함수로 두고 Charnes-Cooper 변환으로 선형화했다. 구현해 돌린 결과 **모든 캐파 제약의 shadow price가 0**으로 나왔고, 원인은 코드가 아니라 정식화였다.

> **분수형 목적함수는 규모에 무관하다(scale-invariant).**
> "시간당 이익을 최대화하라"는 지시에 대해 모델의 최적 대응은 **덜 만드는 것**이다.
> 캐파를 다 쓸 이유가 없으므로 C1-a·C1-b가 절대 구속되지 않고,
> **병목 판정(차별점 ①)이 정의 자체가 되지 않는다.**

#### 3.7.2 정정이 오히려 모델을 강화한다

캐파 제약이 구속되면 그 **shadow price가 곧 "설비시간 1초의 한계이익"**이다. 즉 단위당 지표를 목적함수로 강제할 필요가 없다 — **캐파 제약의 듀얼로 내생적으로 나온다.** 그리고 **병목 = 두 듀얼 중 큰 쪽**이다.

**검증 8에서 이 등식이 수치로 확인됐다.** 캐파를 단일 풀로 합쳤을 때 듀얼이 0.20754로, 직접 계산한 시간당 이익 0.20754와 소수점 다섯 자리까지 일치한다.

**이것이 차별점 ①의 직접 증거다.** "캐파 제약이 없으면 단위 시간당 한계이익도 병목도 정의되지 않는다"를 모델 안에서 보일 수 있다. Charnes-Cooper는 불필요해졌다.

#### 3.7.3 선행연구와의 관계는 유지된다

Agrawal & Chakrabarty가 total cost보다 **cost per good package**를 권한 것은(Fig. 7) **캐파 제약이 없고 생산량이 주어진 설정**에서다. 그들의 표현:
> "Using total cost as the objective function offsets the profit margin per good stack by 2% for this example, but for large examples, the profit margin may be significantly reduced."

캐파가 하드 제약이고 물량이 내생이면 **총이익 최대화가 곧 시간당 이익 최대화이며, 그 값이 듀얼로 나온다.** 두 목적함수가 등가가 되는 조건을 우리가 명시한 셈이다. 서론에서 인용하되 **"캐파 제약 하에서는 등가"**를 함께 밝힌다.

### 3.8 제약

| # | 제약 | 형태 |
|---|---|---|
| C1-a | **본더 처리량** | Σ_L q_L × E[T_bond](L, k_L) ≤ H_b |
| C1-b | **테스터 처리량** | Σ_L q_L × E[T_test](L, k_L) ≤ H_t |
| C2 | **고객 용량 수요** | 세그먼트별 최소 층수 및 물량 |
| C3 | **웨이퍼 공급** | Σ_L q_L × (L + 1) ≤ 가용 die 수 |
| C4 | **출하 품질** | outgoing DPPM ≤ 상한 |

**C1-a·C1-b가 이 프로젝트의 차별점 ①이다. 병목 판정 = 두 제약 중 shadow price가 큰 쪽.** 선행 문헌 계보 전체가 C1을 다루지 않는다 (6.2 참조).

**C3의 (L+1)**: core die L장 + base die 1장.

---

## 4. 해 탐색

### 4.1 방법

탐색공간이 |L| × |K| = 3 × 3 = 9개 구성이고, 각 구성의 생산량 q_L이 연속변수다.

> **혼합정수선형계획(MILP)** — 구성 선택은 이진, 생산량은 연속

Python + PuLP 또는 Gurobi(학술 라이선스). 규모가 작아 즉시 해결된다.

### 4.2 왜 A*나 메타휴리스틱을 쓰지 않는가

**주기 제약(2.1)으로 탐색공간을 이미 축소했기 때문이다.** Agrawal & Chakrabarty가 A*를 쓴 이유는 O(N^(l²)) 공간을 다뤄야 했기 때문이고, 우리는 그 공간을 산업적 근거로 제약해 MILP 규모로 만들었다.

**이 축소 자체가 기여다.** 방법론 신규성을 주장하지 않는다.

### 4.3 ⚠️ 전수탐색을 쓰지 않는다

Agrawal & Chakrabarty가 전수탐색을 baseline으로 두고 "현실적 시나리오에서 실행 불가능"으로 기각했다(4-die 6-test에서 28시간 9분). **전수탐색을 방법으로 내세우면 안 된다.**

---

## 5. 시나리오 (본체)

파라미터가 추정치이므로 점추정 최적해가 목표가 아니다. **최적 구성이 전환되는 임계 조건**을 규명한다.

| # | 시나리오 | 변동 파라미터 | 관찰 대상 | 우선순위 |
|---|---|---|---|---|
| **A** | **층당 수율** | x = 0.94 ~ 0.99 | 16단이 유리해지는 임계 x | **절대 유지** |
| **B** | **조립 고정성분 비율** | **a = 0 ~ 8**, φ_cost = 0.1 ~ 0.6 | 최적 층수의 이동 | **절대 유지** |
| **C** | **설비 캐파** | 가용 설비시간 ±50% | 어느 제약이 먼저 구속되는가 | **절대 유지** |
| D | 검사 효과 | 검출률 β = 0.84 ~ 0.99, 검사 단가 | 최적 주기 k의 전환점 | 유지 |
| E | 원가비 | base die 원가비, 검사비 | 임계값 이동 | 1순위 축소 |
| **F** | **층수 프리미엄** | p(L) 0 ~ 15% 상승 | **매출 선형성 가정의 강건성** | **신설 (06_Parameters 5.3)** |

**A·B·C가 주축이다.** 각각 차별점 ③·②·①에 대응한다.

### 5.1 불확실성 처리 절차

**Epoch AI (2026-03-12) 방식을 템플릿으로 차용한다.**
> 웨이퍼 가격, 패키징·로직 수율, 캐파 벤치마크, 제조 리드타임, HBM GB당 가격 등 모든 불확실 파라미터를 **삼각분포**로 모델링하고, 각 파라미터를 독립적으로 샘플링하는 **몬테카를로**를 돌려 결과를 **중앙값과 90% 신뢰구간**으로 보고한다. Epoch의 저작물은 출처와 저자를 밝히면 CC BY 라이선스로 자유 이용 가능하다.
> https://epoch.ai/data-insights/ai-chip-supply-chain-constraints

**대안 템플릿**: Ahmad et al., EuroSimE 2022 §6 — 27개 입력변수를 확률분포로 모델링(결함밀도·수요=정규분포, 조립수율=균등분포), 10,000회 몬테카를로, 토네이도 차트로 최대 민감 인자 식별. DOI 10.1109/EuroSimE54907.2022.9758914

### 5.2 파라미터 강건성 — 선행연구가 이미 확인

Agrawal & Chakrabarty (Fig. 11):
> "As the die yields vary, the selection of test insertions does not change rapidly, except for very high yields. **A minor deviation in the actual parameter values is not expected to significantly affect the selection of test flow.**"

**"파라미터가 추정치인데 괜찮나요"에 대한 답이 원 논문에 있다.** 인용한다.

---

## 6. 차별점 및 선행연구 대비 위치

### 6.1 차별점 4개

| # | 항목 | 선행연구 상태 | 검증 시나리오 |
|---|---|---|---|
| 1 | **설비 처리량 캐파 제약** | 계보 전체가 원가만 다룸. 시간 개념 부재 | C |
| 2 | **층수가 다른 이질적 제품의 설비 공유** | 전부 단일 제품·단일 스택. 하나의 설비 위에서 여러 층수 구성을 동시에 다루지 않음 | B |
| 3 | **층수를 결정변수로** | l은 given parameter | A |
| 4 | **대규모 스택 계산 가능성** | 실험 최대 5-die | 2.1 |

**⚠️ ②를 "제품 믹스가 발생한다"로 서술하면 안 된다 (2026.08.12 정정).** 구속 제약이 둘이면 기저 변수가 둘까지 나오는 것은 선형계획의 성질이므로, **"제약을 둘 넣었으니 당연한 것 아니냐"**는 반론에 방어가 안 된다. **②의 본질은 결과가 아니라 모델링 범위에 있다** — 선행 계보가 단일 제품·단일 스택인 것은 LP 기저와 무관한 문제 설정의 차이다.

**★ 그리고 ②에는 내용 측면의 발견이 따로 있다 — 이건 LP 기저와 무관하다.**

> **층수를 다양화하는 것과 검사 주기를 다양화하는 것은 서로 대체재다.**

`single_k` 를 풀어 12단이 k=2 와 k=4 를 동시에 가질 수 있게 하면 **16단이 C4 유무와 무관하게 사라진다**(32%→0%). 12단이 두 주기를 못 가지면 16단이 그 자리를 대신 떠맡는다 (`data/single_k_log.txt`).

**이것이 제안서 부제 "설비 한 단위를 더 높이 쌓는 데 쓸 것인가, 더 자주 검사하는 데 쓸 것인가"에 대한 직접적인 답이다. 두 축은 독립이 아니라 서로를 대신할 수 있다.** 층수와 검사를 동시에 결정변수로 놨기 때문에만 보이며 선행연구에 없다. **"제약을 둘 넣었으니 당연" 반론은 믹스의 존재를 공격하는 것이고, 이건 믹스의 내용에 대한 발견이라 별개다.**

### 6.2 문헌 지형도 (조사 완료)

| 영역 | 상태 | 대표 문헌 |
|---|---|---|
| 3D 적층 원가 모델 | ❌ 선점 | **3D-COSTAR** — Taouil, Hamdioui, Marinissen, Bhawmik, 3D-Test 2012 / **CATCH** — Graening, Talukdar, Pal, Chakrabarty, Gupta, IEEE TCAD 2025, DOI 10.1109/TCAD.2025.3597570, arXiv 2503.15753 |
| Test flow 선택 최적화 | ❌ 선점 | **Agrawal & Chakrabarty**, VTS 2013 / Duke ECE-2015-01 |
| Mid-bond test 원가 영향 | ❌ 선점 | Taouil 외, DFT 2013 |
| 층수 최적점 존재 | ❌ 선점 | IEEE Xplore 4114978 (2006) / Coskun, Kahng, Rosing, DSD 2009 |
| 품질-원가 trade-off, DPPM | ❌ 선점 | Taouil 외, VTS 2014 |
| Layer redundancy 원가 | ❌ 선점 | Taouil & Hamdioui, JETTA, DOI 10.1007/s10836-012-5314-3 |
| D2W 원가 프레임워크 | ❌ 선점 | Taouil, Hamdioui, Beenakker, Marinissen, JETTA 28(1), 2012, **Open Access**, DOI 10.1007/s10836-011-5270-3 |
| **설비 처리량 캐파 제약** | ✅ **공백** | 예산 제약 한 줄 언급뿐 |
| **제품 믹스·설비 공유** | ✅ **공백** | — |
| **층수를 결정변수로** | ✅ **공백** | — |
| **12~16단 계산 가능성** | ✅ **공백** | — |

### 6.3 유일한 자원 제약 언급 — 정확히 인용

Agrawal & Chakrabarty, Section VII:
> "When we have a limited supply of resources for manufacturing and testing of 3D-Stacked ICs, our approach can be adapted to report an optimal test flow **under an additional constraint on the total amount that can spent**. The A*-based method can discard nodes with the value of g(n) + h(n) exceeding the available resources."

**이것은 예산 제약(금액)이며 처리량 제약(시간)이 아니다. 그리고 "can be adapted"로 언급만 하고 구현하지 않았다.**

**추가 근거**: 이 논문은 시간 개념 자체가 없다. 테스트 비용을 전부 금액으로 다루고, "We use **the number of test patterns as a surrogate measure of test cost**"라고 명시한다. test time → 설비 점유 → 캐파 연결이 부재한다.

### 6.4 선행연구가 남긴 확장 지점

Agrawal & Chakrabarty, Section VII 말미:
> "Note also that different manufacturing flows lead to different manufacturing cost and die yield, which affect the optimal test flow. In order to evaluate manufacturing flows along with the associated test flows, the test-flow selection tool **must be invoked repeatedly**."

**제조 흐름(= 층수 선택)과 테스트 흐름을 동시 최적화하지 않고 반복 호출로 처리하라고 했다.** 본 연구가 이를 통합한다.

### 6.5 서론 구조 (확정)

> imec·Qualcomm·TU Delft 연구진은 "모든 적층 제품을 아우르는 만능 test flow는 없다"고 결론했고, Duke 연구진은 "원가 최소화를 위한 일반 규칙을 명시할 수 없다"고 밝혔다. 두 계보 모두 조건별 최적해를 후속 과제로 남겼다.
> 그러나 이 계보는 **원가만을 목적으로 하며 설비 처리량 제약을 다루지 않고**, 탐색공간이 O(N^(l²))로 증가해 실험 규모가 최대 5-die에 머문다. HBM의 12~16단은 계산 불가능하다.
> 본 연구는 층 단위 주기 패턴으로 탐색 구조를 제약해 대규모 스택을 다룰 수 있게 하고, 설비 처리량 제약과 층수 구성별 제품 믹스를 추가한다.

**"아무도 안 했다"가 아니라 "그들이 요청한 것을 생산관리 관점에서 한다"다.**

---

## 7. 모델 구성

모델은 두 모듈과 결합층으로 나뉜다. 두 모듈은 **서로 데이터를 주고받지 않고** 공통 입력 (L, k)만 공유한다.

| 모듈 | 영역 | 산출 |
|---|---|---|
| **Block T** | 설비·원가 | T(L,k), 설비 점유시간, 캐파 이용률, 총비용, 병목 판정 |
| **Block Y** | 수율·검사 | Y_stack(L), E[layer](L,k), E[test](L,k), escape 및 outgoing DPPM |
| **결합층** | 최적화·해석 | MILP 정식화, 시나리오 실행, 임계조건 도출 |

**한쪽 모듈만으로는 해가 결정되지 않는다.** 설비만 보면 "처리 빠른 구성 최대", 수율만 보면 "실패 적은 구성 최대"가 답이다. 두 모듈을 같은 목적함수에 넣어야 해가 하나로 정해진다. 인터페이스 규약은 `04_Interface.md`.

---

## 8. 검증 및 한계

### 8.1 검증 전략

| # | 방법 |
|---|---|
| 1 | **CATCH 원가식 구조 정합** — 테스트비 = 장비 초당비용 × 패턴수 × 스캔체인길이 × 클럭주기, Y_test = 1 − coverage × (1 − Y_true) |
| 2 | **극단값 검증** — x → 1이면 층수 무제한 유리, φ → 0이면 최소 층수 유리 |
| 3 | **문헌 재현** — 캐파 제약을 해제하면 선행연구 결론(층수 최적점 존재)이 재현되는가 |

### 8.2 명시할 한계

- **데이터 분석이 아니라 모델 기반 분석이다.** 인풋은 데이터셋이 아니라 **파라미터 공간**이다. 이 프레이밍을 먼저 제시한다
- **절대 금액을 쓰지 않는다.** die 원가 또는 stack 단가로 정규화한다. HBM 적층 수율·die 원가의 절대값은 전부 비공개로 확정됐다
- **"업계 최신 대비 신규"라고 주장하지 않는다.** "공개 문헌 기준"으로 한정한다
- **방법론 신규성을 주장하지 않는다.** MILP·몬테카를로는 확립된 도구이며, 기여는 문제 정식화와 구조 제약에 있다
- **조립 시간의 고정성분 절대값은 미확보다.** φ를 시나리오 변수로 처리하며, 결론은 φ 구간별로 제시한다
- **검사 효과는 조기 폐기로만 모델링한다.** repair에 의한 수율 회복은 범위 외다. 검출률 β를 단일 파라미터로 축약하며 불량 유형별 검출 특성은 반영하지 않는다
- **base die 수율은 상수로 둔다.** 결정변수가 아니다
- **단일 사업장·단일 기간 모델이다.** 다기간 계획, 다사업장 배분, 물류는 범위 외
- **~~T5 이전 구간의 모든 결과는 C2 비구속 조건 하의 것이다~~ → 2026.08.12 T5 에서 해소.** C2 는 현행 설정(cap 200 ppm, ≥12단 0.70)에서 **구속된다.** 상충 구조의 다섯 번째 힘이 처음으로 작동했고, **8.3 결과 해석 지침이 정정 대상이 아니라 검증 사례가 됐다** — 설비 경제성만 보면 8단이 69% 로 지배적인데 C2 가 12단 이상을 강제한다
- **업계 DPPM 값과의 직접 비교는 수행하지 않았다.** HBM 출하 DPPM 목표치의 공개 수치를 확보하지 못했으므로, 분모 단위(스택 대 die)와 분자 범위(우리 escape 는 접합 불량 미검출만 계상)의 정합 확인이 성립하지 않는다. **모델의 DPPM 은 내부 비교용이며 업계 절대 수준과 대조하지 않는다**
- **품질 목표와 최종 검사의 존재는 분리할 수 없다.** 200 ppm 이라는 목표는 최종 검사 없이는 달성 자체가 불가능하므로(β_f=0 이면 하한이 1,909 ppm), **"품질을 조이는 비용"을 최종 검사와 독립적으로 말할 수 없다.** 조건을 붙여 쓴다 — **최종 검사가 있는 조건(β_f=0.95)에서 출하 품질을 5,000 ppm 에서 200 ppm 으로 조이는 비용은 설비시간 단위당 이익 9.1% 다** (0.17546 → 0.15945, `data/transition_point_log.txt`)
- **층수마다 검사 주기를 하나만 선택한다**(`single_k`). **이것은 모델링 편의가 아니라 공정 현실 제약이다.** 2.1 이 검사 주기를 k ∈ {1,2,4} 로 제약한 근거가 "현장은 규칙적 패턴으로만 검사하며 7번 같은 값은 라인 운영이 안 된다"였고, **같은 층수 제품에 두 주기를 동시에 운영하는 것도 같은 이유로 라인 운영이 안 된다.** SemiEngineering(2026-05-12)이 "조립업체의 공정에 따라" 한 장/2장/4장마다 테스트한다고 쓴 것도 **업체·라인 단위 정책**을 뜻하지 같은 제품 안에서 주기를 섞는다는 뜻이 아니다.
  - **기회비용은 정량화됐다 — 1.5% 이내.** 제약을 풀면 총이익이 C4 적용 시 +0.11%, 미적용 시 +1.43% 늘어난다 (`data/single_k_log.txt`). **한계가 아니라 값이 매겨진 설계 선택이다.**
  - **범위 한계**: 해제하면 기준선(x=0.965)에서 16단이 사라지고 12단이 두 주기를 나눠 갖는다. 고수율 구간(x ≥ 0.980)의 결론은 이 선택과 무관하나, **층수 전환 구간의 배분은 민감하다** (S-1A, `data/single_k_xsweep_log.txt`)

### 8.3 결과 해석 지침 (사전 고정)

모델 결과가 낮은 층수를 지지할 경우 업계 동향(층수 상승)과 상반될 수 있다. **모델 실패가 아니다.**

| 결과 | 해석 |
|---|---|
| 낮은 층수 유리 | 설비 효율만 보면 낮은 층수 우위 → **층수 상승은 고객 용량 요구(3.5)가 강제하는 것이며 설비 경제성 때문이 아니다** |
| 높은 층수 유리 | 고정성분 분산과 base die 희석이 수율 하락을 상쇄 → 업계 동향과 정합 |

**4주차에 억지 해석을 방지하기 위해 사전 고정한다.**

---

## 9. 핵심 파라미터 요약

상세는 `06_Parameters.md`. 여기서는 모델 구조를 결정하는 것만 기재한다.

| # | 파라미터 | 값 / 범위 | 등급 | 출처 |
|---|---|---|---|---|
| 1 | 복합수율 공식 | Y = x^L | **A** | SemiAnalysis, nomadsemi 교차검증 |
| 2 | 층당 접합 수율 x | 0.94 ~ 0.99 (기준 0.965) | **B** | HBM3E 12단 65%, HBM4 60~70% 역산 |
| 3 | 비트당 단가 | $8~10/GB (세대 무관 근사 일정) | **B** | Silicon Analysts |
| 4 | 층당 용량 c | 3 GB/layer | **A** | 24GB/8층, 36GB/12층 일치 |
| 5 | 검사 주기 후보 | k ∈ {1, 2, 4} | **A** | SemiEngineering 2026-05-12 |
| 6 | 12단 인서션 수 | 3 ~ 12회 | **A** | 동일 |
| 6-1 | 검사 검출률 β | 0.84 ~ 0.99 (기준 0.95) | **B** | CATCH coverage sweep (IEEE TCAD 2025). 시나리오 D 변수 |
| 7 | 고정성분 비율 φ_cost | 0.1 ~ 0.6 | **C (가정)** | 미확보. 원가식 전용 |
| 7-1 | **고정시간 배수 a = t_fix_a / t_stack** | 0 ~ 8 (기준 3) | **C (가정)** | **캐파 축. 시나리오 B 주축** (3.3.3) |
| 8 | pick&place / bonding | 10초 / 20초 per step | **B** | CATCH XML, 저자 출처 명시 |
| 9 | TC-NCF 처리량 | 1,500~2,000 UPH | **B** | ECTC 계열 |
| 10 | 인서션당 추가비용 | 유닛당 $2~5 (패키지 레벨) | **B** | Mordor Intelligence 2026-02 |
| 11 | probe card 원가 | $500,000 (sacrificial pad 시 최대 80% 절감) | **A** | SemiEngineering 2026-05-12 |
| 12 | 병렬 테스트 | 64~128 site | **A** | 동일 |
| 13 | GPU 슬롯 수 | 8 (고정) | **A** | Wing VC |
| 14 | 웨이퍼 교환비 | HBM 1비트 ≈ DDR5 3비트 면적 | **B** | 다수 매체 일치 |

**등급 정의**: A = 학술 문헌·표준·1차 자료 명시 / B = 업계 매체·기업 발표 추론 / C = 합리적 가정 (근거 서술 필수)

### 9.1 ⚠️ 출처 간 불일치 1건

HBM이 AI 칩 원가에서 차지하는 비중에 대해 두 값이 존재한다.

| 값 | 출처 |
|---|---|
| **거의 절반** | SemiEngineering 2026-05-12 |
| **30~40%** | Silicon Analysts 2026-08 (B200은 8스택 $2,400로 로직 다이 원가 초과) |

**보고서에는 "30~50%"로 범위 표기하고 양쪽을 인용한다.** 단일 값으로 확정하지 않는다.

---

## 10. 미확정 — 1주차 확정 대상

| # | 항목 | 구분 |
|---|---|---|
| 1 | **설비 시간을 무엇으로 세는가** — UPH vs 스택당 초. **추가: T_fix의 (a)적층 전 / (b)적층 후 분해 비율** (3.6.2) | Block T |
| 2 | φ (고정성분 비율)의 현실적 범위 | Block T |
| 3 | ~~검사 효과 모델~~ → **조기 폐기로 확정** (3.6절) | ✅ 완료 |
| 4 | 수요 세그먼트 정의 — 몇 개로 나눌 것인가 | 공동 |
| 5 | ~~목적함수 분모~~ → **설비시간당으로 확정** (3.6.3) | ✅ 완료 |
| 6 | 블록 간 인터페이스 변수 목록 → `04_Interface.md` | 공동 |

---

## 11. 참고문헌

### 핵심 (필독)

1. **Agrawal, M. & Chakrabarty, K.**, "Test-Cost Modeling and Optimal Test-Flow Selection of 3D-Stacked ICs", Duke University ECE-2015-01. 예비판: IEEE VLSI Test Symposium (VTS) 2013. **무료 공개**
   https://dukespace.lib.duke.edu/items/021375fb-eba2-4d6c-a663-a3acdc274804/full
2. **Taouil, M., Hamdioui, S., Beenakker, C.I.M., Marinissen, E.J.**, "Test Impact on the Overall Die-to-Wafer 3D Stacked IC Cost", *JETTA* 28(1), 2012. **Open Access**, DOI 10.1007/s10836-011-5270-3
3. **Graening, A., Talukdar, J., Pal, S., Chakrabarty, K., Gupta, P.**, "CATCH: a Cost Analysis Tool for Co-optimization of chiplet-based Heterogeneous systems", *IEEE TCAD* 2025, DOI 10.1109/TCAD.2025.3597570. arXiv 2503.15753. 코드: https://github.com/nanocad-lab/CATCH (Apache-2.0)

### 원가 모델 계보

4. Taouil, M., Hamdioui, S., Marinissen, E.J., Bhawmik, S., "3D-COSTAR: A Cost Model For 3D Stacked ICs", 3D-Test 2012
5. Taouil, M. 외, "Using 3D-COSTAR for 2.5D Test Cost Optimization", 3DIC 2013, DOI 10.1109/3DIC.2013.6702351
6. Taouil, M., Hamdioui, S., Marinissen, E.J., "Cost modeling for 2.5D and 3D stacked ICs", *Handbook of 3D Integration Vol.4*, Wiley-VCH, DOI 10.1002/9783527697052.ch9
7. Taouil, M. 외, "Impact of Mid-Bond Testing in 3D Stacked ICs", DFT 2013
8. Taouil, M., Hamdioui, S., Marinissen, E.J., "Quality versus Cost Analysis for 3D Stacked ICs", VTS 2014, DOI 10.1109/VTS.2014.6818763
9. "Yield and Cost Modeling for 3D Chip Stack Technologies", IEEE Xplore 4114978
10. Ahmad, DeLaCruz, Ramamurthy, "Heterogeneous Integration of Chiplets: Cost and Yield Tradeoff Analysis", EuroSimE 2022, DOI 10.1109/EuroSimE54907.2022.9758914

### 캐파 계획 (OR 계열)

11. Hood, S., Bermon, S., Barahona, F., "Capacity Planning Under Demand Uncertainty for Semiconductor Manufacturing", *IEEE TSM* 16(2), May 2003
12. Barahona, F., Bermon, S., Günlük, O., Hood, S., "Robust capacity planning in semiconductor manufacturing", *Naval Research Logistics* 52(5): 459-468, 2005
13. Mönch, L., Uzsoy, R., Fowler, J.W., "A survey of semiconductor supply chain models Part I & III", *IJPR* 56, 2018

### 산업 자료

14. SemiEngineering, "HBM Shifts Testing Left To Preserve AI Chip Yield", 2026-05-12
15. SemiAnalysis, "Scaling the Memory Wall: The Rise and Roadmap of HBM", 2025-10-03
16. Hsu, T., "DRAM-301-1", Future Memory & Storage 2025, 2025-08-07
17. Epoch AI, Somala, V., "Advanced packaging and HBM, not logic dies, were the bottlenecks on AI chip production in 2025", 2026-03-12, CC BY
18. TrendForce, "DRAM Supply to Remain Tight in 2027...", 2026-08-04
19. Wing Venture Capital, "The Memory Triopoly", 2026-05-12
20. Silicon Analysts, "HBM Memory Pricing and Specifications (2026)", 2026-08
