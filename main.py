from app import app
import logging

logging.basicConfig(
    level=logging.INFO,  # אפשר גם DEBUG אם אתה רוצה לראות הכל
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)

if __name__ == "__main__":
    logging.info("🚀 Starting Flask app manually (no background tasks)")
    app.run(host="0.0.0.0", port=5000, debug=True)
