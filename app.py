import os
import sys
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from google import genai

app = Flask(__name__)

# --- 環境變數讀取 ---
LINE_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_SECRET = os.getenv('LINE_CHANNEL_SECRET')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_SECRET)
client = genai.Client(api_key=GEMINI_KEY)

# 啟動時自動列出可用模型 (輸出在 Render Logs)
print("--- [啟動診斷] 您的金鑰目前支援的模型如下 ---", flush=True)
try:
    for m in client.models.list():
        print(f"可用模型: {m.name}", flush=True)
except Exception as e:
    print(f"診斷失敗: {e}", flush=True)

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
    
    # 針對 limit: 0 的狀況，我們依序嘗試不同型號
    # 2.0 沒額度就換 1.5，1.5 沒額度就換 1.5-8b
    models_to_try = ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-flash-8b']
    final_reply = "AI 目前完全無法連線，可能是 Google 伺服器今日波動導致配額歸零。"

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name, 
                contents=user_text
            )
            final_reply = response.text
            break # 成功就跳出
        except Exception as e:
            err_msg = str(e)
            print(f"嘗試 {model_name} 失敗: {err_msg}", flush=True)
            if "429" in err_msg:
                continue # 換下一個模型再試
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
