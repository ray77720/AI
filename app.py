import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from google import genai

app = Flask(__name__)

# --- 讀取環境變數 ---
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))
# 建立客戶端
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    handler.handle(body, signature)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    if not user_text.lower().startswith('g'):
        return
    
    ai_question = user_text[1:].strip()
    
    try:
        # 直接鎖定免費版最穩定的模型
        # 此處使用最簡潔的調用方式，避開 v1beta 產生的 404 錯誤
        response = client.models.generate_content(
            model='gemini-1.5-flash', 
            contents=ai_question
        )
        reply_text = response.text
        
    except Exception as e:
        print(f"！！！模型調用失敗: {e}", flush=True)
        if "429" in str(e):
            reply_text = "【免費版配額限制】Google 目前暫時關閉了您的 API 權限，請稍後再試。"
        elif "404" in str(e):
            reply_text = "【系統錯誤】找不到模型路徑，請檢查 API 版本設定。"
        else:
            reply_text = f"連線異常，請稍後再試。({str(e)[:30]})"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
