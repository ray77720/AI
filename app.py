import os
import sys
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from google import genai  # 2026 新版 SDK

app = Flask(__name__)

# 讀取環境變數
line_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
line_secret = os.getenv('LINE_CHANNEL_SECRET')
gemini_key = os.getenv('GEMINI_API_KEY')

line_bot_api = LineBotApi(line_access_token)
handler = WebhookHandler(line_secret)

# 初始化 2026 新版 Gemini Client
client = genai.Client(api_key=gemini_key)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    try:
        # 使用 2026 最新模型與語法
        response = client.models.generate_content(
            model='gemini-2.0-flash', 
            contents=user_text
        )
        reply_text = response.text
    except Exception as e:
        # 加上 flush=True 確保日誌立即顯示
        print(f"！！！Gemini 報錯了: {e}", flush=True)
        reply_text = f"AI 呼叫失敗，原因：{str(e)[:50]}"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
