import logging
from typing import Optional, List
from datetime import datetime, timedelta
from infrastructure.database import Database
from models.models import Product
from llm.signal_detector import SignalDetector
from models.models import Company
from infrastructure.email_service import EmailService

logger = logging.getLogger(__name__)

def print_separator(char="=", length=60):
    print("\n" + char * length)

def print_section_header(title: str):
    print_separator()
    print(title)
    print_separator()

def analyze_signals(limit: Optional[int] = None, product_ids: Optional[List[int]] = None, is_automatic: bool = False, scrape_date: Optional[str] = None):
    from datetime import datetime
    print_section_header("STEP 3: LLM Signal Analysis")

    signal_detector = SignalDetector()

    with Database() as db:
        query = db.db.query(Product).filter(
            Product.status == 1,
            Product.is_reviewed == False
        )

        # For automatic runs, only analyze products from the specified scrape date
        if is_automatic and scrape_date:
            from datetime import datetime
            scrape_date_obj = datetime.strptime(scrape_date, "%Y-%m-%d").date()
            query = query.filter(Product.created_at >= scrape_date_obj)
            print(f"Processing products created on {scrape_date} (automatic mode)")

        if product_ids:
            query = query.filter(Product.id.in_(product_ids))
            print(f"Processing specific product IDs: {product_ids}")
        elif limit:
            query = query.limit(limit)

        pending_products = query.all()

        if not pending_products:
            print("No products pending LLM review (status=1, is_reviewed=False)")
            print_separator()
            print("STEP 3 COMPLETE:")
            print("Success: 0")
            print("Failed: 0")
            print("Total Processed: 0")
            print_separator()
            return

        print(f"Found {len(pending_products)} products pending LLM review\n")

        success_count = 0
        failed_count = 0
        newly_signaled_companies = []

        for idx, product in enumerate(pending_products, 1):
            print_section_header(
                f"Analyzing {idx}/{len(pending_products)}: {product.product_name}"
            )

            metadata = product.product_metadata or {}
            ph_data = metadata.get("product_hunt", {})

            if not ph_data:
                print("No Product Hunt data found, skipping LLM analysis")
                product.is_reviewed = True
                product.reviewed_at = datetime.now()
                product.status = 2  
                db.db.commit()
                failed_count += 1
                continue

            print("Running LLM signal detection...")
            try:
                result = signal_detector.analyze(metadata)

                if result:
                    product.signal_score = result.signal_score
                    product.signal_strength = result.signal_strength
                    product.is_signal = result.is_signal
                    product.rationale = result.rationale
                    product.category_fit = result.category_fit
                    product.traction_assessment = result.traction_assessment
                    product.team_assessment = result.team_assessment
                    product.early_stage_indicators = result.early_stage_indicators
                    product.is_reviewed = True
                    product.reviewed_at = datetime.now()
                    product.status = 2
                    
                    if product.is_signal:
                        company = db.db.query(Company).filter(Company.id == product.company_id).first()
                        if company and not company.is_signal:
                            company.is_signal = True
                            db.db.add(company)

                            # Track newly signaled companies for email notification
                            # Extract logo the same way as the API (routes.py line 92)
                            ph_data = product.product_metadata.get('product_hunt', {}) if product.product_metadata else {}
                            logo_url = ph_data.get('thumbnail_url') or ph_data.get('thumbnail')

                            newly_signaled_companies.append({
                                'company_id': company.id,
                                'company_name': company.company_name,
                                'score': product.signal_score,
                                'product_name': product.product_name,
                                'logo_url': logo_url,
                                'launch_date': product.launch_date.strftime("%B %d, %Y") if product.launch_date else None,
                                'created_date': product.created_at.strftime("%Y-%m-%d") if product.created_at else scrape_date,
                                'product_metadata': product.product_metadata
                            })
                    
                    db.db.commit()

                    print("\nLLM Analysis Complete:")
                    print(f"Signal Score: {result.signal_score}")
                    print(f"Signal Strength: {result.signal_strength}")
                    print(f"Is Signal: {result.is_signal}")
                    print(f"Category Fit: {result.category_fit}")
                    print(f"Traction: {result.traction_assessment}")
                    print(f"Rationale: {result.rationale[:100]}...")
                    print("Status updated to 2 (Complete)")
                    success_count += 1
                else:
                    print("LLM analysis returned no result")
                    product.is_reviewed = True
                    product.reviewed_at = datetime.now()
                    product.status = 2  
                    db.db.commit()
                    failed_count += 1

            except Exception as e:
                print(f"LLM analysis error: {e}")
                logger.error(f"LLM analysis error for {product.product_name}: {e}")
                product.is_reviewed = True
                product.reviewed_at = datetime.now()
                product.status = 2  
                db.db.commit()
                failed_count += 1

        print_separator()
        print("STEP 3 COMPLETE:")
        print(f"Success: {success_count}")
        print(f"Failed: {failed_count}")
        print(f"Total Processed: {len(pending_products)}")
        print(f"New Signal Companies: {len(newly_signaled_companies)}")
        print_separator()

        # Send email notification for newly signaled companies (only for automatic runs)
        if newly_signaled_companies and is_automatic:
            try:
                print(f"Sending email notification for {len(newly_signaled_companies)} new signal companies...")

                # Group signals by their creation date
                signals_by_date = {}
                for signal in newly_signaled_companies:
                    date_key = signal.get('created_date', scrape_date or 'unknown')
                    if date_key not in signals_by_date:
                        signals_by_date[date_key] = []
                    signals_by_date[date_key].append(signal)

                email_service = EmailService()

                # Send separate email for each date
                for date_str, signals in signals_by_date.items():
                    print(f"Sending email for {len(signals)} signals from {date_str}")
                    email_service.send_signal_notification(signals, date_str)

                print("Email notifications sent successfully!")
            except Exception as e:
                print(f"Failed to send email notification: {e}")
                logger.error(f"Email notification failed: {e}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of products to analyze"
    )
    args = parser.parse_args()

    analyze_signals(limit=args.limit)