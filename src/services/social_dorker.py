from urllib.parse import urlencode, urlparse

import httpx

from src.core.config import config


class SocialDorkerService:
    def __init__(
        self,
        api_key=config.GOOGLE_API_KEY,
        search_engine_id=config.GOOGLE_SEARCH_ENGINE_ID,
        search_api_endpoint=config.GOOGLE_SEARCH_API_ENDPOINT,
        httpx_client=None,
        timeout=config.HTTPX_TIMEOUT,
    ):
        self.api_key = api_key
        self.search_engine_id = search_engine_id
        self.search_api_endpoint = search_api_endpoint
        self.timeout = timeout
        self.httpx_client = httpx_client or httpx.Client(timeout=self.timeout)

    def close(self):
        self.httpx_client.close()

    def get_tiktok_dork(self, username):
        return f"site:www.tiktok.com inurl:@{username}/video/"

    def get_x_dork(self, username):
        return f"site:https://x.com inurl:{username}/status/"

    def get_facebook_dork(self, username):
        return f"site:www.facebook.com inurl:{username}/posts/"

    def extract_create_time(self, social_media, item):
        """
        Extracts the creation time of a social media post from a Google search result item.

        Args:
            social_media (str): The social media platform of the post.
            item (dict): A Google search result item.

        Returns:
            str: The creation time of the post as a string, or None if it could not be extracted.
        """  # noqa
        if social_media == "tiktok" or social_media == "facebook":
            date = item["htmlSnippet"].split("<")[0]
            return date[: (len(date) - 1)]
        if social_media == "x":
            return item["pagemap"]["socialmediaposting"][0]["datepublished"]

        return None

    def get_video_dates(self, profile_url, dork_fn=None, page=2):
        """
        Scrapes video creation dates for a profile using Google Custom Search.

        Args:
            profile_url (str): The profile URL (e.g., TikTok or X).
            dork_fn (callable): Function to generate a Google dork query (username -> query string).
            page (int): Number of pages (10 results per page).

        Returns:
            list: Video creation dates (Unix timestamp or string, depending on extractor).
        """  # noqa
        parsed_url = urlparse(profile_url)
        # Try to extract username in a robust way
        path = parsed_url.path.strip("/")
        raw_username = path.split("/")[-1] if path else None
        username = raw_username.split("@")[-1]
        if not username:
            raise ValueError("Could not extract username from profile URL")

        # Choose dork query generator
        dork_query = dork_fn(username) if dork_fn else self.get_tiktok_dork(username)
        video_list = []
        start = 1

        for _ in range(page):
            params = {
                "key": self.api_key,
                "cx": self.search_engine_id,
                "num": 10,
                "q": dork_query,
                "start": start,
                "sort": "date",
            }
            url = f"{self.search_api_endpoint}?{urlencode(params)}"
            response = self.httpx_client.get(url, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            social_media = None
            for item in data.get("items", []):
                link = item["link"]
                # Adjust the link check for the social media being scraped
                if dork_query.startswith("site:www.tiktok.com"):
                    url_check = f"https://www.tiktok.com/@{username}/video/"
                    social_media = "tiktok"
                elif dork_query.startswith("site:https://x.com"):
                    url_check = f"https://x.com/{username}/status/"
                    social_media = "x"
                elif dork_query.startswith("site:www.facebook.com"):
                    url_check = f"https://www.facebook.com/{username}/posts/"
                    social_media = "facebook"
                else:
                    url_check = None
                if url_check and link.lower().startswith(url_check.lower()):
                    create_time = self.extract_create_time(social_media, item)
                    if create_time is not None:
                        video_list.append(create_time)
            start += 10

        return video_list
