import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from google import genai  # 使用 2026 新版 SDK

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
        # 注意：2026 年建議使用 gemini-2.0-flash 或最新穩定版
        response = client.models.generate_content(
            model='gemini-2.0-flash', 
            contents=user_text
        )
        reply_text = response.text
    except Exception as e:
        # 發生錯誤時直接印出，方便你在 Render 日誌查看
        print(f"！！！Gemini 報錯了: {e}")
        reply_text = f"AI 目前無法處理您的訊息。\n錯誤原因：{str(e)[:100]}"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
