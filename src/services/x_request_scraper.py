import httpx
from concurrent.futures import ThreadPoolExecutor

url = "https://x.com/Jollibee"
headers = {
    # "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    "Accept-Language": "en-US,en;q=0.9",
}

import re


def get_followers_following_posts(text):
    pattern = r'content="([\d,\.]+)K? Followers, ([\d,\.]+) Following, ([\d,\.]+) Posts'
    match = re.search(pattern, text)
    page_details = str(match.group(0)).split('"').pop().split(" ")
    if match:
        followers = page_details[0]
        following = page_details[2]
        posts = page_details[4]

        print(f"Followers: {followers}")
        print(f"Following: {following}")
        print(f"Posts: {posts}")
    else:
        print("No match found")


async def fetch_url():
    async with httpx.AsyncClient(headers=headers) as client:
        response = await client.get(url)
        print("Response: ", response.text)
        print(get_followers_following_posts(response.text.split("/n")[0]))


# with ThreadPoolExecutor(max_workers=15) as executor:
#     for _ in range(100):
#         executor.submit(fetch_url)

import asyncio

asyncio.run(fetch_url())
