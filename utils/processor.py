import logging
import re
import requests
from datetime import datetime
from app import app, db
from utils.google_api import GoogleAPI
from models import Article, Log
from io import BytesIO
from utils.wordpress_api import WordPressAPI

def convert_drive_link_to_direct(link):
    file_id_match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', link)
    if not file_id_match:
        file_id_match = re.search(r'id=([a-zA-Z0-9_-]+)', link)
    if file_id_match:
        file_id = file_id_match.group(1)
        return f'https://drive.google.com/uc?export=download&id={file_id}'
    return link

class ArticleProcessor:
    def __init__(self):
        self.google_api = GoogleAPI()
        self.wp_api = WordPressAPI(
            app.config['WP_API_URL'],
            app.config['WP_API_USER'],
            app.config['WP_API_KEY']
        )
        self.spreadsheet_id = app.config['GOOGLE_SHEETS_ID']
        self.sheet_name = app.config.get('GOOGLE_SHEET_NAME') or 'Sheet1'
        self.site_url = app.config['WP_SITE_URL']

    def add_log(self, level, message):
        log = Log(level=level, message=message)
        db.session.add(log)
        db.session.commit()
        logging.log(
            logging.DEBUG if level == 'DEBUG' else
            logging.INFO if level == 'INFO' else
            logging.WARNING if level == 'WARNING' else
            logging.ERROR,
            message
        )

    def run_processor(self, row_filter=None):
        with app.app_context():
            self.add_log('INFO', '🚀 Starting article processing')

            sheet_metadata = self.google_api.sheets_service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
            sheet_names = [s['properties']['title'] for s in sheet_metadata.get('sheets', [])]
            if not sheet_names:
                self.add_log('ERROR', 'No sheets found')
                return
            sheet_name = sheet_names[0]

            if row_filter and len(row_filter) == 2:
                start_row, end_row = row_filter
                range_name = f'{sheet_name}!A1:H{end_row}'
            else:
                range_name = f'{sheet_name}!A1:H'

            rows = self.google_api.get_sheet_data(self.spreadsheet_id, range_name)
            if not rows:
                self.add_log('WARNING', 'No data found in sheet')
                return

            headers = rows[0]

            for row_idx, row in enumerate(rows[1:], start=2):
                if row_filter and (row_idx < row_filter[0] or row_idx > row_filter[1]):
                    continue

                try:
                    self.add_log('INFO', f'📥 Processing row {row_idx}')
                    row_data = {headers[i]: row[i] if i < len(row) else '' for i in range(len(headers))}

                    title = next((row_data[k] for k in ['Title', 'כותרת מאמר', 'נושא'] if k in row_data and row_data[k]), None)
                    if not title:
                        self.add_log('WARNING', f'Row {row_idx}: Missing title')
                        continue
                    self.add_log('DEBUG', f'Row {row_idx}: Title = {title}')

                    doc_link = next((row_data[k] for k in ['קישור למאמר', 'Document Link'] if k in row_data and row_data[k]), None)
                    content = ''
                    if doc_link:
                        match = re.search(r'/document/d/([a-zA-Z0-9-_]+)', doc_link)
                        if match:
                            doc_id = match.group(1)
                            content = self.google_api.get_doc_content(doc_id)
                            self.add_log('DEBUG', f'Row {row_idx}: Content loaded from doc')

                    category = row_data.get('קטגוריה') or None
                    date_str = row_data.get('תאריך פרסום') or ''
                    scheduled_date = None
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                        try:
                            scheduled_date = datetime.strptime(date_str, fmt)
                            break
                        except ValueError:
                            continue
                    self.add_log('DEBUG', f'Row {row_idx}: Scheduled date = {scheduled_date}')

                    image_link = row_data.get('קישור לתמונה')
                    image_name = row_data.get('שם תמונה') or 'default.jpg'
                    featured_media_id = None
                    if image_link:
                        direct_link = convert_drive_link_to_direct(image_link)
                        response = requests.get(direct_link, timeout=10)
                        if response.status_code == 200:
                            media_id = self.wp_api.upload_media(BytesIO(response.content).read(), image_name)
                            if media_id:
                                featured_media_id = media_id
                                self.add_log('INFO', f'🖼 Uploaded image: {image_name}')
                        else:
                            self.add_log('ERROR', f'Failed to fetch image {image_name} from {direct_link}')

                    post_data = self.wp_api.create_post(
                        title=title,
                        content=content,
                        category_id=None,
                        featured_media_id=featured_media_id,
                        date=scheduled_date,
                        status='publish' if scheduled_date else 'draft'
                    )
                    if not post_data:
                        self.add_log('ERROR', f'Failed to publish post for row {row_idx}')
                        continue

                    post_id = post_data.get('id')
                    post_url = post_data.get('link')

                    article = Article(
                        title=title,
                        category=category,
                        status='published',
                        scheduled_date=scheduled_date,
                        google_doc_link=doc_link,
                        image_link=image_link,
                        featured_media_id=featured_media_id,
                        wordpress_id=post_id,
                        content=content
                    )
                    db.session.add(article)
                    db.session.commit()

                    self.google_api.update_cell(self.spreadsheet_id, sheet_name, f'C{row_idx}', 'מוכן')
                    self.google_api.update_cell(self.spreadsheet_id, sheet_name, f'H{row_idx}', post_url)
                    self.add_log('INFO', f'✅ Row {row_idx}: Post published – {post_url}')

                except Exception as e:
                    self.add_log('ERROR', f'Row {row_idx} error: {str(e)}')

            self.add_log('INFO', '✅ Processing complete')

def run_article_processor(row_filter=None):
    ArticleProcessor().run_processor(row_filter)

def run_specific_rows(start_row, end_row):
    ArticleProcessor().run_processor((start_row, end_row))

if __name__ == "__main__":
    run_article_processor()
