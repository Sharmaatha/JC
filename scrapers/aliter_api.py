import requests
import json
import logging
import os
from typing import List, Dict, Any, Optional
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

#Specter API integration
"""
class SpecterAPIClient:
    '''
    Client for Specter API integration

    API Documentation: https://docs.specter.com
    Endpoint: GET /searches/companies/{searchId}/results

    '''

    def __init__(self):
        self.base_url = "https://api.specter.com"
        self.api_key = os.getenv('SPECTER_API_KEY')
        self.search_id = os.getenv('SPECTER_SEARCH_ID')

        if not self.api_key:
            logger.warning("SPECTER_API_KEY environment variable not set")
        if not self.search_id:
            logger.warning("SPECTER_SEARCH_ID environment variable not set")

        # Rate limiting - Specter recommends at least 1 second between requests
        self.min_request_interval = 1.0
        self.last_request_time = 0

    def _wait_for_rate_limit(self):
        '''Ensure minimum interval between API calls'''
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        if time_since_last < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def fetch_company_search_results(
        self,
        new_only: bool = False,
        new_growth_highlights: bool = False,
        new_funding_highlights: bool = False,
        limit: int = 50,
        page: int = 0
    ) -> List[Dict[str, Any]]:

        '''
        Fetch company search results from Specter API

        GET /searches/companies/{searchId}/results
        '''
        if not self.api_key or not self.search_id:
            logger.warning("API key or search ID not configured, falling back to mock data")
            return self._fallback_to_mock_data()

        # Build the API endpoint URL
        endpoint = f"/searches/companies/{self.search_id}/results"
        url = f"{self.base_url}{endpoint}"

        # Set up headers with API key
        headers = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json"
        }

        # Build query parameters
        params = {
            "limit": min(limit, 1000), 
            "page": max(page, 0)      
        }

        # Add optional filters
        if new_only:
            params["new"] = "true"
        if new_growth_highlights:
            params["newGrowthHighlights"] = "true"
        if new_funding_highlights:
            params["newFundingHighlights"] = "true"

        try:
            # Respect rate limiting
            self._wait_for_rate_limit()

            logger.info(f"Making Specter API request to: {endpoint}")
            logger.info(f"Parameters: limit={params.get('limit')}, page={params.get('page')}, filters={[(k,v) for k,v in params.items() if k not in ['limit', 'page']]}")

            # Make the GET request to Specter API
            response = requests.get(
                url,
                headers=headers,
                params=params,
                timeout=30  # 30 second timeout
            )

            # Check for HTTP errors
            response.raise_for_status()

            # Parse JSON response
            data = response.json()

            # Extract companies from response
            # Specter API typically returns companies in 'results' or 'data' field
            companies = data.get('results', data.get('data', data.get('companies', [])))

            if not isinstance(companies, list):
                logger.error(f"Unexpected API response format. Expected list, got {type(companies)}")
                logger.error(f"Response structure: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                return self._fallback_to_mock_data()

            # Calculate credits used 
            credits_used = len(companies)
            logger.info(f"Successfully fetched {len(companies)} companies from Specter API")
            logger.info(f"API credits consumed: {credits_used} (1 credit per company)")

            return companies

        except requests.exceptions.Timeout:
            logger.error("Specter API request timed out (30 seconds)")
            return self._fallback_to_mock_data()
        except requests.exceptions.ConnectionError:
            logger.error("Failed to connect to Specter API")
            return self._fallback_to_mock_data()
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else 'Unknown'
            logger.error(f"Specter API HTTP error {status_code}: {e}")
            if status_code == 429:
                logger.warning("Rate limit exceeded. Consider increasing min_request_interval")
            elif status_code == 401:
                logger.error("Invalid API key. Check SPECTER_API_KEY environment variable")
            elif status_code == 403:
                logger.error("Access forbidden. Check if search is shared with API")
            elif status_code == 404:
                logger.error("Search not found. Check SPECTER_SEARCH_ID environment variable")
            return self._fallback_to_mock_data()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Specter API JSON response: {e}")
            return self._fallback_to_mock_data()
        except Exception as e:
            logger.error(f"Unexpected error with Specter API: {e}")
            return self._fallback_to_mock_data()

    def _fallback_to_mock_data(self) -> List[Dict[str, Any]]:
        '''Fallback to mock data when API is unavailable'''
        logger.info("Falling back to mock data")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        filename = os.path.join(current_dir, "mock.json")

        try:
            with open(filename, 'r', encoding='utf-8') as f:
                mock_data = json.load(f)
                logger.info(f"Successfully loaded mock data from {filename}")
                return mock_data if isinstance(mock_data, list) else [mock_data]
        except FileNotFoundError:
            logger.error(f" data file not found: {filename}")
            return []
        except json.JSONDecodeError:
            logger.error(f"Failed to decode JSON from mock file: {filename}")
            return []
        except Exception as e:
            logger.error(f"Error loading mock data: {e}")
            return []

# Global client instance
_specter_client = None

def get_specter_client() -> SpecterAPIClient:
    '''Get or create Specter API client instance'''
    global _specter_client
    if _specter_client is None:
        _specter_client = SpecterAPIClient()
    return _specter_client

def fetch_company_data_from_api(company_url: str = None):
    '''
    Fetch company data from Specter API
    Falls back to mock data if API is unavailable

    '''
    # client = get_specter_client()
    # if company_url:
    #     logger.info(f"Requested data for company URL: {company_url}")
    # return client.fetch_company_search_results(limit=50)

    # For now, use mock data
    return _fallback_to_mock_data_legacy()

def fetch_new_companies_only():
    '''Fetch only companies that are newly discovered'''
    # client = get_specter_client()
    # return client.fetch_company_search_results(new_only=True, limit=50)

    return _fallback_to_mock_data_legacy()

def fetch_companies_with_growth():
    '''Fetch companies with recent growth highlights'''
    # client = get_specter_client()
    # return client.fetch_company_search_results(new_growth_highlights=True, limit=50)

    return _fallback_to_mock_data_legacy()

def fetch_companies_with_funding():
    '''Fetch companies with recent funding highlights'''
    # client = get_specter_client()
    # return client.fetch_company_search_results(new_funding_highlights=True, limit=50)

    return _fallback_to_mock_data_legacy()
"""

def fetch_company_data_from_api(company_url: str):
    """
    Takes a company URL and returns the JSON response from a local mock file.
    TODO: Production Team - Replace with Specter API integration
    """
    print(f"Fetching external data for: {company_url}")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(current_dir, "mock.json")

    try:
        with open(filename, 'r') as f:
            mock_response = json.load(f)
            logger.info(f"Successfully loaded mock data from {filename}")
            return mock_response

    except FileNotFoundError:
        logger.error(f"Error: The file '{filename}' was not found.")
        return {}
    except json.JSONDecodeError:
        logger.error(f"Error: Failed to decode JSON from '{filename}'. Check the file format.")
        return {}

def _fallback_to_mock_data_legacy():
    """Legacy fallback function for backward compatibility"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    filename = os.path.join(current_dir, "mock.json")

    try:
        with open(filename, 'r', encoding='utf-8') as f:
            mock_data = json.load(f)
            return mock_data if isinstance(mock_data, list) else [mock_data]
    except Exception as e:
        logger.error(f"Error loading mock data: {e}")
        return []