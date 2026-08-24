"""One-off: capture a real screenshot of the running Streamlit app (S1,
Workspace tab) for the pitch-deck hero slide. Not part of the reproducible
render pipeline — render.py embeds the resulting PNG as a static asset,
because the app requires a live model/session to reproduce this exact view.
"""
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(__file__).resolve().parent.parent / "assets" / "hero_s1_workspace.png"


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1000, "height": 2300}, device_scale_factor=2)
        page.goto("http://localhost:8503", wait_until="networkidle", timeout=60_000)
        page.wait_for_timeout(1500)

        run_btn = page.get_by_role("button", name="Run analysis")
        run_btn.wait_for(state="visible", timeout=15_000)
        run_btn.click()

        page.get_by_text("MATERIAL MOVEMENT").wait_for(state="visible", timeout=60_000)
        page.get_by_role("button", name="Raise the request").wait_for(state="visible", timeout=30_000)
        page.wait_for_timeout(600)

        container = page.locator('[data-testid="stMainBlockContainer"]').first
        btn = page.get_by_role("button", name="Raise the request")
        top = container.bounding_box()["y"]
        bottom = btn.bounding_box()["y"] + btn.bounding_box()["height"] + 24
        box = container.bounding_box()
        page.screenshot(
            path=str(OUT),
            clip={"x": box["x"], "y": top, "width": box["width"], "height": bottom - top + 20},
        )
        print(f"wrote {OUT}")

        browser.close()


if __name__ == "__main__":
    sys.exit(main())
