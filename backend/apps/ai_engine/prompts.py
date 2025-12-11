"""
System prompts for AI generation
"""

ANALYZE_APP_PROMPT = """You are an expert software architect. Analyze the following request and determine what needs to be built.

IMPORTANT: This system can build ANYTHING - websites, web apps, dashboards, tools, games, calculators, forms, etc. Determine the appropriate structure based on what the user asks for.

User Request:
{user_prompt}

Analyze and extract:
1. Type of Product: What is being requested (website, web app, dashboard, tool, game, etc.)
2. Core Features: List all main features needed
3. Data Models: Identify entities/models needed (if any - some products don't need backend models)
4. Relationships: Define relationships between models (if applicable)
5. API Endpoints: List necessary API endpoints (if backend is needed - some products are purely frontend)
6. UI Components: List main UI components needed
7. Styling Requirements: Extract ANY color, font, layout, or visual requirements from the description

Provide your analysis in the following JSON format:
{{
    "product_type": "website|webapp|dashboard|tool|game|calculator|form|other",
    "app_name": "string",
    "features": ["feature1", "feature2", ...],
    "styling": {{
        "backgroundColor": "extracted color or default",
        "textColor": "extracted color or default",
        "fontFamily": "extracted font or default",
        "layout": "description of layout requirements"
    }},
    "models": [
        {{
            "name": "ModelName",
            "fields": [
                {{"name": "field_name", "type": "CharField", "options": {{"max_length": 100, "blank": true}}}},
                ...
            ]
        }}
    ],
    "relationships": [
        {{
            "from_model": "Model1",
            "to_model": "Model2",
            "type": "ForeignKey",
            "related_name": "model1s"
        }}
    ],
    "api_endpoints": [
        {{
            "path": "/api/resource/",
            "method": "GET",
            "description": "List all resources",
            "permissions": "AllowAny"
        }}
    ],
    "ui_components": [
        {{
            "name": "ComponentName",
            "type": "page|component",
            "route": "/path",
            "description": "What this component does - include ALL styling requirements and data needs"
        }}
    ]
}}

NOTE: For simple tools/calculators/games that don't need a database, set models and api_endpoints to empty arrays.
"""

GENERATE_DJANGO_MODEL_PROMPT = """Generate Django model code for the following specification:

Model Name: {model_name}
Fields: {fields}
Relationships: {relationships}

Generate complete Django model code with:
- Proper field types and validators
- String representation (__str__ method)
- Meta class with ordering if appropriate
- Docstrings

Return ONLY the Python code without any explanations or markdown formatting."""

GENERATE_DRF_SERIALIZER_PROMPT = """Generate Django REST Framework serializer for this model:

Model Name: {model_name}
Fields: {fields}

Generate complete DRF serializer code with:
- All necessary fields
- Read-only fields where appropriate
- Any custom validation needed
- Docstrings

Return ONLY the Python code without any explanations or markdown formatting."""

GENERATE_DRF_VIEW_PROMPT = """Generate Django REST Framework viewset for this resource:

Model Name: {model_name}
Endpoints: {endpoints}
Permissions: {permissions}

Generate complete DRF viewset code with:
- Appropriate viewset class (ModelViewSet, ReadOnlyModelViewSet, etc.)
- Query filtering if needed
- Custom actions if specified
- Permission classes
- Docstrings

Return ONLY the Python code without any explanations or markdown formatting."""

GENERATE_REACT_COMPONENT_PROMPT = """Generate a React TypeScript component with REAL CONTENT (NO PLACEHOLDERS):

Component Name: {component_name}
Type: {component_type}
Description: {description}
Data Fields: {data_fields}

CRITICAL REQUIREMENTS:
1. NO PLACEHOLDERS ALLOWED - Generate real, meaningful content with actual data
2. If the component displays a list, include at least 5-10 real items with full details
3. Use inline styles ONLY (no external CSS files, no Material-UI, no Tailwind imports)
4. Use functional components with hooks
5. Include proper TypeScript types/interfaces
6. Make it fully self-contained - no external dependencies except React
7. Respect any color/styling requirements mentioned in the description
8. IMPORTANT: Use proper JSX syntax - for template literals in JSX attributes, use {{}} not backticks
   WRONG: href=`mailto:${{email}}`
   RIGHT: href={{'mailto:' + email}} OR href="mailto:email@example.com"
9. Test all syntax - make sure it's valid TypeScript/JSX that will compile

Return ONLY the TypeScript/React code without any explanations or markdown formatting."""

REFINE_CODE_PROMPT = """Review and refine this code based on the user's feedback:

Original Code:
{original_code}

User Feedback:
{user_feedback}

Generate improved code that addresses the feedback while maintaining functionality.
Return ONLY the code without any explanations or markdown formatting."""

