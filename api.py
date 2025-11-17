from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from main import main as run_scraper
import traceback

app = FastAPI(title="Product Hunt Scraper API")

class ScrapeRequest(BaseModel):
    date: str   # expects DD-MM-YYYY (example: 17-11-2025)

@app.post("/scrape")
def scrape_data(request: ScrapeRequest):
    try:
        day, month, year = request.date.split("-")
        date_str = f"{year}-{month}-{day}"
    except:
        raise HTTPException(status_code=400, detail="Invalid format. Use DD-MM-YYYY")

    try:
        run_scraper(date_str)
        return {"status": "success", "date_used": date_str}
    
    except Exception as e:
        print("\n" + "="*60)
        print("ERROR DETAILS:")
        print("="*60)
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("\nFull traceback:")
        traceback.print_exc()
        print("="*60 + "\n")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
def root():
    return {"message": "Product Hunt Scraper API is running"}