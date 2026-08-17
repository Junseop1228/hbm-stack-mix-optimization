# -*- coding: utf-8 -*-
"""
check_layer_approx.py — III-C "약 4배 과대추정" 의 유도

조기 폐기를 무시하고 E[layer] 를 L 로 근사하면 층수 전환 임계 a 가 얼마나
이동하는지 수치로 보인다. 원고는 이 배수를 유도 없이 인용하고 있었다(3라운드 지적).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import gate0_threshold as G

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

KW = dict(theta=3.0, r=5.0, c_base=1.5, c_fix_b=4.5, c_test=0.012, x=0.965, beta=0.95)
buf = []


def P(s=""):
    print(s); buf.append(s)


def main():
    P("=" * 78)
    P("III-C 유도 — E[layer] 를 L 로 근사했을 때 층수 전환 임계 a 의 이동")
    P("=" * 78)
    P("  파라미터 : " + ", ".join("%s=%s" % kv for kv in sorted(KW.items())))
    P("")
    base = G.threshold(**KW)

    _orig = G.block_y

    def approx(L, k, x, beta, beta_f=0.0):
        """조기 폐기 무시 = 모든 스택이 L 층까지 적층됐다고 계상한다."""
        y = dict(_orig(L, k, x, beta, beta_f))
        y["e_layer"] = float(L)
        y["e_die"] = 1.0 + float(L)
        return y

    G.block_y = approx
    apx = G.threshold(**KW)
    G.block_y = _orig

    y16 = _orig(16, 1, KW["x"], KW["beta"])
    P("  E[layer] (L=16, k=1) = %.2f   vs   L = 16   (%.1f %% 작다)"
      % (y16["e_layer"], 100.0 * (1 - y16["e_layer"] / 16.0)))
    P("")
    P("  전환        기준(E[layer])   근사(L)      배수")
    for i, lab in enumerate(("8->12", "12->16")):
        if base[i] is not None and apx[i] is not None:
            P("  %-10s %12.3f %12.3f %9.2f" % (lab, base[i], apx[i], apx[i] / base[i]))
        else:
            P("  %-10s %12s %12s   %s"
              % (lab, base[i], apx[i], "근사 하에서는 탐색 범위 안에 전환이 없다"))
    P("")
    P("  → 8->12 단 임계 a 가 약 4배 과대평가된다. 원인은 조기 폐기를 무시하면")
    P("    폐기 손실이 E[layer] 가 아니라 L 에 비례하는 것으로 계상되고, 그 과대분이")
    P("    층수마다 다르게 작용해 층수 간 비교에서 증폭되기 때문이다.")
    P("=" * 78)
    open(os.path.join(ROOT, "data", "layer_approx_log.txt"), "w",
         encoding="utf-8").write("\n".join(buf))
    print("\n[저장] data/layer_approx_log.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())