import logging
from typing import Dict, Any, Optional
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field
from config import GROQ_API_KEY

logger = logging.getLogger(__name__)


class SignalAnalysis(BaseModel):
    """VC Signal Scoring Output"""
    signal_score: int = Field(description="0–100 investment signal score")
    signal_strength: str = Field(description="strong, moderate, weak")
    is_signal: bool = Field(description="true if strong signal (score >= 70), false otherwise") 
    rationale: str = Field(description="Short explanation for the score")
    category_fit: str = Field(description="good, moderate, poor")
    traction_assessment: str = Field(description="good, moderate, poor")
    team_assessment: str = Field(description="good, moderate, poor")
    early_stage_indicators: str = Field(description="strong, moderate, weak")


class SignalDetector:
    """Detects Jan Cap investment signals from metadata"""
    
    def __init__(self):
        self.llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            api_key=GROQ_API_KEY,
            temperature=0
        )
        self.parser = PydanticOutputParser(pydantic_object=SignalAnalysis)
        
        self.prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                """
You are a venture analyst for Jan Cap VC. Your role is to evaluate whether a Product Hunt launch represents a TRUE investment signal or not.

You must score objectively and conservatively. Very few products should qualify as high-confidence signals.

====================================================
JAN CAP THESIS & PRIORITY AREAS
====================================================
Jan Cap invests in:
- AI / Applied AI
- DevTools / Developer productivity
- APIs / Infrastructure / Data platforms
- B2B SaaS with strong GTM potential
- Fintech infrastructure

Jan Cap does NOT prioritize:
- Consumer social
- Lifestyle apps
- Simple mobile apps / templates
- No-code page builders unless novel infra
- Hobby projects, extensions, gimmicks

====================================================
SCORING (0–100)
====================================================

CATEGORY FIT — 25 pts
• Great fit with thesis = 25
• Some overlap = 10–20
• Weak or irrelevant = 0–5

TRACTION — 25 pts
• Votes > 200, strong launch, clear excitement → 20–25
• Average traction → 10–18
• Weak traction / unclear demand → 0–8

TEAM / SOCIAL SIGNALS — 20 pts
• Demonstrated domain expertise → 15–20
• Neutral / unclear → 7–14
• Very weak / no credibility → 0–6
(Missing social data should NOT reduce score — only negative signals should.)

EARLY-STAGE INDICATORS — 15 pts
• Shows serious commitment and momentum even if early: recent launch, founders shipping fast, lean strengths → 10–15
• Neutral → 5–9
• Low intent / hackathon vibe / project-style → 0–4

PRODUCT QUALITY & PROBLEM FIT — 15 pts
• Clear pain reliever + strong value prop for enterprises / teams / developers → 10–15
• Looks promising but unproven → 5–9
• Generic / unclear problem → 0–4

====================================================
FINAL CLASSIFICATION
====================================================
80–100 → strong signal  
50–79 → moderate signal  
0–49 → weak signal

IMPORTANT:
is_signal MUST be true ONLY IF score >= 70.

This means only the *best launches* should qualify as true opportunities.

====================================================
STRICT RULES
====================================================
DO NOT inflate scores.
DO NOT treat every AI project as strong.
DO NOT mark everything as a signal.

Scrutinize the product like an investor.
Missing LinkedIn/Twitter data should be neutral, not harmful.
High hype with no substance should reduce score.


{format_instructions}

====================
FORMAT
====================
Respond ONLY with the following Pydantic structure:

{format_instructions}
"""
            ),
            (
                "user",
                """
Product: {product_name}

Tagline: {tagline}

Description: {description}

Votes: {votes}

LinkedIn Summary: {linkedin_summary}

Twitter Summary: {twitter_summary}

Product Hunt Topics: {topics}

Analyze and produce a 0–100 score and final signal assessment.
"""
            )
        ])
    
    def _extract_metadata(self, metadata: Dict[str, Any]) -> Dict[str, str]:
        """Extract relevant fields from metadata"""
        ph = metadata.get("product_hunt", {})
        linkedin = metadata.get("linkedin", {})
        twitter = metadata.get("twitter", {})
        
        linkedin_summary = (
            f"{linkedin.get('company_size', 'N/A')} employees, "
            f"{linkedin.get('industry', 'N/A')}. "
            f"Overview: {linkedin.get('overview', 'N/A')}"
            if linkedin else "No data"
        )
        
        twitter_summary = (
            f"{twitter.get('followers_count', 0)} followers, "
            f"Bio: {twitter.get('bio', 'N/A')}"
            if twitter else "No data"
        )
        
        topics = ", ".join(ph.get("topics", [])) if ph.get("topics") else "N/A"

        return {
            "product_name": ph.get("name", "Unknown"),
            "tagline": ph.get("tagline", "No tagline"),
            "description": ph.get("description", "No description"),
            "votes": str(ph.get("votes_count", 0)),
            "linkedin_summary": linkedin_summary,
            "twitter_summary": twitter_summary,
            "topics": topics
        }
    
    def analyze(self, metadata: Dict[str, Any]) -> Optional[SignalAnalysis]:
        """Analyze product metadata and return signal detection result"""
        try:
            extracted = self._extract_metadata(metadata)
            
            chain = self.prompt | self.llm | self.parser
            
            result = chain.invoke({
                **extracted,
                "format_instructions": self.parser.get_format_instructions()
            })
            
            logger.info(
                f"Analyzed {extracted['product_name']}: "
                f"Score={result.signal_score}, Strength={result.signal_strength}, IsSignal={result.is_signal}"
            )
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing metadata: {e}")
            return None