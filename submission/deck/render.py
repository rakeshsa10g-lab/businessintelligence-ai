"""Render the Round 2 pitch deck: HTML slides -> PNG -> one PDF.

    python -m submission.deck.render

Renders every `submission/deck/slides/slide-*.html` file to a PNG at the
canvas's native 1600x900 (via Playwright driving the system-installed
Chrome — no browser download, no new heavy dependency), then combines the
PNGs into `submission/R2_BUSINESSINTELLIGENCE_PITCH.pdf` in slide order.

The hero screenshot embedded in slide 03 (`assets/hero_s1_workspace.png`)
is captured separately by `render/_capture_hero.py`, because it requires a
live run of the Streamlit app rather than a static HTML file. It is
committed as a static asset and this script does not regenerate it.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

DECK_DIR = Path(__file__).resolve().parent
SLIDES_DIR = DECK_DIR / "slides"
RENDER_DIR = DECK_DIR / "render"
PNG_DIR = RENDER_DIR / "png"
OUT_PDF = DECK_DIR.parent / "R2_BUSINESSINTELLIGENCE_PITCH.pdf"

SLIDE_W, SLIDE_H = 1600, 900


def render_slides_to_png() -> list[Path]:
    PNG_DIR.mkdir(parents=True, exist_ok=True)
    slide_files = sorted(SLIDES_DIR.glob("slide-*.html"))
    if not slide_files:
        raise SystemExit(f"no slide-*.html files found in {SLIDES_DIR}")

    png_paths: list[Path] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": SLIDE_W, "height": SLIDE_H}, device_scale_factor=2)
        for html_path in slide_files:
            page.goto(html_path.as_uri(), wait_until="networkidle")
            png_path = PNG_DIR / f"{html_path.stem}.png"
            page.screenshot(path=str(png_path), clip={"x": 0, "y": 0, "width": SLIDE_W, "height": SLIDE_H})
            png_paths.append(png_path)
            print(f"rendered {html_path.name} -> {png_path.relative_to(DECK_DIR.parent.parent)}")
        browser.close()
    return png_paths


def combine_to_pdf(png_paths: list[Path]) -> None:
    images = [Image.open(p).convert("RGB") for p in png_paths]
    images[0].save(OUT_PDF, save_all=True, append_images=images[1:])
    print(f"wrote {OUT_PDF.relative_to(DECK_DIR.parent.parent)} ({len(images)} pages)")


def main() -> None:
    png_paths = render_slides_to_png()
    combine_to_pdf(png_paths)


if __name__ == "__main__":
    sys.exit(main())
