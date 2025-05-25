from app import app
import logging
import schedule
import time
import threading
from utils.wordpress_api import WordPressAPI
from utils.scheduler import PublishScheduler
from utils.processor import run_article_processor

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)

def run_scheduler():
    """Start the scheduler for publishing posts"""
    with app.app_context():
        wordpress_api = WordPressAPI(
            app.config['WP_API_URL'],
            app.config['WP_API_USER'],
            app.config['WP_API_KEY']
        )
        scheduler = PublishScheduler(wordpress_api)
        scheduler.start()
        logging.info("WordPress publishing scheduler started")

def scheduled_article_processor():
    """Run the article processor hourly"""
    logging.info("Running scheduled article processing")
    run_article_processor()

def start_background_tasks():
    """Start all background tasks"""
    # We're no longer running an initial article processor at startup
    # since this will now be manually triggered from the UI
    # for specific rows only
    
    # Start the publishing scheduler (to publish already processed articles)
    try:
        run_scheduler()
    except Exception as e:
        logging.error(f"Error starting scheduler: {str(e)}")
    
    # We no longer schedule automatic article processing
    # as it will be manually triggered
    
    # Keep running the scheduler (just for publishing already processed articles)
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    # Start background tasks in a separate thread
    background_thread = threading.Thread(target=start_background_tasks)
    background_thread.daemon = True
    background_thread.start()
    
    # Start the Flask app
    app.run(host="0.0.0.0", port=5000, debug=True)
