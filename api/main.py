from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, validator
from datetime import datetime
from api.routes import router as signals_router
from fastapi.middleware.cors import CORSMiddleware
from infrastructure.database import init_db

# Import Celery tasks
from infrastructure.tasks import scrape_task, enrich_task, analyze_task, full_pipeline_task

from core.scrape_ph import scrape_producthunt_only, scrape_producthunt_date_streamlined
from core.enrich_social import enrich_social_links
from core.analyze_signals import analyze_signals


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
    date: str = Field(..., pattern=r'^\d{4}-\d{2}-\d{2}$')
    limit: int | None = Field(50, ge=1, le=1000)  # Default 50, None = unlimited
    use_streamlined: bool = Field(True, description="Use optimized streaming scraper with complexity limits")

    @validator('date')
    def validate_date(cls, v):
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except Exception:
            raise ValueError("Invalid date. Use YYYY-MM-DD")
        return v


class EnrichRequest(BaseModel):
    limit: int | None = Field(None, ge=1, le=1000)


class AnalyzeRequest(BaseModel):
    limit: int | None = Field(None, ge=1, le=1000)


class TaskResponse(BaseModel):
    status: str
    task_id: str
    message: str
    step: int
    next_step: str


class PipelineTaskResponse(BaseModel):
    status: str
    task_id: str
    message: str
    date_used: str


@app.on_event("startup")
def startup():
    init_db()
    print("✓ Database initialized")
    print("✓ Celery ready (if running)")
    print("Manual mode available using ?sync=true")


@app.post("/scrape", response_model=TaskResponse)
def scrape(request: ScrapeRequest, sync: bool = False):
    """
    Scrape products. If limit is None, scrape ALL products for that date.
    Use streamlined=True for optimized complexity-aware scraping.
    """
    date_str = request.date
    limit = request.limit  # Can be None for unlimited
    use_streamlined = request.use_streamlined

    if sync:
        if use_streamlined:
            product_ids = scrape_producthunt_date_streamlined(date_str, max_products=limit)
        else:
            product_ids = scrape_producthunt_only(date_str, limit=limit)

        scraper_type = "streamlined" if use_streamlined else "standard"
        return {
            "status": "completed",
            "task_id": "manual",
            "message": f"{scraper_type.title()} scrape completed for {date_str}. Fetched {len(product_ids)} products.",
            "step": 1,
            "next_step": "Call /enrich?sync=true"
        }

    # For async tasks, pass the streamlined flag
    task = scrape_task.apply_async(args=[date_str, limit, use_streamlined])
    return {
        "status": "task_started",
        "task_id": task.id,
        "message": f"Scrape task queued for {date_str} (streamlined={use_streamlined})",
        "step": 1,
        "next_step": "Check /task/{task_id}"
    }


@app.post("/enrich", response_model=TaskResponse)
def enrich(request: EnrichRequest, sync: bool = False):
    """
    Run enrichment either:
    - async via Celery
    - manually via API (/enrich?sync=true)
    """
    if sync:
        enrich_social_links(limit=request.limit)
        return {
            "status": "completed",
            "task_id": "manual",
            "message": "Enrichment completed manually",
            "step": 2,
            "next_step": "Call /analyze?sync=true"
        }

    task = enrich_task.apply_async(kwargs={"limit": request.limit})
    return {
        "status": "task_started",
        "task_id": task.id,
        "message": "Enrichment task queued",
        "step": 2,
        "next_step": "Check /task/{task_id} or call /analyze"
    }


@app.post("/analyze", response_model=TaskResponse)
def analyze(request: AnalyzeRequest, sync: bool = False):
    """
    Run analysis either:
    - async via Celery
    - manually via API (/analyze?sync=true)
    """
    if sync:
        analyze_signals(limit=request.limit)
        return {
            "status": "completed",
            "task_id": "manual",
            "message": "Signal analysis completed manually",
            "step": 3,
            "next_step": "View results at /signals"
        }

    task = analyze_task.apply_async(kwargs={"limit": request.limit})
    return {
        "status": "task_started",
        "task_id": task.id,
        "message": "LLM analysis task queued",
        "step": 3,
        "next_step": "Check /task/{task_id}"
    }


@app.post("/scrape-full", response_model=PipelineTaskResponse)
def scrape_full_pipeline(request: ScrapeRequest, sync: bool = False):
    """
    Full pipeline with unlimited scraping support
    """
    day, month, year = request.date.split("-")
    date_str = f"{year}-{month}-{day}"
    limit = request.limit  # Can be None

    if sync:
        product_ids = scrape_producthunt_only(date_str, limit=limit)
        enrich_social_links(product_ids=product_ids)
        analyze_signals(product_ids=product_ids)
        return {
            "status": "completed",
            "task_id": "manual",
            "message": f"Full pipeline completed for {date_str}. Processed {len(product_ids)} products.",
            "date_used": date_str
        }

    task = full_pipeline_task.apply_async(args=[date_str, limit])
    return {
        "status": "task_started",
        "task_id": task.id,
        "message": f"Full pipeline queued for {date_str}",
        "date_used": date_str
    }

@app.get("/task/{task_id}")
def get_task_status(task_id: str):
    """
    Check Celery task status
    """
    from celery.result import AsyncResult
    from celery_app import celery_app

    task_result = AsyncResult(task_id, app=celery_app)

    if task_result.state == "PENDING":
        return {"task_id": task_id, "status": "pending"}
    elif task_result.state == "STARTED":
        return {"task_id": task_id, "status": "running"}
    elif task_result.state == "SUCCESS":
        return {"task_id": task_id, "status": "completed", "result": task_result.result}
    elif task_result.state == "FAILURE":
        return {"task_id": task_id, "status": "failed", "error": str(task_result.info)}

    return {"task_id": task_id, "status": task_result.state}
