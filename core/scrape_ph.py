import logging
from typing import Dict, Any, List
from datetime import datetime
from infrastructure.database import Database
from scrapers.producthunt import ProductHuntScraper
from models.models import Company 
from models.models import Product


logger = logging.getLogger(__name__)


def print_separator(char="=", length=60):
    print("\n" + char * length)


def print_section_header(title: str):
    print_separator()
    print(title)
    print_separator()


def scrape_producthunt_only(date_str: str, limit: int = None) -> List[int]:
    """
    Scrape Product Hunt for a given date.
    If limit is None, scrape ALL products using pagination.
    If limit is set, stop after that many products.
    """
    print_section_header(f"STEP 1: Scraping Product Hunt for {date_str}")

    ph_scraper = ProductHuntScraper()
    launch_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    
    with Database() as db:
        scrape_progress = db.get_or_create_scrape_progress(launch_date)
        current_cursor = scrape_progress.last_cursor
        has_next_page = scrape_progress.has_next_page

        if not has_next_page:
            print(f"All products for {date_str} have already been scraped.")
            return []

        product_ids = []
        total_fetched = 0
        page_num = 1

        while True:
            print(f"\n{'='*60}")
            print(f"Fetching page {page_num} (cursor: {current_cursor or 'initial'})")
            print(f"{'='*60}")

            # Fetch next batch - use limit as batch size when limit is set
            batch_limit = limit if limit else None
            scrape_result = ph_scraper.get_products_by_date(
                date_str,
                limit=batch_limit,  # Use limit as batch size when specified
                after_cursor=current_cursor
            )
            
            products = scrape_result["products"]
            new_end_cursor = scrape_result.get("endCursor")
            new_has_next_page = scrape_result.get("hasNextPage", False)

            if not products:
                print("✗ No more products found")
                db.update_scrape_progress(launch_date, None, False)
                break

            print(f"Found {len(products)} products on this page\n")

            # Process each product
            for idx, p in enumerate(products, 1):
                print_section_header(f"Processing {total_fetched + idx}/{total_fetched + len(products)}: {p['name']}")

                # Check if product already exists
                existing_product = db.db.query(Product).filter(Product.product_name == p["name"]).first()
                if existing_product:
                    print(f"Product '{p['name']}' already exists (ID: {existing_product.id}), skipping.")
                    product_ids.append(existing_product.id)
                    continue

                company_name = p["name"]
                company_id = db.get_or_create_company(company_name)

                # Check if company is already a signal (skip processing)
                company = db.db.query(Company).filter(Company.id == company_id).first()
                if company and company.is_signal:
                    print(f"Company '{company_name}' is marked as signal, skipping product.")
                    continue

                # Insert product
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
                print(f"✓ Product ID: {product_id} stored")

            total_fetched += len(products)

            # Update progress after each page
            db.update_scrape_progress(launch_date, new_end_cursor, new_has_next_page)

            # Check if we should stop
            if limit and total_fetched >= limit:
                print(f"\n✓ Reached limit of {limit} products")
                break

            if not new_has_next_page:
                print("\n✓ No more pages available")
                db.update_scrape_progress(launch_date, None, False)
                break

            # Move to next page
            current_cursor = new_end_cursor
            page_num += 1

        # Log complexity statistics
        complexity_stats = ph_scraper.get_complexity_stats()
        print(f"Complexity Stats: {complexity_stats['total_complexity_used']}/{complexity_stats['max_complexity']} used")
        print(f"Total API requests: {complexity_stats['request_count']}")
        print(f"Average complexity per request: {complexity_stats['avg_complexity_per_request']:.0f}")

        print_separator()
        print(f"STEP 1 COMPLETE: {len(product_ids)} products processed")
        print(f"Total pages fetched: {page_num}")
        print_separator()

        return product_ids


def scrape_producthunt_date_streamlined(date_str: str, max_products: int = None) -> List[int]:
    """
    Streamlined version using the scraper's built-in pagination.
    More efficient for large-scale scraping.
    """
    print_section_header(f"STREAMLINED SCRAPING: {date_str}")

    ph_scraper = ProductHuntScraper()

    # Get all products for the date
    all_products = ph_scraper.scrape_all_products_for_date(date_str, max_products)

    if not all_products:
        print("No products found for this date.")
        return []

    print(f"Found {len(all_products)} products total")

    launch_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    product_ids = []

    with Database() as db:
        for idx, p in enumerate(all_products, 1):
            print(f"Processing {idx}/{len(all_products)}: {p['name']}")

            # Check if product already exists
            existing_product = db.db.query(Product).filter(Product.product_name == p["name"]).first()
            if existing_product:
                print(f"Product '{p['name']}' already exists (ID: {existing_product.id}), skipping.")
                product_ids.append(existing_product.id)
                continue

            company_name = p["name"]
            company_id = db.get_or_create_company(company_name)

            # Check if company is already a signal
            company = db.db.query(Company).filter(Company.id == company_id).first()
            if company and company.is_signal:
                print(f"Company '{company_name}' is marked as signal, skipping product.")
                continue

            # Insert product
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

    # Log final complexity statistics
    complexity_stats = ph_scraper.get_complexity_stats()
    print(f"\nFinal Complexity Stats:")
    print(f"  Total complexity used: {complexity_stats['total_complexity_used']}")
    print(f"  API requests made: {complexity_stats['request_count']}")
    print(f"  Final batch size: {complexity_stats['current_batch_size']}")

    print_section_header(f"STREAMLINED SCRAPING COMPLETE: {len(product_ids)} products processed")
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