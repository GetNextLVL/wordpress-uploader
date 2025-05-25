import requests
import logging
from base64 import b64encode
from datetime import datetime

class WordPressAPI:
    def __init__(self, api_url, username, api_key):
        self.api_url = api_url.rstrip('/')
        self.auth = b64encode(f"{username}:{api_key}".encode()).decode('ascii')
        self.headers = {
            'Authorization': f'Basic {self.auth}',
            'Content-Type': 'application/json'
        }

    def create_post(self, title, content, status='draft', category_id=None, featured_media_id=None, date=None):
        endpoint = f"{self.api_url}/posts"
        data = {
            'title': title,
            'content': content,
            'status': status,
        }

        if category_id:
            data['categories'] = [category_id]
        if featured_media_id:
            data['featured_media'] = featured_media_id
        if date:
            data['date'] = date.isoformat()

        try:
            response = requests.post(endpoint, json=data, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logging.error(f"Error creating WordPress post: {str(e)}")
            return None

    def upload_media(self, image_data, filename):
        endpoint = f"{self.api_url}/media"
        headers = {
            'Authorization': f'Basic {self.auth}',
            'Content-Disposition': f'attachment; filename={filename}'
        }

        try:
            response = requests.post(endpoint, data=image_data, headers=headers)
            response.raise_for_status()
            return response.json().get('id')
        except requests.exceptions.RequestException as e:
            logging.error(f"Error uploading media: {str(e)}")
            return None
