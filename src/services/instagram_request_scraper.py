import requests
import re

url = "https://www.instagram.com/jollibee/"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
}


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


def fetch_url():
    response = requests.get(url, headers=headers)
    print("Response: ", response.text)
    print(get_followers_following_posts(response.text.split("/n")[0]))


fetch_url()
