import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from google import genai  # 2026 新版 SDK

app = Flask(__name__)

# 讀取環境變數
LINE_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_SECRET = os.getenv('LINE_CHANNEL_SECRET')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_SECRET)
client = genai.Client(api_key=GEMINI_KEY)

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
    
    # 策略：優先使用 1.5-flash，因為它在 2026 年配額最穩定
    # 若失敗則嘗試 2.0-flash
    models_to_try = ['gemini-1.5-flash', 'gemini-2.0-flash']
    reply_text = "AI 服務目前不穩定，請稍後再試。"

    for model_name in models_to_try:
        try:
            # 2026 最新呼叫語法，自動避開 v1beta 錯誤
            response = client.models.generate_content(
                model=model_name,
                contents=user_text
            )
            if response and response.text:
                reply_text = response.text
                break
        except Exception as e:
            print(f"DEBUG: {model_name} 失敗原因: {e}", flush=True)
            continue

    try:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )
    except Exception as e:
        print(f"DEBUG: LINE 回傳失敗: {e}", flush=True)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
