import logging, re, requests, random, os
from datetime import datetime
from io import BytesIO
from app import app
from utils.google_api import GoogleAPI
from utils.wordpress_api import WordPressAPI

LOG_PATH = "logs/runtime.log"
MAX_LOG_LINES = 500

def convert_drive_link_to_direct(link):
    m = re.search(r'/file/d/([a-zA-Z0-9_-]+)', link) or re.search(r'id=([a-zA-Z0-9_-]+)', link)
    return f'https://drive.google.com/uc?export=download&id={m.group(1)}' if m else link

def ensure_logs_dir():
    os.makedirs("logs", exist_ok=True)

def log_to_file(time, action, status, details):
    ensure_logs_dir()
    line = f"{time} | {action} | {status} | {details}\n"
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()[-MAX_LOG_LINES+1:]
    else:
        lines = []
    lines.append(line)
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        f.writelines(lines)

class ArticleProcessor:
    def __init__(self):
        ensure_logs_dir()
        self.google = GoogleAPI()
        self.wp = WordPressAPI(app.config['WP_API_URL'], app.config['WP_API_USER'], app.config['WP_API_KEY'])
        self.sheet = app.config['GOOGLE_SHEETS_ID']
        self.tab = app.config.get('GOOGLE_SHEET_NAME') or 'Sheet1'
        self.errors = False

    def run_processor(self, row_filter=None):
        try:
            meta = self.google.sheets_service.spreadsheets().get(spreadsheetId=self.sheet).execute()
        except Exception as e:
            log_to_file(datetime.now().isoformat(), "System", "Exception", f"Sheet metadata fetch failed: {str(e)}")
            return

        rows = self.google.get_sheet_data(self.sheet, f"{meta['sheets'][0]['properties']['title']}!A1:H")
        if not rows: return
        headers = rows[0]
        col_map = {k.strip(): i for i, k in enumerate(headers)}

        for i, row in enumerate(rows[1:], start=2):
            if row_filter and not (row_filter[0] <= i <= row_filter[1]): continue
            try:
                data = {h: row[j] if j < len(row) else '' for h, j in col_map.items()}
                title = next((data[k] for k in ['Title', 'כותרת מאמר', 'נושא'] if data.get(k)), None)
                if not title:
                    log_to_file(datetime.now().isoformat(), f"Row {i}", "Skipped", "Missing title")
                    continue

                doc = next((data[k] for k in ['קישור למאמר', 'Document Link'] if data.get(k)), '')
                content = ''
                try:
                    match = re.search(r'/document/d/([a-zA-Z0-9-_]+)', doc)
                    if match:
                        content = self.google.get_doc_content(match.group(1))
                    else:
                        log_to_file(datetime.now().isoformat(), f"Row {i}", "Error", "Invalid Doc URL")
                        continue
                except Exception as e:
                    log_to_file(datetime.now().isoformat(), f"Row {i}", "Error", f"Doc fetch failed: {str(e)}")
                    continue

                date_str = data.get('תאריך פרסום') or ''
                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y']:
                    try:
                        date = datetime.strptime(date_str, fmt)
                        date = date.replace(hour=random.randint(8, 17), minute=random.randint(0, 59))
                        break
                    except: date = None

                img = data.get('קישור לתמונה')
                name = data.get('שם תמונה') or 'default.jpg'
                media_id = None
                if img:
                    try:
                        r = requests.get(convert_drive_link_to_direct(img), timeout=10)
                        if r.status_code == 200:
                            media_id = self.wp.upload_media(BytesIO(r.content).read(), name, title=title)
                        else:
                            log_to_file(datetime.now().isoformat(), f"Row {i}", "Error", "Image download failed")
                    except Exception as e:
                        log_to_file(datetime.now().isoformat(), f"Row {i}", "Error", f"Image fetch error: {str(e)}")

                post = self.wp.create_post(title=title, content=content, category_id=None, featured_media_id=media_id, date=date)
                if not post:
                    log_to_file(datetime.now().isoformat(), f"Row {i}", "Error", "Post creation failed")
                    continue

                url = post.get('link')
                try:
                    if 'סטטוס' in col_map:
                        self.google.update_cell(self.sheet, self.tab, f"{chr(65+col_map['סטטוס'])}{i}", 'מוכן')
                    if 'POST URL' in col_map:
                        self.google.update_cell(self.sheet, self.tab, f"{chr(65+col_map['POST URL'])}{i}", url)
                except Exception as e:
                    log_to_file(datetime.now().isoformat(), f"Row {i}", "Error", f"Sheet update failed: {str(e)}")

                log_to_file(datetime.now().isoformat(), f"Row {i}", "Success", f"Published to {url}")

            except Exception as e:
                log_to_file(datetime.now().isoformat(), f"Row {i}", "Exception", str(e))

def run_article_processor(row_filter=None): ArticleProcessor().run_processor(row_filter)
def run_specific_rows(start, end): ArticleProcessor().run_processor((start, end))
if __name__ == "__main__": run_article_processor()
