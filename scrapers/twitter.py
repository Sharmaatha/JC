import requests
from config import RAPIDAPI_KEY, SERPER_API_KEY

class TwitterScraper:
    def __init__(self):
        self.api_key = RAPIDAPI_KEY
        self.serper_key = SERPER_API_KEY
        self.base_url = "https://twitter-api45.p.rapidapi.com"
        self.serper_url = "https://google.serper.dev/search"
        self.headers = {
            "X-RapidAPI-Key": self.api_key,
            "X-RapidAPI-Host": "twitter-api45.p.rapidapi.com"
        }
    
    def search_twitter_profile(self, company_name):
        """
        Search for Twitter/X profile by company name using Serper
        Returns the Twitter URL if found
        """
        headers = {
            'X-API-KEY': self.serper_key,
            'Content-Type': 'application/json'
        }
        
        payload = {
            "q": f"{company_name} (site:twitter.com OR site:x.com)",
            "num": 3
        }
        
        try:
            response = requests.post(self.serper_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            organic_results = data.get('organic', [])
            if not organic_results:
                print(f"No Twitter profile found for: {company_name}")
                return None
        
            for result in organic_results:
                url = result.get('link', '')
                if ('twitter.com/' in url or 'x.com/' in url) and '/status/' not in url:
                    print(f"Found Twitter profile: {url}")
                    return url
            
            print(f"No valid Twitter profile found for: {company_name}")
            return None
            
        except requests.exceptions.RequestException as e:
            print(f"Error searching Twitter: {e}")
            return None
    
    def get_profile(self, twitter_handle, rest_id=None):
        """
        Get Twitter profile data by handle
        """
        if not twitter_handle:
            return None
        
        twitter_handle = twitter_handle.lstrip('@')
        
        url = f"{self.base_url}/screenname.php"
        querystring = {"screenname": twitter_handle}
        
        if rest_id:
            querystring["rest_id"] = rest_id
        
        try:
            response = requests.get(url, headers=self.headers, params=querystring)
            response.raise_for_status()
            data = response.json()
            
            if not data or 'error' in data:
                print(f"Error fetching Twitter profile for @{twitter_handle}")
                return None
            
            profile_data = {
                'handle': twitter_handle,
                'name': data.get('name', ''),
                'bio': data.get('desc', ''),  
                'followers_count': data.get('sub_count', 0),  
                'following_count': data.get('friends', 0), 
                'tweet_count': data.get('statuses_count', 0),
                'location': data.get('location', ''),
                'website': data.get('website', ''),
                'profile_image': data.get('avatar', ''), 
                'verified': data.get('blue_verified', False),  
                'created_at': data.get('created_at', ''),
                'source': 'rapidapi_twitter'
            }
            
            print(f"Twitter data scraped for @{twitter_handle}")
            return profile_data
            
        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
            if hasattr(http_err.response, 'text'):
                print(f"Response body: {http_err.response.text}")
            return None
        except requests.exceptions.RequestException as err:
            print(f"An unexpected error occurred: {err}")
            return None
    
    def extract_handle_from_url(self, twitter_url):

        if not twitter_url:
            return None
        
        try:
            if 'twitter.com/' in twitter_url or 'x.com/' in twitter_url:
                handle = twitter_url.rstrip('/').split('/')[-1]
                handle = handle.split('?')[0]
                return handle
            return None
        except:
            return None