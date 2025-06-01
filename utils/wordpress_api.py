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

    def create_post(self, title, content, category_id=None, featured_media_id=None, date=None):
        endpoint = f"{self.api_url}/posts"
        now = datetime.now(date.tzinfo) if date else datetime.now()
        status = "future" if date and date > now else "publish"

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
            res = requests.post(endpoint, json=data, headers=self.headers, timeout=10)
            res.raise_for_status()
            post = res.json()
            post_id = post.get('id')
            link = post.get('link')

            if status == "future":
                try:
                    post_res = requests.get(f"{self.api_url}/posts/{post_id}?_embed", headers=self.headers, timeout=10)
                    post_res.raise_for_status()
                    embedded_post = post_res.json()
                    link = embedded_post.get('link', link)
                except:
                    pass

            logging.info(f"✅ Post created: ID {post_id} | Link: {link}")
            post['link'] = link
            return post
        except requests.exceptions.RequestException as e:
            logging.error(f"❌ Error creating post: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logging.error(f"Response content: {e.response.text}")
            return None

    def upload_media(self, image_data, filename, title=None):
        if not image_data or not filename:
            return None

        endpoint = f"{self.api_url}/media"
        headers = {
            'Authorization': f'Basic {self.auth}',
            'Content-Disposition': f'attachment; filename={filename}',
            'Content-Type': 'image/jpeg'
        }

        try:
            logging.debug(f"🖼 Uploading media: {filename}")
            res = requests.post(endpoint, data=image_data, headers=headers, timeout=10)
            res.raise_for_status()
            media = res.json()
            media_id = media.get('id')

            if title:
                meta = {
                    'alt_text': title,
                    'description': title,
                    'caption': "Credit Canva.com"
                }
                meta_res = requests.post(f"{self.api_url}/media/{media_id}", json=meta, headers=self.headers, timeout=10)
                meta_res.raise_for_status()

            return media_id
        except requests.exceptions.RequestException as e:
            logging.error(f"❌ Error uploading media: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logging.error(f"Response content: {e.response.text}")
            return None
