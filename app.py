import os
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
    
    # 策略：如果 2.0 報錯 limit 0，自動降級到 1.5 試試
    models_to_try = ['gemini-2.0-flash', 'gemini-1.5-flash']
    reply_text = "AI 目前暫時無法回應，請稍後再試。"

    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name, 
                contents=user_text
            )
            reply_text = response.text
            break # 成功獲取回應，跳出迴圈
        except Exception as e:
            err_msg = str(e)
            print(f"嘗試模型 {model_name} 失敗: {err_msg}", flush=True)
            # 如果是 429 且還有下一個模型，則繼續嘗試
            if "429" in err_msg and model_name != models_to_try[-1]:
                continue
            reply_text = f"AI 呼叫失敗。原因：{err_msg[:100]}"
            break

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
    )

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
