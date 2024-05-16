import datetime
import time

import nest_asyncio
import pyodbc
from TikTokApi import TikTokApi

nest_asyncio.apply()


class Scrapper:
    def __init__(self, ms_token):
        """
        Initialize the scrapper
        Args:
            ms_token: token to access the TikTok API - can be found in browser cookies
        """
        self.ms_token = ms_token

    def update_ms_token(self, ms_token):
        """
        Update the ms_token
        Args:
            ms_token: token to access the TikTok API - can be found in browser cookies
        """
        self.ms_token = ms_token

    async def search_videos_by_hashtags(self, count=10, hashtags=[], videos=[]):
        """
        Search for videos by hashtags
        Args:
            count: number of videos to search for per hashtag
            hashtags: list of hashtags to search for
            videos: list to store the videos
        Returns:
            list of videos (TikTokApi video objects)
        """
        if not hashtags:
            raise ValueError("No hashtags provided")

        async with TikTokApi() as api:
            await api.create_sessions(
                ms_tokens=[self.ms_token], num_sessions=1, sleep_after=3, headless=False
            )

            for hashtag in hashtags:
                print(f"Searching for {hashtag}")
                tag = api.hashtag(name=hashtag)
                async for video in tag.videos(count=count, cursor=0):
                    # print(video)
                    videos.append(video)
                    # print(video.as_dict)

        return videos

    async def get_user_info_by_username(self, count=10, user_name=None):
        """
        Search for a user by username
        Args:
            count: number of videos to search for per hashtag
            user_name: username to search for
        Returns:
            user_info (TikTokApi user info)
        """
        if not user_name:
            raise ValueError("No user_name provided")

        async with TikTokApi() as api:
            await api.create_sessions(
                ms_tokens=[self.ms_token], num_sessions=1, sleep_after=3, headless=False
            )
            print(f"Searching for {user_name}")
            user = api.user(user_name)
            info = await user.info()
            return info

    async def search_videos_by_users(self, count=10, users=[], videos=[]):
        """
        Search for videos by users
        Args:
            count: number of videos to search for per hashtag
            users: list of users to search for
            videos: list to store the videos
        Returns:
            list of videos (TikTokApi video objects)
        """
        if not users:
            raise ValueError("No hashtags provided")

        async with TikTokApi() as api:
            await api.create_sessions(
                ms_tokens=[self.ms_token], num_sessions=1, sleep_after=3, headless=False
            )

            for user in users:
                user_tag = api.user(user)
                print(f"Searching for {user}")
                info = await user_tag.info()
                print(info)
                async for video in user_tag.videos(count=count, cursor=0):
                    # print(video)

                    videos.append(video)
                    # print(video.as_dict)

        return videos

    def filter_unique_videos(self, videos):
        """
        Filter unique videos
        Args:
            videos: list of videos
        Returns:
            list of unique videos
        """

        # Get unique videos
        seen_ids = set()
        unique_videos = []
        for video in videos:
            video = video.as_dict
            if video["id"] not in seen_ids:
                unique_videos.append(video)
                seen_ids.add(video["id"])
        return unique_videos

    def filter_unique_sounds(self, videos):
        """
        Filter unique videos
        Args:
            videos: list of videos
        Returns:
            list of unique sound ids videos
        """

        # Get unique videos
        seen_ids = set()
        unique_videos = []
        for video in videos:
            if video["music"]["id"] not in seen_ids:
                unique_videos.append(video)
                seen_ids.add(video["music"]["id"])
        return unique_videos

    def process_video(self, video):
        """
        Function to apply operations to each video dictionary
        Args:
            video: video dictionary
        Returns:
            processed video dictionary
        """

        def extract_duration(video_info):
            # Helper function to safely extract 'duration' from each dictionary in the 'video' column
            return (
                video_info.get("duration")
                if isinstance(video_info, dict) and "duration" in video_info
                else None
            )

        processed_video = {
            "video_id": int(video["id"]),
            "video_timestamp": datetime.datetime.fromtimestamp(video["createTime"]),
            "video_duration": extract_duration(video["video"]),
            "video_diggcount": int(video["statsV2"]["diggCount"]),
            "video_sharecount": int(video["statsV2"]["shareCount"]),
            "video_commentcount": int(video["statsV2"]["commentCount"]),
            "video_playcount": int(video["statsV2"]["playCount"]),
            "video_description": video["desc"],
            "video_is_ad": video["isAd"] if "isAd" in video else False,
            "author_username": video["author"]["uniqueId"],
            "author_name": video["author"]["nickname"],
            "author_id": int(video["author"]["id"]),
            "author_followercount": (
                video["authorStats"]["followerCount"] if "authorStats" in video else None
            ),
            "author_followingcount": (
                video["authorStats"]["followingCount"] if "authorStats" in video else None
            ),
            "author_heartcount": video["authorStats"]["heart"] if "authorStats" in video else None,
            "author_videocount": (
                video["authorStats"]["videoCount"] if "authorStats" in video else None
            ),
            "author_diggcount": (
                video["authorStats"]["diggCount"] if "authorStats" in video else None
            ),
            "author_verified": video["author"]["verified"],
            "suggested_words": (
                [word["hashtagName"] for word in video["textExtra"]]
                if "textExtra" in video and isinstance(video["textExtra"], list)
                else None
            ),
            "url": f"https://www.tiktok.com/@{video['author']['uniqueId']}/video/{video['id']}",
            "sound_id": int(video["music"]["id"]) if isinstance(video["music"], dict) else None,
            "music": video["music"],
        }
        return processed_video

    def add_users_to_db(self, processed_videos, connection_str):
        """
        Add users to the SQL database
        Args:
            processed_videos: list of processed videos
            connection_str: connection string to the SQL database
        """

        # check if there are any videos to process
        if not processed_videos:
            raise ValueError("No videos to process")

        # check if there is a connection string
        if not connection_str:
            raise ValueError("No connection string provided")

        with pyodbc.connect(connection_str) as cnxn:
            cursor = cnxn.cursor()

            # Make sure only new users get added to the db
            # Get all unique author ids from the processed videos
            unique_author_ids = {video["author_id"] for video in processed_videos}

            # Get all unique author ids from the SQL database
            cursor.execute("SELECT id FROM dbo.Users")
            unique_author_ids_sql = {row[0] for row in cursor.fetchall()}

            # Determine which author ids need to be added
            unique_author_ids_to_add = unique_author_ids - unique_author_ids_sql

            # Filter authors to add
            authors_to_add = [
                video
                for video in processed_videos
                if video["author_id"] in unique_author_ids_to_add
            ]
            print("Number of new users to be added to database", len(authors_to_add))

            # Add authors to SQL database
            for author in authors_to_add:
                query = """
                INSERT INTO dbo.Users
                (id, unique_name_id, nickname, follower_count, following_count, heart_count, video_count, digg_count, verified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                data = (
                    int(author["author_id"]),
                    str(author["author_username"]),
                    str(author["author_name"]),
                    int(author["author_followercount"]),
                    int(author["author_followingcount"]),
                    int(author["author_heartcount"]),
                    int(author["author_videocount"]),
                    int(author["author_diggcount"]),
                    bool(author["author_verified"]),
                )
                cursor.execute(query, data)
            cnxn.commit()
            print("Users added to database successfully")

    def add_sounds_to_db(self, processed_videos, connection_str):
        """
        Add sounds to the SQL database
        Args:
            processed_videos: list of processed videos
            connection_str: connection string to the SQL database
        """
        # check if there are any videos to process
        if not processed_videos:
            raise ValueError("No videos to process")

        # check if there is a connection string
        if not connection_str:
            raise ValueError("No connection string provided")

        with pyodbc.connect(connection_str) as cnxn:
            cursor = cnxn.cursor()

            # check for duplicate sounds in processed videos
            processed_videos = self.filter_unique_sounds(processed_videos)

            # Get all unique sound ids from the processed videos
            unique_sound_ids = {
                video["sound_id"] for video in processed_videos if video["sound_id"]
            }

            # Get all unique sound ids from the SQL database
            cursor.execute("SELECT id FROM dbo.Sounds")
            unique_sound_ids_sql = {row[0] for row in cursor.fetchall()}

            # Determine which sound ids need to be added
            unique_sound_ids_to_add = unique_sound_ids - unique_sound_ids_sql

            # Filter sounds to add
            sounds_to_add = [
                video for video in processed_videos if video["sound_id"] in unique_sound_ids_to_add
            ]

            print("Number of new sounds to be added to database", len(sounds_to_add))

            # Add sounds to SQL database
            for sound in sounds_to_add:
                query = """
                INSERT INTO dbo.Sounds
                (id, title, original_sound, album, author_name, url)
                VALUES (?, ?, ?, ?, ?, ?)
                """
                title = str(sound["music"]["title"]).strip().replace(" ", "-")
                url = f"https://www.tiktok.com/music/{title}-{sound['sound_id']}"
                data = (
                    int(sound["sound_id"]),
                    str(sound["music"]["title"]),
                    bool(sound["music"]["original"]),
                    str(sound["music"]["album"]) if "album" in sound["music"] else None,
                    str(sound["music"]["authorName"]) if "authorName" in sound["music"] else None,
                    url,
                )
                cursor.execute(query, data)
            cnxn.commit()

            print("Sounds added to database successfully")

    def add_videos_to_db(self, processed_videos, connection_str):
        """
        Add videos to the SQL database
        Args:
            processed_videos: list of processed videos
            connection_str: connection string to the SQL database
        """

        # check if there are any videos to process
        if not processed_videos:
            raise ValueError("No videos to process")

        # check if there is a connection string
        if not connection_str:
            raise ValueError("No connection string provided")

        with pyodbc.connect(connection_str) as cnxn:
            cursor = cnxn.cursor()

            # Get all unique video ids from the SQL database
            cursor.execute("SELECT id FROM dbo.Videos")
            unique_video_ids_sql = {row[0] for row in cursor.fetchall()}

            # Determine which video ids need to be added
            unique_video_ids_to_add = {
                video["video_id"] for video in processed_videos
            } - unique_video_ids_sql

            # Filter videos to add
            videos_to_add = [
                video for video in processed_videos if video["video_id"] in unique_video_ids_to_add
            ]

            print("Number of new videos to be added to database", len(videos_to_add))

            # Add videos to SQL database
            for video in videos_to_add:
                query = """
                INSERT INTO dbo.Videos
                (id, timestamp_upload, timestamp_db, duration, digg_count, share_count, comment_count, play_count, description, is_ad, author_id, suggested_words, url, transcript_en, transcript_de, sound_id, removed, has_transcript, no_transcript_reason, core_messages_de)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                data = (
                    int(video["video_id"]),
                    video["video_timestamp"],
                    datetime.datetime.fromtimestamp(time.time()),  # Current time as datetime
                    float(video["video_duration"]),
                    int(video["video_diggcount"]),
                    int(video["video_sharecount"]),
                    int(video["video_commentcount"]),
                    int(video["video_playcount"]),
                    str(video["video_description"]),
                    bool(video["video_is_ad"]),
                    int(video["author_id"]),
                    str(video["suggested_words"]),
                    str(video["url"]),
                    None,
                    None,
                    int(video["sound_id"]) if video["sound_id"] else None,
                    False,
                    None,
                    None,
                    None,
                )
                cursor.execute(query, data)
            cnxn.commit()
            print("Videos added to database successfully")
