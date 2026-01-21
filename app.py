import os
import sys
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from google import genai  # 2026 年新版 SDK

app = Flask(__name__)

# --- 設定區：從 Render 環境變數讀取 ---
# 這些變數名稱必須與您在 Render 上的 Key 完全一致
LINE_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_SECRET = os.getenv('LINE_CHANNEL_SECRET')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

# 初始化 LINE API
line_bot_api = LineBotApi(LINE_ACCESS_TOKEN)
handler = WebhookHandler(LINE_SECRET)

# 初始化 2026 Gemini 客戶端
client = genai.Client(api_key=GEMINI_KEY)

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Webhook 簽章錯誤，請檢查 LINE_CHANNEL_SECRET 設定", flush=True)
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    
    # 這裡預設使用 1.5-flash，因為您的 2.0-flash 目前回報 429 額度錯誤
    # 在 2026 年，1.5-flash 的免費配額通常比 2.0 系列更穩定
    target_model = 'gemini-1.5-flash' 
    
    try:
        # 呼叫 Gemini 產生內容
        response = client.models.generate_content(
            model=target_model, 
            contents=user_text
        )
        reply_text = response.text
        
    except Exception as e:
        # 錯誤診斷邏輯
        err_msg = str(e)
        print(f"！！！Gemini 報錯了: {err_msg}", flush=True)
        
        if "429" in err_msg:
            reply_text = "【系統通知】目前連線人數過多 (429 限制)，請稍等 30 秒後再試一次，我會努力為您服務！"
        elif "401" in err_msg or "API_KEY_INVALID" in err_msg:
            reply_text = "【系統通知】API 金鑰無效，請檢查 Google AI Studio 設定。"
        else:
            reply_text = f"AI 暫時無法回應。原因：{err_msg[:50]}..."

    # 回傳訊息給使用者
    try:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )
    except Exception as e:
        print(f"！！！LINE 回傳失敗: {e}", flush=True)

if __name__ == "__main__":
    # 支援 Render 分配的連接埠
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
