"""
backend/hunter/extractors/scrapy_extractor.py

Source: project/hunter/scrapy_engine/scrapy/spiders/__init__.py → Spider base class
  - Copied: Spider subclass pattern with name, custom_settings, parse(response)
  - From spiders/__init__.py: class Spider → start_urls, parse(response), yield Request
  - Modified: ContentDNASpider finds img/video/og:image media, CrawlerRunner for async
"""
import asyncio
import logging
import os
import tempfile
from typing import List
from urllib.parse import urlparse

import scrapy
from scrapy.crawler import CrawlerRunner
from scrapy.http import HtmlResponse

from backend.hunter.media_item import MediaItem

logger = logging.getLogger(__name__)

# Install asyncio-compatible Twisted reactor before anything else
try:
    from twisted.internet import asyncioreactor
    asyncioreactor.install()
except Exception:
    pass

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif"}
VIDEO_EXTS = {".mp4", ".webm", ".mov", ".avi", ".mkv"}


class ContentDNASpider(scrapy.Spider):
    """
    Copied pattern from scrapy/spiders/__init__.py → Spider base class.
    Modified to find media URLs and yield MediaItems.
    """
    name = "ContentDNASpider"

    # Copied from Spider.custom_settings class attribute pattern
    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "DOWNLOAD_DELAY": 1,
        "CONCURRENT_REQUESTS": 8,
        "DEPTH_LIMIT": 3,
        "LOG_ENABLED": False,
        "TELNETCONSOLE_ENABLED": False,
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
        self._seen: set = set()

    def _media_type(self, url: str):
        path = urlparse(url).path.lower()
        if any(path.endswith(e) for e in IMAGE_EXTS): return "image"
        if any(path.endswith(e) for e in VIDEO_EXTS): return "video"
        return None

    # Copied from Spider.parse(response) pattern in spiders/__init__.py
    def parse(self, response: HtmlResponse):
        if self._pages_crawled >= self.max_pages:
            return
        self._pages_crawled += 1
        page_url = response.url

        # Find all media URLs
        candidates = set()
        for sel in ["img::attr(src)", "video::attr(src)", "source::attr(src)"]:
            for src in response.css(sel).getall():
                candidates.add(response.urljoin(src))
        for content in response.css(
            "meta[property='og:image']::attr(content), "
            "meta[name='twitter:image']::attr(content)"
        ).getall():
            candidates.add(response.urljoin(content))
        for href in response.css("a::attr(href)").getall():
            full = response.urljoin(href)
            if self._media_type(full):
                candidates.add(full)

        for url in candidates:
            if url in self._seen: continue
            self._seen.add(url)
            mt = self._media_type(url)
            if mt:
                self.results.append(MediaItem(
                    url=url, path=None, page_url=page_url, media_type=mt
                ))

        # Follow internal links — copied from Spider start() → yield Request pattern
        for link in response.css("a::attr(href)").getall():
            full = response.urljoin(link)
            if urlparse(full).netloc in self.allowed_domains:
                yield scrapy.Request(full, callback=self.parse)


async def extract_media_scrapy(url: str, max_depth: int = 3, max_pages: int = 100):
    results: List[MediaItem] = []
    runner = CrawlerRunner()
    deferred = runner.crawl(
        ContentDNASpider,
        start_url=url,
        max_depth=max_depth,
        max_pages=max_pages,
        results=results,
    )

    future = asyncio.get_running_loop().create_future()
    deferred.addCallback(lambda _: future.set_result(None))
    deferred.addErrback(lambda f: future.set_exception(Exception(str(f.value))))

    try:
        await asyncio.wait_for(future, timeout=120.0)
    except (asyncio.TimeoutError, Exception) as exc:
        logger.warning("ScrapyExtractor error: %s", exc)

    for item in results:
        yield item
