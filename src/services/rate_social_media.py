import time


class RateSocialMediaService:
    def __init__(self):
        pass

    def calculate_score(self, value, max_value, max_score):
        if value > max_value:
            return max_score

        return (value / max_value) * max_score

    def calculate_post_score(self, post_list, max_score):
        now = time.time()
        FIRST_WEEK_SECONDS = 7 * 24 * 60 * 60  # days x hours x minutes x seconds
        SECOND_WEEK_SECONDS = 14 * 24 * 60 * 60  # days x hours x minutes x seconds
        THIRD_WEEK_SECONDS = 21 * 24 * 60 * 60  # days x hours x minutes x seconds
        LAST_WEEK_SECONDS = 30 * 24 * 60 * 60  # days x hours x minutes x seconds
        sorted_posts = sorted(post_list, reverse=True)[:5]
        post_length = len(sorted_posts)

        if post_length == 0:
            return 0

        fourth = sum(
            1
            for ts in sorted_posts
            if now - ts <= LAST_WEEK_SECONDS and now - ts > THIRD_WEEK_SECONDS
        )
        third = sum(
            1
            for ts in sorted_posts
            if now - ts <= THIRD_WEEK_SECONDS and now - ts > SECOND_WEEK_SECONDS
        )
        second = sum(
            1
            for ts in sorted_posts
            if now - ts <= SECOND_WEEK_SECONDS and now - ts > FIRST_WEEK_SECONDS
        )
        first = sum(1 for ts in sorted_posts if now - ts <= FIRST_WEEK_SECONDS)
        total_score = (
            ((first) + (second * 0.75) + (third * 0.5) + (fourth * 0.25)) / post_length
        ) * max_score

        # Round to the nearest 2 decimal places
        return round(total_score, 2)

    def calculate_overall_score(self, platform_scores: dict):
        if not platform_scores:
            return 0

        percentage = {
            "facebook": 50,
            "instagram": 30,
            "x": 11,
            "tiktok": 9,
        }

        main_platform = ""
        highest_percentage = 0
        for k, _ in platform_scores.items():
            if percentage[k] > highest_percentage:
                highest_percentage = percentage[k]
                main_platform = k

        main_platform_percentage_addition = 0
        for k, _ in percentage.items():
            if k not in platform_scores:
                main_platform_percentage_addition += percentage[k]

        percentage[main_platform] += main_platform_percentage_addition
        total_score = 0
        for platform, score in platform_scores.items():
            total_score += score * (percentage[platform] / 100)

        # Round to the nearest 2 decimal places
        return round(total_score, 2)

    def rate(self, data):
        MAX_FOLLOWERS = 10_000  # 10k
        MAX_LIKES = 10_000  # 10k

        platform_scores = {}

        for platform, info in data.items():
            if type(info) is not dict or "error" in info:
                continue

            verified_score = 1 if info.get("verified") else 0

            followers = info.get("follower") or info.get("followers") or 0
            follower_score = self.calculate_score(followers, MAX_FOLLOWERS, 2)

            likes = info.get("likes") or info.get("like") or 0
            like_score = self.calculate_score(likes, MAX_LIKES, 2)

            posts = info.get("posts") or []
            # Calculate post score based on recent posts within the last 30 days
            post_score = 0
            post_score = self.calculate_post_score(posts, 7)

            if (platform == "x" or platform == "instagram") or (
                likes == 0 and platform == "facebook"
            ):
                like_score = follower_score

            total_score = (
                verified_score + ((follower_score + like_score) / 2) + post_score
            )
            platform_scores[platform] = total_score

        overall = self.calculate_overall_score(platform_scores)

        for platform, info in data.items():
            if type(info) is not dict or "error" in info:
                platform_scores[platform] = info

        return {
            "platformScores": platform_scores,
            "overallRating": overall,
        }


# Example data (timestamps are Unix seconds)
# data = {
#     # "facebook": {
#     #     "verified": True,
#     #     "like": 100,
#     #     "follower": 9000000,
#     #     "reviews": "No reviews",
#     #     "posts": [1752048421, 1752048421, 1751962021, 1751875621, 1751789221],
#     # },
#     # "instagram": {
#     #     "verified": True,
#     #     "follower": 542000,
#     #     "posts": [1752076800, 1751990400, 1751904000, 1751817600, 1751731200],
#     # },
#     "tiktok": {
#         "verified": True,
#         "likes": 12000000,
#         "follower": 1500000,
#         "posts": [1752045631, 1751777240, 1751623208, 1750932644, 1750759223],
#     },
#     "x": {
#         "verified": True,
#         "follower": 579100,
#         "posts": [1718640000, 1579622400, 1645200000, 1720800000],
#     },
# }


# data = {'facebook': {'verified': False, 'reviews': '78% recommend (412 Reviews)\ufeff', 'posts': [1751221380, 1750188480, 1750003380, 1749139200, 1748534400, 1748361600, 1747238400]}, 'instagram': 'No URL provided.', 'tiktok': 'No URL provided.', 'x': 'No URL provided.'}
# service = RateSocialMediaService()
# result = service.rate(data)
# print(result)
