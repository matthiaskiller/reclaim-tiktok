import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from chatbot import ChatBot

load_dotenv()
app = Flask(__name__)
cors = CORS(app)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/get-chat-completion", methods=["POST"])
def get_chat_completion():
    api_key = os.environ["AZURE_OPENAI_API_KEY"]
    endpoint = os.environ["AZURE_CHAT_COMPLETIONS_ENDPOINT"]

    data = request.get_json()
    user_message = data["message"]

    chatbot = ChatBot(api_key=api_key, endpoint=endpoint)
    response = chatbot.send_message(user_message)

    response = jsonify({"message": response})

    return response


if __name__ == "__main__":
    app.run(port=5000)
