import asyncio
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright
from lxml import html
import re
from src.utils.convert_number_with_suffix import convert_number_with_suffix
from src.utils.time_to_epoch import time_to_epoch


class XScraperService:
    def __init__(self, headless=True):
        self.headless = headless
        self.executor = ThreadPoolExecutor(max_workers=1)

    async def scrape(self, url, timeout=2000):
        """
        Run sync Playwright in a thread pool to avoid event loop conflicts
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, lambda: self._sync_scrape(url, timeout)
        )

    def _sync_scrape(self, url, timeout=2000):
        if not url:
            return "No URL provided."

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                locale="en-US", extra_http_headers={"Accept-Language": "en-US,en;q=0.9"}
            )
            page = context.new_page()

            # Set a realistic user-agent
            page.set_extra_http_headers(
                {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0"  # noqa
                }
            )

            # Navigate to the page
            page.goto(url)

            # Wait for page content to load (you can adjust the selector)
            page.wait_for_load_state("domcontentloaded")
            # Close the "Create New Account" popup
            close_button = page.query_selector('[aria-label="Close"]')
            if close_button:
                close_button.click()

            # Scroll to the bottom of the page to load more content
            page.evaluate("window.scrollTo(0, document.body.scrollHeight);")

            # Wait for page content to load (you can adjust the selector)
            page.wait_for_timeout(timeout)

            # Get the full HTML after JS has rendered
            html_content = page.content()
            tree = html.fromstring(html_content)
            post_age_list = tree.xpath(
                "//*[contains(@href, 'status')][contains(@dir, 'ltr')]"
            )
            page_follower = tree.xpath("//*[contains(@href, 'verified')]")[0]
            is_verified = (
                True
                if len(tree.xpath("//*[contains(@aria-label, 'Verified account')]")) > 0
                else False
            )

            posts = []
            for post in post_age_list:
                posts.append(
                    time_to_epoch(re.sub(r"\s+", " ", post.text_content()).strip())
                )
            browser.close()
            return {
                "verified": is_verified,
                "follower": convert_number_with_suffix(
                    page_follower.text_content().split(" ")[0]
                ),
                "posts": posts,
            }
