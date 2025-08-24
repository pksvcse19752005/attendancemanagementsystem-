from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sqlite3
import os

app = Flask(__name__)
CORS(app)  # Allow CORS for frontend locally or different origin

# Hardcoded credentials (should be in config or env in production)
VALID_USERNAME = "DEPTCSE"
VALID_PASSWORD = "pksv"

# Gmail credentials with updated app password (16-digit)
sender_email = "vinaypydi85@gmail.com"
sender_pass = "pxbntsohbnbojhtw"  # New app password without spaces

DATABASE = 'database.db'

# Initialize the SQLite database and create tables if not exists
def init_db():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            section TEXT,
            date TEXT,
            regd TEXT,
            status TEXT,
            PRIMARY KEY (section, date, regd)
        )
    ''')
    conn.commit()
    conn.close()

# Helper to get DB connection
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def home():
    return render_template('attendance.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    if username != VALID_USERNAME or password != VALID_PASSWORD:
        return jsonify({"success": False, "message": "Password is incorrect"}), 401
    return jsonify({"success": True, "message": "Login successful"}), 200

@app.route('/api/save_attendance', methods=['POST'])
def save_attendance():
    data = request.json
    section = data.get('section')
    date = data.get('date')
    records = data.get('records')  # dict of regd: status
    if not section or not date or not isinstance(records, dict):
        return jsonify({"success": False, "message": "Invalid data"}), 400
    conn = get_db_connection()
    cur = conn.cursor()
    for regd, status in records.items():
        cur.execute('''
            INSERT OR REPLACE INTO attendance (section, date, regd, status)
            VALUES (?, ?, ?, ?)
        ''', (section, date, regd, status))
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Attendance saved."}), 200

@app.route('/api/load_attendance', methods=['GET'])
def load_attendance():
    section = request.args.get('section')
    date = request.args.get('date')
    if not section or not date:
        return jsonify({"success": False, "message": "Missing parameters"}), 400
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT regd, status FROM attendance WHERE section = ? AND date = ?
    ''', (section, date))
    rows = cur.fetchall()
    conn.close()
    records = {row['regd']: row['status'] for row in rows}
    return jsonify({"success": True, "records": records}), 200

@app.route('/api/reset_password', methods=['POST'])
def reset_password():
    data = request.json
    user_email = data.get('email')
    if not user_email:
        return jsonify({"success": False, "message": "Email required"}), 400
    try:
        send_reset_email(user_email)
        return jsonify({"success": True, "message": "Password reset email sent."}), 200
    except Exception as e:
        return jsonify({"success": False, "message": f"Failed to send email: {str(e)}"}), 500

def send_reset_email(to_email):
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = to_email
    msg['Subject'] = "Password Reset for Attendance System"

    body = (
        "Dear User,\n\n"
        "You requested a password reset for the Attendance Management System.\n"
        "Your username remains: DEPTCSE\n"
        "Your password is: pksv\n\n"
        "If you did not request this, please contact admin immediately.\n\n"
        "Best Regards,\nAttendance System Team"
    )

    msg.attach(MIMEText(body, 'plain'))

    # Using SMTP_SSL for secure connection on port 465
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(sender_email, sender_pass)
        server.send_message(msg)

if __name__ == "__main__":
    if not os.path.exists(DATABASE):
        init_db()
    app.run(host='0.0.0.0', port=5000, debug=False)
      
