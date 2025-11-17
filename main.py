import argparse
from datetime import datetime
from database import Database
from scrapers.producthunt import ProductHuntScraper
from scrapers.linkedin import LinkedInScraper
from scrapers.twitter import TwitterScraper

def main(date_str):
    """
    Main scraping workflow
    """

    print(f"\n{'='*60}")
    print(f"Starting scraping process for date: {date_str}")
    print(f"{'='*60}\n")

    ph_scraper = ProductHuntScraper()
    linkedin_scraper = LinkedInScraper()
    twitter_scraper = TwitterScraper()
    db = Database()

    try:

        print(f"Fetching products from Product Hunt for {date_str}...")
        products = ph_scraper.get_products_by_date(date_str)
        print(f"Found {len(products)} products\n")

        if not products:
            print("No products found for this date.")
            return

        # Process each product
        for idx, product in enumerate(products, 1):

            print(f"\n{'='*60}")
            print(f"Processing product {idx}/{len(products)}: {product['name']}")
            print(f"{'='*60}")

            company_name = product["name"]
            company_id = db.get_or_create_company(company_name)
            print(f"Company ID: {company_id}")

            metadata = {
                "product_hunt": product
            }

            linkedin_link, twitter_link = ph_scraper.extract_social_links(product)

            # LinkedIn enrichment
            if not linkedin_link:
                print("Searching LinkedIn profile...")
                linkedin_data = linkedin_scraper.enrich_with_company_name(company_name)
                if linkedin_data:
                    linkedin_link = linkedin_data.get("url")
                    metadata["linkedin"] = linkedin_data
                    print("LinkedIn profile found")
                else:
                    print("No LinkedIn profile found")
            else:
                print("LinkedIn link found in website")
                linkedin_data = linkedin_scraper.scrape_company_profile(linkedin_link)
                if linkedin_data:
                    metadata["linkedin"] = linkedin_data
                    print("LinkedIn data scraped")
            # Twitter enrichment
            if not twitter_link:
                print("Searching Twitter profile...")
                twitter_link = twitter_scraper.search_twitter_profile(company_name)
            else:
                print("Twitter link found in website")
            
            if twitter_link:
                twitter_handle = twitter_scraper.extract_handle_from_url(twitter_link)
                if twitter_handle:
                    twitter_data = twitter_scraper.get_profile(twitter_handle)
                    if twitter_data:
                        metadata["twitter"] = twitter_data
                        print(f"Twitter data scraped for @{twitter_handle}")
                    else:
                        print("Failed to scrape Twitter data")
                else:
                    print("Could not extract Twitter handle")
            else:
                print("No Twitter profile found")

            # Insert into DB
            print("\nInserting into database...")
            product_id = db.insert_product(
                company_id=company_id,
                product_name=product["name"],
                metadata=metadata,
                twitter_link=twitter_link,
                linkedin_link=linkedin_link
            )
            print(f"Product inserted with ID: {product_id}")

            print(f"\nSummary for {product['name']}:")
            print(f"   - Company ID: {company_id}")
            print(f"   - Product ID: {product_id}")
            print(f"   - LinkedIn: {'✓' if linkedin_link else '✗'}")
            print(f"   - Twitter: {'✓' if twitter_link else '✗'}")

        print(f"\n{'='*60}")
        print("Scraping completed successfully!")
        print(f"{'='*60}\n")

    except Exception as e:
        print(f"\nError during scraping: {e}")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Product Hunt launches for a specific date")
    parser.add_argument(
        "--date",
        type=str,
        required=True,
        help="Date in YYYY-MM-DD format"
    )

    args = parser.parse_args()

    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        print("Error: Invalid date format. Use YYYY-MM-DD")
        exit(1)

    main(args.date)