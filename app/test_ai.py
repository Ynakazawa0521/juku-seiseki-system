import os
import google.generativeai as genai
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

try:
    # 環境変数からAPIキーを取得して設定
    api_key = os.environ.get('GEMINI_API_KEY')
    genai.configure(api_key=api_key)

    # AIモデルを準備 (モデル名を 'gemini-1.0-pro' に変更)
    model = genai.GenerativeModel('models/gemini-1.5-flash-latest')
    # AIに簡単な質問をしてみる
    print("AIに質問しています...")
    response = model.generate_content("自己紹介として、あなたは優秀な塾講師です。30字程度で自己紹介をしてください。")

    # AIからの返答を表示
    print("\nAIからの返答:")
    print(response.text)
    print("\nテスト成功！APIキーは正しく設定されています。")

except Exception as e:
    print(f"\nエラーが発生しました: {e}")
    print("APIキーが正しく設定されているか、.envファイルを確認してください。")