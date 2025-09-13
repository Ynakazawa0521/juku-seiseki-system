import os
import psycopg2
import psycopg2.extras
from flask import Flask, render_template, request, redirect, url_for
from datetime import date, timedelta, datetime

# --- Flaskアプリケーションの初期化 ---
app = Flask(__name__)

# --- データベース接続関数 ---
def get_db_connection():
    database_url = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(database_url)
    return conn

# --- メインページ ---
@app.route('/', methods=['GET', 'POST'])
def title():
    conn = get_db_connection()
    if request.method == 'POST':
        form_type = request.form.get('form_type')
        if form_type == 'student':
            name = request.form.get('student_name')
            if name: conn.execute('INSERT INTO students (name) VALUES (%s)', (name,))
        elif form_type == 'test':
            name = request.form.get('test_name')
            if name: conn.execute('INSERT INTO tests (name) VALUES (%s)', (name,))
        conn.commit()
        return redirect(url_for('title'))

    students = conn.execute('SELECT * FROM students ORDER BY id').fetchall()
    tests = conn.execute('SELECT * FROM tests ORDER BY id').fetchall()
    conn.close()
    return render_template('title.html', students=students, tests=tests)

@app.route('/calendar')
def calendar():
    try:
        year = int(request.args.get('year', date.today().year))
        month = int(request.args.get('month', date.today().month))
        selected_date = date(year, month, 1)
    except ValueError:
        selected_date = date.today().replace(day=1)

    first_day = selected_date
    last_day = (first_day.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)

    wednesdays = []
    current_day = first_day
    while current_day <= last_day:
        if current_day.weekday() == 2: # 2 is Wednesday
            wednesdays.append(current_day.isoformat())
        current_day += timedelta(days=1)

    prev_month_date = (selected_date - timedelta(days=1)).replace(day=1)
    next_month_date = (selected_date + timedelta(days=32)).replace(day=1)

    return render_template('calendar.html', 
                           wednesdays=wednesdays,
                           current_month_str=f"{selected_date.year}年{selected_date.month}月",
                           prev_year=prev_month_date.year,
                           prev_month=prev_month_date.month,
                           next_year=next_month_date.year,
                           next_month=next_month_date.month)

@app.route('/entry/<test_date>', methods=['GET', 'POST'])
def entry(test_date):
    conn = get_db_connection()
    if request.method == 'POST':
        conn.execute('DELETE FROM scores WHERE test_date = %s', (test_date,))
        for key, value in request.form.items():
            if key.startswith('score_') and value:
                _, student_id, test_id = key.split('_')
                conn.execute('INSERT INTO scores (student_id, test_id, score, test_date) VALUES (%s, %s, %s, %s)',
                             (student_id, test_id, int(value), test_date))
        conn.commit()
        return redirect(url_for('entry', test_date=test_date))

    students = conn.execute('SELECT * FROM students ORDER BY id').fetchall()
    tests = conn.execute('SELECT * FROM tests ORDER BY id').fetchall()
    score_data = conn.execute('SELECT student_id, test_id, score FROM scores WHERE test_date = %s', (test_date,)).fetchall()
    
    scores = {}
    for item in score_data:
        if item['student_id'] not in scores:
            scores[item['student_id']] = {}
        scores[item['student_id']][item['test_id']] = item['score']
    
    conn.close()
    return render_template('entry.html', test_date=test_date, students=students, tests=tests, scores=scores)

@app.route('/student/<int:student_id>')
def student_detail(student_id):
    period = request.args.get('period', 'all')
    test_filter_id = request.args.get('test_filter', 'all')
    
    if test_filter_id != 'all':
        test_filter_id = int(test_filter_id)

    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE id = %s', (student_id,)).fetchone()
    
    start_date = None
    if period == '1m':
        start_date = date.today() - timedelta(weeks=4)
    elif period == '3m':
        start_date = date.today() - timedelta(days=90)
    
    tests_taken = conn.execute("SELECT DISTINCT t.id, t.name FROM tests t JOIN scores s ON t.id = s.test_id WHERE s.student_id = %s ORDER BY t.name", (student_id,)).fetchall()
    
    all_avg_scores_data = conn.execute("SELECT test_id, test_date, AVG(score) as avg_score FROM scores GROUP BY test_id, test_date").fetchall()
    averages_map = {}
    for row in all_avg_scores_data:
        if row['test_id'] not in averages_map: averages_map[row['test_id']] = {}
        averages_map[row['test_id']][row['test_date']] = round(row['avg_score'], 1)

    charts_data = []
    for test in tests_taken:
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

# --- ランキングページ ---
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
        date_objects = [datetime.strptime(d, '%Y-%m-%d').date() for d in all_dates]
        closest_date = min(date_objects, key=lambda d: abs(d - today))
        selected_date = closest_date.isoformat()

    rankings_data = []
    if selected_date:
        query = "SELECT t.name as test_name, st.name as student_name, s.score FROM scores s JOIN tests t ON s.test_id = t.id JOIN students st ON s.student_id = st.id WHERE s.test_date = ?"
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
                rankings_data.append({"test_name": test_name, "records": test_records})
                processed_tests.add(test_name)
    conn.close()

    return render_template('ranking.html', 
                           rankings_data=rankings_data,
                           all_dates=all_dates,
                           all_tests=all_tests,
                           selected_date=selected_date,
                           selected_test_id=int(selected_test_id) if selected_test_id != 'all' else 'all')

@app.route('/ranking/average')
def average_ranking():
    conn = get_db_connection()
    avg_scores_data = conn.execute("""
        SELECT 
            t.id as test_id, t.name as test_name, st.name as student_name,
            AVG(s.score) as average_score, COUNT(s.score) as test_count
        FROM scores s
        JOIN tests t ON s.test_id = t.id
        JOIN students st ON s.student_id = st.id
        GROUP BY t.id, st.id
        ORDER BY t.id, average_score DESC
    """).fetchall()
    conn.close()

    rankings_by_test = []
    if avg_scores_data:
        processed_tests = set()
        for score in avg_scores_data:
            test_id = score['test_id']
            if test_id not in processed_tests:
                test_records = [r for r in avg_scores_data if r['test_id'] == test_id]
                rankings_by_test.append({
                    "test_id": test_id,
                    "test_name": score['test_name'],
                    "records": test_records
                })
                processed_tests.add(test_id)
    
    return render_template('average_ranking.html', rankings_by_test=rankings_by_test)

# --- 印刷用ページ ---
@app.route('/ranking/print')
def print_weekly_ranking():
    selected_date = request.args.get('test_date')
    selected_test_id = request.args.get('test_id', 'all')
    
    conn = get_db_connection()
    query = "SELECT st.name as student_name, s.score FROM scores s JOIN students st ON s.student_id = st.id WHERE s.test_date = ?"
    params = [selected_date]
    if selected_test_id != 'all':
        query += " AND s.test_id = ?"
        params.append(int(selected_test_id))
    query += " ORDER BY s.score DESC"
    records = conn.execute(query, tuple(params)).fetchall()
    
    test_name = "総合"
    if selected_test_id != 'all':
        test = conn.execute("SELECT name FROM tests WHERE id = %s", (selected_test_id,)).fetchone()
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
    selected_test_id = request.args.get('test_id', type=int)
    if not selected_test_id:
        return "A Test ID is required to print a ranking.", 400

    conn = get_db_connection()
    avg_scores_data = conn.execute("""
        SELECT t.id as test_id, t.name as test_name, st.name as student_name, AVG(s.score) as average_score
        FROM scores s JOIN tests t ON s.test_id = t.id JOIN students st ON s.student_id = st.id
        GROUP BY t.id, st.id ORDER BY t.id, average_score DESC
    """).fetchall()
    conn.close()

    records_for_selected_test = [r for r in avg_scores_data if r['test_id'] == selected_test_id]
    selected_test_name = ""
    if records_for_selected_test:
        selected_test_name = records_for_selected_test[0]['test_name']
    
    return render_template('ranking_print_template.html', 
                           title="平均点ランキング",
                           subtitle=selected_test_name,
                           records=records_for_selected_test,
                           score_column_name="平均点",
                           score_key="average_score")

# --- データ処理（更新・削除） ---
@app.route('/test/<int:test_id>/update', methods=['POST'])
def update_test(test_id):
    new_name = request.form['new_test_name']
    conn = get_db_connection()
    conn.execute('UPDATE tests SET name = %s WHERE id = %s', (new_name, test_id))
    conn.commit()
    conn.close()
    return redirect(url_for('title'))

@app.route('/test/<int:test_id>/delete', methods=['POST'])
def delete_test(test_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM scores WHERE test_id = %s', (test_id,))
    conn.execute('DELETE FROM tests WHERE id = %s', (test_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('title'))

@app.route('/student/delete/<int:id>', methods=['POST'])
def delete_student(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM scores WHERE student_id = %s', (id,))
    conn.execute('DELETE FROM students WHERE id = %s', (id,))
    conn.commit()
    conn.close()
    return redirect(url_for('title'))

# --- アプリケーションの実行 ---
if __name__ == "__main__":
    app.run(debug=True)