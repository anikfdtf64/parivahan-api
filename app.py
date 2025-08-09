from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from playwright.async_api import async_playwright, TimeoutError as PWTimeoutError
import asyncio

app = FastAPI()

@app.get("/")
def root():
    return {"ok": True, "msg": "parivahan-api running"}

@app.get("/search")
async def search(
    number: str = Query(..., min_length=4, max_length=20, alias="number"),
    appl: str = Query(..., min_length=6, max_length=30, alias="appl")
):
    """
    Query: /search?number=UP16EN4167&appl=DL23052982132739
    """
    url_home = "https://vahan.parivahan.gov.in/vahanservice/vahan/ui/statevalidation/homepage.xhtml"

    # small helper
    async def click_if_exists(page, selector=None, xpath=None, timeout=3000):
        try:
            if selector:
                await page.wait_for_selector(selector, timeout=timeout, state="visible")
                await page.click(selector)
                return True
            if xpath:
                el = await page.wait_for_selector(f"xpath={xpath}", timeout=timeout, state="visible")
                await el.click()
                return True
        except Exception:
            return False
        return False

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)  # Playwright image has browsers preinstalled
            context = await browser.new_context()
            page = await context.new_page()

            # STEP 1: open homepage
            await page.goto(url_home, wait_until="domcontentloaded", timeout=60000)

            # STEP 2: enter vehicle number
            await page.fill("#regnid", number)

            # STEP 3: tick checkbox
            await click_if_exists(page, selector=".ui-chkbox-box")

            # STEP 4: proceed (primary/alternate)
            proceeded = await click_if_exists(page, selector="#proccedHomeButtonId", timeout=5000)
            if not proceeded:
                proceeded = await click_if_exists(page, selector="#j_idt590", timeout=3000)
            if not proceeded:
                await context.close()
                await browser.close()
                return JSONResponse({"ok": False, "error": "Proceed button not found"}, status_code=400)

            # STEP 5: popup Proceed (if appears)
            await click_if_exists(
                page,
                xpath="//div[contains(@class,'right-position')]//button[.//span[normalize-space(text())='Proceed']]",
                timeout=4000
            )

            # STEP 6: go to Download Document → Print Fitness Certificate
            # Sometimes menu takes a moment to render
            await page.wait_for_load_state("domcontentloaded")
            clicked = await click_if_exists(page, xpath="//a[contains(.,'Download Document')]", timeout=10000)
            if not clicked:
                return JSONResponse({"ok": False, "error": "Download Document link not found"}, status_code=400)

            clicked = await click_if_exists(page, xpath="//a[contains(.,'Print Fitness Certificate')]", timeout=10000)
            if not clicked:
                return JSONResponse({"ok": False, "error": "Print Fitness Certificate link not found"}, status_code=400)

            # STEP 7: Fill form
            await page.fill("#tf_reg_no", number)
            await page.fill("#tf_appl_no", appl)
            await click_if_exists(page, xpath="//button[.//span[normalize-space(text())='Verify Details']]", timeout=10000)

            # STEP 8: extract mobile
            try:
                await page.wait_for_selector("#tf_mob_no", timeout=15000)
                mobile = await page.input_value("#tf_mob_no")
            except PWTimeoutError:
                mobile = None

            await context.close()
            await browser.close()

            if not mobile:
                return {"ok": False, "number": number, "appl": appl, "message": "Mobile number not found (maybe CAPTCHA/flow changed)"}

            return {"ok": True, "number": number, "appl": appl, "mobile": mobile}

    except Exception as e:
        # Any unexpected error
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
