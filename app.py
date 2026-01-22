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
SYSTEM_PROMPT = os.getenv('SYSTEM_INSTRUCTION', '你是一位全能的 AI 助手。')

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

    # 設定搜尋工具
    search_tool = types.Tool(google_search_retrieval=types.GoogleSearchRetrieval())
    
    # 定義嘗試的模型順序：最高階 3.0 -> 穩定版 1.5
    models_to_try = ['gemini-3-pro-preview', 'gemini-1.5-flash']
    reply_text = ""

    for model_name in models_to_try:
        try:
            print(f"正在嘗試呼叫模型: {model_name}...", flush=True)
            response = client.models.generate_content(
                model=model_name, 
                contents=ai_question,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    tools=[search_tool],
                    temperature=0.7
                )
            )
            if response.text:
                reply_text = response.text
                print(f"成功透過 {model_name} 取得回覆！", flush=True)
                break  # 成功取得回覆，跳出循環

        except Exception as e:
            err_msg = str(e)
            print(f"！！！模型 {model_name} 呼叫失敗: {err_msg}", flush=True)
            # 如果是最後一個模型也失敗了，才回傳錯誤訊息
            if model_name == models_to_try[-1]:
                reply_text = f"AI 目前完全無法連線。錯誤詳情：{err_msg[:50]}"
            else:
                continue # 嘗試下一個更低階的模型

    # 回傳結果
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
