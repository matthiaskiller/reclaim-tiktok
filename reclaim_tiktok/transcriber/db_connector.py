import logging
import os

import pyodbc
from dotenv import load_dotenv

from reclaim_tiktok.transcriber.main_transcriber import StatCollector, print_progress_bar
from reclaim_tiktok.transcriber.tiktok_video_details import (
    HTTPRequestError,
    RequestReturnedNoneError,
    TiktokVideoDetails,
    VideoIsPrivateError,
)

load_dotenv()

LOG = logging.getLogger("reclaim_tiktok")


class DBConnector:
    def __init__(self):
        driver = os.environ["DB_DRIVER"]
        server = os.environ["DB_SERVER"]
        database = os.environ["DB_DATABASE"]
        username = os.environ["DB_USERNAME"]
        password = os.environ["DB_PASSWORD"]

        self.table = "[dbo].[Videos]"

        self.connection_str = (
            f"Driver={driver};Server={server},1433;Database={database};"
            f"Uid={username};Pwd={password};Encrypt=yes;"
            "TrustServerCertificate=no;Connection Timeout=30;"
        )

    def get_videos_without_transcription(self):
        """
        Get all the videos that do not have a transcript in the database
        Returns:
            list of pyodbc.Row: The rows that do not have a transcript
        """
        with pyodbc.connect(self.connection_str) as cnxn:
            cursor = cnxn.cursor()
            query = (
                f"SELECT * FROM {self.table} "
                "WHERE transcript_en IS NULL AND transcript_de IS NULL AND no_transcript_reason IS NULL"
            )
            cursor.execute(query)
            rows = cursor.fetchall()
            LOG.debug("Fetched %d rows without transcription", len(rows))
            return rows

    def get_videos_with_transcription(self):
        """
        Get all the videos that have a transcript in the database
        Returns:
            list of pyodbc.Row: The rows that have a transcript
        """
        with pyodbc.connect(self.connection_str) as cnxn:
            cursor = cnxn.cursor()
            query = (
                f"SELECT * FROM {self.table} "
                "WHERE transcript_en IS NOT NULL OR transcript_de IS NOT NULL"
            )
            cursor.execute(query)
            rows = cursor.fetchall()
            return rows

    def get_videos_with_german_transcription(self):
        """
        Get all the videos that have a german transcript in the database
        Returns:
            list of pyodbc.Row: The rows that have a transcript
        """
        with pyodbc.connect(self.connection_str) as cnxn:
            cursor = cnxn.cursor()
            query = f"SELECT * FROM {self.table} " "WHERE transcript_de IS NOT NULL"
            cursor.execute(query)
            rows = cursor.fetchall()
            return rows

    def get_videos_with_german_transcription_without_core_message(self):
        """
        Get all the videos that have a german transcript in the database but no core message
        Returns:
            list of pyodbc.Row: The rows that have a transcript
        """
        with pyodbc.connect(self.connection_str) as cnxn:
            cursor = cnxn.cursor()
            query = (
                f"SELECT * FROM {self.table} "
                "WHERE transcript_de IS NOT NULL AND core_messages_de IS NULL"
            )
            cursor.execute(query)
            rows = cursor.fetchall()
            return rows

    def get_videos_with_german_transcription_with_core_message(self):
        """
        Get all the videos that have a german transcript in the database and a core message
        Returns:
            list of pyodbc.Row: The rows that have a transcript
        """
        with pyodbc.connect(self.connection_str) as cnxn:
            cursor = cnxn.cursor()
            query = (
                f"SELECT * FROM {self.table} "
                "WHERE transcript_de IS NOT NULL AND core_messages_de IS NOT NULL"
            )
            cursor.execute(query)
            rows = cursor.fetchall()
            return rows

    def update_transcript(
        self,
        video_id: int,
        transcript_en: str,
        transcript_de: str,
        no_transcript_reason: str,
    ):
        """
        Update the transcript of a video in the database
        Args:
            video_id (int): The video ID
            transcript_en (str): The English transcript
            transcript_de (str): The German transcript
            no_transcript_reason (str): The reason why there is no transcript
        """
        with pyodbc.connect(self.connection_str) as cnxn:
            cursor = cnxn.cursor()
            query = f"""
            UPDATE {self.table}
            SET transcript_en = ?, transcript_de = ?, has_transcript = ?, no_transcript_reason = ?
            WHERE id = ?
            """

            has_transcript = True if transcript_de or transcript_en else False
            if not transcript_en:
                transcript_en = None
            if not transcript_de:
                transcript_de = None
            if not no_transcript_reason:
                no_transcript_reason = None

            cursor.execute(
                query, transcript_en, transcript_de, has_transcript, no_transcript_reason, video_id
            )

    def update_transcript_multiple(self, rows: list[pyodbc.Row]) -> None:
        """
        Update the transcripts of multiple videos in the database

        Args:
            rows (list[pyodbc.Row]): List of rows to be updated
        """
        with pyodbc.connect(self.connection_str) as cnxn:
            cursor = cnxn.cursor()
            query = f"""
            UPDATE {self.table}
            SET transcript_en = ?, transcript_de = ?, has_transcript = ?, no_transcript_reason = ?
            WHERE id = ?
            """

            total_rows = len(rows)
            stats = StatCollector()

            def update_with_failure(failure_reason: str, video_id: int):
                cursor.execute(query, None, None, False, failure_reason, video_id)

            try:
                index = 0
                for row in rows:
                    completion_percentage = (index / total_rows) * 100
                    print_progress_bar(
                        completion_percentage,
                        successes=stats.successes,
                        private=len(stats.private_videos),
                        failed=len(stats.failed_requests),
                    )
                    video_id = row[0]
                    url = row[12]
                    index += 1
                    try:
                        tt_obj = TiktokVideoDetails(url=url)
                    except VideoIsPrivateError as error:
                        stats.add_private_video(url)
                        update_with_failure(str(error), video_id)
                        LOG.info("Video is private", extra={"video_id": video_id})
                        continue
                    except (RequestReturnedNoneError, HTTPRequestError) as error:
                        stats.add_failed_request(url)
                        update_with_failure(str(error), video_id)
                        LOG.info("Video request returned None", extra={"video_id": video_id})
                        continue
                    except Exception as error:
                        stats.add_failed_request(url)
                        LOG.exception(
                            "\nUnexpected Exception occured: %s",
                            error,
                            extra={"video_id": video_id},
                        )
                        update_with_failure(str(error), video_id)
                        continue

                    try:
                        transcriptions = tt_obj.get_transcriptions(disable_azure=True)
                        if transcriptions:
                            cursor.execute(
                                query,
                                transcriptions.get("eng-US", None),
                                transcriptions.get("deu-DE", None),
                                True,
                                None,
                                video_id,
                            )
                            stats.add_success()
                            LOG.debug(
                                "Video transcripts added succesfully", extra={"video_id": video_id}
                            )
                        else:
                            update_with_failure("No transcription provided by Tiktok", video_id)
                            LOG.debug("Video has no transcription", extra={"video_id": video_id})

                    except Exception as error:
                        # print("\n", error)
                        LOG.exception(
                            "Unexpected error when getting transcripts: %s",
                            error,
                            extra={"video_id": video_id},
                        )
                        update_with_failure(str(error), video_id)
                        # ? stats.add_failed_request(url)

            except KeyboardInterrupt:
                print("\nKeyboard Interrupt detected. Stopping...")
            except Exception as error:
                # print("\nUnexpected Exception occurred when handling exception:", error)
                LOG.exception(
                    "\nUnexpected Exception occurred when handling exception: %s",
                    error,
                    extra={"video_id": video_id},
                )
            finally:
                stats.print_stats()

    def update_core_messages(
        self,
        video_id: int,
        core_messages_de: str,
    ):
        """
        Update the core_messages_de of a video in the database
        Args:
            video_id (int): The video ID
            core_messages_de: core_messages_de to be added
        """
        with pyodbc.connect(self.connection_str) as cnxn:
            cursor = cnxn.cursor()
            query = f"""
            UPDATE {self.table}
            SET core_messages_de = ?
            WHERE id = ?
            """

            cursor.execute(query, core_messages_de, video_id)

    def update_cluster_description(
        self,
        cluster_id: int,
        description: str,
    ):
        """
        Update the decsription of a cluster in the database
        Args:
            cluster (int): The cluster ID
            description: description to be added
        """
        with pyodbc.connect(self.connection_str) as cnxn:
            cursor = cnxn.cursor()
            query = """
            UPDATE [dbo].[Clusters]
            SET description = ?
            WHERE id = ?
            """

            cursor.execute(query, description, cluster_id)
            cursor.commit()
            print(f"Updated cluster {cluster_id} with description {description}")

    def get_existing_cluster_ids(self):
        """
        Get all the existing cluster ids in the database.
        Returns:
            list of pyodbc.Row: The rows that have a transcript
        """
        with pyodbc.connect(self.connection_str) as cnxn:
            cursor = cnxn.cursor()
            query = "SELECT id FROM [dbo].[Clusters] "
            cursor.execute(query)
            rows = cursor.fetchall()
            return rows
