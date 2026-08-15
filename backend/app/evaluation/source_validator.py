"""
source_validator.py
Evaluates source credibility and scores domains based on trustworthiness using multiple signals:
HTTPS validation, domain authority, source freshness, organization/research detection, and citation counts.
"""
from urllib.parse import urlparse
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

HIGH_TRUST_DOMAINS = {
    "edu", "gov", "org", "ac.uk",
    "nature.com", "science.org", "arxiv.org", "github.com",
    "bloomberg.com", "reuters.com", "wsj.com", "nytimes.com",
    "nvidia.com", "microsoft.com", "google.com", "aws.amazon.com",
    "openai.com", "anthropic.com", "deepmind.com", "meta.com"
}

LOW_TRUST_DOMAINS = {
    "quora.com", "reddit.com", "yahoo.com",
    "blogspot.com", "wordpress.com"
}

ORGANIZATION_RESEARCH_DOMAINS = {
    "edu", "gov", "org", "ac.uk",
    "nature.com", "science.org", "arxiv.org", "nih.gov", "ieee.org"
}

def parse_publication_date(src: dict) -> datetime:
    """Helper to parse publication date from source metadata."""
    date_fields = ["pub_date", "date", "published_date", "created_at", "timestamp"]
    metadata = src.get("metadata", {}) if isinstance(src.get("metadata"), dict) else {}
    
    for field in date_fields:
        val = src.get(field) or metadata.get(field)
        if not val:
            continue
        if isinstance(val, datetime):
            return val
        if isinstance(val, (int, float)):
            try:
                return datetime.fromtimestamp(val)
            except Exception:
                continue
        val_str = str(val).strip()
        for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y"):
            try:
                return datetime.strptime(val_str, fmt)
            except ValueError:
                continue
        # Fallback regex for 4-digit year
        match = re.search(r"\b(19\d\d|20\d\d)\b", val_str)
        if match:
            try:
                return datetime(int(match.group(1)), 1, 1)
            except ValueError:
                pass
    return None

class SourceValidator:
    @staticmethod
    def evaluate_sources(sources: list) -> dict:
        """
        Evaluate a list of source dictionaries.
        Returns average source quality and detailed breakdowns.
        """
        if not sources:
            return {"source_quality": 0.0, "details": []}
            
        total_score = 0
        details = []
        current_year = 2026  # reference current year
        
        for src in sources:
            url = src.get("url", "")
            domain = urlparse(url).netloc.lower()
            if domain.startswith("www."):
                domain = domain[4:]
                
            # 1. HTTPS Validation
            is_https = url.lower().startswith("https://")
            https_score = 1.0 if is_https else 0.0
            
            # 2. Domain Authority Score
            domain_authority = 0.5  # Base authority
            reasoning = "Standard domain."
            
            if any(domain == d or domain.endswith("." + d) for d in HIGH_TRUST_DOMAINS):
                domain_authority = 1.0
                reasoning = "High-trust official/research domain."
            elif any(domain == d or domain.endswith("." + d) for d in LOW_TRUST_DOMAINS):
                domain_authority = 0.2
                reasoning = "Low-trust community/blog domain."
            elif domain.endswith(".io") or domain.endswith(".ai") or domain.endswith(".co") or domain.endswith(".dev"):
                domain_authority = 0.7
                reasoning = "Tech/Startup domain."
                
            # 3. Source Freshness Score (using datetime)
            pub_date = parse_publication_date(src)
            if pub_date:
                years_old = max(0, current_year - pub_date.year)
                if years_old <= 1:
                    freshness_score = 1.0
                elif years_old <= 3:
                    freshness_score = 0.8
                elif years_old <= 5:
                    freshness_score = 0.6
                else:
                    freshness_score = 0.4
            else:
                freshness_score = 0.75  # default neutral
                
            # 4. Organization/Research Detection
            is_org_or_res = any(domain == d or domain.endswith("." + d) for d in ORGANIZATION_RESEARCH_DOMAINS)
            org_res_score = 1.0 if is_org_or_res else 0.0
            
            # 5. Citation Count Score (if available)
            metadata = src.get("metadata", {}) if isinstance(src.get("metadata"), dict) else {}
            citation_count = None
            for key in ["citation_count", "citations"]:
                if src.get(key) is not None:
                    citation_count = src.get(key)
                    break
                elif metadata.get(key) is not None:
                    citation_count = metadata.get(key)
                    break
            
            if citation_count is not None:
                try:
                    c_count = int(citation_count)
                    if c_count >= 10:
                        citation_score = 1.0
                    elif c_count >= 5:
                        citation_score = 0.8
                    elif c_count >= 1:
                        citation_score = 0.5
                    else:
                        citation_score = 0.0
                except (ValueError, TypeError):
                    citation_score = 0.5
                    c_count = None
            else:
                citation_score = 0.5  # default if not available
                c_count = None
                
            # Compute weighted source score
            # HTTPS: 10% | Domain Authority: 40% | Freshness: 20% | Org/Research: 20% | Citation Score: 10%
            source_score = (
                (https_score * 0.1) +
                (domain_authority * 0.4) +
                (freshness_score * 0.2) +
                (org_res_score * 0.2) +
                (citation_score * 0.1)
            )
            source_score = min(max(source_score, 0.0), 1.0)
            total_score += source_score
            
            details.append({
                "url": url,
                "domain": domain,
                "https_valid": is_https,
                "domain_authority": domain_authority,
                "freshness_score": freshness_score,
                "is_organization_or_research": is_org_or_res,
                "citation_count": c_count,
                "trust_score": round(source_score, 2),
                "reasoning": reasoning
            })
            
        avg_quality = round(total_score / len(sources), 2)
        logger.info(f"Source validation complete. Avg Quality: {avg_quality}")
        
        return {
            "source_quality": avg_quality,
            "details": details
        }
