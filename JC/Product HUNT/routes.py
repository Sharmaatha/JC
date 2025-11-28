from fastapi import APIRouter, Query
from sqlalchemy.orm import Session
from database import SessionLocal
from models.models import Product
from llm.signal_detector import SignalDetector
from datetime import datetime
from typing import Optional

router = APIRouter()

detector = SignalDetector()


@router.get("/signals")
def get_signals(date: Optional[str] = Query(None)):
    """
    Get all signals, optionally filtered by launch date
    """
    db: Session = SessionLocal()
    
    query = db.query(Product)
    
    if date:
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
            query = query.filter(Product.launch_date == target_date)
        except ValueError:
            pass  
    
    products = query.all()

    result = []
    for p in products:
        md = p.product_metadata or {}
        ph = md.get("product_hunt", {})
        
        if p.launch_date:
            display_date = p.launch_date.isoformat()
        else:
            ph_created_at = ph.get("created_at")
            display_date = ph_created_at if ph_created_at else (p.created_at.isoformat() if p.created_at else None)
        
        result.append({
            "id": p.id,
            "company_id": p.company_id,
            "company_name": p.company.company_name if p.company else None,
            "name": ph.get("name"),
            "tagline": ph.get("tagline"),
            "description": ph.get("description"),
            "thumbnail_url": ph.get("thumbnail_url") or ph.get("thumbnail"),
            "topics": ph.get("topics", []),
            "votes": ph.get("votes_count", 0),
            "signal_score": p.signal_score,
            "signal_strength": p.signal_strength,
            "is_signal": p.is_signal,
            "created_at": display_date,
            "launch_date": p.launch_date.isoformat() if p.launch_date else None,
            "is_social_scraped": p.is_social_scraped,
            "is_reviewed": p.is_reviewed,
            "status": p.status,

        })

    db.close()
    return {"data": result}


@router.get("/signals/check-date/{date}")
def check_date_exists(date: str):
    """
    Check if products exist for a given launch date
     """
    db: Session = SessionLocal()
    
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        db.close()
        return {"exists": False, "count": 0, "error": "Invalid date format. Use YYYY-MM-DD"}
    
    count = db.query(Product).filter(Product.launch_date == target_date).count()
    
    db.close()
    return {"exists": count > 0, "count": count}


@router.post("/score/{product_id}")
def score_product(product_id: int):
    """Re-run LLM analysis for a specific product"""
    db: Session = SessionLocal()
    product = db.query(Product).filter(Product.id == product_id).first()

    if not product:
        db.close()
        return {"error": "Product not found"}

    result = detector.analyze(product.product_metadata)

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

        db.commit()

    db.close()

    return {"success": True, "score": result.signal_score, "is_signal": result.is_signal}