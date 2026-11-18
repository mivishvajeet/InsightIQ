#!/usr/bin/env python3
"""
InsightIQ: Automated Screen Capture & Walkthrough Video Recorder.

Uses Playwright Chromium to:
1. Navigate across all 8 Streamlit workspaces.
2. Wait for reactive Plotly charts and Streamlit metrics to render.
3. Record a full HD session video in docs/assets/videos/insightiq_walkthrough.webm.
4. Capture high-resolution desktop screenshots of each module in docs/assets/screenshots/.
5. Compile an animated visual walkthrough GIF in docs/assets/screenshots/insightiq_walkthrough.gif.
"""

import os
import sys
import time
from pathlib import Path
from PIL import Image
from playwright.sync_api import sync_playwright

ROOT_DIR = Path(__file__).resolve().parents[1]
ASSETS_DIR = ROOT_DIR / "docs" / "assets"
SCREENSHOTS_DIR = ASSETS_DIR / "screenshots"
VIDEOS_DIR = ASSETS_DIR / "videos"

SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

PAGES = [
    {
        "name": "01_landing_page",
        "title": "Landing Page & System Architecture",
        "url": "http://localhost:8501/",
        "wait_selector": "h1",
    },
    {
        "name": "02_executive_dashboard",
        "title": "Executive Performance Dashboard",
        "url": "http://localhost:8501/Executive_Dashboard",
        "wait_selector": "div[data-testid='stMetric']",
    },
    {
        "name": "03_sales_analytics",
        "title": "Sales Analytics & Category Performance",
        "url": "http://localhost:8501/Sales_Analytics",
        "wait_selector": ".js-plotly-plot",
    },
    {
        "name": "04_customer_analytics",
        "title": "Customer Analytics & RFM Segmentation",
        "url": "http://localhost:8501/Customer_Analytics",
        "wait_selector": ".js-plotly-plot",
    },
    {
        "name": "05_operations_logistics",
        "title": "Operations & Fulfillment Logistics",
        "url": "http://localhost:8501/Operations_and_Logistics",
        "wait_selector": ".js-plotly-plot",
    },
    {
        "name": "06_business_investigation",
        "title": "Business Investigation Studio",
        "url": "http://localhost:8501/Business_Investigation",
        "wait_selector": "h1",
    },
    {
        "name": "07_ai_analyst",
        "title": "Autonomous AI Analyst Studio",
        "url": "http://localhost:8501/AI_Analyst",
        "wait_selector": "h1",
    },
    {
        "name": "08_reports",
        "title": "Executive Intelligence Reports",
        "url": "http://localhost:8501/Reports",
        "wait_selector": "button",
    },
    {
        "name": "09_evaluation_framework",
        "title": "Evaluation Framework & Benchmark Scorecard",
        "url": "http://localhost:8501/Evaluation_Framework",
        "wait_selector": "div[data-testid='stMetric']",
    },
]


def run_capture():
    print("🚀 Launching Playwright Chromium for HD screenshot & video capture...")
    captured_images = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            record_video_dir=str(VIDEOS_DIR),
            record_video_size={"width": 1440, "height": 900},
        )
        page = context.new_page()

        for item in PAGES:
            name = item["name"]
            title = item["title"]
            url = item["url"]
            selector = item["wait_selector"]
            out_path = SCREENSHOTS_DIR / f"{name}.png"

            print(f"📸 Capturing: {title} ({url})...")
            try:
                page.goto(url, wait_until="networkidle", timeout=45000)
                # Allow Streamlit WebSocket and Plotly animations to settle
                time.sleep(3.5)
                page.wait_for_selector(selector, timeout=15000)
                time.sleep(1.5)
            except Exception as e:
                print(f"  ⚠️ Warning waiting for selector '{selector}': {e}")
                time.sleep(3)

            # Snap screenshot
            page.screenshot(path=str(out_path), full_page=False)
            print(f"  ✓ Saved {out_path.name} ({out_path.stat().st_size // 1024} KB)")

            # Open for GIF generation
            try:
                img = Image.open(out_path).convert("RGB")
                # Downscale slightly for smooth GIF size
                img.thumbnail((1200, 750), Image.Resampling.LANCZOS)
                captured_images.append(img)
            except Exception as e:
                print(f"  Error loading image for GIF: {e}")

        # Close page and context to finalize video recording
        page.close()
        context.close()
        browser.close()

    # Rename video to permanent walkthrough filename
    video_files = list(VIDEOS_DIR.glob("*.webm"))
    if video_files:
        latest_video = max(video_files, key=lambda f: f.stat().st_mtime)
        final_video_path = VIDEOS_DIR / "insightiq_walkthrough.webm"
        if latest_video != final_video_path:
            latest_video.replace(final_video_path)
        print(f"🎬 Walkthrough video recorded at: {final_video_path} ({final_video_path.stat().st_size // 1024} KB)")

    # Build animated walkthrough GIF
    if captured_images:
        gif_path = SCREENSHOTS_DIR / "insightiq_walkthrough.gif"
        print("🎞️ Generating animated walkthrough GIF...")
        captured_images[0].save(
            str(gif_path),
            save_all=True,
            append_images=captured_images[1:],
            duration=3000,  # 3 seconds per slide
            loop=0,
            optimize=True,
        )
        print(f"✨ Animated GIF generated at: {gif_path} ({gif_path.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    run_capture()

