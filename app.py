import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import google.generativeai as genai

app = Flask(__name__)

# 讀取環境變數 (請確認 Render 的 Key 也是這三個名字)
line_access_token = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
line_secret = os.getenv('LINE_CHANNEL_SECRET')
gemini_key = os.getenv('GEMINI_API_KEY')

line_bot_api = LineBotApi(line_access_token)
handler = WebhookHandler(line_secret)

# 設定 Gemini
genai.configure(api_key=gemini_key)
model = genai.GenerativeModel('gemini-1.5-flash')

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
        # 呼叫 Gemini
        response = model.generate_content(user_text)
        reply_text = response.text
    except Exception as e:
        # 重點：直接把錯誤傳回 LINE，方便診斷
        reply_text = f"Gemini 呼叫失敗！\n錯誤原因：{str(e)}"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
