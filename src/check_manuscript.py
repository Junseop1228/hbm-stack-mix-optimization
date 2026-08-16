# -*- coding: utf-8 -*-
"""
check_manuscript.py — 원고의 수치를 정본 JSON 과 대조한다

배경
----
2라운드 심사 진단: "T-1 스테일 항목 24개 중 절반 이상이 '숫자는 스크립트가
갱신했지만 산문은 사람이 갱신하지 않았다' 는 하나의 원인에서 나온다."

사람이 체크리스트를 관리하는 방식으로는 재발을 막을 수 없다. 실제로 총이익을
기계 치환할 때 가수만 바꾸고 지수를 남겨 값이 8.7배로 부풀었고, 그것을 심사자가
먼저 발견했다.

방법
----
① **금지 문자열 검사** — 폐기된 값·표현이 원고에 남아 있는지. 지수 누락처럼
   "값 자체는 그럴듯한" 오류를 잡는 유일한 방법이다.
② **필수 문자열 검사** — 정본 값이 원고에 실제로 존재하는지.
③ **주장-실체 검사** — 개정 통지문이 주장한 것이 본문에 실재하는지 (2라운드 N1).
④ **언어 오염 검사** — 영문 원고에 한글, 국문 원고에 미번역 잔여.

exit code 1 로 종료하면 run_all 파이프라인이 중단된다.

사용: python src/check_manuscript.py
"""

import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

TARGETS = [
    ("paper/paper_ko.html", "ko"),
    ("paper/paper_en.html", "en"),
    ("docs/07_Results.md", "ko"),
    ("docs/11_Report.md", "ko"),
    ("README.md", "ko"),
]


# 철회·정정 이력 문맥에서는 구 값·구 주장의 인용이 정당하다.
# 일치 지점 주변 WINDOW 자 안에 아래 표지가 있으면 검출하지 않는다.
WITHDRAW = (
    "철회", "정정 이력", "정정 전", "초판", "종전", "폐기",
    "withdrawn", "withdraw", "first version", "earlier figures",
    "was wrong", "no longer", "superseded",
)
WINDOW = 300


def in_withdrawal_context(text, start, end):
    ctx = text[max(0, start - WINDOW): end + WINDOW]
    return any(w in ctx for w in WITHDRAW)


def load(path):
    p = os.path.join(ROOT, path.replace("/", os.sep))
    return open(p, encoding="utf-8").read() if os.path.exists(p) else None


def build_rules(C):
    """정본 JSON 에서 검사 규칙을 생성한다."""
    b = C["baseline"]
    tr = C.get("transition", {})
    mc = C.get("monte_carlo", {})
    corr = mc.get("correlation", {})
    nu = C.get("nonuniform_schedule", {})

    forbidden = []   # (패턴, 사유, 대체값)
    required = []    # (문자열, 사유)

    # ── 총이익 : 가수·지수 동시 검사 ────────────────────────
    tp = b["total_profit"]
    forbidden.append((r"9\.4182\s*(&times;|×|x)\s*10<sup>7</sup>",
                      "총이익 지수 오류 (가수만 치환하고 10^7 을 남긴 것)",
                      "%s × 10^%d" % (tp["mantissa"], tp["exponent"])))
    forbidden.append((r"1\.0866", "v1 총이익", tp["mantissa"]))

    # ── 가동률·듀얼·J ───────────────────────────────────────
    for bad, why, good in (
        (r"74\.6\s*%", "v1 본더 가동률", "%s %%" % b["util_bonder_pct"]),
        (r"62\.1\s*%", "구 인스턴스(ρ=0.8) 본더 가동률", "%s %%" % b["util_bonder_pct"]),
        (r"0\.31240", "v1 테스터 듀얼", str(b["duals"].get("C1b_tester"))),
        (r"0\.15953", "구 인스턴스 J", str(b["J"])),
        (r"0\.20840", "구 단일풀 듀얼", str(C["check8"]["single_pool_dual"])),
    ):
        forbidden.append((bad, why, good))

    # ── 병목 전환점 ────────────────────────────────────────
    if tr:
        for bad, why in ((r"1\.1398", "v1 전환점(φ_f=0)"),
                         (r"0\.5837|0\.584(?![0-9])", "v1 평탄값"),
                         (r"0\.8693", "v1 250ppm 전환점"),
                         (r"0\.7737", "v1 300ppm"), (r"0\.5928", "v1 400ppm")):
            forbidden.append((bad, why, "at_cap_200=%s / plateau=%s"
                              % (tr.get("at_cap_200"), tr.get("plateau"))))

    # ── 몬테카를로 ─────────────────────────────────────────
    if mc:
        forbidden.append((r"953\s*(draws|회)", "v1 실행가능 표본수",
                          str(mc.get("feasible"))))
        forbidden.append((r"47\.6\s*%", "v1 실행가능률",
                          "%s %%" % mc.get("feasible_pct")))
        forbidden.append((r"roughly 72\s*%|약 72\s*%|71\.9\s*%",
                          "v1 병목=테스터 확률",
                          "%s %%" % mc.get("p_bottleneck_tester_pct")))
        forbidden.append((r"35\.9\s*%", "v1 8단 중앙값", "share_8 median"))
        forbidden.append((r"0\.1527", "v1 J 중앙값", "J median"))

    # ── 상관계수 (2라운드 N5) ──────────────────────────────
    for name, bad_share, bad_bn in (("x", r"\+0\.476", None),
                                    ("theta", None, r"\+0\.417"),
                                    ("r", None, None)):
        if name in corr:
            if bad_share:
                forbidden.append((bad_share, "v1 %s→16단 상관" % name,
                                  str(corr[name]["share_16"])))
            if bad_bn:
                forbidden.append((bad_bn, "v1 %s→병목 상관" % name,
                                  str(corr[name]["tester_bottleneck"])))
    if "r" in corr:
        forbidden.append((r"\+0\.741", "v1 r→이익 상관",
                          str(corr["r"]["profit_per_s"])))
        forbidden.append((r"−0\.073|-0\.073", "v1 r→16단 상관",
                          str(corr["r"]["share_16"])))

    # ── 8단 관련 폐기 서술 ─────────────────────────────────
    for bad, why in (
        (r"8단 k=2 \(69\.3", "v1 믹스"),
        (r"8-high <i>k</i>=2 \(69\.3", "v1 믹스"),
        (r"8단 등장 메커니즘 \| \*\*미규명", "M1 정정으로 해소된 항목"),
        (r"8-high stacks enter the mix remains unexplained", "M1 정정으로 해소"),
        (r"charged to escapes only and not to time", "M1 이 폐기한 부록 A 문장"),
        (r"escape에만 곱한다|escape 에만 곱한다", "M1 이 폐기한 부록 A 문장"),
        (r"Monte Carlo over defect events is not performed",
         "M11 대응으로 event-MC 를 수행했으므로 모순"),
        (r"불량 발생 사건의 몬테카를로는 수행하지 않는다",
         "M11 대응으로 수행했으므로 모순"),
        (r"the capacity literature has no quality|캐파 문헌은 품질이 없다",
         "M9 대응으로 철회한 주장"),
        (r"\+0\.11\s*%.*\+1\.43\s*%|기회비용은 품질 제약 적용 시 총이익 \+0\.11",
         "VII-H 에서 철회한 수치"),
    ):
        forbidden.append((bad, why, "정정 필요"))

    # ── 필수 : 통지문 주장의 실체 (2라운드 N1) ─────────────
    required += [
        (r"t_final|t</i><sub>final</sub>|t<sub>final</sub>",
         "M1 정정 수식이 본문에 있어야 한다 (III-D)"),
        ("phi_final|φ<sub>f</sub>|&phi;<sub>f</sub>|φ_f",
         "φ_f 가 파라미터 표에 있어야 한다 (Table II)"),
    ]

    # ── 필수 : 신규 결과 ──────────────────────────────────
    if nu.get("16"):
        required.append((re.escape(str(nu["16"]["tester_time_saving_pct"])),
                         "비균일 스케줄 결과(테스터 시간 절감)가 보고돼야 한다"))
    if "phi_final_threshold" in C:
        required.append((re.escape(str(C["phi_final_threshold"])),
                         "임계 φ_f 가 보고돼야 한다"))
    if "c4_blending" in C:
        required.append((re.escape(str(C["c4_blending"]["predicted_16L_share_pct"])),
                         "C4 blending 예측값이 보고돼야 한다 (2라운드 N6)"))

    return forbidden, required


def main():
    jp = os.path.join(ROOT, "data", "canonical_results.json")
    if not os.path.exists(jp):
        print("!! data/canonical_results.json 이 없다. src/canonical.py 를 먼저 실행하라.")
        return 1
    C = json.load(open(jp, encoding="utf-8"))
    forbidden, required = build_rules(C)

    print("=" * 88)
    print("원고 대조 검사 — data/canonical_results.json 기준")
    print("=" * 88)
    print("금지 규칙 %d개 / 필수 규칙 %d개 / 대상 원고 %d개"
          % (len(forbidden), len(required), len(TARGETS)))
    print()

    fails = 0
    for path, lang in TARGETS:
        t = load(path)
        if t is None:
            print("  SKIP %s (없음)" % path); continue
        issues = []

        # ① 금지
        for pat, why, good in forbidden:
            for m in re.finditer(pat, t):
                if in_withdrawal_context(t, m.start(), m.end()):
                    continue          # 철회·정정 이력 서술은 정당한 인용이다
                ln = t[:m.start()].count("\n") + 1
                issues.append(("STALE", ln, m.group()[:40], why, good))

        # ② 필수 (논문 원고에만 적용)
        if path.startswith("paper/"):
            for pat, why in required:
                if not re.search(pat, t):
                    issues.append(("MISSING", 0, pat[:32], why, "-"))

        # ③ 언어 오염
        if lang == "en":
            for m in re.finditer(r"[가-힣]{2,}", t):
                ln = t[:m.start()].count("\n") + 1
                issues.append(("LANG", ln, m.group()[:20], "영문 원고에 한글 잔존", "-"))

        if issues:
            print("  [%s] %d건" % (path, len(issues)))
            seen = set()
            for kind, ln, tok, why, good in issues:
                key = (kind, tok, why)
                if key in seen:
                    continue
                seen.add(key)
                loc = ("L%d" % ln) if ln else "—"
                print("    %-8s %-6s %-42s %s" % (kind, loc, tok, why))
                if good != "-":
                    print("             → 정본: %s" % good)
            fails += len(issues)
        else:
            print("  [%s] OK" % path)

    print()
    if fails:
        print("!! 총 %d건. 원고가 정본과 어긋난다." % fails)
        print("   금지 규칙은 폐기된 값이 남아 있음을, 필수 규칙은 통지문이 주장한")
        print("   내용이 본문에 없음을 뜻한다.")
    else:
        print("★ 전 원고가 정본과 일치한다.")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
