import os
import sys
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from google import genai  # 2026 最新版 SDK

app = Flask(__name__)

# --- 1. 環境變數讀取 ---
# 請確保 Render 設定中的 Key 名稱與下方完全一致
LINE_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_SECRET = os.getenv('LINE_CHANNEL_SECRET')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

# 初始化 LINE API
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_SECRET)

# 初始化 Gemini 2026 客戶端
client = genai.Client(api_key=GEMINI_KEY)

# --- 2. 啟動診斷：列出可用模型 (輸出在 Render Logs) ---
print("--- [系統啟動] 正在掃描您的 API Key 可用模型 ---", flush=True)
try:
    models = client.models.list()
    print("您目前的專案支援以下模型：", flush=True)
    for m in models:
        print(f" - {m.name}", flush=True)
except Exception as e:
    print(f"無法取得模型清單，請檢查 API Key 是否正確: {e}", flush=True)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Webhook 驗證失敗，請檢查 LINE_CHANNEL_SECRET", flush=True)
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    
    # 策略：優先使用 1.5-flash，因為它的免費額度通常最寬鬆，較不容易出現 limit: 0
    # 如果您想挑戰 2.0，請將其改為 'gemini-2.0-flash'
    primary_model = 'gemini-1.5-flash'
    
    try:
        # 呼叫 Gemini
        response = client.models.generate_content(
            model=primary_model, 
            contents=user_text
        )
        reply_text = response.text
        
    except Exception as e:
        err_msg = str(e)
        print(f"！！！Gemini 呼叫失敗: {err_msg}",
