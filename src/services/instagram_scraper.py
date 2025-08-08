import asyncio
import logging
import re
from concurrent.futures import ThreadPoolExecutor

import requests
from apify_client import ApifyClient
from lxml import html
from playwright.sync_api import sync_playwright

from src.core.config import config
from src.utils.convert_number_with_suffix import convert_number_with_suffix
from src.utils.time_to_epoch import time_to_epoch


class InstagramScraperService:
    def __init__(self, headless=True):
        self.logger = logging.getLogger("InstagramScraperService")
        self.headless = headless
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.apify_client = ApifyClient(config.APIFY_KEY)

    def _fallback_to_apify(self, url):
        """
        Fallback method to retrieve Instagram data using Apify's Instagram scraper.

        This method interacts with the Apify platform to scrape Instagram data
        in situations where the main scraping method fails. It retrieves the
        number of followers, verification status, and latest post timestamps
        for a specific Instagram URL.

        Args:
            url (str): The Instagram URL to scrape.

        Returns:
            dict: A dictionary containing:
                - verified (int): Whether the account is verified 1 or 0.
                - follower (str): The number of followers in a human-readable format.
                - posts (list): A list of timestamps of the latest posts.
        """

        posts = []

        run = self.apify_client.actor("apify/instagram-scraper").call(
            run_input={
                "directUrls": [
                    url,
                ],
                "enhanceUserSearchWithFacebookPage": False,
                "isUserReelFeedURL": False,
                "isUserTaggedFeedURL": False,
                "resultsLimit": 1,
                "resultsType": "details",
                "searchLimit": 1,
                "searchType": "hashtag",
            },
            logger=None,
        )
        for item in self.apify_client.dataset(run["defaultDatasetId"]).iterate_items():
            followers = item["followersCount"]
            verified = item["verified"]
            for post in item["latestPosts"]:
                posts.append(time_to_epoch(post["timestamp"]))
            break

        return {
            "verified": int(verified),
            "follower": convert_number_with_suffix(str(followers)),
            "posts": posts,
        }

    def _check_url(self, session, href):
        """
        Extracts the timestamp of the most recent post from an Instagram URL.

        This method constructs the full URL using the provided href, sends a GET request
        to retrieve the page content, and parses the HTML to find the post date. The
        date is then converted to an epoch timestamp.

        Args:
            session (requests.Session): The HTTP session for making requests.
            href (str): The relative URL path of the Instagram post.

        Returns:
            int: The epoch timestamp of the most recent post date.

        Raises:
            requests.exceptions.HTTPError: If the HTTP request returns an
                unsuccessful status code.
        """

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
        """
        Synchronously scrapes Instagram page data using Playwright.

        This method navigates to a given Instagram URL, waits for the content to load,
        and extracts various data points such as verification status, followers, and
        post timestamps. The scraping process involves setting custom headers, closing
        pop-ups, scrolling to load more content, and parsing the rendered HTML.

        Args:
            url (str): The Instagram URL to scrape.
            timeout (int, optional): The time to wait for page content to load.

        Returns:
            dict: A dictionary containing the scraped data, including:
                - verified (bool): Whether the account is verified.
                - follower (int): The number of followers, if available.
                - posts (list): A list of timestamps of the posts.
                - error (str, optional): An error message if scraping fails.
                - message (str, optional): A failure message if scraping fails.
        """
        log = self.logger.getChild("scrape")
        if not url:
            return "No URL provided."

        log.info("Scraping instagram %s", url)

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
                browser.close()

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
                                self._check_url, session, href
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
                                log.error("Error processing URL: %s", e)
                gathered_data = {
                    "verified": is_verified,
                    "follower": convert_number_with_suffix(
                        page_follower.text_content().split(" ")[0]
                    ),
                    "posts": dates,
                }
                log.info("Gathered data: %s", gathered_data)

                return gathered_data

        except Exception as e:
            log.error(
                "Failed to scrape Instagram using playwright: %s. Using fallback.", e
            )
            try:
                return self._fallback_to_apify(url)
            except Exception as e:
                log.error("Fallback failed: %s", e)
                return {
                    "error": str(e),
                    "message": "Failed to scrape Instagram",
                }

    async def scrape_via_apify(self, url, timeout=2000):
        """
        Run sync apify in a thread pool to avoid event loop conflicts
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, lambda: self._sync_scrape_via_apify(url, timeout)
        )

    def _sync_scrape_via_apify(self, url, timeout=2000):
        """
        Scrapes Instagram data using Apify's Instagram scraper.

        Args:
            url (str): The Instagram URL to scrape.
            timeout (int, optional): The time to wait for page content to load.

        Returns:
            dict: A dictionary containing the scraped data, including:
                - verified (bool): Whether the account is verified.
                - follower (int): The number of followers, if available.
                - posts (list): A list of timestamps of the posts.
                - error (str, optional): An error message if scraping fails.
                - message (str, optional): A failure message if scraping fails.
        """
        if not url:
            return "No URL provided."

        log = self.logger.getChild("scrape_via_apify")
        try:
            gathered_data = self._fallback_to_apify(url)
            log.info("Gathered data: %s", gathered_data)

            return gathered_data
        except Exception as e:
            log.error("Fallback failed: %s", e)
            return {
                "error": str(e),
                "message": "Failed to scrape Instagram",
            }
