import os
from flask import Flask, render_template, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from datetime import datetime

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev_key_change_this")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///wordpress_uploader.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["GOOGLE_SHEETS_ID"] = os.environ.get("GOOGLE_SHEETS_ID")
app.config["WP_API_URL"] = os.environ.get("WP_API_URL")
app.config["WP_API_USER"] = os.environ.get("WP_API_USER")
app.config["WP_API_KEY"] = os.environ.get("WP_API_KEY")
app.config["GOOGLE_SHEET_NAME"] = os.environ.get("GOOGLE_SHEET_NAME")
app.config["WP_SITE_URL"] = os.environ.get("WP_SITE_URL")

db.init_app(app)

@app.route('/')
def dashboard():
    return render_template('dashboard.html')

@app.route('/api/status')
def api_status():
    from models import Article, Log
    today = datetime.utcnow().date()

    pending_posts = Article.query.filter_by(status='draft').count()
    published_today = Article.query.filter(
        Article.status == 'published',
        db.func.date(Article.updated_at) == today
    ).count()
    recent_errors = Log.query.filter_by(level='ERROR').count()

    recent_activities = []
    logs = Log.query.order_by(Log.timestamp.desc()).limit(10).all()
    for log in logs:
        recent_activities.append({
            'timestamp': log.timestamp.isoformat(),
            'action': 'Article Processing',
            'status': 'error' if log.level == 'ERROR' else 'success',
            'details': log.message
        })

    return jsonify({
        'pending_posts': pending_posts,
        'published_today': published_today,
        'error_count': recent_errors,
        'recent_activity': recent_activities
    })

@app.route('/api/process/rows', methods=['POST'])
def process_rows():
    from utils.processor import run_specific_rows
    try:
        start_row = request.args.get('start', type=int)
        end_row = request.args.get('end', type=int)
        if not start_row or not end_row:
            return jsonify({'success': False, 'error': 'Missing required parameters'}), 400
        if start_row > end_row:
            return jsonify({'success': False, 'error': 'Invalid row range'}), 400
        run_specific_rows(start_row, end_row)
        return jsonify({'success': True, 'message': f'Processing rows {start_row} to {end_row}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/process/rows/<int:start_row>/<int:end_row>', methods=['POST'])
def process_specific_rows(start_row, end_row):
    from utils.processor import run_specific_rows
    try:
        run_specific_rows(start_row, end_row)
        return jsonify({'success': True, 'message': f'Processing rows {start_row} to {end_row}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template('base.html', error="Page not found"), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('base.html', error="Internal server error"), 500

with app.app_context():
    import models
    db.create_all()
