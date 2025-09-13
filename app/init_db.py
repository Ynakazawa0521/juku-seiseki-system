# init_db.py

import sqlite3

conn = sqlite3.connect('database.db')
cur = conn.cursor()

# 既存のテーブルをすべて削除
cur.execute("DROP TABLE IF EXISTS students")
cur.execute("DROP TABLE IF EXISTS tests")
cur.execute("DROP TABLE IF EXISTS scores")

# 生徒マスタテーブル
cur.execute("""
CREATE TABLE students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
)
""")

# テストマスタテーブル
cur.execute("""
CREATE TABLE tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE
)
""")

# 成績テーブル (test_idとtest_dateを追加)
cur.execute("""
CREATE TABLE scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id INTEGER NOT NULL,
    test_id INTEGER NOT NULL,
    score INTEGER,
    test_date TEXT NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students (id),
    FOREIGN KEY (test_id) REFERENCES tests (id)
)
""")

# サンプルデータを挿入
sample_students = [('佐藤 陽葵',), ('鈴木 陽翔',), ('高橋 葵',)]
cur.executemany("INSERT INTO students (name) VALUES (?)", sample_students)

sample_tests = [('英単語テスト',), ('数学のテスト',), ('歴史用語テスト',)]
cur.executemany("INSERT INTO tests (name) VALUES (?)", sample_tests)

conn.commit()
conn.close()

print("データベースが再初期化され、サンプル生徒とテストが登録されました。")