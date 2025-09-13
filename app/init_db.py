import os
from dotenv import load_dotenv
import psycopg2

load_dotenv()
# Renderは環境変数としてデータベースURLを提供します。
DATABASE_URL = os.environ.get('DATABASE_URL')

conn = psycopg2.connect('postgresql://postgres:Yuki0521@localhost:5432/postgres')
cur = conn.cursor()

# SERIAL PRIMARY KEY は PostgreSQL での AUTOINCREMENT に相当します
cur.execute("""
CREATE TABLE students (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL
);
""")

cur.execute("""
CREATE TABLE tests (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL
);
""")

cur.execute("""
CREATE TABLE scores (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL,
    test_id INTEGER NOT NULL,
    score INTEGER NOT NULL,
    test_date TEXT NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students (id),
    FOREIGN KEY (test_id) REFERENCES tests (id)
);
""")

conn.commit()
cur.close()
conn.close()

print("Database initialized successfully.")