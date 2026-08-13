# -*- coding: utf-8 -*-
"""
HBM Stack Mix Optimization — 공동 모델 모듈
2026.08.12 | Phase 2

★ 이 파일이 04_Interface.md 6절이 말하는 "결합 함수를 두는 공동 파일"이다.
   각자 자기 블록에서 결합 계산을 하면 두 벌이 생기고 반드시 어긋난다.
   결합은 여기서만 한다.

구성
----
  Block Y (수율·검사) : block_y()      — 확률·기대횟수. 01_Spec 3.6.1
  Block T (설비·원가) : Params 의 시간·원가 계수 — 공개 자료 미확보, placeholder
  결합층 (공동)   : coefficients()     — 04_Interface 6절

단위 규약 (04_Interface 8절)
---------------------------
  시간 : 초(second)
  원가 : core die 1장 = 1.0 로 정규화
  확률 : 0~1 실수
"""

from dataclasses import dataclass, field

L_SET = (8, 12, 16)
K_SET = (1, 2, 4)


# ======================================================================
# Block Y — 수율·검사 (01_Spec 3.6.1 조기 폐기 모델)
# ======================================================================

def block_y(L, k, x, beta, beta_f=0.0):
    """투입 스택 1개 기준 기대값. 04_Interface 4절 컬럼 명세.

    beta_f : 몰딩 후 최종 검사의 검출률 (S3-2, 2026.08.12 신설)

    최종 검사는 FormFactor(2026-05-12)가 명시한 HBM 표준 흐름 3단계 중 3번이며,
    SWTest 2017(FormFactor·Advantest)의 흐름도와 교차 확인됐다.
    1번(웨이퍼 레벨)은 x 에, 2번(적층 후 중간 검사)은 k 에 반영돼 있었으나
    3번이 모델에 없었다. beta_f = 0 이면 종전 모델과 완전히 동일하다.

    ★ 왜 beta_f 는 결정변수가 아닌가 (01_Spec 3.6)
      중간 검사는 **선택적**이고 최종 검사는 **상시**다(동 출처). 그래서 k 는
      결정변수, beta_f 는 파라미터다. 모델 구조가 문헌으로 정당화된다.

    ★ 왜 beta_f 를 시간·원가에 넣지 않는가
      최종 검사는 모든 완결 스택이 상시로 거치므로 (L, k) 와 무관한 고정
      성분이다. 목적함수에 상수를 더하는 것은 최적해를 바꾸지 않는다.
      넣으면 코드만 복잡해진다. **escape 에만 곱한다.**
    """
    npts = L // k
    p_good = x ** L
    e_layer = p_good * L
    e_test = p_good * npts
    p_escape = 0.0

    for i in range(1, L + 1):
        p_i = x ** (i - 1) * (1 - x)
        first = -(-i // k)
        m = npts - first + 1
        for j in range(1, m + 1):
            prob = p_i * ((1 - beta) ** (j - 1)) * beta
            pt = (first + j - 1) * k
            e_layer += prob * pt
            e_test += prob * (pt // k)
        miss = p_i * ((1 - beta) ** m)
        p_escape += miss
        e_layer += miss * L
        e_test += miss * npts

    # --- 04_Interface 4절 컬럼 정의 (S3-2 에서 확장) ---
    # p_escape_raw : 중간 검사를 전부 통과한 미검출 불량 (최종 검사 이전)
    # p_escape     : 최종 검사도 통과해 **실제로 출하되는** 불량
    # p_complete   : 적층을 끝까지 마친 스택 = mass reflow·몰딩 원가 부담 대상
    #                (최종 검사는 몰딩 **뒤**이므로 beta_f 와 무관하다)
    # p_ship       : 실제 출하량 = DPPM 의 분모
    p_escape_raw = p_escape
    p_escape = p_escape_raw * (1.0 - beta_f)
    p_complete = p_good + p_escape_raw
    p_ship = p_good + p_escape
    return {
        "L": L, "k": k,
        "e_layer": e_layer, "e_test": e_test,
        "p_good": p_good,
        "p_escape_raw": p_escape_raw, "p_escape": p_escape,
        "p_complete": p_complete, "p_ship": p_ship,
        "p_discard": 1.0 - p_complete,
        "e_die": 1.0 + e_layer,
        "dppm": (p_escape / p_ship * 1e6) if p_ship > 0 else 0.0,
    }


# ======================================================================
# 파라미터
# ======================================================================

@dataclass
class Params:
    # --- Block Y (06_Parameters 2절) ---
    x: float = 0.965          # 층당 접합 수율          [B등급]
    beta: float = 0.95        # 중간 검사 검출률         [B등급]
    beta_f: float = 0.95      # 최종 검사 검출률         [모델 기반 추정]
                              # 2026.08.12 S3-4 역산으로 확정.
                              # 자유 최적해의 출하 DPPM 이 277 ppm 이 되는 수준이며,
                              # "업계 수준(수백 ppm)을 재현하려면 얼마여야 하는가"의 답이다.
                              # 범위 0.87~0.99 는 시나리오로 처리한다.
                              # ⚠️ 문헌 실측이 아니다 — FormFactor(2026-05-12)와
                              #    SWTest 2017 로 **존재만** 확증했고 수치는 미확보다.
                              # ⚠️ 역산값이 beta(0.95)와 같은 수준으로 나왔다. 즉 모델은
                              #    최종 검사가 중간 검사보다 정확할 것을 요구하지 않는다.
                              #    **존재하기만 하면 된다.** beta_f > beta 제약은 걸지 않는다.
                              # beta_f = 0.0 으로 두면 종전 모델이 그대로 재현된다.

    # --- Block T : 시간 (06_Parameters 3절) — placeholder ---
    t_stack: float = 5.4      # 초/층. SemiAnalysis 3.6~7.2 중앙 [B등급]
    a: float = 3.0            # t_fix_a / t_stack               [C등급 ★핵심]
    theta: float = 3.0        # t_test  / t_stack               [C등급]
    phi_final: float = 1.0    # t_final / t_test                [미확보 ★2026.08.12 신규]
    # 최종 검사(가정 4)는 몰딩 후 완결 스택 전량이 거친다. HBM 최종 검사는
    # full-speed·전 채널·soak 를 포함하므로 in-line 개방/단락 검사보다 길다.
    # 절대값·비율 모두 공개 자료에 없다 → 시나리오 축으로 다룬다 (1, 3, 10).
    #
    # ★ 기준값을 분포의 최소값 1.0 으로 택한 이유
    #   φ_f 를 키우면 최종 검사 시간이 층수 무관 고정 부하로 작용해 높은 층수가
    #   유리해진다. 즉 φ_f 를 크게 잡으면 M1 정정으로 새로 얻은 결론(16단 우위)이
    #   강해진다. 근거 없이 그 방향을 택하는 것은 결과 맞춤이다. 따라서 M1 을
    #   정정하는 최소값(최종 검사가 in-line 검사 1회와 같은 시간)을 기준으로 두고,
    #   보고하는 효과를 하한으로 취급한다. φ_f 의존은 final_test_sweep.py 로 별도 보고.

    # --- Block T : 원가, core die = 1.0 정규화 ---
    r: float = 5.0            # 층당 매출
    c_die: float = 1.0
    c_base: float = 1.5       # base die 원가비          [C등급]
    c_fix_b: float = 4.5      # 적층 후 고정원가         [C등급]
    c_test: float = 0.012     # 검사 1회 비용            [B등급]
                              # 06_Parameters T18 : 유닛당 $2~5 → 무차원 0.007~0.017
                              # 2026.08.12 정정 — 종전 0.05 는 범위 상한의 3배였다

    # --- 제품 ---
    gb_per_layer: float = 3.0  # 06_Parameters D2         [A등급]
    layer_premium: float = 0.0  # 시나리오 F. 16단에서 $/GB 가 몇 % 오르는가
                                # 06_Parameters 5.3 (매출 선형성 반증 가능성)

    @property
    def t_fix_a(self):
        return self.a * self.t_stack

    @property
    def t_test(self):
        return self.theta * self.t_stack

    @property
    def t_final(self):
        """최종 검사 1회 시간. 완결 스택 전량이 거친다."""
        return self.phi_final * self.t_test


# ======================================================================
# 수요 — 절대 상수 (S1.5, 2026.08.12 동결)
# ======================================================================
# 종전에는 scenarios.make_demand() 가 기준 시나리오를 한 번 풀어 그 산출량의
# 40% / 18% 를 수요로 삼았다. **인과가 거꾸로다** — 고객 수요는 우리 공장 능력과
# 무관하게 정해진다. 그리고 파라미터를 바꿀 때마다 기준선이 따라 움직이면
# 시나리오 간 비교가 성립하지 않는다. 실제로 milp.py 는 60%/35%, scenarios.py 는
# 40%/18% 로 서로 다른 수요를 쓰고 있었다.
#
# 동결 시점 : 2026.08.12, c_test 를 0.012 로 정정한 뒤의 scenarios.py 기준선
#             (H_t/H_b = 0.90, x = 0.965, beta = 0.95)
# 동결 근거 : Phase 3 의 대표 결과·몬테카를로·정보가치 분석이 전부 이 값 위에
#             서 있다. milp.py 값으로 동결하면 Phase 3 전체가 무효가 된다.
#
# ⚠️ 이 값은 근거 있는 절대값이 아니다. T5(S3.5)에서 GPU 용량 목표
#    (슬롯 8개 x 제품별 총용량)에서 역산한 값으로 교체한다.
# ⚠️ 현재 이 수요 수준에서 C2 는 **비구속**이다 (듀얼 0). 01_Spec 1.1 상충 구조의
#    다섯 번째 힘(고객 용량 요구가 층수를 강제)이 작동하지 않는다. 01_Spec 8.2 참조.

# T5(S3.5) 확정 — GPU 용량 목표에서 역산 (2026.08.12)
#   슬롯당 용량 = 총용량 / 스택수, 층수 = 스택당용량 / 3GB
#     192GB급 (B200/GB200, Hopper)  → 24GB/stack → 8단
#     288GB급 (B300/GB300, Rubin)   → 36GB/stack → 12단
#   ≥12단 비중 0.70 — **구속 시작점(0.15)의 4.7배.**
#   TrendForce 2026-04-08 추정 구간 0.65~0.75 전 범위에서 C2 가 구속된다.
#   B300 대 B200 분리 비중은 미확보이므로 점추정이 아니라 구간으로 다룬다.
#
#   ★ 16단 세그먼트 = 0. 확정 고객 제품이 없다.
#     Rubin Ultra 원안은 1TB HBM4E · 스택 16개 · 16-Hi 였으나 후퇴 중이다
#     (16-Hi 4-die → 12-Hi → 4-die MCM 취소 → 2-die → HBM4 8-Hi 192GB 유력,
#      2026년 8월 기준 최종 미확정). 억지로 수요를 만들지 않는다.
DEMAND_SEG = ((8, 5.666e6), (12, 3.966e6))   # (최소 층수, 요구 양품 GB)
DEMAND_WAFER_DIES = 1.054e7                   # C3 웨이퍼 공급 상한 (die)


# ======================================================================
# 결합층 — 04_Interface 6절
# ======================================================================

def coefficients(p: Params):
    """(L,k) 조합별 계수. 전부 '투입 스택 1개' 기준이다."""
    out = {}
    for L in L_SET:
        for k in K_SET:
            y = block_y(L, k, p.x, p.beta, p.beta_f)

            # 설비 점유시간 — t_fix_b 는 캐파식에서 제외 (06_Parameters 3.3)
            tau_bond = p.t_fix_a + p.t_stack * y["e_layer"]
            # ★ M1 정정 (2026.08.12) — 최종 검사의 테스터 시간을 포함한다.
            # 종전에는 "(L,k) 무관 상수" 로 보고 제외했으나, 최종 검사를 받는
            # 스택 수는 p_ship(L,k) 이므로 조기 폐기를 통해 k·L 에 의존한다.
            # 원가식이 c_fix_b 를 p_ship 에 곱하는 것과 같은 성질의 항이다.
            # 최종 검사 비용은 c_fix_b 에 포함된 것으로 재정의한다(추가 미지수 없음).
            tau_test = p.t_test * y["e_test"] + p.t_final * y["p_ship"]

            # 원가 — t_fix_b 의 원가분은 여기 남는다
            cost = (p.c_base
                    + p.c_die * y["e_layer"]
                    + p.c_test * y["e_test"]
                    + y["p_complete"] * p.c_fix_b)

            # 매출 — escape 는 반품 처리로 미계상 (04_Interface 4절)
            # 시나리오 F : 층수 프리미엄. 8단=1.0, 16단=1+layer_premium 로 선형 보간
            prem = 1.0 + p.layer_premium * (L - 8) / 8.0
            revenue = p.r * L * y["p_good"] * prem

            out[(L, k)] = dict(
                y,
                tau_bond=tau_bond,
                tau_test=tau_test,
                tau=tau_bond + tau_test,
                cost=cost,
                revenue=revenue,
                profit=revenue - cost,
                gb_good=p.gb_per_layer * L * y["p_good"],
                ratio=(revenue - cost) / (tau_bond + tau_test),
            )
    return out


def best_by_ratio(coef):
    """캐파·수요 제약이 없을 때의 최적 구성. 검증 8번의 기준선."""
    return max(coef.items(), key=lambda kv: kv[1]["ratio"])
