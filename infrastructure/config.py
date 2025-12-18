import os
from dotenv import load_dotenv
from typing import Dict

load_dotenv()

def get_env_variable(var_name: str, default: str = None) -> str:
    """Get environment variable with error handling"""
    value = os.getenv(var_name, default)
    if value is None:
        raise ValueError(f"Environment variable {var_name} is not set")
    return value


# Database Configuration
DB_CONFIG: Dict[str, str] = {
    'host': get_env_variable('DB_HOST', 'localhost'),
    'port': get_env_variable('DB_PORT', '5432'),
    'database': get_env_variable('DB_NAME'),
    'user': get_env_variable('DB_USER'),
    'password': get_env_variable('DB_PASSWORD')
}

# API Keys
PRODUCTHUNT_API_TOKEN: str = get_env_variable('PRODUCTHUNT_API_TOKEN')
SERPER_API_KEY: str = get_env_variable('SERPER_API_KEY')
RAPIDAPI_KEY: str = get_env_variable('RAPIDAPI_KEY')
GROQ_API_KEY: str = get_env_variable('GROQ_API_KEY')

# Specter API Configuration
SPECTER_API_KEY: str = os.getenv('SPECTER_API_KEY', '')
SPECTER_SEARCH_ID: str = os.getenv('SPECTER_SEARCH_ID', '')
SPECTER_BASE_URL: str = os.getenv('SPECTER_BASE_URL', 'https://api.specter.com')

# Script Configuration
CREATED_BY: str = get_env_variable('CREATED_BY', 'system_scraper')

# API Configuration
API_TIMEOUT: int = int(get_env_variable('API_TIMEOUT', '30'))
MAX_RETRIES: int = int(get_env_variable('MAX_RETRIES', '3'))
