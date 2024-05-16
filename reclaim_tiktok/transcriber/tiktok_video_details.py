import io
import json
import logging
import os
import re

import browser_cookie3
import numpy as np
import pandas as pd
import pyktok as pyk
import requests
import webvtt
from bs4 import BeautifulSoup
from moviepy.editor import VideoFileClip
from requests.exceptions import ReadTimeout, SSLError

from reclaim_tiktok.transcriber.azure_connector import AzureConnector

pyk.specify_browser("chrome")

LOG = logging.getLogger("reclaim_tiktok")

BROWSER_NAME = "chrome"

headers = {
    "Accept-Encoding": "gzip, deflate, sdch",
    "Accept-Language": "en-US,en;q=0.8",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
}


class VideoIsPrivateError(Exception):
    """Raised when a tiktok video's details are not present"""

    pass


class RequestReturnedNoneError(Exception):
    """Raised when the request to get tiktok video metadata has failed
    due to Tiktok or other unknown reasons
    """

    pass


class HTTPRequestError(Exception):
    """Raised when an exception occurred in making a request for tiktok
    metadata due to an HTTP error from the ``requests`` library
    """

    pass


class TiktokVideoDetails:
    """Creates an instance of a tiktok object, which allows easy methods
    of obtaining information pertaining to the video linked by the
    ``url`` given in the ``__init__()``
    """

    def __init__(self, url: str) -> None:
        """
        Params
        ---
        :param url: a string representing a url to a tiktok video
        """
        self.transcription_source: str
        self.transcriptions: dict = None
        self.cookies = None
        self.url = url
        retries = 3
        while retries > 0:
            try:
                # tt_json = pyk.alt_get_tiktok_json(self.url)
                tt_json = self._get_tiktok_json(self.url)
            except (ReadTimeout, SSLError, HTTPRequestError):
                retries -= 1
                LOG.debug(
                    "HTTPRequestError encountered",
                    extra={"video_url": url, "retries_left": retries},
                )
                if retries == 0:
                    raise HTTPRequestError("\nEncountered an error when making the http request.")
                continue
            except Exception as error:
                retries -= 1
                LOG.debug(
                    "Exception encountered: %s",
                    error,
                    extra={"video_url": url, "retries_left": retries},
                )
                if retries == 0:
                    raise
                continue
            if tt_json is None:
                retries -= 1
                LOG.debug(
                    "RequestReturnedNoneError encountered",
                    extra={"video_url": url, "retries_left": retries},
                )
                if retries == 0:
                    raise RequestReturnedNoneError(
                        "\nJson request returned None. Please try again later."
                    )
                continue
            try:
                self.details: dict = tt_json["__DEFAULT_SCOPE__"]["webapp.video-detail"][
                    "itemInfo"
                ]["itemStruct"]
            except KeyError:
                retries -= 1
                LOG.debug(
                    "VideoIsPrivateError encountered",
                    extra={"video_url": url, "retries_left": retries},
                )
                if retries == 0:
                    raise VideoIsPrivateError(
                        "\nVideo details could not be parsed. "
                        "Video is private or has been removed."
                    )
                continue
            break

    def _get_tiktok_json(self, video_url) -> dict | None:
        if self.cookies is None:
            self.cookies = getattr(browser_cookie3, BROWSER_NAME)(domain_name="www.tiktok.com")
        tt = requests.get(video_url, headers=headers, cookies=self.cookies, timeout=20)
        if tt.status_code != 200:
            raise HTTPRequestError
        soup = BeautifulSoup(tt.text, "html.parser")
        tt_script = soup.find("script", attrs={"id": "__UNIVERSAL_DATA_FOR_REHYDRATION__"})
        if tt_script is None:
            return
        tt_json = json.loads(tt_script.string)
        self.cookies = tt.cookies
        return tt_json

    @property
    def video_id(self) -> int:
        """The id of the video"""
        return int(self.details.get("id"))

    @property
    def description(self) -> str:
        """The description of the video"""
        return self.details.get("desc")

    @property
    def suggested_words(self) -> list:
        """A list of suggested words associated with the video,
        can be empty
        """
        return self.details.get("suggestedWords", [])

    @property
    def has_original_sound(self) -> bool:
        """Returns ``True`` if the sound associated with the video is
        list as original. Returns ``False`` otherwise.
        """
        if sound_is_original := self.details["music"].get("original"):
            return eval(sound_is_original.title())
        music_author_name = self.details["music"]["authorName"]
        video_author_nickname = self.details["author"]["nickname"]
        return music_author_name == video_author_nickname

    @property
    def download_url(self) -> str:
        """The url to use when downloading the video."""
        return self.details["video"].get("downloadAddr")

    @property
    def duration(self) -> int:
        """Duration of the tiktok in seconds. Defaults to 20."""
        return int(self.details["video"].get("duration", 20))

    @property
    def as_mp4_file_name(self) -> str:
        video_prefix = re.findall(pyk.url_regex, self.url)[0]
        video_filename = video_prefix.replace("/", "_") + ".mp4"
        return video_filename

    def get_transcriptions(self, disable_azure: bool = False) -> dict:
        """Gets english and/or german transcriptions of the video.

        If none are present and ``disable_azure=False``, then the video
        is downloaded and sent to Azure Speech to Text for transcribing.

        Params
        ---
        :param disable_azure: (optional) Enables or disables Azure Speech
            to Text. Default is ``False``.

        Returns
        ---
        :returns: dict with possible keys 'eng-US', 'deu-DE' or empty.
        """
        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        )
        headers = {"User-Agent": user_agent}
        self.transcriptions = {}

        for info in self.details["video"].get("subtitleInfos", []):
            if (language := info["LanguageCodeName"]) in ["eng-US", "deu-DE"] and info[
                "Format"
            ] == "webvtt":
                result = requests.get(info["Url"], headers=headers)
                if vtt := result.content.decode():
                    transcript = ""
                    try:
                        for caption in webvtt.read_buffer(io.StringIO(vtt)):
                            # Some captions require an extra space in between
                            transcript += f"{caption.text} "
                    except webvtt.MalformedFileError as error:
                        LOG.exception(
                            "Encountered MalfromedFileError in transcription: %s",
                            error,
                            {"video_url": self.url},
                        )
                        continue
                    self.transcriptions[language] = transcript

        self.transcription_source = "Tiktok"

        if not self.transcriptions and not disable_azure:
            if True:  # self.has_original_sound: # TODO Check if this is viable
                self.transcriptions = self.get_transcription_from_azure()

            # TODO
            # if not transcriptions:
            #     transcriptions = AzureConnector.get_ocr_from_azure(
            #       url=self.download_url)
            #     self.transcription_source = "Azure Video Indexer"

        return self.transcriptions

    def save_data_to_csv_file(self, csv_filename: str, disable_azure: bool = False) -> None:
        """Creates .csv file containing the videos metadata. If the file
        already exists, the metadata will be appended to the existing
        data in the .csv file.

        Params
        ---
        :param csv_filename: A string path to a .csv file that may or
            may not exist
        :param disable_azure: Enables or disables Azure when getting
            transcriptions.
        """
        # Gather video meta data
        meta_data = pyk.generate_data_row(video_obj=self.details)

        # Many columns come consistently empty, so we remove them here
        meta_data = meta_data.dropna(axis=1)

        if self.transcriptions is None:
            self.get_transcriptions(disable_azure=disable_azure)

        # Add custom desired info
        meta_data["suggested_words"] = " / ".join(self.suggested_words)
        meta_data["url"] = self.url
        meta_data["transcription_source"] = self.transcription_source
        meta_data["english_transcript"] = self.transcriptions.get("eng-US", np.nan)
        meta_data["german_transcript"] = self.transcriptions.get("deu-DE", np.nan)

        if os.path.exists(csv_filename):
            df = pd.read_csv(csv_filename, index_col=0)
            meta_data = pd.concat([df, meta_data], ignore_index=True)
        else:
            print("Creating new csv file")

        meta_data.to_csv(csv_filename)

    def get_transcription_from_azure(self) -> dict:
        """Downloads and separates the audio of a tiktok video for
        processing in Azure Speech to be trancribed.

        Returns
        ---
        :returns: dictionary containing possible keys 'eng-US',
            'deu-DE', or empty
        """
        # save audio/video and perform speech to text
        # pyktok uses the below logic to name the file
        pyk.save_tiktok(self.url)
        video_prefix = re.findall(pyk.url_regex, self.url)[0]
        video_filename = video_prefix.replace("/", "_") + ".mp4"

        # Get audio from tiktok
        video_clip = VideoFileClip(video_filename)
        audio = video_clip.audio
        audio_filename = os.path.splitext(video_filename)[0] + ".wav"
        audio.write_audiofile(audio_filename)

        transcriptions = AzureConnector.translation_continuous_with_lid_from_multilingual_file(
            audio_filename
        )

        audio.close()
        video_clip.close()

        os.remove(video_filename)
        os.remove(audio_filename)

        self.transcription_source = "Azure Speech to Text"

        return transcriptions
