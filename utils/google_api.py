import os
import logging
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/documents.readonly',
    'https://www.googleapis.com/auth/drive.readonly'
]

class GoogleAPI:
    def __init__(self):
        self.creds = None
        self.sheets_service = None
        self.docs_service = None
        self.drive_service = None
        self._authenticate()

    def _authenticate(self):
        try:
            service_account_file = 'service_account_sheets.json'
            if os.path.exists(service_account_file):
                self.creds = Credentials.from_service_account_file(
                    service_account_file, scopes=SCOPES)
                logging.info("✅ Authenticated with Google successfully.")
            else:
                logging.error(f"❌ Service account file not found: {service_account_file}")
                return
            self.sheets_service = build('sheets', 'v4', credentials=self.creds)
            self.docs_service = build('docs', 'v1', credentials=self.creds)
            self.drive_service = build('drive', 'v3', credentials=self.creds)
        except Exception as e:
            logging.error(f"❌ Authentication failed: {str(e)}")
            raise

    def get_sheet_data(self, spreadsheet_id, range_name):
        logging.debug(f"📄 Fetching sheet data for range: {range_name}")
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            return result.get('values', [])
        except HttpError as http_err:
            logging.error(f"❌ HTTP error fetching sheet data: {http_err}")
            return []
        except Exception as e:
            logging.error(f"❌ Error fetching sheet data: {str(e)}")
            return []

    def get_doc_content(self, doc_id):
        logging.debug(f"📝 Fetching Google Doc content for doc ID: {doc_id}")
        try:
            document = self.docs_service.documents().get(documentId=doc_id).execute()
            content = []
            for element in document.get('body', {}).get('content', []):
                if 'paragraph' in element:
                    for para_element in element['paragraph'].get('elements', []):
                        if 'textRun' in para_element:
                            content.append(para_element['textRun']['content'])
            logging.debug(f"✅ Google Doc fetched: {len(content)} lines")
            return '\n'.join(content).strip()
        except HttpError as http_err:
            logging.error(f"❌ HTTP error fetching doc {doc_id}: {http_err}")
            raise
        except Exception as e:
            logging.error(f"❌ Error fetching doc content ({doc_id}): {str(e)}")
            raise

    def update_cell(self, spreadsheet_id, sheet_name, cell_ref, value):
        logging.debug(f"✏️ Updating cell {cell_ref} to: {value}")
        try:
            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!{cell_ref}",
                valueInputOption="RAW",
                body={"values": [[value]]}
            ).execute()
            logging.info(f"✅ Updated cell {cell_ref} with value: {value}")
        except Exception as e:
            logging.error(f"❌ Error updating cell {cell_ref}: {str(e)}")
