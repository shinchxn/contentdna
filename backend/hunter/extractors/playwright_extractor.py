"""
backend/hunter/extractors/playwright_extractor.py
───────────────────────────────────────────────────
Uses Playwright Chromium (headless) to extract media from JavaScript-heavy pages.

Used as:
  a) Primary extractor for SOCIAL type URLs when gallery-dl fails.
  b) Fallback when scrapy returns fewer than 3 items.

Two-pronged approach:
  1. DOM scraping — after networkidle, query all media elements.
  2. Network interception — intercept all responses with image/* or video/*
     content-type and save them directly, catching lazy-loaded media that
     never appears in the static DOM.
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from typing import AsyncGenerator, Set
from urllib.parse import urlparse

from backend.hunter.media_item import MediaItem

logger = logging.getLogger(__name__)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"}
VIDEO_EXTS = {".mp4", ".webm", ".mov", ".avi", ".mkv"}


async def extract_media_playwright(
    url: str,
    max_items: int = 50,
) -> AsyncGenerator[MediaItem, None]:
    """
    Launch a headless Chromium browser, navigate to *url*, and yield
    MediaItems for all discovered images and videos.

    Parameters
    ----------
    url : str
    max_items : int
        Maximum number of media items to yield (safety cap).
    """
    from playwright.async_api import async_playwright

    logger.info("PlaywrightExtractor: navigating to %s", url)
    tmp_dir = tempfile.mkdtemp(prefix="contentdna_playwright_")
    discovered_urls: Set[str] = set()
    intercepted_items: list[MediaItem] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="ContentDNA/1.0 (+https://contentdna.io)",
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        # ── Network interception ─────────────────────────────────────────
        async def handle_response(response):
            if len(intercepted_items) >= max_items:
                return
            ct = response.headers.get("content-type", "").lower()
            resp_url = response.url

            if resp_url in discovered_urls:
                return

            if "image/" in ct and "svg" not in ct:
                try:
                    body = await response.body()
                    if len(body) > 2048:   # skip tiny icons
                        discovered_urls.add(resp_url)
                        intercepted_items.append(MediaItem(
                            url=resp_url,
                            path=None,
                            page_url=url,
                            media_type="image",
                            file_bytes=body,
                        ))
                except Exception:
                    pass

            elif "video/" in ct:
                try:
                    body = await response.body()
                    if len(body) > 10240:
                        discovered_urls.add(resp_url)
                        ext = ".mp4"
                        fname = os.path.join(tmp_dir, f"vid_{len(intercepted_items)}{ext}")
                        with open(fname, "wb") as f:
                            f.write(body)
                        intercepted_items.append(MediaItem(
                            url=resp_url,
                            path=fname,
                            page_url=url,
                            media_type="video",
                        ))
                except Exception:
                    pass

        page.on("response", handle_response)

        # ── Navigate ─────────────────────────────────────────────────────
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
        except Exception as exc:
            logger.warning("PlaywrightExtractor navigation failed: %s", exc)
            await browser.close()
            for item in intercepted_items:
                yield item
            return

        # ── DOM scraping ─────────────────────────────────────────────────
        # Images
        img_srcs = await page.eval_on_selector_all(
            "img[src]", "els => els.map(e => e.src)"
        )
        for src in img_srcs:
            if src and src not in discovered_urls and len(src) > 10:
                discovered_urls.add(src)
                intercepted_items.append(MediaItem(
                    url=src,
                    path=None,
                    page_url=url,
                    media_type="image",
                ))

        # Videos
        vid_srcs = await page.eval_on_selector_all(
            "video[src], source[src]", "els => els.map(e => e.src)"
        )
        for src in vid_srcs:
            if src and src not in discovered_urls:
                discovered_urls.add(src)
                intercepted_items.append(MediaItem(
                    url=src,
                    path=None,
                    page_url=url,
                    media_type="video",
                ))

        # OG image
        og = await page.get_attribute(
            "meta[property='og:image']", "content"
        )
        if og and og not in discovered_urls:
            discovered_urls.add(og)
            intercepted_items.append(MediaItem(
                url=og,
                path=None,
                page_url=url,
                media_type="image",
            ))

        await browser.close()

    logger.debug("PlaywrightExtractor: found %d items from %s",
                 len(intercepted_items), url)

    for item in intercepted_items[:max_items]:
        yield item
