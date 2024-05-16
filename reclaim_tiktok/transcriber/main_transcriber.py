import os
import time

import numpy as np
import pandas as pd

from reclaim_tiktok.transcriber.tiktok_video_details import (
    HTTPRequestError,
    RequestReturnedNoneError,
    TiktokVideoDetails,
    VideoIsPrivateError,
)


class StatCollector:
    """Provides an easy method of collecting and printing statistics
    for tiktok video data collection
    """

    def __init__(self) -> None:
        self.start_time = time.time()
        self.successes = 0
        self.private_videos = []
        self.failed_requests = []

    def add_success(self) -> None:
        """Adds 1 to the success counter"""
        self.successes += 1

    def add_private_video(self, url: str) -> None:
        """Appends the ``url`` to the list of private videos to be
        returned when ``print_stats()`` is called.

        Params
        ---
        :param url: A string representing the url that links to a private video
        """
        self.private_videos.append(url)

    def add_failed_request(self, url: str) -> None:
        """Appends the ``url`` to the list of failed requests to be
        returned when ``print_stats()`` is called.

        Params
        ---
        :param url: A string representing the url that links to a failed video
        """
        self.failed_requests.append(url)

    def print_stats(self) -> None:
        """Prints the collected statistics

        Prints:
        - the list of collected private videos
        - the list of failed requests
        - Total successes
        - Total Private
        - Total Failed
        - Total elapsed time in H M S.
        """
        end_time = time.time()
        print("\n")
        print("Private: \n\t", "\n\t".join(self.private_videos))
        print("Failed: \n\t", "\n\t".join(self.failed_requests))
        print("Successes: ", self.successes)
        print("Private: ", len(self.private_videos))
        print("Failed: ", len(self.failed_requests))
        total_time = end_time - self.start_time
        hours = total_time // 3600
        minutes = (total_time % 3600) // 60
        seconds = total_time - 3600 * hours - 60 * minutes
        print("Total elapsed time: %dh %dm %.2fs" % (hours, minutes, seconds))


def print_progress_bar(percentage: float, bar_length: int = 20, **kwargs) -> None:
    """Prints a simple progress bar based on an updated percentage

    Params
    ---
    :param percentage: The percentage to be displayed
    :param bar_length: The desired length of the bar, defaulted to 20 ``'='``
    :param kwargs: Additional key value pairs to be printed next to the bar
    """
    normalizer = int(100 / bar_length)
    progress = "\r[%s%s] %.2f%%" % (
        "=" * int(percentage / normalizer),
        " " * int(bar_length - percentage / normalizer),
        percentage,
    )
    for key, value in kwargs.items():
        progress += f" {key}: {value}"
    print(progress, end="", flush=True)


def save_tiktok_info_to_existing_csv(csv_filename: str) -> None:
    """Gets tiktok urls from an existing .csv file and appends
    transcriptions and errors to it.

    Also collects and prints the statistics of the run.

    Params
    ---
    :param csv_filename: string representing a path to an existing .csv file
    """

    df = pd.read_csv(csv_filename)

    total_rows = len(df)
    errors = {}
    en_transcriptions = {}
    de_transcriptions = {}

    stats = StatCollector()

    try:
        for index, row in df.iterrows():
            completion_percentage = (index / total_rows) * 100
            print_progress_bar(completion_percentage)
            url = row["url"]
            try:
                tt_obj = TiktokVideoDetails(url=url)
            except VideoIsPrivateError as error:
                stats.add_private_video(url)
                print("\n", error)
                errors[index] = error
                continue
            except (RequestReturnedNoneError, HTTPRequestError) as error:
                stats.add_failed_request(url)
                print("\n", error)
                errors[index] = error
                continue
            except Exception as error:
                stats.add_failed_request(url)
                print("\nUnexpected Exception occured:", error)
                errors[index] = error
                continue

            try:
                transcriptions = tt_obj.get_transcriptions(disable_azure=False)
                if transcriptions:
                    stats.add_success()
                else:
                    errors[index] = "No transcription provided by Tiktok"
            except Exception as error:
                print("\n", error)
                transcriptions = {}
                errors[index] = error

            en_transcriptions[index] = transcriptions.get("eng-US", np.nan)
            de_transcriptions[index] = transcriptions.get("deu-DE", np.nan)
    except KeyboardInterrupt:
        print("\nKeyboard Interrupt detected. Stopping...")
    except Exception as error:
        print("\nUnexpected Exception occurred:", error)
    finally:
        stats.print_stats()

        target_filename = os.path.splitext(csv_filename)[0] + "_transcribed_copy.csv"
        new_df = df.assign(
            english_transcript=en_transcriptions,
            german_transcript=de_transcriptions,
            error_reason=errors,
        )
        new_df.to_csv(target_filename)


if __name__ == "__main__":
    save_tiktok_info_to_existing_csv(
        csv_filename="data/tiktok_videos_based_on_hashtags_cleaned.csv"
    )
