import os
import logging
from flask import Flask, render_template, jsonify, request
from datetime import datetime

app = Flask(__name__)

# Config
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_key_change_this")
app.config["GOOGLE_SHEETS_ID"] = os.environ.get("GOOGLE_SHEETS_ID")
app.config["GOOGLE_SHEET_NAME"] = os.environ.get("GOOGLE_SHEET_NAME")
app.config["WP_API_URL"] = os.environ.get("WP_API_URL")
app.config["WP_API_USER"] = os.environ.get("WP_API_USER")
app.config["WP_API_KEY"] = os.environ.get("WP_API_KEY")
app.config["WP_SITE_URL"] = os.environ.get("WP_SITE_URL")

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/status')
def api_status():
    try:
        with open("logs/runtime.log", "r", encoding="utf-8") as f:
            lines = f.readlines()[-10:]
        recent_activities = []
        for line in lines:
            parts = line.strip().split(" | ")
            if len(parts) == 4:
                recent_activities.append({
                    'timestamp': parts[0],
                    'action': parts[1],
                    'status': parts[2],
                    'details': parts[3]
                })
        return jsonify({
            'pending_posts': 0,
            'published_today': 0,
            'error_count': sum(1 for log in recent_activities if log['status'].lower() == 'error'),
            'recent_activity': recent_activities
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/logs')
def get_logs():
    try:
        with open("logs/runtime.log", "r", encoding="utf-8") as f:
            lines = f.readlines()[-50:]
        logs = []
        for line in lines:
            parts = line.strip().split(" | ")
            if len(parts) == 4:
                logs.append({
                    "time": parts[0],
                    "action": parts[1],
                    "status": parts[2],
                    "details": parts[3]
                })
        return jsonify(logs)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/process/rows', methods=['POST'])
def process_rows():
    from utils.processor import run_specific_rows
    try:
        start_row = request.args.get('start', type=int)
        end_row = request.args.get('end', type=int)
        logging.info(f"📥 /api/process/rows called with: start={start_row}, end={end_row}")

        if start_row is None or end_row is None:
            return jsonify({'success': False, 'error': 'Missing required parameters'}), 400
        if start_row > end_row:
            return jsonify({'success': False, 'error': 'Invalid row range'}), 400

        run_specific_rows(start_row, end_row)
        return jsonify({'success': True, 'message': f'Processing rows {start_row} to {end_row}'})
    except Exception as e:
        logging.error(f"❌ Error in process_rows: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/process/rows/<int:start_row>/<int:end_row>', methods=['POST'])
def process_specific_rows(start_row, end_row):
    from utils.processor import run_specific_rows
    try:
        logging.info(f"📥 /api/process/rows/{start_row}/{end_row} called")
        run_specific_rows(start_row, end_row)
        return jsonify({'success': True, 'message': f'Processing rows {start_row} to {end_row}'})
    except Exception as e:
        logging.error(f"❌ Error in process_specific_rows: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template('base.html', error="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('base.html', error="Internal server error"), 500
