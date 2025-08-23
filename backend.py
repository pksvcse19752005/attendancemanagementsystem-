from flask import Flask, request, jsonify, send_from_directory, session, render_template_string
import sqlite3
import os
import smtplib
from email.mime.text import MIMEText
import io
import csv
from itsdangerous import URLSafeTimedSerializer

app = Flask(__name__)
app.secret_key = "your_secret_key"
DB_FILE = "database.db"

SECRET_KEY = "another_random_secret_key"
serializer = URLSafeTimedSerializer(SECRET_KEY)

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT NOT NULL)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS attendance (reg TEXT, name TEXT, date TEXT, status TEXT, PRIMARY KEY(reg, date))''')
        user = conn.execute("SELECT * FROM users WHERE username='DEPTCSE'").fetchone()
        if not user:
            conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("DEPTCSE", "pksv"))
init_db()

@app.route('/')
def index():
    return send_from_directory(os.getcwd(), "attendance.html")

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    with sqlite3.connect(DB_FILE) as conn:
        user = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password)).fetchone()
    if user:
        session['username'] = username
        return jsonify({'success':True})
    else:
        return jsonify({'success':False, 'error':'Incorrect username or password.'})

@app.route('/api/forgot_password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    username = data.get('username', 'DEPTCSE')
    with sqlite3.connect(DB_FILE) as conn:
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
    if not user:
        return jsonify({'success':False, 'error':'Username not found.'})
    token = serializer.dumps(username, salt='reset-password')
    reset_url = f"http://127.0.0.1:5000/reset_password/{token}"
    sender_email = "vinaypydi85@gmail.com"
    sender_pass = "gbohosjvdquzkzlr"
    to_email = "vinaypydi85@gmail.com"
    subject = "Attendance Admin Password Reset"
    body = f"""
The user '{username}' has requested a password reset via the attendance admin panel.

Click the link below to reset the password (valid for 10 minutes):
{reset_url}

If you didn't request this, please ignore this email.

-- Attendance Management System
"""
    message = MIMEText(body)
    message['Subject'] = subject
    message['From'] = sender_email
    message['To'] = to_email
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_pass)
            server.sendmail(sender_email, to_email, message.as_string())
        return jsonify({'success':True})
    except Exception as e:
        print("EMAIL ERROR:", e)
        return jsonify({'success':False, 'error':str(e)})

reset_page_html = """
<!DOCTYPE html>
<html><body>
<h2>Reset Admin Password</h2>
<form method="post">
  <label>New Password:</label>
  <input type="password" name="newpw" required>
  <button type="submit">Change Password</button>
</form>
<div style="color:green;">{{ msg }}</div>
<div style="color:red;">{{ err }}</div>
</body></html>
"""

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    msg = ''
    err = ''
    try:
        username = serializer.loads(token, salt='reset-password', max_age=600)
    except Exception as e:
        return "Reset link expired or invalid."
    if request.method == 'POST':
        newpw = request.form.get('newpw')
        if newpw:
            with sqlite3.connect(DB_FILE) as conn:
                conn.execute("UPDATE users SET password=? WHERE username=?", (newpw, username))
                conn.commit()
            msg = "Password changed! You may now log in."
            return render_template_string(reset_page_html, msg=msg, err='')
        else:
            err = "Please enter a new password."
    return render_template_string(reset_page_html, msg=msg, err=err)

@app.route('/api/save', methods=['POST'])
def save_attendance():
    data = request.get_json()
    date = data.get('date')
    try:
        with sqlite3.connect(DB_FILE) as conn:
            for reg, record in data.get('attendance', {}).items():
                name = record['name']
                status = record['status']
                conn.execute(
                    "INSERT OR REPLACE INTO attendance (reg, name, date, status) VALUES (?, ?, ?, ?)",
                    (reg, name, date, status)
                )
            conn.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/api/export_absentees/<date>', methods=['GET'])
def export_absentees(date):
    with sqlite3.connect(DB_FILE) as conn:
        rows = conn.execute(
            "SELECT reg, name FROM attendance WHERE date=? AND status='Absent'", (date,)
        ).fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Reg. Number', 'Name', 'Status'])
    for row in rows:
        writer.writerow([row[0], row[1], "Absent"])
    output.seek(0)
    return output.getvalue(), 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': f'attachment; filename=absentees_{date}.csv'
    }

@app.route('/api/check')
def api_check():
    reg = request.args.get("regno", "").upper()
    date_ = request.args.get("date", "")
    with sqlite3.connect(DB_FILE) as conn:
        q = conn.execute("SELECT status FROM attendance WHERE reg=? AND date=?", (reg, date_)).fetchone()
    return jsonify({'regno': reg, 'date': date_, 'status': q[0] if q else "Absent"})

if __name__ == '__main__':
    app.run(debug=True)
