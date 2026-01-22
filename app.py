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
    if not user_text.lower().startswith('g'):
        return
    
    ai_question = user_text[1:].strip()
    if not ai_question:
        return

    # 模型嘗試清單：優先用 3.0，失敗就換成免費版最穩定的 1.5
    # 注意：針對免費版，我們改用最單純的呼叫方式避開路徑錯誤
    model_list = ['gemini-3-pro-preview', 'gemini-1.5-flash']
    reply_text = ""

    for model_name in model_list:
        try:
            print(f"正在嘗試呼叫模型: {model_name}...", flush=True)
            response = client.models.generate_content(
                model=model_name, 
                contents=ai_question
            )
            if response.text:
                reply_text = response.text
                print(f"成功使用 {model_name} 回覆！", flush=True)
                break
        except Exception as e:
            err_msg = str(e)
            print(f"模型 {model_name} 失敗: {err_msg}", flush=True)
            if model_name == model_list[-1]:
                reply_text = "【系統提示】目前免費版 API 配額已達上限或路徑異常，請稍後再試。"

    try:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )
    except Exception as line_e:
        print(f"！！！LINE 回傳失敗: {line_e}", flush=True)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
