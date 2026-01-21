import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from google import genai  # 2026 新版 SDK

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
    
    # 鎖定您診斷清單中確認存在的 3.0 預覽版模型
    target_model = 'gemma-3-27b-it'
    
    try:
        # 使用 2026 最新 SDK 呼叫語法
        response = client.models.generate_content(
            model=target_model, 
            contents=user_text
        )
        reply_text = response.text
        
    except Exception as e:
        err_msg = str(e)
        print(f"！！！Gemini 3.0 呼叫失敗: {err_msg}", flush=True)
        
        # 針對今日 Google 伺服器波動 (Limit: 0) 的處理
        if "429" in err_msg:
            reply_text = "【系統通知】Gemini 3.0 目前請求量極高且 Google 伺服器波動中，請一分鐘後再試。"
        else:
            reply_text = f"AI 暫時無法回應。原因：{err_msg[:50]}..."

    # 回傳給 LINE 使用者
    try:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )
    except Exception as line_e:
        print(f"！！！LINE 回傳失敗: {line_e}", flush=True)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
