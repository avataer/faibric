"""
Template Composer - Composes a complete app from golden templates.

FLOW:
1. Analyze user request to determine needed components
2. Select appropriate templates for each component
3. Generate data for all components (single AI call)
4. Render templates with data
5. Generate AI images for any user-specified image requests
6. Compose into final App.jsx

RESULT: Guaranteed valid code because:
- Templates are pre-validated (no syntax errors)
- Data is JSON (validated before injection)
- Composition is deterministic (no AI)
"""

import logging
import re
from typing import Dict, List, Tuple, Optional

from .template_registry import get_template, TEMPLATE_REGISTRY, GoldenTemplate
from .data_generator import generate_all_component_data

logger = logging.getLogger(__name__)


# Component selection based on keywords
COMPONENT_KEYWORDS = {
    "hero": ["welcome", "home", "landing", "main", "header"],
    "navigation": ["nav", "menu", "header"],
    "features": ["feature", "benefit", "offer", "advantage"],
    "services": ["service", "product", "what we do", "offer"],
    "about": ["about", "who we are", "our story", "team"],
    "contact": ["contact", "reach", "email", "phone", "message"],
    "testimonials": ["testimonial", "review", "client", "customer says"],
    "footer": ["footer", "copyright"],
}

# Industry to hero variant mapping for design variety
INDUSTRY_HERO_VARIANTS = {
    "restaurant": "photo_overlay",    # Full-width food photo with floating card
    "cafe": "photo_overlay",
    "bakery": "photo_overlay",
    "food": "photo_overlay",
    "spa": "photo_overlay",
    "wellness": "photo_overlay",
    "salon": "photo_overlay",
    "saas": "split",                  # Text left, image right
    "software": "split",
    "tech": "split",
    "startup": "split",
    "app": "split",
    "portfolio": "minimal",           # Clean text-only
    "artist": "minimal",
    "designer": "minimal",
    "photographer": "minimal",
    "agency": "video",                # Animated zoom background
    "creative": "video",
    "studio": "video",
    "gaming": "video",
    "ecommerce": "cards",             # Feature cards below headline
    "shop": "cards",
    "store": "cards",
    "retail": "cards",
    "vinyl": "cards",                 # Record stores use cards for featured albums
    "music": "cards",
    "kids": "cards",                  # Feature cards for activities/services
    "children": "cards",
    "architecture": "minimal",        # Clean minimalist for architecture
    "interior": "photo_overlay",
}


def detect_hero_variant(prompt: str) -> str:
    """
    Detect the best hero variant based on industry keywords in the prompt.

    Returns a variant name: centered, split, minimal, photo_overlay, cards, video
    """
    prompt_lower = prompt.lower()

    # Priority order: Check more specific/longer keywords first
    # This prevents "tech" in "TechGear" from matching before "ecommerce"
    priority_keywords = [
        # Ecommerce/shop variants (high priority - check first)
        ("ecommerce", "cards"),
        ("e-commerce", "cards"),
        ("shop", "cards"),
        ("store", "cards"),
        ("retail", "cards"),
        # Food/hospitality (photo overlay)
        ("restaurant", "photo_overlay"),
        ("cafe", "photo_overlay"),
        ("bakery", "photo_overlay"),
        ("spa", "photo_overlay"),
        ("wellness", "photo_overlay"),
        ("salon", "photo_overlay"),
        # Creative/agency (video)
        ("agency", "video"),
        ("creative", "video"),
        ("studio", "video"),
        ("gaming", "video"),
        # Portfolio/design (minimal)
        ("portfolio", "minimal"),
        ("designer", "minimal"),
        ("photographer", "minimal"),
        ("artist", "minimal"),
        ("architecture", "minimal"),
        # SaaS/tech (split) - check AFTER ecommerce
        ("saas", "split"),
        ("software", "split"),
        ("startup", "split"),
        ("platform", "split"),
        # Music/entertainment (cards)
        ("vinyl", "cards"),
        ("music", "cards"),
        ("records", "cards"),
        ("kids", "cards"),
        ("children", "cards"),
    ]

    for keyword, variant in priority_keywords:
        # Use word boundary matching to avoid partial matches like "tech" in "TechGear"
        import re
        if re.search(rf'\b{re.escape(keyword)}\b', prompt_lower):
            logger.info(f"[COMPOSE] Detected industry '{keyword}' -> hero variant '{variant}'")
            return variant

    # Default to centered (classic gradient hero)
    return "centered"


def analyze_request(prompt: str) -> List[str]:
    """
    Analyze user request to determine which components are needed.

    Returns list of component types to include.
    """
    prompt_lower = prompt.lower()
    needed = set()

    # Always include these
    needed.add("navigation")
    needed.add("hero")
    needed.add("footer")

    # Check for specific component keywords
    for component, keywords in COMPONENT_KEYWORDS.items():
        if any(kw in prompt_lower for kw in keywords):
            needed.add(component)

    # Business website patterns - add common sections
    business_keywords = ["business", "company", "service", "professional", "website"]
    if any(kw in prompt_lower for kw in business_keywords):
        needed.update(["features", "about", "contact"])

    # Service-based business
    if "service" in prompt_lower or "offer" in prompt_lower:
        needed.add("services")

    # If testimonials mentioned or "trust" / "reviews"
    if any(kw in prompt_lower for kw in ["testimonial", "review", "trust", "client"]):
        needed.add("testimonials")

    # Order components logically
    order = ["navigation", "hero", "features", "services", "about", "testimonials", "contact", "footer"]
    result = [c for c in order if c in needed]

    logger.info(f"[COMPOSE] Analyzed request, need components: {result}")
    return result


def compose_from_templates(
    prompt: str,
    components: List[str] = None
) -> Tuple[str, Dict]:
    """
    Compose a complete app from golden templates.

    Args:
        prompt: User's request describing the business
        components: Optional list of specific components to include

    Returns:
        Tuple of (app_code, metadata)
    """
    # Step 1: Determine components
    if components is None:
        components = analyze_request(prompt)

    logger.info(f"[COMPOSE] Building app with {len(components)} template components")

    # Step 2: Generate data for all components (single AI call)
    all_data = generate_all_component_data(prompt, components)

    # Extract business info for consistency
    nav_data = all_data.get("navigation", {})
    business_name = nav_data.get("business_name", "Our Business")

    # Ensure footer has consistent business name
    if "footer" in all_data:
        all_data["footer"]["business_name"] = business_name

    # Step 3: Render each template with its data
    rendered_components = []
    metadata = {
        "components_used": [],
        "template_system": True,
    }

    # Detect hero variant based on industry
    hero_variant = detect_hero_variant(prompt)
    metadata["hero_variant"] = hero_variant

    for comp_type in components:
        # Use industry-specific variant for hero, default for others
        if comp_type == "hero":
            template = get_template(comp_type, variant=hero_variant)
            logger.info(f"[COMPOSE] Using hero variant: {hero_variant}")
        else:
            template = get_template(comp_type)
        if template:
            data = all_data.get(comp_type, {})
            rendered = template.render(data)
            rendered_components.append({
                "type": comp_type,
                "code": rendered,
                "template": template.name,
            })
            metadata["components_used"].append(template.name)
            logger.info(f"[COMPOSE] Rendered {comp_type} using template {template.name}")
        else:
            logger.warning(f"[COMPOSE] No template for {comp_type}, skipping")

    # Step 4: Compose into final App.jsx
    app_code = _compose_app_jsx(rendered_components, business_name)

    # Step 5: Generate AI images if user requested specific images
    app_code, generated_images = _generate_ai_images(app_code, prompt)
    metadata["generated_images"] = generated_images

    metadata["code_size"] = len(app_code)
    metadata["line_count"] = app_code.count("\n")

    logger.info(f"[COMPOSE] Template composition complete: {metadata['line_count']} lines, {len(generated_images)} AI images")

    return app_code, metadata


def _extract_image_descriptions(prompt: str, max_images: int = 4) -> List[str]:
    """
    Extract user-specified image descriptions from the prompt.

    Looks for phrases like:
    - "AI generated image of..."
    - "image where there is..."
    - "picture of..."
    - "drawing of..."
    - "artwork of..."
    - "illustration of..."
    - "example image", "example drawing", etc.

    Returns list of image descriptions (up to max_images).
    """
    # Patterns for image requests - case-insensitive matching
    # Order matters: more specific patterns first
    patterns = [
        # AI-generated with description
        r'AI[- ]generated (?:image|picture|photo|drawing|artwork|illustration) (?:of|where|with|showing) ([^.!?,]+)',
        # "example X of something"
        r'example (?:image|picture|photo|drawing|artwork|illustration) (?:of|where|with|showing) ([^.!?,]+)',
        # "add/create example X of something"
        r'(?:add|include|create|generate|show) (?:an? )?(?:example )?(?:image|picture|photo|drawing|artwork|illustration) (?:of|where|with|showing) ([^.!?,]+)',
        # Standard "X of Y" patterns
        r'(?:image|picture|photo) (?:of|where|with|showing) ([^.!?,]+)',
        r'(?:drawing|artwork|illustration) (?:of|where|with|showing) ([^.!?,]+)',
        # Standalone requests like "add example drawing" - capture the image type as description hint
        r'(?:add|include|create|generate|show) (?:an? )?(?:at least (?:one|two|three|four|\d+) )?(?:example )?(drawing|artwork|illustration|image|picture|photo)s?(?:\s|$|,)',
    ]

    descriptions = []
    seen = set()  # Avoid duplicates

    for pattern in patterns:
        # Case-insensitive search on original prompt
        for match in re.finditer(pattern, prompt, re.IGNORECASE):
            description = match.group(1).strip()
            # Clean up the description
            description = description.rstrip('.,!?')
            description_lower = description.lower()

            # For standalone image type matches, enhance the description
            if description_lower in ('drawing', 'artwork', 'illustration', 'image', 'picture', 'photo'):
                # Use the full context as description hint for AI image generator
                description = f"professional {description_lower} for this website"

            # Only if meaningful and not duplicate (min length 3 for short descriptions)
            if len(description) >= 3 and description_lower not in seen:
                descriptions.append(description)
                seen.add(description_lower)

                if len(descriptions) >= max_images:
                    return descriptions

    return descriptions


def _extract_image_description(prompt: str) -> Optional[str]:
    """
    Extract user-specified image description from the prompt.

    Legacy function - returns first description found.
    For multiple images, use _extract_image_descriptions().
    """
    descriptions = _extract_image_descriptions(prompt, max_images=1)
    return descriptions[0] if descriptions else None


def _generate_ai_images(app_code: str, prompt: str) -> Tuple[str, Dict[str, bytes]]:
    """
    Generate AI images for user-specified image requests.

    Replaces picsum.photos URLs with AI-generated images.
    Returns updated code and dict of {filename: image_bytes}.
    """
    # Check if user requested specific images
    image_description = _extract_image_description(prompt)

    if not image_description:
        logger.info("[COMPOSE] No specific image request found in prompt")
        return app_code, {}

    logger.info(f"[COMPOSE] User requested image: '{image_description}'")

    try:
        from apps.ai_engine.image_generator import get_image_generator

        image_gen = get_image_generator()

        if not image_gen.use_ai:
            logger.warning("[COMPOSE] No OpenAI API key - cannot generate AI images")
            return app_code, {}

        # Find the hero/main picsum URL and replace it with AI image
        picsum_pattern = r"https://picsum\.photos/seed/([^/]+)/(\d+)/(\d+)"
        match = re.search(picsum_pattern, app_code)

        if not match:
            logger.info("[COMPOSE] No picsum URLs found to replace")
            return app_code, {}

        seed = match.group(1)
        width = int(match.group(2))
        height = int(match.group(3))

        # Generate the AI image with user's description
        filename, image_bytes = image_gen.generate_image(
            prompt=image_description,
            width=width,
            height=height,
            filename="hero-image.jpg"
        )

        # Replace the first picsum URL with reference to generated image
        old_url = match.group(0)
        new_url = f"/images/{filename}"
        app_code = app_code.replace(old_url, new_url, 1)

        logger.info(f"[COMPOSE] Generated AI image: {filename} ({len(image_bytes)} bytes)")

        return app_code, {filename: image_bytes}

    except Exception as e:
        logger.error(f"[COMPOSE] AI image generation failed: {e}")
        # Don't fail the whole build - just skip AI images
        return app_code, {}


def _compose_app_jsx(components: List[Dict], business_name: str) -> str:
    """
    Compose rendered components into final App.jsx.

    This is deterministic - no AI call needed.
    """
    # Collect all component code
    component_definitions = []
    component_types = []

    for comp in components:
        component_definitions.append(comp["code"])
        component_types.append(comp["type"])

    # Build navigation items from components
    nav_views = []
    for t in component_types:
        if t not in ["navigation", "footer"]:
            label = t.title()
            nav_views.append(f'{{ id: "{t}", label: "{label}" }}')

    nav_items_str = ", ".join(nav_views) if nav_views else '{ id: "home", label: "Home" }'

    # Build view switching
    view_cases = []
    for t in component_types:
        if t == "navigation":
            continue
        elif t == "footer":
            continue
        elif t == "hero":
            view_cases.append(f'''
        {{currentView === "hero" && <HeroSection onNavigate={{handleNavigate}} />}}''')
        elif t == "features":
            view_cases.append(f'''
        {{currentView === "features" && <FeaturesSection />}}''')
        elif t == "services":
            view_cases.append(f'''
        {{currentView === "services" && <ServicesSection />}}''')
        elif t == "about":
            view_cases.append(f'''
        {{currentView === "about" && <AboutSection />}}''')
        elif t == "testimonials":
            view_cases.append(f'''
        {{currentView === "testimonials" && <TestimonialsSection />}}''')
        elif t == "contact":
            view_cases.append(f'''
        {{currentView === "contact" && <ContactSection />}}''')

    view_cases_str = "".join(view_cases)

    # Check if we have specific components
    has_nav = "navigation" in component_types
    has_footer = "footer" in component_types

    # Compose final app
    # NOTE: Include "LIBRARY COMPONENTS" marker so Vercel uses ZERO-TRANSFORM
    # This prevents regex corruption of the pre-validated template code
    app_code = f'''// LIBRARY COMPONENTS - Golden Templates (pre-validated, do not transform)
{"".join(component_definitions)}

// Main App Component
function App() {{
  const [currentView, setCurrentView] = React.useState("hero");

  const handleNavigate = (viewId) => {{
    setCurrentView(viewId);
    window.scrollTo({{ top: 0, behavior: "smooth" }});
  }};

  return (
    <div className="min-h-screen bg-white">
      {f'<Navigation currentView={{currentView}} onNavigate={{handleNavigate}} />' if has_nav else ''}

      <main>
        {view_cases_str}
      </main>

      {f'<FooterSection />' if has_footer else ''}
    </div>
  );
}}

export default App;
'''

    return app_code


def quick_compose(prompt: str) -> str:
    """
    Quick composition for simple requests.

    Returns just the code (no metadata).
    """
    code, _ = compose_from_templates(prompt)
    return code
