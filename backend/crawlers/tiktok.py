"""
backend/crawlers/tiktok.py

TikTok crawler using gallery-dl.
gallery-dl natively supports TikTok hashtag pages and user URLs.
Downloads media files to a temp directory, runs detection, then cleans up immediately.
"""
import logging
import asyncio
import os
import tempfile
import shutil

logger = logging.getLogger(__name__)

DEFAULT_TIKTOK_URLS = [
    "https://www.tiktok.com/tag/sportshighlights",
    "https://www.tiktok.com/tag/footballhighlights",
    "https://www.tiktok.com/tag/cricketlive",
    "https://www.tiktok.com/tag/nbaclips",
]

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv"}


async def crawl_tiktok(urls: list[str] = None):
    """
    For each TikTok URL (hashtag page or user profile),
    use gallery-dl to download media, run detection, then delete files.
    """
    try:
        from backend.detection.engine import detect_from_file, detect_from_url
    except ImportError as e:
        logger.error("Detection engine import failed: %s", e)
        return

    try:
        import gallery_dl
        import gallery_dl.config
        import gallery_dl.job
    except ImportError:
        logger.warning(
            "gallery-dl not installed. Run: pip install gallery-dl"
        )
        return

    if urls is None:
        urls = DEFAULT_TIKTOK_URLS

    total_found = 0
    total_matched = 0

    for tiktok_url in urls:
        tmp_dir = tempfile.mkdtemp(prefix="contentdna_tiktok_")
        try:
            # Configure gallery-dl for this run
            gallery_dl.config.clear()
            gallery_dl.config.set((), "directory", [tmp_dir])
            gallery_dl.config.set((), "filename", "{id}.{extension}")
            gallery_dl.config.set((), "retries", 2)
            gallery_dl.config.set((), "timeout", 30)
            gallery_dl.config.set(
                ("extractor", "tiktok"), "videos", True
            )
            gallery_dl.config.set(
                ("extractor", "tiktok"), "thumbnails", True
            )

            try:
                job = gallery_dl.job.DownloadJob(tiktok_url)
                job.run()
            except Exception as e:
                logger.warning("gallery-dl job failed for %s: %s", tiktok_url, e)
                continue

            # Process each downloaded file
            for fname in os.listdir(tmp_dir):
                fpath = os.path.join(tmp_dir, fname)
                if not os.path.isfile(fpath):
                    continue

                ext = os.path.splitext(fname)[1].lower()
                if ext not in IMAGE_EXTS and ext not in VIDEO_EXTS:
                    continue

                total_found += 1
                media_type = "video" if ext in VIDEO_EXTS else "image"

                try:
                    with open(fpath, "rb") as f:
                        file_bytes = f.read()

                    result = await detect_from_file(
                        file_bytes=file_bytes,
                        media_type=media_type,
                        source_url=tiktok_url,
                        platform="tiktok",
                        source_type="crawler",
                    )
                    if result and result.get("matched"):
                        total_matched += 1

                except Exception as e:
                    logger.debug("Detection error for %s: %s", fname, e)
                finally:
                    # Delete immediately after fingerprinting
                    try:
                        os.unlink(fpath)
                    except OSError:
                        pass

                await asyncio.sleep(0.1)

        finally:
            # Always clean up temp dir
            try:
                shutil.rmtree(tmp_dir, ignore_errors=True)
            except Exception:
                pass

    logger.info(
        "[TikTok] Crawl complete — %d media processed, %d matches",
        total_found, total_matched,
    )
