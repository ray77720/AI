import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from google import genai

app = Flask(__name__)

# --- 讀取環境變數 ---
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
    except Exception as e:
        print(f"Webhook 錯誤: {e}", flush=True)
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    if not user_text.lower().startswith('g'):
        return
    
    ai_question = user_text[1:].strip()
    if not ai_question:
        return

    try:
        # 直接使用免費版最穩定的模型名，不帶額外工具以避開 v1beta 報錯
        response = client.models.generate_content(
            model='gemini-1.5-flash', 
            contents=ai_question
        )
        reply_text = response.text
        
    except Exception as e:
        err_msg = str(e)
        print(f"！！！模型呼叫失敗: {err_msg}", flush=True)
        # 針對 429 進行友善回覆
        if "429" in err_msg:
            reply_text = "【系統通知】Google 目前暫時關閉了免費 API 配額，請稍後再試。"
        else:
            reply_text = f"抱歉，連線異常，請稍後再試。"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
