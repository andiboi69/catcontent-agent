"""Capture channel logo (800x800) and banner (2560x1440) as PNG files."""
import os
from playwright.sync_api import sync_playwright

PROJECT_DIR = os.path.dirname(__file__)

def capture():
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # --- Logo: 800x800 ---
        print("Capturing logo (800x800)...")
        page = browser.new_page(viewport={"width": 1200, "height": 1000})
        page.goto(f"file:///{PROJECT_DIR}/channel-logo.html".replace("\\", "/"))
        page.wait_for_timeout(2000)  # wait for fonts + animations

        logo_el = page.locator(".logo")
        logo_el.screenshot(path=os.path.join(PROJECT_DIR, "channel-logo.png"))
        print(f"  -> Saved: channel-logo.png")
        page.close()

        # --- Banner: 2560x1440 ---
        print("Capturing banner (2560x1440)...")
        page = browser.new_page(viewport={"width": 2560, "height": 1440})
        page.goto(f"file:///{PROJECT_DIR}/channel-banner.html".replace("\\", "/"))

        # Override the banner CSS to show at full size (remove the scale transform)
        page.evaluate("""
            document.querySelector('.banner').style.transform = 'none';
            document.querySelector('.banner').style.margin = '0';
            document.body.style.padding = '0';
            document.body.style.margin = '0';
            document.body.style.display = 'block';
            document.querySelector('.hint').style.display = 'none';
        """)
        page.wait_for_timeout(2000)

        banner_el = page.locator(".banner")
        banner_el.screenshot(path=os.path.join(PROJECT_DIR, "channel-banner.png"))
        print(f"  -> Saved: channel-banner.png")
        page.close()

        browser.close()

    print("\nDone! Files ready for YouTube upload:")
    print(f"  Logo:   {PROJECT_DIR}/channel-logo.png (800x800)")
    print(f"  Banner: {PROJECT_DIR}/channel-banner.png (2560x1440)")

if __name__ == "__main__":
    capture()
