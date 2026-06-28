"""
backend/hunter/extractors/playwright_extractor.py

Source: project/hunter/playwright_engine/examples/ → async page pattern
  - Copied: async with async_playwright() as p: chromium.launch(headless=True)
  - Copied: page.goto(url, wait_until="networkidle")
  - Copied: page.on("response", handler) for network interception
  - Modified: DOM scraping for img/video/og:image + response interception for image/* video/*
  - Used only as fallback when Scrapy returns < 3 items
"""
import asyncio
import logging
import os
import tempfile
from typing import Set
from backend.hunter.media_item import MediaItem

logger = logging.getLogger(__name__)


async def extract_media_playwright(url: str, max_items: int = 50):
    """
    Copied from playwright async page example:
      async with async_playwright() as p:
          browser = await p.chromium.launch(headless=True)
          page = await browser.new_page()
          await page.goto(url, wait_until="networkidle")

    Modified: intercept all image/video responses + DOM scraping.
    Used as fallback when Scrapy returns < 3 items.
    """
    from playwright.async_api import async_playwright

    tmp_dir = tempfile.mkdtemp(prefix="contentdna_playwright_")
    discovered: Set[str] = set()
    items: list[MediaItem] = []

    async with async_playwright() as p:
        # Copied pattern: chromium.launch(headless=True)
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="ContentDNA/1.0 (+https://contentdna.io)",
        )
        page = await context.new_page()

        # Copied pattern: page.on("response", handler) for image/* video/*
        async def handle_response(response):
            if len(items) >= max_items: return
            ct = response.headers.get("content-type", "").lower()
            resp_url = response.url
            if resp_url in discovered: return

            if "image/" in ct and "svg" not in ct:
                try:
                    body = await response.body()
                    if len(body) > 2048:
                        discovered.add(resp_url)
                        items.append(MediaItem(url=resp_url, path=None, page_url=url,
                                               media_type="image", file_bytes=body))
                except Exception: pass

            elif "video/" in ct:
                try:
                    body = await response.body()
                    if len(body) > 10240:
                        discovered.add(resp_url)
                        fpath = os.path.join(tmp_dir, f"vid_{len(items)}.mp4")
                        with open(fpath, "wb") as f: f.write(body)
                        items.append(MediaItem(url=resp_url, path=fpath, page_url=url,
                                               media_type="video"))
                except Exception: pass

        page.on("response", handle_response)

        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception as exc:
            logger.warning("Playwright navigation failed: %s", exc)
            await browser.close()
            for item in items: yield item
            return

        # DOM scraping — copied pattern: page.query_selector_all("img,video,source")
        for src in await page.eval_on_selector_all("img[src]", "els => els.map(e => e.src)"):
            if src and src not in discovered and len(src) > 10:
                discovered.add(src)
                items.append(MediaItem(url=src, path=None, page_url=url, media_type="image"))

        for src in await page.eval_on_selector_all("video[src],source[src]", "els => els.map(e => e.src)"):
            if src and src not in discovered:
                discovered.add(src)
                items.append(MediaItem(url=src, path=None, page_url=url, media_type="video"))

        og = await page.get_attribute("meta[property='og:image']", "content")
        if og and og not in discovered:
            discovered.add(og)
            items.append(MediaItem(url=og, path=None, page_url=url, media_type="image"))

        await browser.close()

    for item in items[:max_items]:
        yield item
