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
            f"Uid={username}:Pwd={password};Encrypt=yes;"
            "TrustServerCertificate=no;Connection Timeout=30;"
        )

    def get_urls_without_transcription(self):
        with pyodbc.connect(self.connection_str) as cnxn:
            cursor = cnxn.cursor()
            query = (
                f"SELECT * FROM {self.table} "
                "WHERE transcript_en IS NULL AND transcript_de IS NULL"
            )
            cursor.execute(query)
            rows = cursor.fetchall()
            return rows

    def update_transcript(
        self,
        transcript_en: str,
        transcript_de: str,
        video_id,
        no_transcript_reason: str,
    ):
        with pyodbc.connect(self.connection_str) as cnxn:
            cursor = cnxn.cursor()
            query = f"""
            UPDATE {self.table}
            SET transcript_en = ?, transcript_de = ?, has_transcript = ?, error_reason = ?
            WHERE video_id = ?
            """

            has_transcript = "true" if transcript_de or transcript_en else "false"
            if not transcript_en:
                transcript_en = "NULL"
            if not transcript_de:
                transcript_de = "NULL"
            if not no_transcript_reason:
                no_transcript_reason = "NULL"

            cursor.execute(
                query, transcript_en, transcript_de, has_transcript, no_transcript_reason, video_id
            )
