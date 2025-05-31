import logging
import re
import requests
import random
import shutil
import os
from datetime import datetime
from io import BytesIO
from app import app
from utils.google_api import GoogleAPI
from utils.wordpress_api import WordPressAPI

def convert_drive_link_to_direct(link):
    file_id_match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', link)
    if not file_id_match:
        file_id_match = re.search(r'id=([a-zA-Z0-9_-]+)', link)
    if file_id_match:
        file_id = file_id_match.group(1)
        return f'https://drive.google.com/uc?export=download&id={file_id}'
    return link

def log_to_file(time, action, status, details):
    with open("logs/runtime.log", "a", encoding="utf-8") as f:
        f.write(f"{time} | {action} | {status} | {details}\n")

class ArticleProcessor:
    def __init__(self):
        # מחיקת תיקיית logs אם קיימת ויצירתה מחדש
        if os.path.exists("logs"):
            shutil.rmtree("logs")
        os.makedirs("logs", exist_ok=True)

        self.google_api = GoogleAPI()
        self.wp_api = WordPressAPI(
            app.config['WP_API_URL'],
            app.config['WP_API_USER'],
            app.config['WP_API_KEY']
        )
        self.spreadsheet_id = app.config['GOOGLE_SHEETS_ID']
        self.sheet_name = app.config.get('GOOGLE_SHEET_NAME') or 'Sheet1'
        self.errors_found = False  # כדי לדעת אם הייתה שגיאה

    def run_processor(self, row_filter=None):
        sheet_metadata = self.google_api.sheets_service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
        sheet_name = sheet_metadata['sheets'][0]['properties']['title']
        range_name = f'{sheet_name}!A1:H'
        rows = self.google_api.get_sheet_data(self.spreadsheet_id, range_name)
        if not rows:
            return

        headers = rows[0]
        col_map = {key.strip(): idx for idx, key in enumerate(headers)}

        for row_idx, row in enumerate(rows[1:], start=2):
            if row_filter and (row_idx < row_filter[0] or row_idx > row_filter[1]):
                continue
            try:
                row_data = {headers[i]: row[i] if i < len(row) else '' for i in range(len(headers))}
                title = next((row_data[k] for k in ['Title', 'כותרת מאמר', 'נושא'] if k in row_data and row_data[k]), None)
                if not title:
                    log_to_file(datetime.now().isoformat(), f"Row {row_idx}", "Skipped", "Missing title")
                    continue

                doc_link = next((row_data[k] for k in ['קישור למאמר', 'Document Link'] if k in row_data and row_data[k]), None)
                content = ''
                if doc_link:
                    match = re.search(r'/document/d/([a-zA-Z0-9-_]+)', doc_link)
                    if match:
                        content = self.google_api.get_doc_content(match.group(1))

                category = row_data.get('קטגוריה')
                date_str = row_data.get('תאריך פרסום') or ''
                scheduled_date = None
                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                    try:
                        scheduled_date = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue
                if scheduled_date:
                    hour = random.randint(8, 17)
                    minute = random.randint(0, 59)
                    scheduled_date = scheduled_date.replace(hour=hour, minute=minute)

                image_link = row_data.get('קישור לתמונה')
                image_name = row_data.get('שם תמונה') or 'default.jpg'
                featured_media_id = None
                if image_link:
                    direct_link = convert_drive_link_to_direct(image_link)
                    response = requests.get(direct_link, timeout=10)
                    if response.status_code == 200:
                        featured_media_id = self.wp_api.upload_media(BytesIO(response.content).read(), image_name, title=title)

                post_data = self.wp_api.create_post(
                    title=title,
                    content=content,
                    category_id=None,
                    featured_media_id=featured_media_id,
                    date=scheduled_date
                )
                if not post_data:
                    self.errors_found = True
                    log_to_file(datetime.now().isoformat(), f"Row {row_idx}", "Error", "Post creation failed")
                    continue

                post_url = post_data.get('link')

                if 'סטטוס' in col_map:
                    col_letter = chr(65 + col_map['סטטוס'])
                    self.google_api.update_cell(self.spreadsheet_id, sheet_name, f'{col_letter}{row_idx}', 'מוכן')

                if 'POST URL' in col_map:
                    col_letter = chr(65 + col_map['POST URL'])
                    self.google_api.update_cell(self.spreadsheet_id, sheet_name, f'{col_letter}{row_idx}', post_url)

                log_to_file(datetime.now().isoformat(), f"Row {row_idx}", "Success", f"Published to {post_url}")

            except Exception as e:
                self.errors_found = True
                log_to_file(datetime.now().isoformat(), f"Row {row_idx}", "Exception", str(e))
        if not self.errors_found:
            try:
                shutil.rmtree("logs", ignore_errors=True)
                print("✅ logs directory deleted (no errors).")
            except Exception as e:
                print(f"⚠️ Failed to delete logs: {e}")

def run_article_processor(row_filter=None):
    ArticleProcessor().run_processor(row_filter)

def run_specific_rows(start_row, end_row):
    ArticleProcessor().run_processor((start_row, end_row))

if __name__ == "__main__":
    run_article_processor()
