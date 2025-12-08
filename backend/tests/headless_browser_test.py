#!/usr/bin/env python3
"""
Headless Browser Smoke Test - Verify UI components render correctly without user interaction.

This script uses Playwright to:
1. Navigate to frontend (http://localhost:3000)
2. Open Create Story modal
3. Verify form fields render
4. Submit story creation
5. Verify JobProgressCard appears
6. Confirm placeholder image and audio render
7. Wait for final video link (or timeout gracefully)

Requirements:
    pip install playwright
    playwright install

Usage:
    python platform/tests/headless_browser_test.py [--host http://localhost:3000] [--headless]

Environment:
    - Frontend must be running at {host}
    - Backend running at http://localhost:8000/api/v1
"""
import asyncio
import json
import sys
import argparse
import time
from datetime import datetime
from pathlib import Path

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    print("WARNING: playwright not installed. Install with: pip install playwright")
    print("Then run: playwright install")


class HeadlessBrowserTest:
    def __init__(self, frontend_url="http://localhost:3000", backend_url="http://localhost:8000", headless=True, verbose=True):
        self.frontend_url = frontend_url
        self.backend_url = backend_url
        self.headless = headless
        self.verbose = verbose
        self.browser = None
        self.page = None
        self.report = {
            "start_time": datetime.now().isoformat(),
            "steps": [],
            "placeholders_found": [],
            "errors": []
        }

    def log(self, msg, level="INFO"):
        if self.verbose:
            ts = datetime.now().isoformat()
            print(f"[{ts}] [{level}] {msg}")

    async def step(self, name, fn):
        """Execute a test step and record result."""
        self.log(f"Running: {name}")
        try:
            result = await fn()
            self.report["steps"].append({
                "name": name,
                "status": "ok",
                "result": result,
                "timestamp": datetime.now().isoformat()
            })
            self.log(f"✓ {name}", "SUCCESS")
            return result
        except Exception as e:
            self.log(f"✗ {name}: {e}", "ERROR")
            self.report["steps"].append({
                "name": name,
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            self.report["errors"].append({"step": name, "error": str(e)})
            raise

    async def navigate_to_dashboard(self):
        """Navigate to dashboard."""
        async def _run():
            await self.page.goto(f"{self.frontend_url}/", wait_until="networkidle")
            return {"url": self.page.url}
        return await self.step("Navigate to Dashboard", _run)

    async def verify_dashboard_visible(self):
        """Verify dashboard UI elements are visible."""
        async def _run():
            # Wait for main content
            await self.page.wait_for_selector("[class*='dashboard'], [class*='Dashboard'], h1", timeout=5000)
            
            # Check for Create Story button
            create_story_btn = await self.page.query_selector("button:has-text('Create Story'), button:has-text('✨'), a:has-text('Create Story')")
            if not create_story_btn:
                raise Exception("Create Story button not found")
            
            return {"dashboard_found": True, "create_story_button_found": True}
        return await self.step("Verify Dashboard UI", _run)

    async def click_create_story_button(self):
        """Click the Create Story button."""
        async def _run():
            # Try multiple selectors for the Create Story button
            selectors = [
                "button:has-text('Create Story')",
                "button:has-text('✨')",
                "[class*='CreateStory']",
            ]
            
            btn = None
            for selector in selectors:
                try:
                    btn = await self.page.query_selector(selector)
                    if btn:
                        break
                except:
                    pass
            
            if not btn:
                raise Exception(f"Create Story button not found with selectors: {selectors}")
            
            await btn.click()
            await self.page.wait_for_timeout(500)  # Wait for modal animation
            return {"button_clicked": True}
        
        return await self.step("Click Create Story Button", _run)

    async def verify_modal_appears(self):
        """Verify Create Story modal is visible."""
        async def _run():
            # Wait for modal content
            await self.page.wait_for_selector("[class*='modal'], [class*='Modal'], [role='dialog']", timeout=5000)
            
            # Check for form fields
            title_field = await self.page.query_selector("input[placeholder*='title'], input[placeholder*='Title'], label:has-text('Title')")
            if not title_field and not await self.page.query_selector("input[type='text']"):
                raise Exception("Title field not found in modal")
            
            return {"modal_visible": True, "title_field_found": True}
        
        return await self.step("Verify Modal Appears", _run)

    async def fill_and_submit_form(self):
        """Fill the Create Story form and submit."""
        async def _run():
            # Fill title
            title_input = await self.page.query_selector("input[type='text']")
            if title_input:
                await title_input.fill("Headless Test Story")
            
            # Fill description (optional)
            desc_inputs = await self.page.query_selector_all("textarea, input[type='text']")
            if len(desc_inputs) > 1:
                try:
                    await desc_inputs[1].fill("Testing UI with headless browser")
                except:
                    pass
            
            # Click submit button
            submit_btn = await self.page.query_selector("button:has-text('Start Story'), button:has-text('Create'), button:has-text('Submit')")
            if not submit_btn:
                submit_btns = await self.page.query_selector_all("button")
                if submit_btns:
                    submit_btn = submit_btns[-1]  # Last button is usually submit
            
            if not submit_btn:
                raise Exception("Submit button not found")
            
            await submit_btn.click()
            await self.page.wait_for_timeout(1000)  # Wait for submission
            return {"form_submitted": True}
        
        return await self.step("Fill and Submit Form", _run)

    async def verify_job_progress_card(self):
        """Verify JobProgressCard component appears."""
        async def _run():
            # Wait for progress card or status display
            selectors = [
                "[class*='JobProgress']",
                "[class*='progress']",
                "[class*='Progress']",
                ".progress-bar",
                "[role='progressbar']"
            ]
            
            found = False
            for selector in selectors:
                element = await self.page.query_selector(selector)
                if element:
                    found = True
                    self.log(f"  Found progress component: {selector}")
                    break
            
            if not found:
                raise Exception("JobProgressCard not found")
            
            return {"job_progress_card_visible": True}
        
        return await self.step("Verify JobProgressCard", _run)

    async def verify_placeholder_image(self):
        """Verify placeholder images are rendered."""
        async def _run():
            # Look for images in page
            images = await self.page.query_selector_all("img")
            self.log(f"  Found {len(images)} images on page")
            
            placeholders_found = []
            for img in images:
                src = await img.get_attribute("src")
                alt = await img.get_attribute("alt")
                if src and ("placeholder" in src.lower() or "static" in src.lower()):
                    self.log(f"  Placeholder image: {src}")
                    placeholders_found.append({"src": src, "alt": alt})
            
            # Also check for SVG
            svgs = await self.page.query_selector_all("svg")
            self.log(f"  Found {len(svgs)} SVG elements on page")
            
            if not placeholders_found and len(images) == 0 and len(svgs) == 0:
                self.log("  WARNING: No images or SVGs found (may be loading or placeholder text-based)", "WARN")
            
            self.report["placeholders_found"].extend(placeholders_found)
            return {"placeholder_images_found": len(placeholders_found) > 0 or len(svgs) > 0}
        
        return await self.step("Verify Placeholder Images", _run)

    async def verify_placeholder_audio(self):
        """Verify placeholder audio elements are present."""
        async def _run():
            # Look for audio elements
            audio_elements = await self.page.query_selector_all("audio")
            self.log(f"  Found {len(audio_elements)} audio elements")
            
            if len(audio_elements) == 0:
                self.log("  WARNING: No audio elements found (expected in ScenePreview)", "WARN")
            
            return {"audio_elements_found": len(audio_elements) > 0}
        
        return await self.step("Verify Placeholder Audio", _run)

    async def verify_responsive_layout(self):
        """Verify layout is responsive (test different viewport sizes)."""
        async def _run():
            viewports = [
                {"name": "mobile", "width": 375, "height": 667},
                {"name": "tablet", "width": 768, "height": 1024},
                {"name": "desktop", "width": 1920, "height": 1080}
            ]
            
            results = []
            for vp in viewports:
                await self.page.set_viewport_size({"width": vp["width"], "height": vp["height"]})
                await self.page.wait_for_timeout(200)
                
                # Check if layout is still accessible
                buttons = await self.page.query_selector_all("button")
                results.append({
                    "viewport": vp["name"],
                    "size": f"{vp['width']}x{vp['height']}",
                    "buttons_visible": len(buttons) > 0
                })
                self.log(f"  {vp['name']}: {len(buttons)} buttons visible")
            
            return {"responsive_viewports_tested": results}
        
        return await self.step("Verify Responsive Layout", _run)

    async def run(self):
        """Execute the headless browser test."""
        self.log("=" * 60)
        self.log("HEADLESS BROWSER SMOKE TEST - UI COMPONENT VERIFICATION")
        self.log("=" * 60)
        self.log(f"Frontend: {self.frontend_url}")
        self.log(f"Backend: {self.backend_url}")
        self.log(f"Headless: {self.headless}")
        
        try:
            async with async_playwright() as p:
                # Launch browser
                self.log("Launching browser...")
                self.browser = await p.chromium.launch(headless=self.headless)
                self.page = await self.browser.new_page()
                
                # Set viewport
                await self.page.set_viewport_size({"width": 1280, "height": 720})
                
                # Run tests
                await self.navigate_to_dashboard()
                await self.verify_dashboard_visible()
                await self.click_create_story_button()
                await self.verify_modal_appears()
                await self.fill_and_submit_form()
                await self.verify_job_progress_card()
                await self.verify_placeholder_image()
                await self.verify_placeholder_audio()
                await self.verify_responsive_layout()
                
                await self.browser.close()
            
            # Summary
            self.report["end_time"] = datetime.now().isoformat()
            self.report["success"] = len(self.report["errors"]) == 0
            self.print_summary()
            
            return self.report
        
        except Exception as e:
            self.log(f"BROWSER TEST FAILED: {e}", "ERROR")
            self.report["end_time"] = datetime.now().isoformat()
            self.report["success"] = False
            self.report["fatal_error"] = str(e)
            self.print_summary()
            return self.report

    def print_summary(self):
        """Print a human-readable summary."""
        self.log("")
        self.log("=" * 60)
        success_emoji = "✓" if self.report.get("success") else "✗"
        self.log(f"{success_emoji} BROWSER TEST SUMMARY")
        self.log("=" * 60)
        
        passed = sum(1 for s in self.report["steps"] if s["status"] == "ok")
        total = len(self.report["steps"])
        self.log(f"Steps Passed: {passed}/{total}")
        
        if self.report.get("placeholders_found"):
            self.log(f"Placeholders Found: {len(self.report['placeholders_found'])}")
        
        if self.report.get("errors"):
            self.log("Errors:")
            for err in self.report["errors"]:
                self.log(f"  - {err['step']}: {err['error']}")
        
        self.log("=" * 60)


async def main():
    parser = argparse.ArgumentParser(description="Headless Browser Smoke Test")
    parser.add_argument("--host", default="http://localhost:3000", help="Frontend URL")
    parser.add_argument("--backend", default="http://localhost:8000", help="Backend URL")
    parser.add_argument("--headless", action="store_true", default=True, help="Run in headless mode")
    parser.add_argument("--headed", action="store_true", help="Run in headed mode (show browser)")
    parser.add_argument("--json-report", action="store_true", help="Save JSON report")
    parser.add_argument("--output", default="browser_test_report.json", help="JSON report output file")
    args = parser.parse_args()
    
    if not PLAYWRIGHT_AVAILABLE:
        print("\n✗ Playwright not available. Install with:")
        print("  pip install playwright")
        print("  playwright install")
        sys.exit(1)
    
    headless = not args.headed
    tester = HeadlessBrowserTest(
        frontend_url=args.host,
        backend_url=args.backend,
        headless=headless,
        verbose=True
    )
    report = await tester.run()
    
    if args.json_report or "--json-report" in sys.argv:
        report_path = Path(args.output)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 JSON report saved to: {report_path.absolute()}")
    
    exit_code = 0 if report.get("success") else 1
    print(f"\nExit code: {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
