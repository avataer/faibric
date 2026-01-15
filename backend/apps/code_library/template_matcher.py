"""
Template Matcher - Match user requests to golden templates.

Per strategy: NLP matches to closest template, auto-inject branding,
serve in <5 seconds (instant gratification).
"""
import re
import logging
from typing import Optional, Tuple, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TemplateMatch:
    """Result of template matching."""
    found: bool
    template_name: str
    template_code: str
    confidence: float  # 0-1
    matched_keywords: list


class TemplateMatcher:
    """
    Matches user requests to golden templates using keyword matching.

    Fast, deterministic, no AI cost.
    """

    # Keyword to template mapping with weights
    TEMPLATE_KEYWORDS = {
        "Restaurant Website": {
            "keywords": ["restaurant", "cafe", "coffee", "bakery", "pizza", "food", "menu",
                        "dining", "bistro", "diner", "eatery", "catering", "kitchen", "chef"],
            "weight": 1.0
        },
        "Professional Services": {
            "keywords": ["lawyer", "attorney", "law", "legal", "consulting", "consultant",
                        "accountant", "accounting", "financial", "advisor", "professional",
                        "agency", "firm", "services", "business services"],
            "weight": 1.0
        },
        "Fitness Studio": {
            "keywords": ["fitness", "gym", "yoga", "workout", "training", "exercise",
                        "health", "wellness", "crossfit", "pilates", "personal trainer",
                        "sports", "athletic", "studio"],
            "weight": 1.0
        },
        "Real Estate Agency": {
            "keywords": ["real estate", "property", "realtor", "homes", "houses", "apartments",
                        "listings", "broker", "realty", "housing", "rental", "mortgage"],
            "weight": 1.0
        },
        "Portfolio Website": {
            "keywords": ["portfolio", "photography", "photographer", "design", "designer",
                        "creative", "artist", "gallery", "showcase", "work samples",
                        "freelance", "personal website", "creative portfolio"],
            "weight": 1.0
        },
        "SaaS Landing Page": {
            "keywords": ["saas", "software", "startup", "app", "product", "landing",
                        "tech", "platform", "subscription", "tool", "solution", "service"],
            "weight": 0.9  # Slightly lower - more generic
        },
        "E-commerce Store": {
            "keywords": ["ecommerce", "e-commerce", "store", "shop", "products", "retail",
                        "online store", "shopping", "buy", "sell", "merchandise", "clothing",
                        "fashion", "marketplace"],
            "weight": 1.0
        },
        "Booking System": {
            "keywords": ["booking", "appointment", "schedule", "salon", "spa", "clinic",
                        "doctor", "dentist", "barber", "reservation", "appointments",
                        "book online", "scheduling"],
            "weight": 1.0
        },
        "Dashboard Analytics": {
            "keywords": ["dashboard", "analytics", "metrics", "data", "charts", "admin",
                        "panel", "reports", "kpi", "statistics", "monitoring", "tracking"],
            "weight": 1.0
        },
    }

    # Minimum confidence threshold (lowered to allow more matches)
    MIN_CONFIDENCE = 0.15

    def __init__(self):
        from apps.code_library.models import LibraryItem
        self.model = LibraryItem

    def match(self, user_request: str) -> TemplateMatch:
        """
        Match user request to best template.

        Returns TemplateMatch with found=True if confidence > threshold.
        """
        request_lower = user_request.lower()

        best_template = None
        best_score = 0
        best_keywords = []

        for template_name, config in self.TEMPLATE_KEYWORDS.items():
            keywords = config["keywords"]
            weight = config["weight"]

            matched = []
            for kw in keywords:
                if kw in request_lower:
                    matched.append(kw)

            if matched:
                # Score = (matched keywords / total keywords) * weight
                score = (len(matched) / len(keywords)) * weight

                # Bonus for longer keyword matches (more specific)
                avg_len = sum(len(k) for k in matched) / len(matched)
                score *= (1 + avg_len / 20)  # Slight boost for longer matches

                if score > best_score:
                    best_score = score
                    best_template = template_name
                    best_keywords = matched

        # Normalize score to 0-1 confidence
        confidence = min(best_score, 1.0)

        if confidence >= self.MIN_CONFIDENCE and best_template:
            # Fetch template from database
            template = self.model.objects.filter(
                name=best_template,
                item_type="template",
                is_active=True
            ).first()

            if template:
                return TemplateMatch(
                    found=True,
                    template_name=best_template,
                    template_code=template.code,
                    confidence=confidence,
                    matched_keywords=best_keywords
                )

        return TemplateMatch(
            found=False,
            template_name="",
            template_code="",
            confidence=confidence,
            matched_keywords=best_keywords
        )

    def customize_template(self, template_code: str, business_name: str, tagline: str = "") -> str:
        """
        Customize template with business branding.

        Replaces placeholders:
        - {{BUSINESS_NAME}} -> actual business name
        - {{TAGLINE}} -> actual tagline or generated one
        """
        if not tagline:
            tagline = f"Quality {business_name} Services"

        code = template_code.replace("{{BUSINESS_NAME}}", business_name)
        code = code.replace("{{TAGLINE}}", tagline)

        return code

    def extract_business_info(self, user_request: str) -> Tuple[str, str]:
        """
        Extract business name and tagline from user request.

        Examples:
        - "Create a website for Joe's Pizza" -> ("Joe's Pizza", "")
        - "Build a law firm site called Smith & Associates" -> ("Smith & Associates", "")
        """
        # Common patterns for business names
        patterns = [
            r"(?:called|named|for)\s+[\"']?([A-Z][^\"'\.,]+)[\"']?",
            r"(?:my|our)\s+(?:business|company|store|shop|restaurant|firm|studio)\s+(?:is\s+)?[\"']?([A-Z][^\"'\.,]+)[\"']?",
            r"([A-Z][a-zA-Z]+(?:\s+[A-Z][a-zA-Z]+)*(?:'s)?)\s+(?:website|site|page|store|shop)",
        ]

        business_name = "My Business"  # Default

        for pattern in patterns:
            match = re.search(pattern, user_request, re.IGNORECASE)
            if match:
                business_name = match.group(1).strip()
                break

        # Clean up business name
        business_name = business_name.strip("\"' ")
        if len(business_name) > 50:
            business_name = business_name[:50]

        # Generate tagline based on matched template type
        tagline = ""
        request_lower = user_request.lower()

        if any(k in request_lower for k in ["restaurant", "cafe", "food", "bakery"]):
            tagline = "Delicious Food, Memorable Experiences"
        elif any(k in request_lower for k in ["lawyer", "law", "legal", "attorney"]):
            tagline = "Trusted Legal Excellence"
        elif any(k in request_lower for k in ["fitness", "gym", "yoga"]):
            tagline = "Transform Your Body, Transform Your Life"
        elif any(k in request_lower for k in ["real estate", "property", "homes"]):
            tagline = "Find Your Dream Home"
        elif any(k in request_lower for k in ["portfolio", "photography", "design"]):
            tagline = "Creative Excellence"
        elif any(k in request_lower for k in ["booking", "appointment", "salon"]):
            tagline = "Book Your Experience Today"
        else:
            tagline = "Excellence in Everything We Do"

        return business_name, tagline


def match_template(user_request: str) -> Optional[Dict]:
    """
    Main entry point for template matching.

    Returns dict with template info if matched, None if no match.
    """
    print(f"[TEMPLATE MATCHER] Checking: {user_request[:50]}...")
    matcher = TemplateMatcher()
    result = matcher.match(user_request)
    print(f"[TEMPLATE MATCHER] Result: found={result.found}, confidence={result.confidence:.2f}, keywords={result.matched_keywords}")

    if result.found:
        business_name, tagline = matcher.extract_business_info(user_request)
        customized_code = matcher.customize_template(
            result.template_code,
            business_name,
            tagline
        )

        logger.info(f"Template matched: {result.template_name} (confidence: {result.confidence:.2f})")

        return {
            "template_name": result.template_name,
            "code": customized_code,
            "confidence": result.confidence,
            "matched_keywords": result.matched_keywords,
            "business_name": business_name,
            "tagline": tagline
        }

    logger.info(f"No template match (best confidence: {result.confidence:.2f})")
    return None
