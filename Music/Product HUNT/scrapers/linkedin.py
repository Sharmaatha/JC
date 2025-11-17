import requests
from config import SERPER_API_KEY

class LinkedInScraper:
    def __init__(self):
        self.api_key = SERPER_API_KEY
        self.base_url = "https://google.serper.dev/search"
    
    def scrape_company_profile(self, linkedin_url):
        """
        Scrape LinkedIn company profile using Serper API
        """
        if not linkedin_url:
            return None
        
        headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }
        try:
            company_identifier = linkedin_url.rstrip('/').split('/')[-1]
        except:
            print(f"Invalid LinkedIn URL: {linkedin_url}")
            return None
        
        # Search for LinkedIn company page
        payload = {
            "q": f"site:linkedin.com/company/{company_identifier}",
            "num": 1
        }
        
        try:
            response = requests.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            organic_results = data.get('organic', [])
            if not organic_results:
                print(f"No results found for LinkedIn URL: {linkedin_url}")
                return None
            
            result = organic_results[0]
            
            linkedin_data = {
                'url': linkedin_url,
                'title': result.get('title', ''),
                'snippet': result.get('snippet', ''),
                'source': 'serper_search',
                'company_size': result.get('company_size', '')
            }
            
            print(f"Basic LinkedIn data scraped for: {linkedin_url}")
            return linkedin_data
            
        except requests.exceptions.RequestException as e:
            print(f"Error scraping LinkedIn: {e}")
            return None
    
    def enrich_with_company_name(self, company_name):
        """
        Search for company on LinkedIn by name and get basic info
        """
        headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }
        
        payload = {
            "q": f"{company_name} site:linkedin.com/company",
            "num": 1
        }
        
        try:
            response = requests.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            organic_results = data.get('organic', [])
            if not organic_results:
                print(f"No LinkedIn profile found for: {company_name}")
                return None
            
            result = organic_results[0]
            linkedin_url = result.get('link', '')
            
            linkedin_data = {
                'url': linkedin_url,
                'title': result.get('title', ''),
                'snippet': result.get('snippet', ''),
                'company_name': company_name,
                'company_size': result.get('company_size', ''),
                'source': 'serper_search'
            }
            
            print(f"Found LinkedIn profile: {linkedin_url}")
            return linkedin_data
            
        except requests.exceptions.RequestException as e:
            print(f"Error searching LinkedIn: {e}")
            return None