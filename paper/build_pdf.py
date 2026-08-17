# -*- coding: utf-8 -*-
"""
build_pdf.py — 논문 원고(HTML) → PDF

조판 규격 : IEEE Conference Paper Template (US Letter, 2단)
변환 경로 : HTML + ieee.css → Chrome headless --print-to-pdf

LaTeX 이 설치돼 있지 않은 환경이므로 Chrome 의 인쇄 엔진을 쓴다.
2026.08.17 부터 영문 단일 유지다. 국문판은 paper/_archive_ko/ 로 동결했다.

    python paper/build_pdf.py            # 영문판 생성
"""

import os
import re
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]

EDITIONS = {
    "en": ("paper_en.html", "HBM_Stack_Mix_Optimization_EN.pdf"),
}


def find_chrome():
    for p in CHROME_CANDIDATES:
        if os.path.exists(p):
            return p
    raise RuntimeError("Chrome/Edge 를 찾지 못했다. CHROME_CANDIDATES 를 확인하라.")


def pdf_page_count(path):
    """외부 라이브러리 없이 페이지 수를 센다."""
    raw = open(path, "rb").read()
    n = len(re.findall(rb"/Type\s*/Page[^s]", raw))
    if n == 0:  # 객체 스트림에 들어간 경우
        m = re.search(rb"/Count\s+(\d+)", raw)
        n = int(m.group(1)) if m else 0
    return n


def build(edition):
    src, out = EDITIONS[edition]
    src_path = os.path.join(HERE, src)
    out_path = os.path.join(HERE, out)
    if not os.path.exists(src_path):
        print("  SKIP %s (원고 없음)" % src)
        return None

    if os.path.exists(out_path):
        os.remove(out_path)

    url = "file:///" + src_path.replace("\\", "/")
    cmd = [find_chrome(), "--headless=new", "--disable-gpu",
           "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw",
           "--virtual-time-budget=10000",
           "--print-to-pdf=" + out_path, url]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    for _ in range(20):                      # 파일 flush 대기
        if os.path.exists(out_path):
            break
        time.sleep(0.5)
    if not os.path.exists(out_path):
        print("  FAIL %s\n%s" % (src, (r.stderr or "")[-800:]))
        return None

    kb = os.path.getsize(out_path) / 1024
    pages = pdf_page_count(out_path)
    print("  OK   %-42s %6.1f KB / %d pages / %.1fs"
          % (out, kb, pages, time.time() - t0))
    return out_path


def main():
    want = sys.argv[1:] or list(EDITIONS)
    print("논문 PDF 생성 — IEEE 2단 (US Letter)")
    made = [build(e) for e in want if e in EDITIONS]
    made = [m for m in made if m]
    print("\n생성 %d건" % len(made))


if __name__ == "__main__":
    main()
