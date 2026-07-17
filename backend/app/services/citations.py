import logging
from urllib.parse import urlparse
from app.models.schemas import CitationData
from app.services.providers.base import EngineResult
from typing import List

logger = logging.getLogger(__name__)

def is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        # Check scheme
        if parsed.scheme not in ["http", "https"]:
            return False
        # Check domain has a dot and no spaces
        if not parsed.netloc or "." not in parsed.netloc or " " in parsed.netloc:
            return False
        return True
    except Exception:
        return False

def extract_domain(url: str) -> str:
    try:
        parsed = urlparse(url)
        return parsed.netloc.replace("www.", "")
    except Exception:
        return ""

def reconcile_citations(engine_result: EngineResult, judge_citations: List[CitationData], run_id: str) -> List[CitationData]:
    """
    Reconciles citations: if native_citations are present, uses them instead of judge_citations.
    Validates URLs and maps them to CitationData models.
    """
    if engine_result.native_citations:
        final_citations = []
        for c in engine_result.native_citations:
            url = c.get("url")
            if not url or not is_valid_url(url):
                logger.warning(f"Dropping invalid native citation URL for run {run_id}: {url}")
                continue
            
            domain = extract_domain(url)
            final_citations.append(
                CitationData(
                    url=url,
                    domain=domain,
                    source_type="other", # Default for native, could be enriched later
                    source="native"
                )
            )
        return final_citations
    
    # Fallback to judge extracted citations
    valid_judge_citations = []
    for c in judge_citations:
        if not c.url or not is_valid_url(c.url):
            logger.warning(f"Dropping invalid judge citation URL for run {run_id}: {c.url}")
            continue
        c.source = "judge_extracted"
        valid_judge_citations.append(c)
        
    return valid_judge_citations
