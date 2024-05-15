import os

import pyodbc
from dotenv import load_dotenv

load_dotenv()


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

    def get_urls_without_transcription(self):
        """
        Get all the URLs that do not have a transcript in the database
        Returns:
            list of pyodbc.Row: The rows that do not have a transcript
        """
        with pyodbc.connect(self.connection_str) as cnxn:
            cursor = cnxn.cursor()
            query = (
                f"SELECT * FROM {self.table} "
                "WHERE transcript_en IS NULL AND transcript_de IS NULL"
            )
            cursor.execute(query)
            rows = cursor.fetchall()
            return rows

    def get_urls_with_transcription(self):
        """
        Get all the URLs that have a transcript in the database
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
