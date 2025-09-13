import os
from dotenv import load_dotenv

print("--- .env ファイルテストを開始します ---")

# このスクリプトが実行されているディレクトリを取得
script_dir = os.path.dirname(os.path.abspath(__file__))
print(f"スクリプトの実行場所: {script_dir}")

# .env ファイルのロードを試みる
found_dotenv = load_dotenv()

if found_dotenv:
    print("成功: .env ファイルが見つかり、ロードされました。")
else:
    print("エラー: 現在のディレクトリに .env ファイルが見つかりませんでした。")

# 次に、DATABASE_URL 変数を確認
print("\n--- 変数を確認します ---")
database_url = os.environ.get('DATABASE_URL')

if database_url:
    print("成功: DATABASE_URL 変数が見つかりました。")
    # セキュリティのため、値は表示しません
    # print(f"値: {database_url}")
else:
    print("エラー: .env ファイル内に DATABASE_URL 変数が見つかりませんでした。")
    print("スペルミス（例: 'DTAABASE_URL'）や内容の不足がないか確認してください。")

print("\n--- テスト完了 ---")