import asyncio
import logging
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from lxml import html
from playwright.sync_api import sync_playwright

from src.core.config import config
from src.utils.convert_number_with_suffix import convert_number_with_suffix


class TiktokScraperService:
    def __init__(self, headless=True):
        self.logger = logging.getLogger("TiktokScraperService")
        self.headless = headless
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.posts = []
        self.httpx_client = httpx.AsyncClient()
        if not config.GOOGLE_API_KEY or not config.GOOGLE_SEARCH_ENGINE_ID:
            raise Exception("Environment variable not found.")

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

    async def _get_video_dates_async(self, url, page=2):
        """
        Asynchronously scrape TikTok video creation dates.

        This method uses a custom Google search engine to search for TikTok videos
        with the given username. The `page` parameter determines the number of
        search results to fetch. The method extracts the video creation dates from
        the search results and returns them as a list.

        Args:
            url (str): The TikTok profile URL.
            page (int, optional): The number of search results to fetch. Defaults to 2.

        Returns:
            list: A list of video creation dates as Unix timestamps.
        """
        parsed_url = urlparse(url)
        path = parsed_url.path
        username = path.split("/")[-1] if path else None
        dork_query = f"site:www.tiktok.com inurl:{username}/video/"
        video_list = []
        start = 1
        for _ in range(page):
            params = {
                "key": config.GOOGLE_API_KEY,
                "cx": config.GOOGLE_SEARCH_ENGINE_ID,
                "num": 10,
                "q": dork_query,
                "start": start,
                "sort": "date",
            }
            url = f"{config.GOOGLE_SEARCH_API_ENDPOINT}?{urlencode(params)}"
            response = await self.httpx_client.get(url, timeout=config.HTTPX_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            # Extract only TikTok video links
            for item in data.get("items", []):
                if item["link"].startswith(f"https://www.tiktok.com/{username}/video/"):
                    create_time = await self.extract_create_time(item["link"])
                    if create_time is None:
                        continue

                    video_list.append(create_time)

            start += 10

        return video_list

    async def extract_create_time(self, url):
        """
        Extracts the creation time of a TikTok video from the video URL.

        The method sends a GET request to the TikTok video URL, parses the HTML
        response, and extracts the "createTime" value from the page's JSON metadata.

        Args:
            url (str): The TikTok video URL.

        Returns:
            int: The creation time of the video as a Unix timestamp, or None if the
                video creation time could not be extracted.
        """
        response = await self.httpx_client.get(url)
        data = response.text
        match = re.search(
            r'"createTime":"(\d+)"',
            data,
        )
        if match:
            return int(match.group(1))
        return None

    def scrape_using_request(self, url):
        """
        Scrape TikTok page data using httpx.

        This method sends a GET request to the provided TikTok URL, extracts the
        HTML content, and parses it to extract the secUid, verification status, and
        follower count.

        Args:
            url (str): The TikTok URL to scrape.

        Returns:
            dict: A dictionary containing the scraped data, including:
                - secUid (str): The secUid of the TikTok account.
                - verified (bool): Whether the account is verified.
                - followerCount (int): The number of followers, if available.
        """
        with httpx.Client() as client:
            response = client.get(url)
            data = response.text
            # Extract secUid
            secuid_match = re.search(r'"secUid"\s*:\s*"([^"]+)"', data)
            secuid = secuid_match.group(1) if secuid_match else None

            # Extract verified (bool)
            verified_match = re.search(r'"verified"\s*:\s*(true|false)', data)
            verified = verified_match.group(1) == "true" if verified_match else None

            # Extract followerCount (from stats or statsV2)
            followers_match = re.search(r'"followerCount"\s*:\s*"?(\d+)"?', data)
            followers = int(followers_match.group(1)) if followers_match else None

            return {
                "secUid": secuid,
                "verified": verified,
                "followerCount": followers,
            }

    def handle_response(self, response):
        """
        Handles the response from TikTok's post item list API.

        Given a Playwright response object, this method extracts the post creation
        timestamps from the response content and stores them in the `self.posts`
        attribute.

        Args:
            response (Response): The Playwright response object.

        Returns:
            None
        """
        log = self.logger.getChild("handle_response")
        url = response.url
        if "/api/post/item_list/" in url:
            http_header = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0",  # noqa
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.tiktok.com/",
                "Cookie": f"msToken={config.TIKTOK_COOKIES}; odinId=YOUR_ODINID; device_id=7509009447768409608;",  # noqa
            }
            # Wait for full body to be available
            parsed_url = urlparse(url)
            params = parse_qs(parsed_url.query)

            params["data_collection_enabled"] = True
            params["device_id"] = 7509009447768409608
            params["screen_height"] = 1080
            params["screen_width"] = 1920

            try:
                r = httpx.get(
                    "https://www.tiktok.com/api/post/item_list/",
                    params=params,
                    headers=http_header,
                    timeout=10,
                )
                data = r.json()
                self.posts = [item["createTime"] for item in data["itemList"]]

            except Exception as e:
                log.error("Error reading body: %s", e)

    def extract_post_using_requests(self, secUid):
        """
        Extracts post timestamps using the TikTok API via HTTPX.

        This method takes in a secUid, constructs a GET request to the TikTok API
        with the required headers and parameters, and parses the JSON response to
        retrieve the post timestamps.

        Args:
            secUid (str): The secure user ID of the TikTok account.

        Returns:
            None
        """
        api_endpoint = "https://www.tiktok.com/api/post/item_list/"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36 Edg/138.0.0.0",  # noqa
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.tiktok.com/",
            "Cookie": f"msToken={config.TIKTOK_COOKIES}; odinId=YOUR_ODINID; device_id=7509009447768409608;",  # noqa
        }
        params = {
            "WebIdLastTime": ["1748327509"],
            "aid": ["1988"],
            "app_language": ["en"],
            "app_name": ["tiktok_web"],
            "cookie_enabled": ["true"],
            "count": ["35"],
            "cursor": ["0"],
            "data_collection_enabled": ["true"],
            "device_id": ["7509009447768409608"],
            "odinId": ["7534585605200921607"],
            "secUid": [secUid],
            "msToken": [config.TIKTOK_COOKIES],
        }

        r = httpx.get(api_endpoint, params=params, headers=headers, timeout=10)
        data = r.json()
        return [item["createTime"] for item in data["itemList"]]

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
        Synchronously scrapes Tiktok page data using Playwright.

        This method navigates to a given Tiktok URL, waits for the content to load,
        and extracts various data points such as verification status, likes, followers,
        and post timestamps. The scraping process involves setting custom headers,
        closing pop-ups, scrolling to load more content, and parsing the rendered HTML.

        Args:
            url (str): The Tiktok URL to scrape.
            timeout (int, optional): The time to wait for page content to load.

        Returns:
            dict: A dictionary containing the scraped data, including:
                - verified (bool): Whether the account is verified.
                - likes (int): The number of likes, if available.
                - follower (int): The number of followers, if available.
                - posts (list): A list of timestamps of the posts.
                - error (str, optional): An error message if scraping fails.
                - message (str, optional): A failure message if scraping fails.
        """
        log = self.logger.getChild("scrape")
        if not url:
            return "No URL provided."

        log.info("Scraping tiktok %s", url)
        try:
            is_verified = False
            page_follower = ""
            scraped = {}
            followers = ""
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
                    cookie = [
                        {
                            "name": "msToken",
                            "value": config.TIKTOK_COOKIES,
                            "domain": "www.tiktok.com",
                            "path": "/",
                        }
                    ]
                    context.add_cookies(cookie)
                    page = context.new_page()

                    # page.on("response", self.handle_response)

                    # Navigate to the page
                    page.goto(url, wait_until="networkidle", timeout=60000)

                    # Wait for page content to load (you can adjust the selector)
                    page.wait_for_timeout(timeout=timeout)  # wait 5 seconds

                    # Get the full HTML after JS has rendered
                    html_content = page.content()
                    browser.close()
                    tree = html.fromstring(html_content)
                    page_follower = (
                        tree.xpath("//div/strong[contains(@title, 'Followers')]").pop()
                    ).text_content()  # noqa
                    # page_likes = (
                    #     tree.xpath("//div/strong[contains(@title, 'Likes')]").pop()
                    # ).text_content()
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
            except Exception as e:
                log.error("Failed to scrape Tiktok using playwright: %s", e)
                log.info("Scraping tiktok via httpx %s", url)
                scraped = self.scrape_using_request(url)

            followers = (
                page_follower if page_follower else str(scraped["followerCount"])
            )
            verification = is_verified if is_verified else scraped["verified"]
            posts = self._get_video_dates_sync(url)
            # posts = self.posts
            gathered_data = {
                "verified": verification,
                "likes": convert_number_with_suffix(followers),
                "follower": convert_number_with_suffix(followers),
                "posts": posts,
            }
            log.info("Gathered data: %s", gathered_data)
            return gathered_data

        except Exception as e:
            log.error("Failed to scrape Tiktok: %s", e)
            return {
                "error": str(e),
                "message": "Failed to scrape Tiktok",
            }

    async def scrape_via_httpx(self, url, timeout=2000):
        log = self.logger.getChild("scrape_via_httpx")
        if not url:
            return "No URL provided."

        log.info("Scraping tiktok via httpx %s", url)
        scraped = self.scrape_using_request(url)
        posts = self._get_video_dates_sync(url)
        gathered_data = {
            "verified": scraped["verified"],
            "follower": convert_number_with_suffix(str(scraped["followerCount"])),
            "posts": posts,
        }
        log.info("Gathered data: %s", gathered_data)
        return gathered_data
