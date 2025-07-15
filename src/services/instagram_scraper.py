import asyncio
from concurrent.futures import ThreadPoolExecutor
from playwright.sync_api import sync_playwright
from lxml import html
import re
import requests
from src.core.config import config
from src.utils.convert_number_with_suffix import convert_number_with_suffix
from src.utils.time_to_epoch import time_to_epoch


class InstagramScraperService:
    def __init__(self, headless=True):
        self.headless = headless
        self.executor = ThreadPoolExecutor(max_workers=1)

    def _check_url_sync(self, session, href):
        url = "https://www.instagram.com" + href
        response = session.get(url)
        response.raise_for_status()  # Raises exception for bad status codes

        content = response.text
        tree = html.fromstring(content)
        content = tree.xpath("//meta[@property='og:description']/@content")[0]
        matches = re.findall(
            r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}",  # noqa
            content,
        )
        return time_to_epoch(matches.pop())

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

        url_length = len(url.split("/"))
        # Remove trailing slash, indicator is length is 5 when splitted
        if url_length == 5:
            url = url[:-1]

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=self.headless,
                )  # Set headless=True if you don't want to see the browser
                context = browser.new_context(
                    locale="en-US",
                    extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
                )
                # context.add_cookies(
                #     [
                #         {
                #             "name": "sessionid",
                #             "value": config.INSTAGRAM_COOKIES,
                #             "domain": "www.instagram.com",
                #             "path": "/",
                #             "httpOnly": True,
                #             "secure": True,
                #             "sameSite": "None",
                #         }
                #     ]
                # )
                page = context.new_page()

                # Set a realistic user-agent
                page.set_extra_http_headers(
                    {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"  # noqa
                    }
                )

                # Navigate to the page
                page.goto(
                    url,
                    wait_until="networkidle",
                    timeout=60000,
                )

                # Close the "Create New Account" popup
                close_button = page.query_selector_all('[aria-label="Close"]')
                if close_button:
                    close_button.pop().click()
                # Wait for page content to load (you can adjust the selector)
                page.wait_for_timeout(timeout)  # wait 5 seconds

                # Get the full HTML after JS has rendered
                html_content = page.content()
                with open("instagram.html", "w", encoding="utf-8") as file:
                    file.write(html_content)
                tree = html.fromstring(html_content)
                page_follower = tree.xpath(
                    "//span/span/span[contains(@class, 'html-span')]"  # noqa
                )[1]
                is_verified = (
                    True
                    if len(tree.xpath("//title[contains(text(), 'Verified')]")) > 0
                    else False
                )

                tiles = tree.xpath(
                    "//*[contains(@style, 'flex')]//a[contains(@href,'/')]"
                )
                hrefs = []
                for tile in tiles:
                    hrefs.append(tile.get("href"))
                    if len(hrefs) == 5:
                        break

                with requests.Session() as session:
                    # Set up session headers if needed
                    session.headers.update(
                        {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                    )
                    with ThreadPoolExecutor(max_workers=5) as http_executor:
                        futures = []
                        for href in hrefs:
                            future = http_executor.submit(
                                self._check_url_sync, session, href
                            )
                            futures.append(future)
                        # Collect results
                        dates = []
                        for future in futures:
                            try:
                                date = future.result()
                                if date:  # Only add non-None dates
                                    dates.append(date)
                            except Exception as e:
                                print(f"Error processing URL: {e}")
                browser.close()
                return {
                    "verified": is_verified,
                    "follower": convert_number_with_suffix(
                        page_follower.text_content().split(" ")[0]
                    ),
                    "posts": dates,
                }
        except Exception as e:
            return {
                "error": str(e),
                "message": "Failed to scrape Instagram",
            }
