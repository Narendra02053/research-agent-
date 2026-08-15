"""
source_validator.py
Evaluates source credibility and scores domains based on trustworthiness.
Prioritizes official sites, research papers, engineering blogs, and major news organizations.
"""
from urllib.parse import urlparse
import logging

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
        
        for src in sources:
            url = src.get("url", "")
            domain = urlparse(url).netloc.lower()
            
            score = 0.5  # Base score
            reasoning = "Standard domain."
            
            # Check high trust
            if any(domain.endswith(d) for d in HIGH_TRUST_DOMAINS):
                score = 0.95
                reasoning = "High-trust official/research domain."
            # Check low trust
            elif any(domain.endswith(d) for d in LOW_TRUST_DOMAINS):
                score = 0.3
                reasoning = "Low-trust community/blog domain."
            # Prefer standard professional TLDs slightly higher
            elif domain.endswith(".io") or domain.endswith(".ai") or domain.endswith(".co"):
                score = 0.65
                reasoning = "Tech/Startup domain."
                
            total_score += score
            details.append({
                "url": url,
                "domain": domain,
                "trust_score": score,
                "reasoning": reasoning
            })
            
        avg_quality = round(total_score / len(sources), 2)
        logger.info(f"Source validation complete. Avg Quality: {avg_quality}")
        
        return {
            "source_quality": avg_quality,
            "details": details
        }
