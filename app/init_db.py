import os
import psycopg2
from dotenv import load_dotenv

# .envファイルから環境変数を読み込む
load_dotenv()

# 環境変数からデータベースURLを取得する
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    raise ValueError("DATABASE_URLが見つかりません。.envファイルが正しく設定されているか確認してください。")

conn = None # 接続オブジェクトを初期化
cur = None # カーソルオブジェクトを初期化

try:
    # データベースに接続
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()

    # テーブルを削除（もし存在すれば）
    cur.execute("DROP TABLE IF EXISTS scores CASCADE;")
    cur.execute("DROP TABLE IF EXISTS students CASCADE;")
    cur.execute("DROP TABLE IF EXISTS tests CASCADE;")
    
    # 新しいテーブルを作成
    cur.execute("""
        CREATE TABLE students (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            grade TEXT NOT NULL
        );
    """) # name VARCHAR(255) NOT NULL の後ろにカンマを追加しました
    
    cur.execute("""
        CREATE TABLE tests (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL
        );
    """)
    
    cur.execute("""
        CREATE TABLE scores (
            id SERIAL PRIMARY KEY,
            student_id INTEGER REFERENCES students (id),
            test_id INTEGER REFERENCES tests (id),
            test_date DATE NOT NULL,
            score INTEGER NOT NULL
        );
    """)

    conn.commit()
    print("Database tables created successfully!")

except Exception as e:
    print(f"Error during database initialization: {e}")
    if conn:
        conn.rollback()

finally:
    if cur:
        cur.close()
    if conn:
        conn.close()