# -*- coding: utf-8 -*-
"""
Gate 0 : 층수 최적점의 존재 조건 — 임계 a 계산
HBM Stack Mix Optimization | 2026.08.12

목적
----
목적함수 J(L,k) = (매출 - 원가) / 설비시간 이 층수 L에 대해 내부 최적점을 갖는
조건을 규명한다. 임계 a 가 현실 범위(0~8) 안에 있으면 차별점 ③(층수를 결정변수로)
이 성립하고, 밖이면 01_Spec 8.3 의 해석 경로로 전환한다.

단위 규약 (04_Interface 3절, 8절)
--------------------------------
시간 : t_stack = 1 로 정규화
    a     = t_fix_a / t_stack      적층 전 고정시간 배수
    theta = t_test  / t_stack      검사 1회 시간 배수
원가 : core die 1장 = 1.0 로 정규화
    c_base   base die 원가비
    c_fix_b  적층 후 고정원가 (mass reflow, 몰딩) — 완결 스택만 부담
    c_test   검사 1회 비용
    r        층당 매출

Block Y 계산식은 01_Spec 3.6.1 을 그대로 구현한다.
"""

import csv
import os

# ----------------------------------------------------------------------
# Block Y : 조기 폐기 모델 (01_Spec 3.6.1)
# ----------------------------------------------------------------------

def block_y(L, k, x, beta, beta_f=0.0):
    """투입 스택 1개 기준 기대값. 04_Interface 4절 컬럼 명세와 동일.
    beta_f 는 S3-2 신설. Gate 0 은 목적함수에 dppm 을 쓰지 않으므로
    기본값 0.0(최종 검사 없음)으로 두면 종전 결과가 그대로 재현된다."""
    npts = L // k                      # 검사 지점 수
    p_good = x ** L                    # 무결점 스택
    e_layer = p_good * L
    e_test = p_good * npts
    p_escape = 0.0

    for i in range(1, L + 1):
        p_i = x ** (i - 1) * (1 - x)   # 층 i 에서 첫 불량
        first = -(-i // k)             # ceil(i/k) : 검출 가능한 최초 지점 인덱스
        m = npts - first + 1           # 남은 검사 기회 수

        for j in range(1, m + 1):      # j 번째 기회에서 검출
            prob = p_i * ((1 - beta) ** (j - 1)) * beta
            pt = (first + j - 1) * k   # 그때까지 쌓은 층수
            e_layer += prob * pt
            e_test += prob * (pt // k)

        miss = p_i * ((1 - beta) ** m)  # 끝까지 미검출 = escape
        p_escape += miss
        e_layer += miss * L
        e_test += miss * npts

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


# ----------------------------------------------------------------------
# 자체 검증 (04_Interface 9절 1~6번)
# ----------------------------------------------------------------------

def verify(x=0.965, beta=1.0):
    fails = []
    for L in (8, 12, 16):
        for k in (1, 2, 4):
            y = block_y(L, k, x, beta)
            # 1 범위
            if not (1 <= y["e_layer"] <= L):
                fails.append("range e_layer L=%d k=%d" % (L, k))
            if not (0 <= y["e_test"] <= L // k + 1e-12):
                fails.append("range e_test L=%d k=%d" % (L, k))
            for key in ("p_good", "p_escape", "p_complete"):
                if not (0 <= y[key] <= 1 + 1e-12):
                    fails.append("range %s L=%d k=%d" % (key, L, k))
            # 2 항등식
            if abs(y["p_good"] + y["p_escape"] + y["p_discard"] - 1.0) > 1e-9:
                fails.append("identity L=%d k=%d" % (L, k))
            # 3 k 불변성
            if abs(y["p_good"] - x ** L) > 1e-12:
                fails.append("k-invariance L=%d k=%d" % (L, k))
        # 4 단조성 : k 증가 -> e_layer 증가, e_test 감소
        seq = [block_y(L, k, x, beta) for k in (1, 2, 4)]
        for p, q in zip(seq, seq[1:]):
            if q["e_layer"] < p["e_layer"] - 1e-12:
                fails.append("mono e_layer L=%d" % L)
            if q["e_test"] > p["e_test"] + 1e-12:
                fails.append("mono e_test L=%d" % L)

    # 5 극단값 A : x -> 1
    y = block_y(12, 2, 0.999999, 1.0)
    if abs(y["e_layer"] - 12) > 1e-3 or y["dppm"] > 1e-3:
        fails.append("extreme x->1")
    # 6 극단값 B : beta -> 0
    y = block_y(12, 1, 0.965, 1e-9)
    if abs(y["e_layer"] - 12) > 1e-6:
        fails.append("extreme beta->0 e_layer")
    if abs(y["p_escape"] - (1 - 0.965 ** 12)) > 1e-6:
        fails.append("extreme beta->0 escape")

    # 닫힌형 대조 : k=1, beta=1 에서 e_layer = (1-x^L)/(1-x)
    for L in (8, 12, 16):
        closed = (1 - x ** L) / (1 - x)
        got = block_y(L, 1, x, 1.0)["e_layer"]
        if abs(closed - got) > 1e-9:
            fails.append("closed-form L=%d" % L)
    return fails


# ----------------------------------------------------------------------
# 목적함수 (01_Spec 3.7, 04_Interface 6절) — 투입 스택 1개 기준
# ----------------------------------------------------------------------

def objective(y, a, theta, r, c_base, c_fix_b, c_test, c_die=1.0):
    revenue = r * y["L"] * y["p_good"]          # escape 는 매출 미계상 (04_Interface 4절)
    cost = (c_base
            + c_die * y["e_layer"]
            + c_test * y["e_test"]
            + y["p_complete"] * c_fix_b)
    time = a + y["e_layer"] + theta * y["e_test"]
    return (revenue - cost) / time


def best_L(a, theta, r, c_base, c_fix_b, c_test, x, beta, cache):
    best, arg = None, None
    for L in (8, 12, 16):
        for k in (1, 2, 4):
            y = cache[(L, k)]
            j = objective(y, a, theta, r, c_base, c_fix_b, c_test)
            if best is None or j > best:
                best, arg = j, (L, k)
    return arg


def threshold(theta, r, c_base, c_fix_b, c_test, x, beta,
              a_max=20.0, step=0.005):
    """L 최적해가 8->12, 12->16 으로 전환되는 임계 a. 없으면 None."""
    cache = {(L, k): block_y(L, k, x, beta) for L in (8, 12, 16) for k in (1, 2, 4)}
    sw = {}
    prev = best_L(0.0, theta, r, c_base, c_fix_b, c_test, x, beta, cache)[0]
    a = 0.0
    if prev != 8:
        sw["a_8_12"] = 0.0
        if prev == 16:
            sw["a_12_16"] = 0.0
    while a <= a_max:
        a += step
        cur = best_L(a, theta, r, c_base, c_fix_b, c_test, x, beta, cache)[0]
        if cur != prev:
            if prev == 8 and cur >= 12 and "a_8_12" not in sw:
                sw["a_8_12"] = round(a, 3)
            if cur == 16 and "a_12_16" not in sw:
                sw["a_12_16"] = round(a, 3)
            prev = cur
    return sw.get("a_8_12"), sw.get("a_12_16")


# ----------------------------------------------------------------------
# 실행
# ----------------------------------------------------------------------

BASE = dict(theta=3.0, c_base=1.5, c_test=0.012, x=0.965, beta=0.95)

def fmt(v):
    return "-" if v is None else ("%.2f" % v)

def main():
    out = []
    out.append("=" * 72)
    out.append("Gate 0 : 임계 a 계산")
    out.append("=" * 72)

    f = verify()
    out.append("[검증] Interface 9절 1~6번 + 닫힌형 대조 : %s"
               % ("PASS (0 fail)" if not f else "FAIL " + str(f)))
    out.append("")

    # Block Y 9조합 표
    out.append("[Block Y] x=0.965, beta=0.95  (06_Parameters 기준값)")
    out.append("  L   k   e_layer   e_test   p_good   p_escape  dppm")
    rows = []
    for L in (8, 12, 16):
        for k in (1, 2, 4):
            y = block_y(L, k, BASE["x"], BASE["beta"])
            out.append("  %2d  %2d   %7.3f  %7.3f  %7.4f  %8.4f  %6.0f"
                       % (L, k, y["e_layer"], y["e_test"],
                          y["p_good"], y["p_escape"], y["dppm"]))
            rows.append(y)
    out.append("")

    # 임계 a 격자
    r_list = [3, 4, 5, 6, 8]
    F_list = [0, 3, 6, 9, 12]
    out.append("[임계 a] 8->12 전환 / 12->16 전환   (theta=3, c_base=1.5, x=0.965)")
    out.append("  F = c_base + c_fix_b (층수무관 고정원가)")
    hdr = "   r \\ F  " + "".join("%13s" % ("F=%d" % F) for F in F_list)
    out.append(hdr)
    grid = []
    for r in r_list:
        line = "   r=%-4d " % r
        for F in F_list:
            c_fix_b = max(0.0, F - BASE["c_base"])
            t1, t2 = threshold(BASE["theta"], r, BASE["c_base"], c_fix_b,
                               BASE["c_test"], BASE["x"], BASE["beta"])
            line += "%13s" % ("%s / %s" % (fmt(t1), fmt(t2)))
            grid.append(dict(r=r, F=F, a_8_12=t1, a_12_16=t2))
        out.append(line)
    out.append("")

    # 민감도 : x
    out.append("[민감도] 층당 수율 x  (r=5, F=6)")
    out.append("     x     a(8->12)   a(12->16)")
    sens_x = []
    for x in (0.94, 0.95, 0.965, 0.98, 0.99):
        t1, t2 = threshold(BASE["theta"], 5, BASE["c_base"], 4.5,
                           BASE["c_test"], x, BASE["beta"])
        out.append("   %.3f    %8s    %8s" % (x, fmt(t1), fmt(t2)))
        sens_x.append(dict(param="x", value=x, a_8_12=t1, a_12_16=t2))
    out.append("")

    # 민감도 : theta
    out.append("[민감도] 검사시간 배수 theta  (r=5, F=6)")
    out.append("   theta   a(8->12)   a(12->16)")
    sens_t = []
    for th in (1.0, 3.0, 10.0, 30.0):
        t1, t2 = threshold(th, 5, BASE["c_base"], 4.5,
                           BASE["c_test"], BASE["x"], BASE["beta"])
        out.append("   %5.1f    %8s    %8s" % (th, fmt(t1), fmt(t2)))
        sens_t.append(dict(param="theta", value=th, a_8_12=t1, a_12_16=t2))
    out.append("")

    # 민감도 : beta
    out.append("[민감도] 검출률 beta  (r=5, F=6)")
    out.append("    beta   a(8->12)   a(12->16)")
    for b in (0.84, 0.95, 0.99, 1.0):
        t1, t2 = threshold(BASE["theta"], 5, BASE["c_base"], 4.5,
                           BASE["c_test"], BASE["x"], b)
        out.append("   %.3f    %8s    %8s" % (b, fmt(t1), fmt(t2)))
    out.append("")

    # 반례 : E[layer] 를 L 로 근사했을 때 (외부 리뷰가 쓴 모델)
    out.append("[대조] E[layer]=L 근사 + 원가항 제외 (외부 리뷰 모델)")
    out.append("   a     L=8      L=12     L=16    best")
    for a in (0, 2, 3, 4, 6, 8, 16):
        vals = []
        for L in (8, 12, 16):
            vals.append(L * BASE["x"] ** L / (a + L))
        out.append("  %2d  %7.4f  %7.4f  %7.4f    %d"
                   % (a, vals[0], vals[1], vals[2],
                      (8, 12, 16)[vals.index(max(vals))]))
    out.append("")
    out.append("[대조] E[layer] 실제값 사용 + 원가항 제외")
    out.append("   a     L=8      L=12     L=16    best")
    el = {L: block_y(L, 1, BASE["x"], 1.0)["e_layer"] for L in (8, 12, 16)}
    for a in (0, 2, 2.5, 3, 4, 6, 8):
        vals = [L * BASE["x"] ** L / (a + el[L]) for L in (8, 12, 16)]
        out.append("  %4.1f %7.4f  %7.4f  %7.4f    %d"
                   % (a, vals[0], vals[1], vals[2],
                      (8, 12, 16)[vals.index(max(vals))]))

    text = "\n".join(out)
    print(text)

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "data", "gate0_thresholds.csv"),
              "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["r", "F", "a_8_12", "a_12_16"])
        w.writeheader()
        w.writerows(grid)

    with open(os.path.join(root, "data", "block_y_output.csv"),
              "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["L", "k", "e_layer", "e_test",
                                           "p_good", "p_escape", "p_complete",
                                           "e_die", "dppm"])
        w.writeheader()
        for y in rows:
            w.writerow({key: y[key] for key in w.fieldnames})

    with open(os.path.join(root, "data", "gate0_log.txt"),
              "w", encoding="utf-8") as fh:
        fh.write(text)


if __name__ == "__main__":
    main()
