import logging
import os
import time

import azure.cognitiveservices.speech as speechsdk
import requests
from dotenv import load_dotenv

from reclaim_tiktok.video_indexer.consts import Consts
from reclaim_tiktok.video_indexer.video_indexer_client import VideoIndexerClient

LOG = logging.getLogger("transcriber.azure_connector")
load_dotenv()

SPEECH_SUBSCRIPTION_KEY = os.environ["AZURE_SPEECH_KEY"]
REGION = os.environ["AZURE_SPEECH_REGION"]
SUBSCRIPTION_ID = os.environ["AZURE_SUBSCRIPTION_ID"]
SPEECH_ENDPOINT = os.environ["AZURE_SPEECH_ENDPOINT"]
RESOURCE_GROUP = os.environ["RESOURCE_GROUP"]
ACCOUNT_ID = os.environ["RECLAIM_TIKTOK_ACCOUNT_ID"]
VIDEO_ACCESS_TOKEN = os.environ["AZURE_VIDEO_ACCESS_TOKEN"]


class AzureConnector:
    """Provides functionality for connecting to the Azure Endpoints"""

    """Function taken and slightly modified from https://github.com/Azure-Samples/cognitive-services-speech-sdk/blob/b55026a09e2f807db9289acd6cdd3b623f44b3e9/samples/python/console/translation_sample.py#L231"""

    def translation_continuous_with_lid_from_multilingual_file(
        filename: str, speech_key: str = None, service_region: str = None
    ) -> dict:
        """performs continuous speech translation from a multi-lingual
        audio file, with continuous language identification
        """

        # <TranslationContinuousWithLID>

        # When you use Language ID with speech translation,
        # you must set a v2 endpoint.
        # This will be fixed in a future version of Speech SDK.

        # Set up translation parameters,
        # including the list of target (translated) languages.
        endpoint_string = "wss://{}.stt.speech.microsoft.com/speech/universal/v2".format(
            service_region or REGION
        )
        translation_config = speechsdk.translation.SpeechTranslationConfig(
            subscription=speech_key or SPEECH_SUBSCRIPTION_KEY,
            endpoint=endpoint_string,
            target_languages=("de", "en"),
        )
        audio_config = speechsdk.audio.AudioConfig(filename=filename)

        # Since the spoken language in the input audio changes,
        # you need to set the language identification to "Continuous" mode.
        # (override the default value of "AtStart").
        translation_config.set_property(
            property_id=speechsdk.PropertyId.SpeechServiceConnection_LanguageIdMode,
            value="Continuous",
        )

        # Specify the AutoDetectSourceLanguageConfig, which defines the number of possible languages
        auto_detect_source_language_config = (
            speechsdk.languageconfig.AutoDetectSourceLanguageConfig(languages=["en-US", "de-DE"])
        )

        # Creates a translation recognizer using and audio file as input.
        recognizer = speechsdk.translation.TranslationRecognizer(
            translation_config=translation_config,
            audio_config=audio_config,
            auto_detect_source_language_config=auto_detect_source_language_config,
        )

        translations = {}

        def result_callback(evt):
            """callback to display a translation result"""
            if evt.result.reason == speechsdk.ResultReason.TranslatedSpeech:
                # src_lang = evt.result.properties[speechsdk.PropertyId.SpeechServiceConnection_AutoDetectSourceLanguageResult]
                LOG.info("Succesful translation and transcription from Azure")

                nonlocal translations

                # Add a space between each streamed caption and the
                # previous translations
                translations["eng-US"] = (
                    translations.get("eng-US", "") + evt.result.translations["en"] + " "
                )
                translations["deu-DE"] = (
                    translations.get("deu-DE", "") + evt.result.translations["de"] + " "
                )
            elif evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                print("Recognized:\n {}".format(evt.result.text))
            elif evt.result.reason == speechsdk.ResultReason.NoMatch:
                print("No speech could be recognized: {}".format(evt.result.no_match_details))
            elif evt.result.reason == speechsdk.ResultReason.Canceled:
                print("Translation canceled: {}".format(evt.result.cancellation_details.reason))
                if evt.result.cancellation_details.reason == speechsdk.CancellationReason.Error:
                    print(
                        "Error details: {}".format(evt.result.cancellation_details.error_details)
                    )

        done = False

        def stop_cb(evt):
            """callback that signals to stop continuous recognition upon receiving an event `evt`"""
            print("CLOSING on {}".format(evt))
            nonlocal done
            done = True

        # connect callback functions to the events fired by the recognizer
        recognizer.session_started.connect(lambda evt: print("SESSION STARTED: {}".format(evt)))
        recognizer.session_stopped.connect(lambda evt: print("SESSION STOPPED {}".format(evt)))

        # event for final result
        recognizer.recognized.connect(lambda evt: result_callback(evt))

        # cancellation event
        recognizer.canceled.connect(lambda evt: print("CANCELED: {} ({})".format(evt, evt.reason)))

        # stop continuous recognition on either session stopped or canceled events
        recognizer.session_stopped.connect(stop_cb)
        recognizer.canceled.connect(stop_cb)

        # start translation
        recognizer.start_continuous_recognition()

        while not done:
            time.sleep(0.5)

        recognizer.stop_continuous_recognition()

        return translations

    def copied_get_ocr_from_azure(
        url: str, video_name: str, video_description: str = None, excluded_ai: list = None
    ) -> dict:
        """

        Make sure to be logged in via 'az' cli for this to work
        """
        api_version = "2024-01-01"
        api_endpoint = "https://api.videoindexer.ai"
        azure_resource_manager = "https://management.azure.com"

        consts = Consts(
            api_version,
            api_endpoint,
            azure_resource_manager,
            "tiktok-indexer",
            RESOURCE_GROUP,
            SUBSCRIPTION_ID,
        )

        client = VideoIndexerClient()

        client.authenticate_async(consts)

        if excluded_ai is None:
            excluded_ai = ["Faces", "ObservedPeople"]
        if video_description is None:
            video_description = ""

        video_id = client.upload_url_async(
            video_name=video_name,
            video_url=url,
            excluded_ai=excluded_ai,
            video_description=video_description,
            wait_for_index=True,
        )

        results = client.get_video_async(video_id)

        print(results)

        return {}  # TODO Analyze 'results' and return proper result

    def get_ocr_from_azure(url: str):
        endpoint_url_root = f"https://api.videoindexer.ai/{REGION}/Accounts/{ACCOUNT_ID}"
        access_token_url = (
            "https://management.azure.com/subscriptions/"
            f"{SUBSCRIPTION_ID}/resourceGroups/"
            f"{RESOURCE_GROUP}/providers/Microsoft.VideoIndexer/accounts/"
            f"{ACCOUNT_ID}/generateAccessToken?"
            "api-version=2024-01-01"
        )
        body = {"permissionType": "Contributor", "scope": "Account"}

        response = requests.post(
            access_token_url,
            json=body,
        )
        print(response.json())
        access_token = response.text.replace('"', "")

        upload_video_url = (
            f"{endpoint_url_root}/Videos?"
            f"accessToken={access_token}&name=test&"
            f"privacy=private&videoUrl={url}"
        )
        response = requests.post(upload_video_url).json()

        if "ErrorType" in response.keys():
            print(response.get("Message"))
            return {}
        video_id = response.json()["id"]

        index_url = f"{endpoint_url_root}/Videos/{video_id}/Index?accessToken={access_token}"

        response = requests.get(index_url)

        index = response.json()

        print(index)

        return {}
