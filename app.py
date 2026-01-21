import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from google import genai
from google.genai import types  # 引入搜尋工具類型

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
    
    # 關鍵字觸發邏輯：G 開頭才回應
    if not user_text.lower().startswith('g'):
        return
    
    ai_question = user_text[1:].strip()
    if not ai_question:
        return

    try:
        # 設定搜尋工具
        google_search_tool = types.Tool(
            google_search_retrieval=types.GoogleSearchRetrieval()
        )

        # 呼叫 3.0 模型並開啟 Google 搜尋能力
        response = client.models.generate_content(
            model='gemini-3-pro-preview', 
            contents=ai_question,
            config=types.GenerateContentConfig(
                tools=[google_search_tool]  # 加入搜尋工具
            )
        )
        
        reply_text = response.text
        
    except Exception as e:
        print(f"！！！呼叫失敗: {e}", flush=True)
        reply_text = "抱歉，連線異常，請稍後再試。"

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
