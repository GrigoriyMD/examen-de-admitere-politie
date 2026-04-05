from flask import Flask, render_template, request, session, redirect, url_for
from questions import questions
import random
import psycopg2
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = "police_exam_secret_key"

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
DATABASE_URL = os.getenv("DATABASE_URL")


def get_db_connection():
    return psycopg2.connect(DATABASE_URL)


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS exam_results (
            id SERIAL PRIMARY KEY,
            ic_name TEXT NOT NULL,
            department TEXT NOT NULL,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            percentage REAL NOT NULL,
            status TEXT NOT NULL,
            exam_date TEXT NOT NULL
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()


@app.route('/')
def home():
    return render_template('index.html')


@app.route('/exam', methods=['POST'])
def exam():
    ic_name = request.form.get('ic_name')
    department = request.form.get('department')

    law_questions = [q for q in questions if q["type"] == "law"]
    logic_questions = [q for q in questions if q["type"] == "logic"]
    psych_questions = [q for q in questions if q["type"] == "psych"]

    selected_questions = (
        random.sample(law_questions, 14) +
        random.sample(logic_questions, 3) +
        random.sample(psych_questions, 3)
    )

    random.shuffle(selected_questions)

    session['selected_questions'] = selected_questions
    session['ic_name'] = ic_name
    session['department'] = department
    session['start_time'] = datetime.now().timestamp()

    return render_template(
        'exam.html',
        ic_name=ic_name,
        department=department,
        questions=selected_questions
    )


@app.route('/result', methods=['POST'])
def result():
    ic_name = session.get('ic_name')
    department = session.get('department')
    selected_questions = session.get('selected_questions', [])

    score = 0
    total = len(selected_questions)

    for i, q in enumerate(selected_questions):
        user_answer = request.form.get(f'q{i}')
        if user_answer == q["correct"]:
            score += 1

    percentage = (score / total) * 100 if total > 0 else 0
    status = "PASSED" if percentage >= 90 else "FAILED"
    exam_date = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    start_time = session.get('start_time')
    end_time = datetime.now().timestamp()

    time_spent = int(end_time - start_time) if start_time else 0
    minutes = time_spent // 60
    seconds = time_spent % 60
    time_display = f"{minutes} min {seconds} sec"

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO exam_results (ic_name, department, score, total, percentage, status, exam_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (ic_name, department, score, total, round(percentage, 2), status, exam_date))

    conn.commit()
    cursor.close()
    conn.close()

    return render_template(
        'result.html',
        ic_name=ic_name,
        department=department,
        score=score,
        total=total,
        percentage=round(percentage, 2),
        status=status,
        time_spent=time_display
    )


@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    error = None

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('results'))
        else:
            error = "Username sau parola incorectă."

    return render_template('admin_login.html', error=error)


@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('home'))


@app.route('/results')
def results():
    if not session.get('admin_logged_in'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT ic_name, department, score, total, percentage, status, exam_date
        FROM exam_results
        ORDER BY id DESC
    """)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('results.html', results=rows)


if __name__ == '__main__':
    init_db()
    app.run(debug=True)