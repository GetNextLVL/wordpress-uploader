import schedule
import time
import threading
import logging
from datetime import datetime
from app import db
from models import Article

class PublishScheduler:
    def __init__(self, wordpress_api):
        self.wordpress_api = wordpress_api
        self.running = False
        self.thread = None

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run)
            self.thread.daemon = True
            self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

    def _run(self):
        schedule.every(10).minutes.do(self._check_scheduled_posts)
        
        while self.running:
            schedule.run_pending()
            time.sleep(60)

    def _check_scheduled_posts(self):
        try:
            current_time = datetime.utcnow()
            scheduled_posts = Article.query.filter(
                Article.status == 'draft',
                Article.scheduled_date <= current_time
            ).all()

            for post in scheduled_posts:
                self._publish_post(post)
        except Exception as e:
            logging.error(f"Error checking scheduled posts: {str(e)}")

    def _publish_post(self, article):
        try:
            # Prepare content - use stored content or try to fetch if missing
            content = article.content
            if not content and article.google_doc_link:
                try:
                    # This is a fallback if content wasn't stored during processing
                    from utils.google_api import GoogleAPI
                    google_api = GoogleAPI()
                    
                    # Extract document ID from the URL
                    import re
                    doc_id_match = re.search(r'/document/d/([a-zA-Z0-9-_]+)', article.google_doc_link)
                    if doc_id_match:
                        doc_id = doc_id_match.group(1)
                        content = google_api.get_doc_content(doc_id)
                        
                        # Update the article with the content
                        article.content = content
                        db.session.commit()
                except Exception as e:
                    logging.error(f"Failed to get content from Google Doc: {str(e)}")
            
            # Handle featured media if available
            featured_media_id = None
            if article.featured_media_id:
                featured_media_id = article.featured_media_id
                
            # Create the post in WordPress
            result = self.wordpress_api.create_post(
                title=article.title,
                content=content,
                status='publish',
                date=article.scheduled_date,
                featured_media_id=featured_media_id,
                category_id=None  # Could map to WordPress category if needed
            )

            if result:
                article.status = 'published'
                article.wordpress_id = result.get('id')
                db.session.commit()
                logging.info(f"Successfully published article: {article.title}")
            else:
                logging.error(f"Failed to publish article: {article.title}")
        except Exception as e:
            logging.error(f"Error publishing post: {str(e)}")
