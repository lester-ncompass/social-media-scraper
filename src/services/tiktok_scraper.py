import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading
from playwright.sync_api import sync_playwright
from lxml import html
from TikTokApi import TikTokApi  # type: ignore
import datetime
import logging
from src.core.config import config
from src.utils.convert_number_with_suffix import convert_number_with_suffix
from src.utils.time_to_epoch import time_to_epoch


class TiktokScraperService:
    def __init__(self, headless=True):
        self.logger = logging.getLogger("TiktokScraperService")
        self.headless = headless
        self.executor = ThreadPoolExecutor(max_workers=1)

    def _get_video_dates_sync(
        self,
        url,
    ):
        result = []

        def run():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result.append(loop.run_until_complete(self._get_video_dates_async(url)))
            finally:
                loop.close()

        thread = threading.Thread(target=run)
        thread.start()
        thread.join()

        if not result:
            return []

        return result[0]

    async def _get_video_dates_async(self, url):
        async with TikTokApi() as api:
            await api.create_sessions(
                ms_tokens=[config.TIKTOK_COOKIES],
                num_sessions=5,
                sleep_after=3,
                browser="chromium",
            )
            # Retrieves the username from the URL
            username = url.split("/")[-1].split("@")[-1]
            video_list = []
            async for video in api.user(username=username).videos():
                video_list.append(
                    time_to_epoch(
                        datetime.datetime.fromtimestamp(
                            video.as_dict["createTime"]
                        ).strftime("%Y-%m-%d %H:%M:%S")
                    )
                )
                if len(video_list) == 5:
                    break

        return video_list

    async def scrape(self, url, timeout=2000):
        """
        Run sync Playwright in a thread pool to avoid event loop conflicts
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, lambda: self._sync_scrape(url, timeout)
        )

    def _sync_scrape(self, url, timeout=2000):
        log = self.logger.getChild("scrape")
        if not url:
            return "No URL provided."

        log.info("Scraping tiktok %s", url)
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=self.headless
                )  # Set headless=True if you don't want to see the browser
                context = browser.new_context(
                    has_touch=True,
                    locale="en-US",
                    extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
                )
                page = context.new_page()

                # Set a realistic user-agent
                page.set_extra_http_headers(
                    {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0"  # noqa
                    }
                )

                # Navigate to the page
                page.goto(url, wait_until="networkidle", timeout=60000)

                # Wait for page content to load (you can adjust the selector)
                page.wait_for_timeout(timeout=timeout)  # wait 5 seconds

                # Get the full HTML after JS has rendered
                html_content = page.content()
                tree = html.fromstring(html_content)
                page_follower = tree.xpath(
                    "//div/strong[contains(@title, 'Followers')]"
                ).pop()  # noqa
                page_likes = tree.xpath("//div/strong[contains(@title, 'Likes')]").pop()
                is_verified = (
                    True
                    if len(
                        tree.xpath(
                            "//h1[@data-e2e='user-title']/following-sibling::*[1][self::svg]"  # noqa
                        )
                    )
                    > 0
                    else False
                )
                posts = self._get_video_dates_sync(url)
                browser.close()

                return {
                    "verified": is_verified,
                    "likes": convert_number_with_suffix(page_likes.text_content()),
                    "follower": convert_number_with_suffix(
                        page_follower.text_content()
                    ),
                    "posts": posts,
                }
        except Exception as e:
            log.error("Failed to scrape Tiktok: %s", e)
            return {
                "error": str(e),
                "message": "Failed to scrape Tiktok",
            }
