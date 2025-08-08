import time


class RateSocialMediaService:
    def __init__(self):
        pass

    def calculate_score(self, value, max_value, max_score):
        if value > max_value:
            return max_score

        return (value / max_value) * max_score

    def calculate_post_score(self, post_list, max_score):
        """
        Calculate the post score based on the timestamps of the gathered recent posts.

        The score is calculated as follows:

        - The most recent week gets a full score (1.0)
        - The second most recent week gets 0.75 of the score
        - The third most recent week gets 0.5 of the score
        - The fourth most recent week gets 0.25 of the score

        The total score is then divided by weighted sum of 12.5 which expects 5 posts
        per week
        (5 * 1) + (5 * 0.75) + (5 * 0.5) + (5 * 0.25) = 5 + 3.75 + 2.5 + 1.25 = 12.5

        Args:
            post_list (list): A list of timestamps of the gathered recent posts.
            max_score (float): The maximum score that can be given.

        Returns:
            float: The calculated post score.
        """  # noqa
        now = time.time()
        FIRST_WEEK_SECONDS = 7 * 24 * 60 * 60  # days x hours x minutes x seconds
        SECOND_WEEK_SECONDS = 14 * 24 * 60 * 60  # days x hours x minutes x seconds
        THIRD_WEEK_SECONDS = 21 * 24 * 60 * 60  # days x hours x minutes x seconds
        LAST_WEEK_SECONDS = 30 * 24 * 60 * 60  # days x hours x minutes x seconds
        sorted_posts = sorted(post_list, reverse=True)
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
            ((first) + (second * 0.75) + (third * 0.5) + (fourth * 0.25)) / 12.5
        ) * max_score

        if total_score > max_score:
            total_score = max_score

        # Round to the nearest 2 decimal places
        return round(total_score, 2)

    def calculate_overall_score(self, platform_scores: dict):
        """
        Calculate the overall score based on the scores of individual platforms.

        Given a dictionary of platform names as keys and scores as values, this
        function will calculate the overall score by assigning a percentage of
        importance to each platform and multiplying the score of each platform by
        that percentage. The total score is then returned.

        Args:
            platform_scores (dict): A dictionary with platform names as keys and
                scores as values.

        Returns:
            float: The total score, rounded to the nearest 2 decimal places.
        """
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
        """
        Rates a given social media account based on follower count, likes, posts within the last 30 days, and verification status.

        Args:
            data (dict): A dictionary containing social media platform names as keys and dictionaries of respective data as values.

        Returns:
            dict: A dictionary with platform names as keys, scores as values, and an "overallRating" key with the total score.
        """  # noqa
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
