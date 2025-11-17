import os
from dotenv import load_dotenv

load_dotenv()

# Database Configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD')
}


# API Keys
PRODUCTHUNT_API_TOKEN = os.getenv('PRODUCTHUNT_API_TOKEN')
SERPER_API_KEY = os.getenv('SERPER_API_KEY')
RAPIDAPI_KEY = os.getenv('RAPIDAPI_KEY')

# Script Configuration
CREATED_BY = os.getenv('CREATED_BY', 'system_scraper')