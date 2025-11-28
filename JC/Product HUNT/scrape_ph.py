import logging
from typing import Dict, Any, List
from datetime import datetime
from database import Database
from scrapers.producthunt import ProductHuntScraper

logger = logging.getLogger(__name__)


def print_separator(char="=", length=60):
    print("\n" + char * length)


def print_section_header(title: str):
    print_separator()
    print(title)
    print_separator()


def scrape_producthunt_only(date_str: str, limit: int = 10) -> List[int]:
    print_section_header(f"STEP 1: Scraping Product Hunt for {date_str}")

    ph_scraper = ProductHuntScraper()

    with Database() as db:
        print("Fetching ProductHunt products...")
        products = ph_scraper.get_products_by_date(date_str, limit=limit)
        print(f"Found {len(products)} products\n")

        if not products:
            print("✗ No products found — exiting.")
            return []

        launch_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        product_ids = []

        for idx, p in enumerate(products, 1):
            print_section_header(f"Processing {idx}/{len(products)}: {p['name']}")

            company_name = p["name"]
            company_id = db.get_or_create_company(company_name)
            print(f"Company ID: {company_id}")
            metadata = {"product_hunt": p}

            product_id = db.insert_product(
                company_id=company_id,
                product_name=p["name"],
                metadata=metadata,
                launch_date=launch_date,  
                twitter_link=None,  
                linkedin_link=None,  
            )
            product_ids.append(product_id)
            print(f"Product ID: {product_id} stored")
            print(f"Launch date: {launch_date}")
            print(f"PH created_at: {p.get('created_at', 'N/A')}")
            print(f"Social scraping: PENDING (is_social_scraped=False)")
            print(f"LLM review: PENDING (is_reviewed=False)\n")
        print_separator()
        print(f"STEP 1 COMPLETE: {len(products)} products stored")
        print(f"Product IDs: {product_ids}")
        print("Next: Run STEP 2 to extract social links")
        print_separator()
        
        return product_ids


if __name__ == "__main__":
    import argparse
    from datetime import datetime

    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="Date in YYYY-MM-DD format")
    parser.add_argument("--limit", type=int, default=10, help="Number of products to fetch")

    args = parser.parse_args()

    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print("Invalid date — use YYYY-MM-DD")
        exit(1)

    scrape_producthunt_only(args.date, args.limit)