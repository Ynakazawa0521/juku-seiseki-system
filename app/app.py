import sqlite3
from flask import Flask, render_template, request, redirect, url_for
from datetime import date, timedelta, datetime

app = Flask(__name__)

def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/', methods=['GET', 'POST'])
def title():
    conn = get_db_connection()
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        if form_type == 'student':
            name = request.form.get('student_name')
            if name: conn.execute('INSERT INTO students (name) VALUES (?)', (name,))
        elif form_type == 'test':
            name = request.form.get('test_name')
            if name: conn.execute('INSERT INTO tests (name) VALUES (?)', (name,))
        conn.commit()
        return redirect(url_for('title'))

    students = conn.execute('SELECT * FROM students').fetchall()
    tests = conn.execute('SELECT * FROM tests').fetchall()
    conn.close()
    return render_template('title.html', students=students, tests=tests)

# app.py の calendar 関数をこれに置き換える
# dateクラスに加えて、timedeltaとdatetimeクラスもインポートします
from datetime import date, timedelta, datetime

@app.route('/calendar')
def calendar():
    # URLから年と月を取得 (例: /calendar?year=2025&month=5)
    try:
        year = int(request.args.get('year', date.today().year))
        month = int(request.args.get('month', date.today().month))
        selected_date = date(year, month, 1)
    except ValueError:
        # 無効な年月が指定された場合は今月にフォールバック
        selected_date = date.today().replace(day=1)

    # 選択された月の初日と最終日を取得
    first_day = selected_date
    last_day = (first_day.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

    # 選択された月の水曜日だけをリストアップ
    wednesdays = []
    current_day = first_day
    while current_day <= last_day:
        if current_day.weekday() == 2: # 2は水曜日
            wednesdays.append(current_day.isoformat())
        current_day += timedelta(days=1)

    # 前月と翌月へのリンクを生成
    prev_month = (selected_date - timedelta(days=1)).replace(day=1)
    next_month = (selected_date + timedelta(days=32)).replace(day=1)

    return render_template('calendar.html', 
                           wednesdays=wednesdays,
                           current_month_str=f"{selected_date.year}年{selected_date.month}月",
                           prev_year=prev_month.year,
                           prev_month=prev_month.month,
                           next_year=next_month.year,
                           next_month=next_month.month)

@app.route('/entry/<test_date>', methods=['GET', 'POST'])
def entry(test_date):
    conn = get_db_connection()
    if request.method == 'POST':
        conn.execute('DELETE FROM scores WHERE test_date = ?', (test_date,))
        for key, value in request.form.items():
            if key.startswith('score_') and value:
                _, student_id, test_id = key.split('_')
                conn.execute('INSERT INTO scores (student_id, test_id, score, test_date) VALUES (?, ?, ?, ?)',
                             (student_id, test_id, value, test_date))
        conn.commit()
        return redirect(url_for('entry', test_date=test_date))

    students = conn.execute('SELECT * FROM students').fetchall()
    tests = conn.execute('SELECT * FROM tests').fetchall()
    score_data = conn.execute('SELECT student_id, test_id, score FROM scores WHERE test_date = ?', (test_date,)).fetchall()
    
    scores = {}
    for item in score_data:
        if item['student_id'] not in scores:
            scores[item['student_id']] = {}
        scores[item['student_id']][item['test_id']] = item['score']
    
    conn.close()
    return render_template('entry.html', test_date=test_date, students=students, tests=tests, scores=scores)

# app.py の student_detail 関数をこれに置き換える

@app.route('/student/<int:student_id>')
def student_detail(student_id):
    # URLから期間とテストフィルターの選択を取得
    period = request.args.get('period', 'all')
    test_filter_id = request.args.get('test_filter', 'all')
    
    # test_filter_idを整数に変換（'all'でない場合）
    if test_filter_id != 'all':
        test_filter_id = int(test_filter_id)

    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    
    # グラフのデータロジック
    start_date = None
    if period == '1m':
        start_date = date.today() - timedelta(weeks=4)
    elif period == '3m':
        start_date = date.today() - timedelta(days=90)
    
    tests_taken = conn.execute("SELECT DISTINCT t.id, t.name FROM tests t JOIN scores s ON t.id = s.test_id WHERE s.student_id = ? ORDER BY t.name", (student_id,)).fetchall()
    
    all_avg_scores_data = conn.execute("SELECT test_id, test_date, AVG(score) as avg_score FROM scores GROUP BY test_id, test_date").fetchall()
    averages_map = {}
    for row in all_avg_scores_data:
        if row['test_id'] not in averages_map: averages_map[row['test_id']] = {}
        averages_map[row['test_id']][row['test_date']] = round(row['avg_score'], 1)

    charts_data = []
    for test in tests_taken:
        # ▼▼▼ この一行を追加 ▼▼▼
        # もし特定のテストが選択されていて、現在のテストがそれと違う場合はスキップ
        if test_filter_id != 'all' and test['id'] != test_filter_id:
            continue

        base_query = 'SELECT score, test_date FROM scores WHERE student_id = ? AND test_id = ?'
        params = [student_id, test['id']]
        if start_date:
            base_query += ' AND test_date >= ?'
            params.append(start_date.isoformat())
        base_query += ' ORDER BY test_date'
        personal_scores_data = conn.execute(base_query, tuple(params)).fetchall()

        if personal_scores_data:
            labels = [row['test_date'] for row in personal_scores_data]
            scores = [row['score'] for row in personal_scores_data]
            average_scores = [averages_map.get(test['id'], {}).get(date) for date in labels]
            charts_data.append({"test_name": test['name'], "labels": labels, "scores": scores, "averages": average_scores})

    # 成績履歴のクエリ（ここは変更なし）
    history_query = "SELECT s.test_date, t.name as test_name, s.score FROM scores s JOIN tests t ON s.test_id = t.id WHERE s.student_id = ?"
    history_params = [student_id]
    if test_filter_id != 'all':
        history_query += " AND s.test_id = ?"
        history_params.append(test_filter_id)
    history_query += " ORDER BY s.test_date DESC"
    score_history = conn.execute(history_query, tuple(history_params)).fetchall()
    
    conn.close()
    
    return render_template('student_detail.html', 
                           student=student, 
                           charts_data=charts_data, 
                           current_period=period,
                           score_history=score_history,
                           tests_taken=tests_taken,
                           selected_test_id=test_filter_id)
@app.route('/ranking')
def ranking():
    conn = get_db_connection()

    all_dates_data = conn.execute("SELECT DISTINCT test_date FROM scores ORDER BY test_date DESC").fetchall()
    all_dates = [row['test_date'] for row in all_dates_data]
    all_tests = conn.execute("SELECT * FROM tests ORDER BY name").fetchall()

    selected_date = request.args.get('test_date')
    selected_test_id = request.args.get('test_id', 'all')

    if not selected_date and all_dates:
        today = date.today()
        selected_date = min(all_dates, key=lambda d: abs(datetime.strptime(d, '%Y-%m-%d').date() - today))

    rankings_data = []
    if selected_date:
        query = """
            SELECT t.name as test_name, st.name as student_name, s.score
            FROM scores s
            JOIN tests t ON s.test_id = t.id
            JOIN students st ON s.student_id = st.id
            WHERE s.test_date = ?
        """
        params = [selected_date]

        if selected_test_id != 'all':
            query += " AND s.test_id = ?"
            params.append(int(selected_test_id))

        query += " ORDER BY t.name, s.score DESC"

        filtered_scores = conn.execute(query, tuple(params)).fetchall()

        processed_tests = set()
        for score in filtered_scores:
            test_name = score['test_name']
            if test_name not in processed_tests:
                test_records = [r for r in filtered_scores if r['test_name'] == test_name]
                rankings_data.append({
                    "test_name": test_name,
                    "records": test_records
                })
                processed_tests.add(test_name)

    conn.close()

    return render_template('ranking.html', 
                           rankings_data=rankings_data,
                           all_dates=all_dates,
                           all_tests=all_tests,
                           selected_date=selected_date,
                           selected_test_id=int(selected_test_id) if selected_test_id != 'all' else 'all')
# テスト編集ページを表示するためのルート
@app.route('/test/edit/<int:test_id>')
def edit_test(test_id):
    conn = get_db_connection()
    test = conn.execute('SELECT * FROM tests WHERE id = ?', (test_id,)).fetchone()
    conn.close()
    return render_template('edit_test.html', test=test)

    # app.py の一番下に追加

@app.route('/ranking/average')
def average_ranking():
    conn = get_db_connection()
    avg_scores_data = conn.execute("""
        SELECT 
            t.id as test_id,
            t.name as test_name,
            st.name as student_name,
            AVG(s.score) as average_score,
            COUNT(s.score) as test_count
        FROM scores s
        JOIN tests t ON s.test_id = t.id
        JOIN students st ON s.student_id = st.id
        GROUP BY t.id, st.id
        ORDER BY t.id, average_score DESC
    """).fetchall()
    conn.close()

    rankings_by_test = []
    processed_tests = set()

    if avg_scores_data:
        for score in avg_scores_data:
            test_id = score['test_id']
            if test_id not in processed_tests:
                test_records = [r for r in avg_scores_data if r['test_id'] == test_id]
                
                rankings_by_test.append({
                    "test_id": test_id, # ▼▼▼ Add this line ▼▼▼
                    "test_name": score['test_name'],
                    "records": test_records
                })
                processed_tests.add(test_id)
    
    return render_template('average_ranking.html', rankings_by_test=rankings_by_test)

@app.route('/student/delete/<int:id>', methods=['POST'])
def delete_student(id):
    conn = get_db_connection()
    # 生徒を削除する前に、関連する成績データも削除します
    conn.execute('DELETE FROM scores WHERE student_id = ?', (id,))
    conn.execute('DELETE FROM students WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('title'))
@app.route('/ranking/print')
def print_weekly_ranking():
    # URLから日付とテストIDを取得 (例: /ranking/print?test_date=...&test_id=...)
    selected_date = request.args.get('test_date')
    selected_test_id = request.args.get('test_id', 'all')
    
    conn = get_db_connection()
    
    # 元のranking()関数とほぼ同じロジックでデータを取得
    query = """
        SELECT st.name as student_name, s.score FROM scores s
        JOIN students st ON s.student_id = st.id
        WHERE s.test_date = ?
    """
    params = [selected_date]
    if selected_test_id != 'all':
        query += " AND s.test_id = ?"
        params.append(int(selected_test_id))
    query += " ORDER BY s.score DESC"
    
    records = conn.execute(query, tuple(params)).fetchall()
    
    # どのテストのランキングか分かるようにテスト名も取得
    test_name = "総合"
    if selected_test_id != 'all':
        test = conn.execute("SELECT name FROM tests WHERE id = ?", (selected_test_id,)).fetchone()
        test_name = test['name'] if test else "総合"

    conn.close()

    return render_template('ranking_print_template.html', 
                           title="週間テストランキング",
                           subtitle=f"{selected_date} - {test_name}",
                           records=records,
                           score_column_name="点数",
                           score_key="score")

@app.route('/ranking/average/print')
def print_average_ranking():
    # Get the selected test_id from the URL (e.g., /.../print?test_id=1)
    selected_test_id = request.args.get('test_id', type=int)

    if not selected_test_id:
        return "A Test ID is required to print a ranking.", 400

    conn = get_db_connection()
    # Get all average score data
    avg_scores_data = conn.execute("""
        SELECT 
            t.id as test_id,
            t.name as test_name,
            st.name as student_name,
            AVG(s.score) as average_score
        FROM scores s
        JOIN tests t ON s.test_id = t.id
        JOIN students st ON s.student_id = st.id
        GROUP BY t.id, st.id
        ORDER BY t.id, average_score DESC
    """).fetchall()
    conn.close()

    # Filter the data for only the selected test
    records_for_selected_test = [r for r in avg_scores_data if r['test_id'] == selected_test_id]

    # Get the test name for the title
    selected_test_name = ""
    if records_for_selected_test:
        selected_test_name = records_for_selected_test[0]['test_name']
    
    return render_template('ranking_print_template.html', 
                           title="全体ランキング",
                           subtitle=selected_test_name,
                           records=records_for_selected_test,
                           score_column_name="平均点",
                           score_key="average_score")


@app.route('/test/<int:test_id>/update', methods=['POST'])
def update_test(test_id):
    new_name = request.form['new_test_name']
    conn = get_db_connection()
    conn.execute('UPDATE tests SET name = ? WHERE id = ?', (new_name, test_id))
    conn.commit()
    conn.close()
    return redirect(url_for('title'))

@app.route('/test/<int:test_id>/delete', methods=['POST'])
def delete_test(test_id):
    conn = get_db_connection()
    # 関連する成績も削除
    conn.execute('DELETE FROM scores WHERE test_id = ?', (test_id,))
    # テスト自体を削除
    conn.execute('DELETE FROM tests WHERE id = ?', (test_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('title'))