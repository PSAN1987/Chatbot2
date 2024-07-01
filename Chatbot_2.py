# -*- coding: utf-8 -*-
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient, Configuration, MessagingApi,
    ReplyMessageRequest, TextMessage
)
from linebot.v3.webhooks import (
    FollowEvent, MessageEvent, TextMessageContent
)
import os

# Load .env file
from dotenv import load_dotenv
load_dotenv()

# Assign environment variables to variables
CHANNEL_ACCESS_TOKEN = os.environ["CHANNEL_ACCESS_TOKEN"]
CHANNEL_SECRET = os.environ["CHANNEL_SECRET"]

# Instantiate Flask app
app = Flask(__name__)

# Load LINE access token
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(CHANNEL_SECRET)

# In-memory storage for user states
user_states = {}

# Define possible states
STATE_INITIAL = "initial"
STATE_ASK_BREAKFAST = "ask_breakfast"
STATE_ASK_LUNCH = "ask_lunch"
STATE_ASK_DINNER = "ask_dinner"
STATE_COMPLETED = "completed"

# Callback function
@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

# Send a message when a friend is added
@handler.add(FollowEvent)
def handle_follow(event):
    user_id = event.source.user_id
    user_states[user_id] = {
        "state": STATE_INITIAL,
        "breakfast": None,
        "lunch": None,
        "dinner": None
    }
    # Instantiate API client
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        # Reply
        line_bot_api.reply_message(ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text='Hello! What did you eat yesterday for breakfast?')]
        ))

# Echo back received messages
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    user_id = event.source.user_id
    user_message = event.message.text

    if user_id not in user_states:
        user_states[user_id] = {
            "state": STATE_INITIAL,
            "breakfast": None,
            "lunch": None,
            "dinner": None
        }

    user_state = user_states[user_id]["state"]

    # Instantiate API client
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        
        if user_state == STATE_INITIAL:
            user_states[user_id]["state"] = STATE_ASK_BREAKFAST
            reply = "What did you eat for breakfast?"
        elif user_state == STATE_ASK_BREAKFAST:
            user_states[user_id]["breakfast"] = user_message[:30]
            user_states[user_id]["state"] = STATE_ASK_LUNCH
            reply = "What did you eat for lunch?"
        elif user_state == STATE_ASK_LUNCH:
            user_states[user_id]["lunch"] = user_message[:30]
            user_states[user_id]["state"] = STATE_ASK_DINNER
            reply = "What did you eat for dinner?"
        elif user_state == STATE_ASK_DINNER:
            user_states[user_id]["dinner"] = user_message[:30]
            user_states[user_id]["state"] = STATE_COMPLETED
            breakfast = user_states[user_id]["breakfast"]
            lunch = user_states[user_id]["lunch"]
            dinner = user_states[user_id]["dinner"]
            reply = (f"Thanks! You had {breakfast} for breakfast, "
                     f"{lunch} for lunch, and {dinner} for dinner.")
        else:
            reply = "Thanks! Have a great day!"

        line_bot_api.reply_message(ReplyMessageRequest(
            reply_token=event.reply_token,
            messages=[TextMessage(text=reply)]
        ))

# Top page for checking if the bot is running
@app.route('/', methods=['GET'])
def toppage():
    return 'Hello world!'

# Bot startup code
if __name__ == "__main__":
    # Set `debug=True` for local testing
    app.run(host="0.0.0.0", port=8000, debug=True)

