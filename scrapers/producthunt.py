import requests
from typing import List, Dict, Any
import logging
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from infrastructure.config import PRODUCTHUNT_API_TOKEN, API_TIMEOUT, MAX_RETRIES

logger = logging.getLogger(__name__)


class ProductHuntScraper:
    """Fetch Product Hunt posts with the CORRECT URL (node.url)."""

    def __init__(self):
        self.api_token = PRODUCTHUNT_API_TOKEN
        self.base_url = "https://api.producthunt.com/v2/api/graphql"
        self.timeout = API_TIMEOUT
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        # ProductHunt GraphQL API complexity limits
        self.max_complexity = 500000  # Hard limit
        self.safe_complexity_limit = 450000  # Stay well under the 500k limit
        # Estimated complexity per product (conservative estimate)
        self.complexity_per_product = 4000
        # Calculate safe batch size
        self.max_batch_size = min(50, self.safe_complexity_limit // self.complexity_per_product)

        # Rate limiting
        self.min_request_interval = 1.0  # Minimum 1 second between requests
        self.last_request_time = 0

        # Complexity tracking
        self.total_complexity_used = 0
        self.request_count = 0

        # Setup retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=MAX_RETRIES,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=2,
            allowed_methods=["POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def _track_complexity_usage(self, products_count: int):
        """Track complexity usage for monitoring and optimization."""
        estimated_complexity = products_count * self.complexity_per_product
        self.total_complexity_used += estimated_complexity
        self.request_count += 1

        logger.debug(f"Request #{self.request_count}: {products_count} products, "
                    f"estimated complexity: {estimated_complexity}, "
                    f"total complexity used: {self.total_complexity_used}")

        # Warn if approaching limits
        if self.total_complexity_used > self.safe_complexity_limit * 0.9:
            logger.warning(f"Approaching complexity limit: {self.total_complexity_used}/{self.max_complexity}")

        # Optimize batch size after every few requests
        if self.request_count % 5 == 0:
            self._optimize_batch_size()

    def _optimize_batch_size(self):
        """Dynamically optimize batch size based on complexity usage patterns."""
        if self.request_count < 3:
            # Not enough data to optimize yet
            return

        avg_complexity_per_request = self.total_complexity_used / self.request_count
        current_complexity_per_product = avg_complexity_per_request / max(1, self.max_batch_size)

        # Update our complexity estimate
        self.complexity_per_product = int(current_complexity_per_product)

        # Calculate optimal batch size
        optimal_batch_size = self.safe_complexity_limit // self.complexity_per_product

        # Constrain to reasonable bounds
        optimal_batch_size = max(1, min(100, optimal_batch_size))

        if optimal_batch_size != self.max_batch_size:
            logger.info(f"Optimizing batch size from {self.max_batch_size} to {optimal_batch_size} "
                       f"(complexity per product: {self.complexity_per_product})")
            self.max_batch_size = optimal_batch_size

    def get_complexity_stats(self) -> Dict[str, Any]:
        """Get current complexity usage statistics."""
        return {
            "total_complexity_used": self.total_complexity_used,
            "max_complexity": self.max_complexity,
            "safe_limit": self.safe_complexity_limit,
            "request_count": self.request_count,
            "avg_complexity_per_request": self.total_complexity_used / max(1, self.request_count),
            "current_batch_size": self.max_batch_size,
            "estimated_complexity_per_product": self.complexity_per_product
        }

    def get_products_by_date(self, date: str, limit: int = None, after_cursor: str = None) -> Dict[str, Any]:
        """
        Fetch products for a date with pagination and complexity limits.
        If limit is None, uses calculated safe batch size.
        """

        query = """
        query($postedAfter: DateTime!, $postedBefore: DateTime!, $first: Int!, $after: String) {
          posts(
            postedAfter: $postedAfter,
            postedBefore: $postedBefore,
            first: $first,
            order: RANKING,
            after: $after
          ) {
            edges {
              cursor
              node {
                id
                name
                slug
                url             
                tagline
                description
                votesCount
                createdAt
                website
                thumbnail { url }
                topics { edges { node { name } } }
              }
            }
            pageInfo {
                endCursor
                hasNextPage
            }
          }
        }
        """

        posted_after = f"{date}T00:00:00Z"
        posted_before = f"{date}T23:59:59Z"

        # Use safe batch size if no specific limit provided
        if limit is None:
            batch_size = self.max_batch_size
        else:
            # For specific limits, allow full requested size (bypass complexity limits)
            batch_size = limit

        variables = {
            "postedAfter": posted_after,
            "postedBefore": posted_before,
            "first": batch_size
        }

        if after_cursor:
            variables["after"] = after_cursor

        try:
            # Rate limiting: ensure minimum interval between requests
            current_time = time.time()
            time_since_last_request = current_time - self.last_request_time
            if time_since_last_request < self.min_request_interval:
                sleep_time = self.min_request_interval - time_since_last_request
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
                time.sleep(sleep_time)

            logger.debug(f"Making API call with batch size: {batch_size}")
            response = self.session.post(
                self.base_url,
                headers=self.headers,
                json={"query": query, "variables": variables},
                timeout=self.timeout
            )
            self.last_request_time = time.time()
            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                errors = data["errors"]
                logger.error(f"GraphQL errors: {errors}")

                # Check for complexity limit exceeded
                for error in errors:
                    if "complexity" in error.get("message", "").lower() or "limit" in error.get("message", "").lower():
                        logger.warning(f"Complexity limit hit. Current batch size: {batch_size}. Reducing batch size.")
                        # If we hit complexity limit, reduce batch size for future calls
                        if hasattr(self, 'max_batch_size') and self.max_batch_size > 1:
                            self.max_batch_size = max(1, self.max_batch_size // 2)
                            logger.info(f"Reduced max batch size to: {self.max_batch_size}")

                return {"products": [], "endCursor": None, "hasNextPage": False}

            posts_data = data.get("data", {}).get("posts", {})
            edges = posts_data.get("edges", [])
            page_info = posts_data.get("pageInfo", {})
            
            # Safely get endCursor and hasNextPage
            end_cursor = page_info.get("endCursor")
            has_next_page = page_info.get("hasNextPage", False)

            if not edges:
                # If no edges, it means no products for this page/cursor
                return {"products": [], "endCursor": end_cursor, "hasNextPage": False}

            products = []

            for edge in edges:
                node = edge["node"]

                product_hunt_url = node.get("url")   

                topics = [
                    t["node"]["name"]
                    for t in node.get("topics", {}).get("edges", [])
                ]

                products.append({
                    "id": node.get("id"),
                    "name": node.get("name"),
                    "slug": node.get("slug"),
                    "tagline": node.get("tagline"),
                    "description": node.get("description") or "",
                    "votes_count": node.get("votesCount"),
                    "created_at": node.get("createdAt"),
                    "website": node.get("website"),
                    "product_hunt_url": product_hunt_url,   
                    "thumbnail_url": node.get("thumbnail", {}).get("url"),
                    "topics": topics
                })

            # Track complexity usage
            self._track_complexity_usage(len(products))

            return {
                "products": products,
                "endCursor": end_cursor,
                "hasNextPage": has_next_page
            }

        except Exception as exc:
            logger.error(f"ProductHunt API error: {exc}")
            return {"products": [], "endCursor": None, "hasNextPage": False}

    def scrape_all_products_for_date(self, date: str, max_products: int = None) -> List[Dict[str, Any]]:
        """
        Scrape all products for a given date with proper pagination and complexity limits.
        Returns all products found, respecting complexity limits.

        Args:
            date: Date in YYYY-MM-DD format
            max_products: Maximum number of products to fetch (None for unlimited)

        Returns:
            List of product dictionaries
        """
        all_products = []
        cursor = None
        has_next_page = True
        page_num = 1

        logger.info(f"Starting full scrape for date {date} with complexity-safe pagination")

        while has_next_page:
            logger.debug(f"Fetching page {page_num} (cursor: {cursor or 'initial'})")

            # On first request, try to get all products at once if max_products is reasonable
            if page_num == 1 and max_products and max_products <= self.max_batch_size:
                batch_limit = max_products
                logger.info(f"First request: Attempting to fetch all {max_products} products in one batch")
            else:
                batch_limit = None  # Use safe batch size

            result = self.get_products_by_date(date, limit=batch_limit, after_cursor=cursor)

            products = result.get("products", [])
            cursor = result.get("endCursor")
            has_next_page = result.get("hasNextPage", False)

            if not products:
                logger.debug("No more products found")
                break

            all_products.extend(products)
            logger.info(f"Page {page_num}: Found {len(products)} products (total: {len(all_products)})")

            # Check if we've reached the max limit
            if max_products and len(all_products) >= max_products:
                logger.info(f"Reached max products limit: {max_products}")
                all_products = all_products[:max_products]
                break

            page_num += 1

            # Safety check to prevent infinite loops
            if page_num > 1000:  # Arbitrary high limit
                logger.warning("Reached maximum page limit (1000). Stopping to prevent infinite loop.")
                break

        logger.info(f"Completed scraping {len(all_products)} products for date {date}")
        return all_products