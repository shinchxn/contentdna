"""
backend/hunter/extractors/scrapy_extractor.py
───────────────────────────────────────────────
Crawls a website using Scrapy to discover all embedded media URLs.

Spider strategy:
  - Finds media via CSS selectors: img[src], video[src], source[src],
    meta[property=og:image], a[href] pointing to media files.
  - Follows internal links up to *max_depth* levels deep.
  - Respects *max_pages* limit.
  - Runs inside the current asyncio event loop using CrawlerRunner
    (not CrawlerProcess, which creates its own loop).

Returns a list of MediaItem objects (via a results queue).
Used for STATIC type URLs.  Playwright is the fallback when Scrapy
returns fewer than 3 items (JS-heavy sites).
"""

from __future__ import annotations

import asyncio
import logging
from typing import AsyncGenerator, List, Set
from urllib.parse import urljoin, urlparse

import scrapy
from scrapy.crawler import CrawlerRunner
from scrapy.http import HtmlResponse
from twisted.internet import asyncioreactor, defer

from backend.hunter.media_item import MediaItem

logger = logging.getLogger(__name__)

# Install asyncio reactor for Twisted/Scrapy (must be done before reactor is started)
try:
    asyncioreactor.install()
except Exception:
    pass  # already installed

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"}
VIDEO_EXTS = {".mp4", ".webm", ".mov", ".avi", ".mkv"}


class MediaSpider(scrapy.Spider):
    name = "media_spider"

    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_DELAY": 0.5,
        "CONCURRENT_REQUESTS": 8,
        "DEPTH_LIMIT": 3,
        "LOG_ENABLED": False,
        "TELNETCONSOLE_ENABLED": False,
        "COOKIES_ENABLED": False,
        "USER_AGENT": "ContentDNA/1.0 (+https://contentdna.io)",
    }

    def __init__(self, start_url: str, max_depth: int = 3,
                 max_pages: int = 100, results: list = None, **kwargs):
        super().__init__(**kwargs)
        self.start_urls = [start_url]
        self.allowed_domains = [urlparse(start_url).netloc]
        self.custom_settings["DEPTH_LIMIT"] = max_depth
        self.max_pages = max_pages
        self.results: List[MediaItem] = results if results is not None else []
        self._pages_crawled = 0
        self._seen_media: Set[str] = set()

    def _is_media_url(self, url: str) -> tuple[bool, str]:
        path = urlparse(url).path.lower()
        if any(path.endswith(ext) for ext in IMAGE_EXTS):
            return True, "image"
        if any(path.endswith(ext) for ext in VIDEO_EXTS):
            return True, "video"
        return False, ""

    def parse(self, response: HtmlResponse):
        if self._pages_crawled >= self.max_pages:
            return
        self._pages_crawled += 1

        page_url = response.url

        # ── Collect media ──────────────────────────────────────────────────
        media_urls: Set[str] = set()

        for src in response.css("img::attr(src)").getall():
            media_urls.add(response.urljoin(src))
        for src in response.css("video::attr(src)").getall():
            media_urls.add(response.urljoin(src))
        for src in response.css("source::attr(src)").getall():
            media_urls.add(response.urljoin(src))
        for content in response.css(
            "meta[property='og:image']::attr(content), "
            "meta[name='twitter:image']::attr(content)"
        ).getall():
            media_urls.add(response.urljoin(content))
        for href in response.css("a::attr(href)").getall():
            full = response.urljoin(href)
            is_media, _ = self._is_media_url(full)
            if is_media:
                media_urls.add(full)

        for url in media_urls:
            if url in self._seen_media:
                continue
            self._seen_media.add(url)
            is_media, media_type = self._is_media_url(url)
            if is_media:
                self.results.append(MediaItem(
                    url=url,
                    path=None,
                    page_url=page_url,
                    media_type=media_type,
                ))

        # ── Follow internal links ──────────────────────────────────────────
        for link in response.css("a::attr(href)").getall():
            full = response.urljoin(link)
            parsed = urlparse(full)
            if parsed.netloc in self.allowed_domains:
                yield scrapy.Request(full, callback=self.parse)


async def extract_media_scrapy(
    url: str,
    max_depth: int = 3,
    max_pages: int = 100,
) -> AsyncGenerator[MediaItem, None]:
    """
    Crawl *url* with Scrapy and yield discovered MediaItems.
    """
    logger.info("ScrapyExtractor: crawling %s (depth=%d, pages=%d)",
                url, max_depth, max_pages)

    results: List[MediaItem] = []

    runner = CrawlerRunner()
    deferred = runner.crawl(
        MediaSpider,
        start_url=url,
        max_depth=max_depth,
        max_pages=max_pages,
        results=results,
    )

    # Convert Twisted Deferred to asyncio Future
    future = asyncio.get_event_loop().create_future()
    deferred.addCallback(lambda _: future.set_result(None))
    deferred.addErrback(lambda failure: future.set_exception(
        Exception(str(failure.value))
    ))

    try:
        await asyncio.wait_for(future, timeout=120.0)
    except asyncio.TimeoutError:
        logger.warning("ScrapyExtractor timed out for %s", url)
    except Exception as exc:
        logger.error("ScrapyExtractor error for %s: %s", url, exc)

    logger.debug("ScrapyExtractor: found %d media items from %s",
                 len(results), url)
    for item in results:
        yield item
