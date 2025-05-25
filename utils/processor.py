import logging
import re
import requests
from datetime import datetime
from app import app, db
from utils.google_api import GoogleAPI
from models import Article, Log
from io import BytesIO
from utils.wordpress_api import WordPressAPI

class ArticleProcessor:
    def __init__(self):
        self.google_api = GoogleAPI()
        self.wp_api = WordPressAPI(
            app.config['WP_API_URL'],
            app.config['WP_API_USER'],
            app.config['WP_API_KEY']
        )
        self.spreadsheet_id = app.config['GOOGLE_SHEETS_ID']
        
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

    def process_sheets(self, row_filter=None):
        try:
            try:
                self.add_log('INFO', f'Getting sheet information for spreadsheet: {self.spreadsheet_id}')
                sheet_metadata = self.google_api.sheets_service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
                sheet_names = [sheet['properties']['title'] for sheet in sheet_metadata.get('sheets', [])]
                
                if not sheet_names:
                    self.add_log('ERROR', f'No sheets found in spreadsheet: {self.spreadsheet_id}')
                    return

                self.add_log('INFO', f'Found sheets: {", ".join(sheet_names)}')
                first_sheet_name = sheet_names[0]
            except Exception as e:
                self.add_log('ERROR', f'Error getting sheet metadata: {str(e)}')
                first_sheet_name = 'Sheet1'

            if row_filter and len(row_filter) == 2:
                start_row, end_row = row_filter
                range_name = f'{first_sheet_name}!A1:G{end_row}'
                self.add_log('INFO', f'Using filtered range: {range_name}, will process rows {start_row}-{end_row}')
            else:
                range_name = f'{first_sheet_name}!A1:G'
                self.add_log('INFO', f'Using range: {range_name}')

            rows = self.google_api.get_sheet_data(self.spreadsheet_id, range_name)
            if not rows:
                self.add_log('WARNING', 'No data found in the Google Sheet')
                return

            headers = rows[0]

            for row_idx, row in enumerate(rows[1:], start=2):
                if row_filter and (row_idx < row_filter[0] or row_idx > row_filter[1]):
                    self.add_log('INFO', f'Skipping row {row_idx} (outside filter range {row_filter[0]}-{row_filter[1]})')
                    continue

                try:
                    row_data = {headers[i]: row[i] if i < len(row) else '' for i in range(len(headers))}

                    self.add_log('DEBUG', f'Headers found: {headers}')
                    self.add_log('DEBUG', f'Row data: {row_data}')

                    title = None
                    for possible_title_key in ['Title', 'title', 'כותרת', 'כותרת מאמר', 'שם המאמר', 'נושא']:
                        if possible_title_key in row_data and row_data[possible_title_key]:
                            title = row_data[possible_title_key]
                            break

                    if not title:
                        self.add_log('WARNING', f'Row {row_idx}: Missing title, skipping')
                        continue

                    existing_article = Article.query.filter_by(title=title).first()
                    if existing_article:
                        self.add_log('INFO', f'Article "{title}" already exists in database, skipping')
                        continue

                    content = ''
                    doc_link = None
                    for possible_link_key in ['Document Link', 'google_doc_link', 'קישור למאמר', 'לינק למסמך']:
                        if possible_link_key in row_data and row_data[possible_link_key]:
                            doc_link = row_data[possible_link_key]
                            break

                    if doc_link and 'docs.google.com' in doc_link:
                        doc_id_match = re.search(r'/document/d/([a-zA-Z0-9-_]+)', doc_link)
                        if doc_id_match:
                            doc_id = doc_id_match.group(1)
                            content = self.google_api.get_doc_content(doc_id)
                            self.add_log('INFO', f'Retrieved content from Google Doc: {len(content)} characters')
                        else:
                            self.add_log('WARNING', f'Row {row_idx}: Invalid Google Doc link format')

                    scheduled_date = None
                    date_str = None
                    for possible_date_key in ['Scheduled Date', 'scheduled_date', 'תאריך פרסום', 'תאריך']:
                        if possible_date_key in row_data and row_data[possible_date_key]:
                            date_str = row_data[possible_date_key]
                            break

                    if date_str:
                        try:
                            formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']
                            for fmt in formats:
                                try:
                                    scheduled_date = datetime.strptime(date_str, fmt)
                                    break
                                except ValueError:
                                    continue
                        except Exception as e:
                            self.add_log('WARNING', f'Row {row_idx}: Error parsing date: {str(e)}')

                    category = None
                    for possible_category_key in ['Category', 'category', 'קטגוריה']:
                        if possible_category_key in row_data and row_data[possible_category_key]:
                            category = row_data[possible_category_key]
                            break

                    image_link = None
                    for possible_image_key in ['Image Link', 'image_link', 'קישור לתמונה', 'תמונה']:
                        if possible_image_key in row_data and row_data[possible_image_key]:
                            image_link = row_data[possible_image_key]
                            break

                    article = Article(
                        title=title,
                        category=category,
                        status='draft',
                        scheduled_date=scheduled_date,
                        google_doc_link=doc_link,
                        image_link=image_link,
                        content=content
                    )

                    db.session.add(article)
                    db.session.commit()
                    self.add_log('INFO', f'Added new article: "{title}"')

                except Exception as row_error:
                    self.add_log('ERROR', f'Error processing row {row_idx}: {str(row_error)}')

        except Exception as e:
            self.add_log('ERROR', f'Error processing Google Sheet: {str(e)}')

    def process_images(self):
        try:
            articles = Article.query.filter_by(status='draft').all()

            for article in articles:
                if article.image_link and not article.featured_media_id:
                    try:
                        response = requests.get(article.image_link)
                        response.raise_for_status()

                        filename = article.image_link.split('/')[-1]
                        if '?' in filename:
                            filename = filename.split('?')[0]
                        if '.' not in filename:
                            filename += '.jpg'

                        media_id = self.wp_api.upload_media(
                            BytesIO(response.content).read(),
                            filename
                        )

                        if media_id:
                            article.featured_media_id = media_id
                            db.session.commit()
                            self.add_log('INFO', f'Uploaded image for article: "{article.title}"')
                        else:
                            self.add_log('ERROR', f'Failed to upload image for article: "{article.title}"')

                    except Exception as img_error:
                        self.add_log('ERROR', f'Error processing image for "{article.title}": {str(img_error)}')

        except Exception as e:
            self.add_log('ERROR', f'Error in image processing: {str(e)}')

    def run_processor(self, row_filter=None):
        self.add_log('INFO', 'Starting article processing workflow')
        if row_filter:
            self.add_log('INFO', f'Using row filter: rows {row_filter[0]}-{row_filter[1]}')
        self.process_sheets(row_filter)
        self.process_images()
        self.add_log('INFO', 'Completed article processing workflow')
def run_article_processor(row_filter=None):
    with app.app_context():
        processor = ArticleProcessor()
        processor.run_processor(row_filter)

def run_specific_rows(start_row, end_row):
    with app.app_context():
        processor = ArticleProcessor()
        processor.run_processor((start_row, end_row))

if __name__ == "__main__":
    run_article_processor()
