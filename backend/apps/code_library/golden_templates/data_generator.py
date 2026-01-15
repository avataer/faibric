"""
Data Generator - AI generates JSON data only, not code.

This is the key to reliability:
- AI is excellent at generating structured JSON
- JSON can be validated against schema
- No syntax errors possible with JSON
- Templates handle the code structure

FLOW:
1. Receive business description and template schema
2. Ask AI to generate JSON matching the schema
3. Validate JSON
4. Return data for template injection
"""

import json
import logging
import anthropic
from typing import Dict, Optional, List
from django.conf import settings

from apps.ai_engine.models_config import CODE_MODEL

logger = logging.getLogger(__name__)


def generate_component_data(
    business_description: str,
    component_type: str,
    schema: Dict,
    existing_data: Dict = None
) -> Dict:
    """
    Generate data for a component using AI.

    Args:
        business_description: Full description of the business
        component_type: Type of component (hero, navigation, etc.)
        schema: JSON schema for the data
        existing_data: Already generated data (for context)

    Returns:
        Dict matching the schema
    """
    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Format schema for prompt
    schema_str = json.dumps(schema, indent=2)

    # Build context from existing data
    context = ""
    if existing_data:
        context = f"""
ALREADY GENERATED DATA (use for consistency):
- Business name: {existing_data.get('business_name', 'Unknown')}
- Tagline: {existing_data.get('tagline', '')}
"""

    prompt = f"""You are a professional copywriter creating content for a business website.

BUSINESS DESCRIPTION:
{business_description}

COMPONENT TYPE: {component_type}

{context}

Generate JSON data for this component matching the schema below.
The content should be professional, compelling, and specific to this business.

SCHEMA:
{schema_str}

RULES:
1. Output ONLY valid JSON - no markdown, no explanation
2. Match the schema exactly - all required fields must be present
3. Write professional, business-appropriate content
4. Be specific to this business - no generic placeholder text
5. If generating lists (features, services, etc.), create 3-4 compelling items
6. Use double quotes for all strings
7. Do NOT use emojis anywhere

CRITICAL: Your response must be ONLY the JSON object. Nothing before or after.
Start with {{ and end with }}
"""

    try:
        response = client.messages.create(
            model=CODE_MODEL,  # Use Opus 4.5 for quality
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.content[0].text.strip()

        # Clean up any markdown formatting
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        # Find JSON in response
        start = content.find("{")
        end = content.rfind("}") + 1

        if start == -1 or end == 0:
            logger.error(f"[DATA GEN] No JSON found in response: {content[:100]}")
            return _fallback_data(component_type, business_description)

        json_str = content[start:end]

        # Parse and validate
        data = json.loads(json_str)

        # Validate required fields
        required = schema.get("required", [])
        missing = [f for f in required if f not in data]
        if missing:
            logger.warning(f"[DATA GEN] Missing required fields: {missing}")
            # Add defaults for missing fields
            for field in missing:
                data[field] = _default_for_field(field, component_type)

        logger.info(f"[DATA GEN] Generated data for {component_type}: {len(json.dumps(data))} bytes")
        return data

    except json.JSONDecodeError as e:
        logger.error(f"[DATA GEN] JSON parse error: {e}")
        return _fallback_data(component_type, business_description)
    except Exception as e:
        logger.error(f"[DATA GEN] Error: {e}")
        return _fallback_data(component_type, business_description)


def generate_all_component_data(
    business_description: str,
    components: List[str]
) -> Dict[str, Dict]:
    """
    Generate data for multiple components in one call.

    More efficient than calling generate_component_data multiple times.
    """
    from .template_registry import get_template

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    # Build schema for all components
    all_schemas = {}
    for comp_type in components:
        template = get_template(comp_type)
        if template:
            all_schemas[comp_type] = template.schema

    if not all_schemas:
        logger.error("[DATA GEN] No templates found for components")
        return {}

    schema_str = json.dumps(all_schemas, indent=2)

    prompt = f"""You are a professional copywriter creating content for a business website.

BUSINESS DESCRIPTION:
{business_description}

Generate JSON data for ALL of the following components.
Each component's data must match its schema.

COMPONENT SCHEMAS:
{schema_str}

RULES:
1. Output ONLY valid JSON - no markdown, no explanation
2. Return an object where each key is a component type
3. Each value must match that component's schema
4. Write professional, business-appropriate content
5. Be specific to this business - no generic placeholder text
6. Maintain consistency across components (same business name, tone, etc.)
7. For lists (features, services, testimonials), create 3-4 compelling items
8. Use double quotes for all strings
9. Do NOT use emojis anywhere

CRITICAL: Your response must be ONLY the JSON object.
Format: {{ "component_type": {{ ...data... }}, ... }}
"""

    try:
        response = client.messages.create(
            model=CODE_MODEL,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.content[0].text.strip()

        # Clean up markdown
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        # Find JSON
        start = content.find("{")
        end = content.rfind("}") + 1

        if start == -1 or end == 0:
            logger.error("[DATA GEN] No JSON found in batch response")
            return {c: _fallback_data(c, business_description) for c in components}

        data = json.loads(content[start:end])

        # Post-process: ensure all required fields are filled (no template variables left)
        data = _ensure_required_fields(data, business_description)

        logger.info(f"[DATA GEN] Generated batch data: {len(data)} components")
        return data

    except Exception as e:
        logger.error(f"[DATA GEN] Batch error: {e}")
        return {c: _fallback_data(c, business_description) for c in components}


def _ensure_required_fields(data: Dict[str, Dict], business_description: str) -> Dict[str, Dict]:
    """
    Ensure all template variables will be filled.
    This prevents {{phone}}, {{address}} etc from appearing in production.
    """
    # Contact section must have phone, email, address
    if "contact" in data:
        contact = data["contact"]
        if not contact.get("phone") or contact.get("phone", "").startswith("{{"):
            contact["phone"] = "(555) 123-4567"
        if not contact.get("email") or contact.get("email", "").startswith("{{"):
            # Try to extract email from business description
            import re
            email_match = re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', business_description)
            contact["email"] = email_match.group(0) if email_match else "contact@example.com"
        if not contact.get("address") or contact.get("address", "").startswith("{{"):
            contact["address"] = "123 Main Street, Suite 100, City, ST 12345"
        if not contact.get("submit_text"):
            contact["submit_text"] = "Send Message"
        data["contact"] = contact

    # Hero section must have background_seed
    if "hero" in data:
        hero = data["hero"]
        if not hero.get("background_seed"):
            hero["background_seed"] = "professional"
        data["hero"] = hero

    return data


def _fallback_data(component_type: str, business_description: str) -> Dict:
    """Generate fallback data when AI fails."""

    # Extract business name from description
    words = business_description.split()
    business_name = " ".join(words[:3]) if len(words) >= 3 else "Our Business"

    fallbacks = {
        "hero": {
            "headline": f"Welcome to {business_name}",
            "subheadline": "Professional services tailored to your needs",
            "cta_text": "Get Started",
            "background_seed": "business1",
        },
        "navigation": {
            "business_name": business_name,
            "nav_items": [
                {"id": "home", "label": "Home"},
                {"id": "services", "label": "Services"},
                {"id": "about", "label": "About"},
                {"id": "contact", "label": "Contact"},
            ]
        },
        "features": {
            "section_title": "What We Offer",
            "section_subtitle": "Discover our range of professional services",
            "features": [
                {"title": "Quality Service", "description": "We deliver excellence in everything we do", "icon_letter": "Q"},
                {"title": "Expert Team", "description": "Our professionals bring years of experience", "icon_letter": "E"},
                {"title": "Customer Focus", "description": "Your satisfaction is our top priority", "icon_letter": "C"},
            ]
        },
        "services": {
            "section_title": "Our Services",
            "services": [
                {"name": "Consultation", "description": "Expert advice tailored to your needs", "price": "Contact us"},
                {"name": "Implementation", "description": "Professional execution of your projects", "price": "Contact us"},
                {"name": "Support", "description": "Ongoing assistance when you need it", "price": "Contact us"},
            ]
        },
        "contact": {
            "section_title": "Contact Us",
            "section_subtitle": "We would love to hear from you",
            "submit_text": "Send Message",
            "phone": "(555) 123-4567",
            "email": "hello@example.com",
            "address": "123 Business Street, City, ST 12345",
        },
        "about": {
            "section_title": "About Us",
            "paragraphs": [
                "We are dedicated professionals committed to delivering exceptional results.",
                "With years of experience in our field, we bring expertise and passion to every project.",
            ],
            "image_seed": "team1",
        },
        "testimonials": {
            "section_title": "What Our Clients Say",
            "testimonials": [
                {"quote": "Exceptional service and outstanding results. Highly recommended.", "name": "John Smith", "role": "CEO, Tech Corp"},
                {"quote": "Professional, reliable, and a pleasure to work with.", "name": "Sarah Johnson", "role": "Director, ABC Inc"},
                {"quote": "They exceeded our expectations in every way.", "name": "Michael Brown", "role": "Owner, Local Business"},
            ]
        },
        "footer": {
            "business_name": business_name,
            "tagline": "Quality service you can trust",
            "year": "2024",
        },
    }

    return fallbacks.get(component_type, {"title": component_type})


def _default_for_field(field: str, component_type: str) -> str:
    """Get default value for a missing required field."""
    defaults = {
        "headline": "Welcome",
        "subheadline": "Professional services",
        "cta_text": "Get Started",
        "section_title": component_type.title(),
        "business_name": "Our Business",
        "submit_text": "Submit",
    }
    return defaults.get(field, field.replace("_", " ").title())
