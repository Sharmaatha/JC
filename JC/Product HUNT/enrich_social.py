import logging
from typing import Optional, List
from datetime import datetime
from database import Database
from models.models import Product
from scrapers.ph_social import ProductHuntSocialScraper
from scrapers.linkedin import LinkedInScraper
from scrapers.twitter import TwitterScraper

logger = logging.getLogger(__name__)

def sanitize_twitter_link(url: str) -> Optional[str]:
    if not url:
        return None
    cleaned = url.split("?")[0].rstrip("/")
    cleaned = cleaned.replace("https://twitter.com", "https://x.com")
    handle = cleaned.split("/")[-1].lower()
    GENERIC = {
        "search", "home", "explore", "notifications", "messages", "i", "compose", "login", "signup"
    }
    BLACKLIST = {"producthunt", "product_hunt"}
    if handle in GENERIC or handle in BLACKLIST:
        return None
    return cleaned

def enrich_social_links(limit: Optional[int] = None, product_ids: Optional[List[int]] = None):
    ph_social = ProductHuntSocialScraper()
    linkedin_scraper = LinkedInScraper()
    twitter_scraper = TwitterScraper()

    with Database() as db:
        query = db.db.query(Product).filter(Product.status == 0)
        
        if product_ids:
            query = query.filter(Product.id.in_(product_ids))
        elif limit:
            query = query.limit(limit)

        products = query.all()

        if not products:
            print("No products pending social enrichment (status=0)")
            return

        for product in products:
            print("\n=======")
            print(f"Enriching: {product.product_name} (ID: {product.id})")

            metadata = product.product_metadata or {}
            ph_data = metadata.get("product_hunt", {})
            ph_url = ph_data.get("product_hunt_url")

            if not ph_url:
                print("No ProductHunt URL — skipping")
                product.is_social_scraped = True
                product.status = 1  
                db.db.commit()
                continue

            scrape_url = ph_url.split("?utm_")[0]
            print(f"Extracting social links from: {scrape_url}")

            try:
                socials = ph_social.extract_social_links(scrape_url)
                socials = {
                    "linkedinUrl": socials.get("linkedinUrl"),
                    "twitterUrl": socials.get("twitterUrl")
                }
                print(f"→ Extracted socials: {socials}")
            except Exception as e:
                print(f" Playwright extraction failed: {e}")
                socials = {"linkedinUrl": None, "twitterUrl": None}

            linkedin_url = socials["linkedinUrl"]
            twitter_url = sanitize_twitter_link(socials["twitterUrl"])

            if linkedin_url:
                print("→ Enriching LinkedIn...")
                try:
                    linkedin_data = linkedin_scraper.get_company_about_details(linkedin_url)
                    if linkedin_data:
                        metadata["linkedin"] = linkedin_data
                        print(" LinkedIn enrichment saved")
                    else:
                        print(" No LinkedIn data returned")
                except Exception as e:
                    print(f" LinkedIn enrichment error: {e}")
                    logger.error(e)

            if twitter_url:
                print("→ Enriching Twitter...")
                try:
                    handle = twitter_scraper.extract_handle_from_url(twitter_url)
                    twitter_data = twitter_scraper.get_profile(handle)
                    if twitter_data:
                        metadata["twitter"] = twitter_data
                        print(" Twitter enrichment saved")
                    else:
                        print(" No Twitter data returned")
                except Exception as e:
                    print(f" Twitter enrichment error: {e}")
                    logger.error(e)

            new_metadata = {**metadata}
            if twitter_url and "twitter" in metadata:
                new_metadata["twitter"] = metadata["twitter"]
            if linkedin_url and "linkedin" in metadata:
                new_metadata["linkedin"] = metadata["linkedin"]

            product.product_metadata = new_metadata
            product.linkedin_link = linkedin_url
            product.twitter_link = twitter_url
            product.is_social_media = bool(linkedin_url or twitter_url)
            product.is_social_scraped = True
            product.social_scrape_attempted_at = datetime.now() 
            product.status = 1
            
            db.db.commit()

            print(
                f" Completed {product.id} — LinkedIn={bool(linkedin_url)}, "
                f"Twitter={bool(twitter_url)}, Status=1"
            )