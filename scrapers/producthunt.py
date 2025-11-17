import requests
from config import PRODUCTHUNT_API_TOKEN

class ProductHuntScraper:
    """
    Scraper for Product Hunt API.
    """
    
    def __init__(self):
        """Initialize Product Hunt API connection with authentication."""
        self.api_token = PRODUCTHUNT_API_TOKEN
        self.base_url = "https://api.producthunt.com/v2/api/graphql"
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }

    def get_products_by_date(self, date):
        query = """
        query($postedAfter: DateTime!, $postedBefore: DateTime!) {
          posts(
            postedAfter: $postedAfter,
            postedBefore: $postedBefore,
            first: 1,
            order: RANKING
          ) {
            edges {
              node {
                id
                name
                tagline
                votesCount
                createdAt
                website
                url
                topics {
                  edges {
                    node {
                      name
                    }
                  }
                }
              }
            }
          }
        }
        """

        posted_after = f"{date}T00:00:00Z"   
        posted_before = f"{date}T23:59:59Z"  

        variables = {
            "postedAfter": posted_after,
            "postedBefore": posted_before
        }

        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json={"query": query, "variables": variables}
            )
            response.raise_for_status()
            data = response.json()
            print("DEBUG - API Response:", data)

            if "errors" in data:
                print("GraphQL errors:", data["errors"])
                return []

            edges = data.get("data", {}).get("posts", {}).get("edges", [])
            
            if not edges:
                print(f"No products found for {date}")
                return []
          
            products = []

            for edge in edges:
                node = edge["node"]
                topics = [t['node']['name'] for t in node.get('topics', {}).get('edges', [])]

                product_data = {
                    "id": node.get("id"),
                    "name": node.get("name"),
                    "tagline": node.get("tagline"),
                    "votes_count": node.get("votesCount"),
                    "created_at": node.get("createdAt"),
                    "website": node.get("website"),
                    "product_hunt_url": node.get("url"),
                    "topics": topics
                }

                products.append(product_data)

            return products

        except Exception as e:
            print(f"Error fetching Product Hunt data: {e}")
            return []

    def extract_social_links(self, product):
        website = product.get("website", "")

        # Check if website field contains social media links
        linkedin = website if "linkedin.com" in website else None
        twitter = website if ("twitter.com" in website or "x.com" in website) else None

        return linkedin, twitter