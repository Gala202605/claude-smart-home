"""渲染所有的说明图片"""
import asyncio
from playwright.async_api import async_playwright

FILES = [
    ("方式一-架构图.html", "方式一-架构图.png"),
    ("方式一-架构图-Windows.html", "方式一-架构图-Windows.png"),
    ("方式一-架构图-Mac.html", "方式一-架构图-Mac.png"),
    ("效果对比图.html", "效果对比图.png"),
]

async def render_all():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for html_name, png_name in FILES:
            path = rf"E:\剪辑\彭小嫂\PXS social media\claude-smart-home\{html_name}"
            out = rf"E:\剪辑\彭小嫂\PXS social media\claude-smart-home\{png_name}"
            page = await browser.new_page(viewport={"width": 1080, "height": 1350})
            await page.goto(f"file:///{path}", wait_until="networkidle")
            await page.screenshot(path=out, full_page=True)
            await page.close()
            print(f"OK: {png_name}")
        await browser.close()

asyncio.run(render_all())
