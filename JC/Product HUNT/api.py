from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import traceback
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from routes import router as signals_router
from fastapi.middleware.cors import CORSMiddleware
from scrape_ph import scrape_producthunt_only
from enrich_social import enrich_social_links
from analyze_signals import analyze_signals
from database import init_db


app = FastAPI(title="Product Hunt Signal Detector API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(signals_router)


class ScrapeRequest(BaseModel):
    date: str   # DD-MM-YYYY
    limit: int = 10


class EnrichRequest(BaseModel):
    limit: int = None


class AnalyzeRequest(BaseModel):
    limit: int = None


scheduler = BackgroundScheduler()


def daily_auto_scrape():
    """Automatically run STEP 1 at 2 AM daily"""
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    try:
        print(f"Auto-scraping Product Hunt for {yesterday}...")
        scrape_producthunt_only(yesterday, limit=10)
        print(f"Auto scrape completed for {yesterday}")
    except Exception as e:
        print(f"Auto scrape failed for {yesterday}: {e}")
        traceback.print_exc()


@app.on_event("startup")
def startup():
    init_db()
    scheduler.add_job(daily_auto_scrape, "cron", hour=2, minute=0, id="daily_scrape")
    scheduler.start()
    print("Daily auto scraper scheduled at 2:00 AM")


@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler.shutdown()
    print("Scheduler shut down")


@app.post("/scrape")
def scrape(request: ScrapeRequest):
    """
    STEP 1: Scrape Product Hunt and store data only
    """
    try:
        day, month, year = request.date.split("-")
        date_str = f"{year}-{month}-{day}"  # YYYY-MM-DD
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid format. Use DD-MM-YYYY")

    try:
        product_ids = scrape_producthunt_only(date_str, limit=request.limit)
        return {
            "status": "success",
            "step": 1,
            "message": f"Scraped {len(product_ids)} products from Product Hunt",
            "product_ids": product_ids,
            "date_used": date_str,
            "next_step": "Call POST /enrich to extract social links",
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/enrich")
def enrich(request: EnrichRequest):
    """
    STEP 2: Extract and enrich LinkedIn/Twitter for products
    """
    try:
        enrich_social_links(limit=request.limit)
        return {
            "status": "success",
            "step": 2,
            "message": "Social enrichment completed",
            "next_step": "Call POST /analyze to run LLM signal detection",
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/analyze")
def analyze(request: AnalyzeRequest):
    """
    STEP 3: Run LLM signal analysis on products
    """
    try:
        analyze_signals(limit=request.limit)
        return {
            "status": "success",
            "step": 3,
            "message": "LLM signal analysis completed",
            "next_step": "Check dashboard at /signals",
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/scrape-full")
def scrape_full_pipeline(request: ScrapeRequest):
    """
    Run all 3 steps in sequence for a specific date:
    1. Scrape Product Hunt for that date and get product IDs
    2. Enrich social links ONLY for those specific product IDs
    3. Analyze signals ONLY for those specific product IDs
    """
    try:
        day, month, year = request.date.split("-")
        date_str = f"{year}-{month}-{day}"  # YYYY-MM-DD
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid format. Use DD-MM-YYYY")

    try:
        print("Starting full 3-step pipeline...")

        print("\n[1/3] Scraping Product Hunt...")
        product_ids = scrape_producthunt_only(date_str, limit=request.limit)
        
        if not product_ids:
            print("No products scraped, aborting pipeline")
            return {
                "status": "success",
                "steps_completed": [1],
                "message": "No products found for the given date",
                "date_used": date_str,
                "product_ids": [],
            }

        print(f"\n[2/3] Enriching social links for product IDs: {product_ids}...")
        enrich_social_links(product_ids=product_ids)

        print(f"\n[3/3] Analyzing signals for product IDs: {product_ids}...")
        analyze_signals(product_ids=product_ids)

        print("\n✓ Full pipeline completed!")

        return {
            "status": "success",
            "steps_completed": [1, 2, 3],
            "message": "Full pipeline completed successfully",
            "date_used": date_str,
            "product_ids": product_ids,
            "products_processed": len(product_ids),
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status/pending")
def get_pending_counts():
    """Get count of products pending each step"""
    from database import Database
    from models.models import Product

    with Database() as db:
        total = db.db.query(Product).count()
        pending_social = db.db.query(Product).filter(Product.is_social_scraped == False).count()
        pending_review = db.db.query(Product).filter(Product.is_reviewed == False).count()

        return {
            "total_products": total,
            "pending_social_enrichment": pending_social,
            "pending_llm_review": pending_review,
            "completed": total - pending_review,
        }


@app.get("/")
def root():
    return {
        "message": "Product Hunt  Signal Detector API",
        "steps": {
            "1": "POST /scrape - Scrape Product Hunt only",
            "2": "POST /enrich - Extract & enrich social links",
            "3": "POST /analyze - Run LLM signal analysis",
        },
        "combined": "POST /scrape-full - Run all steps for specific date",
        "status": "GET /status/pending - Check pending counts",
    }


@app.get("/scheduler/status")
def scheduler_status():
    jobs = scheduler.get_jobs()
    return {
        "running": scheduler.running,
        "jobs": [{"id": job.id, "next_run": str(job.next_run_time)} for job in jobs],
    }