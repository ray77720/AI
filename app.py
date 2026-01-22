import os
import sys
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from google import genai
from google.genai import types

app = Flask(__name__)

# --- 環境變數設定 ---
LINE_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_SECRET = os.getenv('LINE_CHANNEL_SECRET')
GEMINI_KEY = os.getenv('GEMINI_API_KEY')

# 初始化 LINE 與 Gemini 客戶端
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
        print("Webhook 簽章驗證失敗，請檢查 LINE_SECRET", flush=True)
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    
    # 關鍵字過濾：G 開頭才觸發 AI (支援大小寫)
    if not user_text.lower().startswith('g'):
        return
    
    ai_question = user_text[1:].strip()
    if not ai_question:
        return

    try:
        # 設定 Google 搜尋工具 (Grounding)
        # 這會讓 AI 具備即時檢索 2026 年最新動態的能力
        search_tool = types.Tool(
            google_search_retrieval=types.GoogleSearchRetrieval()
        )

        # 呼叫最高階 Gemini 3.0 Pro 模型
        # 付費版具備極高的 RPM，不再需要考慮 429 降級問題
        response = client.models.generate_content(
            model='gemini-3-pro-preview', 
            contents=ai_question,
            config=types.GenerateContentConfig(
                tools=[search_tool],
                temperature=0.7, # 提升回覆的靈活性與專業感
                max_output_tokens=2048 # 允許更詳盡的長篇回答
            )
        )
        
        reply_text = response.text
        
    except Exception as e:
        err_msg = str(e)
        print(f"！！！最高階模型呼叫失敗: {err_msg}", flush=True)
        # 針對付費帳號提供更精確的錯誤診斷
        if "401" in err_msg:
            reply_text = "【系統通知】API 金鑰驗證失敗，請檢查付費版金鑰設定。"
        else:
            reply_text = f"AI 暫時無法處理您的請求。錯誤詳情：{err_msg[:50]}"

    # 將 AI 回覆傳送至 LINE
    try:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_text)
        )
    except Exception as line_e:
        print(f"！！！LINE 訊息回傳失敗: {line_e}", flush=True)

if __name__ == "__main__":
    # 支援 Render 分配的連接埠 (預設 10000 或 5000)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
