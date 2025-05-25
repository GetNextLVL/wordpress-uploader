import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import logging

# Service account scopes for read-only access
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets.readonly',
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/documents.readonly'
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
            # Use the service account file
            service_account_file = 'service_account_sheets.json'
            
            if os.path.exists(service_account_file):
                self.creds = Credentials.from_service_account_file(
                    service_account_file, scopes=SCOPES)
                logging.info("Authenticated with Google using service account")
            else:
                logging.error(f"Service account file '{service_account_file}' not found")
                return
            
            # Build service clients
            self.sheets_service = build('sheets', 'v4', credentials=self.creds)
            self.docs_service = build('docs', 'v1', credentials=self.creds)
            self.drive_service = build('drive', 'v3', credentials=self.creds)
        
        except Exception as e:
            logging.error(f"Error authenticating with Google: {str(e)}")
            raise

    def get_sheet_data(self, spreadsheet_id, range_name):
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=range_name).execute()
            return result.get('values', [])
        except Exception as e:
            logging.error(f"Error fetching sheet data: {str(e)}")
            return []

    def get_doc_content(self, doc_id):
        try:
            document = self.docs_service.documents().get(documentId=doc_id).execute()
            content = []
            for element in document.get('body').get('content'):
                if 'paragraph' in element:
                    for para_element in element['paragraph']['elements']:
                        if 'textRun' in para_element:
                            content.append(para_element['textRun']['content'])
            return '\n'.join(content)
        except Exception as e:
            logging.error(f"Error fetching doc content: {str(e)}")
            return ""
