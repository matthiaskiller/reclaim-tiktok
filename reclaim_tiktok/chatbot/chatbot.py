import os
from typing import Literal

import requests
from dotenv import load_dotenv

load_dotenv()


class ChatBot:
    def __init__(
        self,
        api_key: str,
        endpoint: str,
        system_message: str | None = None,
        temperature: float | None = 0,
    ):
        self.api_key, self.endpoint = api_key, endpoint
        if system_message is None:
            system_message = (
                "You are an expert on right wing content on social media. "
                "You have been given data which corresponds to far right content on Tiktok, "
                "and will **always** use this data to give answers. "
                "If you do not know the answer, say you do not know. "
                "**Never** make up facts. "
            )
        azure_search_endpoint = os.environ["AZURE_SEARCH_ENDPOINT"]
        azure_index = os.environ["AZURE_SEARCH_INDEX_NAME"]
        azure_search_key = os.environ["AZURE_SEARCH_KEY"]
        # Payload for the request
        self._payload = {
            "dataSources": [
                {
                    "type": "AzureCognitiveSearch",
                    "parameters": {
                        "endpoint": azure_search_endpoint,
                        "indexName": azure_index,
                        "key": azure_search_key,
                    },
                }
            ],
            "messages": [
                {"role": "system", "content": system_message},
            ],
            "temperature": temperature,
            "top_p": 1,
            "max_tokens": 800,
        }

    def _add_message_to_payload(self, message: str, role: Literal["user", "assistant"]):
        new_message = {"role": role, "content": message}
        self._payload["messages"].append(new_message)

    def send_message(self, message: str):
        self._add_message_to_payload(message=message, role="user")

        headers = {
            "Content-Type": "application/json",
            "api-key": self.api_key,
        }
        # Send request
        try:
            response = requests.post(self.endpoint, headers=headers, json=self._payload)
            response.raise_for_status()  # Will raise an HTTPError if the HTTP request returned an unsuccessful status code
        except requests.RequestException as e:
            raise SystemExit(f"Failed to make the request. Error: {e}")

        response = response.json()
        answer = response["choices"][0]["messages"][1]["content"]

        self._add_message_to_payload(message=answer, role="assistant")

        return answer


def main():
    # Configuration
    GPT4V_KEY = os.environ["AZURE_OPENAI_API_KEY"]
    GPT4V_ENDPOINT = os.environ["AZURE_CHAT_COMPLETIONS_ENDPOINT"]

    chatbot = ChatBot(api_key=GPT4V_KEY, endpoint=GPT4V_ENDPOINT)
    while True:
        user_query = input("Please enter a query: ")
        answer = chatbot.send_message(user_query)

        print("\n\nMessage:\n", answer, "\n")


if __name__ == "__main__":
    main()
