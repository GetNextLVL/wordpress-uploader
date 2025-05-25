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
            logging.debug(f"📤 Creating post: {title} | Status: {status}")
            response = requests.post(endpoint, json=data, headers=self.headers, timeout=10)
            response.raise_for_status()
            post = response.json()
            logging.info(f"✅ Post created successfully: ID {post.get('id')} | Link: {post.get('link')}")
            return post
        except requests.exceptions.RequestException as e:
            logging.error(f"❌ Error creating WordPress post: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logging.error(f"Response content: {e.response.text}")
            return None

    def upload_media(self, image_data, filename):
        if not image_data:
            logging.error("❌ No image data provided for upload.")
            return None
        if not filename:
            logging.error("❌ No filename provided for upload.")
            return None

        endpoint = f"{self.api_url}/media"
        headers = {
            'Authorization': f'Basic {self.auth}',
            'Content-Disposition': f'attachment; filename={filename}',
            'Content-Type': 'image/jpeg'
        }

        try:
            logging.debug(f"🖼 Uploading media file: {filename}")
            response = requests.post(endpoint, data=image_data, headers=headers, timeout=10)
            response.raise_for_status()
            media = response.json()
            media_id = media.get('id')
            logging.info(f"✅ Media uploaded successfully: ID {media_id} | Link: {media.get('source_url')}")
            return media_id
        except requests.exceptions.RequestException as e:
            logging.error(f"❌ Error uploading media: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logging.error(f"Response content: {e.response.text}")
            return None
