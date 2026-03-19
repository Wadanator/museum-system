"""
export_pdf.py
-------------
Zoberie všetky SVG v rovnakom priečinku a skonvertuje ich na PDF.
Spusti: python3 export_pdf.py

Požiadavka: pip install cairosvg
"""

import os
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def ensure_cairosvg():
    try:
        import cairosvg
        return True
    except ImportError:
        print("[*] Instalujem cairosvg...")
        r = subprocess.run(
            [sys.executable, "-m", "pip", "install", "cairosvg"],
            capture_output=True, text=True
        )
        if r.returncode == 0:
            print("[✓] cairosvg nainstalovany\n")
            return True
        else:
            print(f"[!] Instalacia zlyhala:\n{r.stderr}")
            return False


def main():
    if not ensure_cairosvg():
        return

    import cairosvg

    svgs = [f for f in os.listdir(SCRIPT_DIR) if f.endswith(".svg")]

    if not svgs:
        print("[!] Ziadne SVG subory nenajdene.")
        return

    print("=" * 45)
    print(f"  Najdenych SVG: {len(svgs)}")
    print("=" * 45)

    ok = 0
    fail = 0

    for svg_name in svgs:
        base     = os.path.splitext(svg_name)[0]
        svg_path = os.path.join(SCRIPT_DIR, svg_name)
        pdf_path = os.path.join(SCRIPT_DIR, f"{base}.pdf")

        try:
            cairosvg.svg2pdf(url=svg_path, write_to=pdf_path)
            print(f"  [✓] {svg_name} → {base}.pdf")
            ok += 1
        except Exception as e:
            print(f"  [!] {svg_name} zlyhalo: {e}")
            fail += 1

    print("=" * 45)
    print(f"  OK: {ok}  |  Chyby: {fail}")
    print("=" * 45)


if __name__ == "__main__":
    main()