# FastAPI + Playwright (headless Chromium) on Render
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from playwright.async_api import async_playwright, TimeoutError as PWTimeout

app = FastAPI()

class Payload(BaseModel):
    vehicle_number: str
    application_number: str

@app.get("/")
async def root():
    return {"ok": True, "msg": "parivahan-api running"}

@app.post("/get-number")
async def get_number(data: Payload):
    url = "https://vahan.parivahan.gov.in/vahanservice/vahan/ui/statevalidation/homepage.xhtml"

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        ctx = await browser.new_context()
        page = await ctx.new_page()
        try:
            # 1) Open homepage
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)

            # 2) Enter vehicle number
            await page.fill("#regnid", data.vehicle_number)

            # 3) Tick checkbox
            # Sometimes label is the clickable target
            cb = page.locator(".ui-chkbox-box")
            if await cb.count():
                await cb.first().click()

            # 4) Click Proceed (primary/alternate)
            clicked = False
            for sel in ["#proccedHomeButtonId", "#j_idt590"]:
                try:
                    await page.click(sel, timeout=3000)
                    clicked = True
                    break
                except Exception:
                    pass
            if not clicked:
                raise Exception("Proceed button not found")

            # 5) Optional popup 'Proceed'
            popup = page.locator(
                "//div[contains(@class,'right-position')]//button[.//span[contains(text(),'Proceed')]]"
            )
            if await popup.count():
                await popup.first().click()

            # 6) Navigate to Print Fitness Certificate
            await page.locator("a:has-text('Download Document')").first().click()
            await page.locator("a:has-text('Print Fitness Certificate')").first().click()

            # 7) Fill form + Verify
            await page.fill("#tf_reg_no", data.vehicle_number)
            await page.fill("#tf_appl_no", data.application_number)
            await page.locator("button:has(span:has-text('Verify Details'))").first().click()

            # 8) Extract mobile
            await page.wait_for_selector("#tf_mob_no", timeout=25000)
            mobile = (await page.input_value("#tf_mob_no")).strip()

            await browser.close()
            return {"ok": True, "mobile": mobile}

        except PWTimeout as e:
            await browser.close()
            raise HTTPException(status_code=504, detail=f"Timeout: {e}")
        except Exception as e:
            await browser.close()
            raise HTTPException(status_code=500, detail=str(e))
