import asyncio
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright
from lxml import html
import re
from src.utils.convert_number_with_suffix import convert_number_with_suffix
from src.utils.time_to_epoch import time_to_epoch


class FacebookScraperService:
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

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                context = browser.new_context(
                    locale="en-US", extra_http_headers={"Accept-Language": "en-US,en;q=0.9"}
                )
                page = context.new_page()

                # Set a realistic user-agent
                page.set_extra_http_headers(
                    {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
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
                    "//div[contains(@data-pagelet, 'TimelineFeedUnit')]//div[2]/span//span//a[contains(@role, 'link')]"  # noqa
                )
                page_like = (
                    tree.xpath("//a[contains(@href, 'friends_likes')]/strong").pop()
                    if len(tree.xpath("//a[contains(@href, 'friends_likes')]/strong")) > 0
                    else None
                )
                page_follower = (
                    tree.xpath("//a[contains(@href, 'followers')]/strong").pop()
                    if len(tree.xpath("//a[contains(@href, 'followers')]/strong")) > 0
                    else None
                )
                is_verified = (
                    True
                    if len(tree.xpath("//*/h1//*[@title='Verified account']")) > 0
                    else False
                )
                review_path = tree.xpath("//a[contains(@href, '/reviews')]//span")
                reviews = (
                    review_path[0].text_content() if len(review_path) > 0 else "No reviews"
                )
                posts = []
                for post in post_age_list:
                    posts.append(
                        time_to_epoch(re.sub(r"\s+", " ", post.text_content()).strip())
                    )

                browser.close()
                gathered_data = {
                    "verified": is_verified,
                    "reviews": reviews,
                    "posts": posts,
                }
                if isinstance(page_like, html.HtmlElement):
                    gathered_data["like"] = convert_number_with_suffix(
                        page_like.text_content()
                    )
                if isinstance(page_follower, html.HtmlElement):
                    gathered_data["follower"] = convert_number_with_suffix(
                        page_follower.text_content()
                    )
                return gathered_data

        except Exception as e:
            return {
                "error": str(e),
                "message": "Failed to scrape Instagram",
            }