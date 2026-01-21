import os
import sys
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from google import genai  # 使用 2026 新版 SDK

app = Flask(__name__)

# --- 環境變數讀取 ---
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
    
    # 2.0 若回報 limit: 0，則強制切換至 1.5 系列
    # 這裡使用正確的模型字串，避免之前的 404 錯誤
    models_to_try = ['gemini-1.5-flash', 'gemini-1.5-flash-8b', 'gemini-2.0-flash']
    final_reply = "AI 目前完全無法連線，可能是 Google 伺服器今日波動導致配額歸零。"

    for model_name in models_to_try:
        try:
            # 2026 新版呼叫語法
            response = client.models.generate_content(
                model=model_name, 
                contents=user_text
            )
            if response.text:
                final_reply = response.text
                break
        except Exception as e:
            err_msg = str(e)
            print(f"嘗試模型 {model_name} 失敗: {err_msg}", flush=True)
            if "429" in err_msg or "404" in err_msg:
                continue # 換下一個試試
            else:
                final_reply = f"呼叫失敗原因：{err_msg[:100]}"
                break

    try:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=final_reply)
        )
    except Exception as line_e:
        print(f"LINE 回傳錯誤: {line_e}", flush=True)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
