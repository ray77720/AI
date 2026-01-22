import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from google import genai

app = Flask(__name__)

# --- 1. 初始化 ---
line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# 核心修正：強制指定使用 v1 穩定版 API，這能解決您看到的 404 錯誤
client = genai.Client(
    api_key=os.getenv('GEMINI_API_KEY'),
    http_options={'api_version': 'v1'}
)

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
        # 直接鎖定 1.5-flash，因為它在免費版中有實質配額
        response = client.models.generate_content(
            model='gemini-1.5-flash', 
            contents=ai_question
        )
        reply_text = response.text
        
    except Exception as e:
        err_msg = str(e)
        print(f"！！！呼叫失敗: {err_msg}", flush=True)
        # 即使報錯，也回傳訊息讓您知道目前後台的具體狀況
        if "429" in err_msg:
            reply_text = "【額度提醒】Google 目前限制了免費版的使用頻率，請稍等一分鐘再試。"
        else:
            reply_text = f"連線異常，請稍後再試。"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
