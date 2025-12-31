#!/usr/bin/env python
"""
Generate all components needed for 19 Lovable-style use cases.

This script:
1. Defines all component specifications
2. Generates code for each using Opus 4.5
3. Saves to Faibric's code library
"""

import os
import sys
import django

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'faibric_backend.settings')
django.setup()

import anthropic
from django.conf import settings
from apps.code_library.models import LibraryItem, LibraryCategory
from apps.ai_engine.models_config import CODE_MODEL

client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

# Component specifications for all 19 use cases
COMPONENTS_TO_GENERATE = [
    # Dashboard Components
    {
        "name": "Metric Card",
        "slug": "metric-card",
        "item_type": "component",
        "description": "KPI metric card showing value, change percentage, trend arrow. Used in all dashboards.",
        "keywords": ["metric", "kpi", "dashboard", "stats", "analytics"]
    },
    {
        "name": "Stats Row",
        "slug": "stats-row",
        "item_type": "component",
        "description": "Horizontal row of multiple KPI metrics. Used in dashboard headers.",
        "keywords": ["stats", "metrics", "row", "dashboard", "overview"]
    },
    {
        "name": "Chart - Line",
        "slug": "chart-line",
        "item_type": "component",
        "description": "Line chart for time series data visualization. Uses SVG, no external libraries.",
        "keywords": ["chart", "line", "graph", "timeseries", "analytics"]
    },
    {
        "name": "Chart - Bar",
        "slug": "chart-bar",
        "item_type": "component",
        "description": "Bar chart for comparing values. Uses SVG, no external libraries.",
        "keywords": ["chart", "bar", "graph", "comparison", "analytics"]
    },
    {
        "name": "Chart - Pie",
        "slug": "chart-pie",
        "item_type": "component",
        "description": "Pie/donut chart for showing distribution. Uses SVG, no external libraries.",
        "keywords": ["chart", "pie", "donut", "distribution", "analytics"]
    },
    {
        "name": "Sidebar - Dashboard",
        "slug": "sidebar-dashboard",
        "item_type": "component",
        "description": "Sidebar navigation for dashboards with icons, sections, and active states.",
        "keywords": ["sidebar", "navigation", "dashboard", "menu"]
    },
    {
        "name": "Progress Bar",
        "slug": "progress-bar",
        "item_type": "component",
        "description": "Visual progress indicator with percentage, label, and color variants.",
        "keywords": ["progress", "bar", "loading", "status", "indicator"]
    },
    {
        "name": "Badge - Status",
        "slug": "badge-status",
        "item_type": "component",
        "description": "Status badge/tag with color coding for different states (success, warning, error, info).",
        "keywords": ["badge", "status", "tag", "label", "indicator"]
    },
    {
        "name": "Alert - Notification",
        "slug": "alert-notification",
        "item_type": "component",
        "description": "Alert/notification component with icon, message, dismissable, and variants.",
        "keywords": ["alert", "notification", "message", "warning", "error"]
    },
    # Data Components
    {
        "name": "Data Table - Advanced",
        "slug": "data-table-advanced",
        "item_type": "component",
        "description": "Advanced data table with sorting, filtering, pagination. For all internal tools.",
        "keywords": ["table", "data", "grid", "sorting", "pagination", "filter"]
    },
    {
        "name": "Filter Panel",
        "slug": "filter-panel",
        "item_type": "component",
        "description": "Filter controls panel with dropdowns, date range, search. For internal tools.",
        "keywords": ["filter", "search", "panel", "controls", "dropdown"]
    },
    {
        "name": "Search Bar - Advanced",
        "slug": "search-bar-advanced",
        "item_type": "component",
        "description": "Search bar with autocomplete suggestions and filters.",
        "keywords": ["search", "autocomplete", "suggestions", "input"]
    },
    # CRM Components
    {
        "name": "Contact Card",
        "slug": "contact-card",
        "item_type": "component",
        "description": "Contact/person card with avatar, name, role, contact info, and actions.",
        "keywords": ["contact", "person", "profile", "card", "crm"]
    },
    {
        "name": "Pipeline View",
        "slug": "pipeline-view",
        "item_type": "component",
        "description": "Kanban-style pipeline view for deals/opportunities. Drag and drop columns.",
        "keywords": ["pipeline", "kanban", "deals", "crm", "sales", "stages"]
    },
    {
        "name": "Activity Feed",
        "slug": "activity-feed",
        "item_type": "component",
        "description": "Timeline/feed of activities with icons, timestamps, and descriptions.",
        "keywords": ["activity", "feed", "timeline", "history", "events"]
    },
    {
        "name": "Deal Card",
        "slug": "deal-card",
        "item_type": "component",
        "description": "Opportunity/deal card with value, stage, probability, and contact.",
        "keywords": ["deal", "opportunity", "card", "crm", "sales"]
    },
    # Event Management Components
    {
        "name": "Event Card",
        "slug": "event-card",
        "item_type": "component",
        "description": "Event display card with image, date, title, location, and registration.",
        "keywords": ["event", "card", "date", "registration", "calendar"]
    },
    {
        "name": "Calendar Grid",
        "slug": "calendar-grid",
        "item_type": "component",
        "description": "Monthly calendar grid view with events. Click to view/add events.",
        "keywords": ["calendar", "grid", "month", "events", "schedule"]
    },
    {
        "name": "Ticket Selector",
        "slug": "ticket-selector",
        "item_type": "component",
        "description": "Ticket type selector with prices, quantity, and total calculation.",
        "keywords": ["ticket", "selector", "pricing", "quantity", "event"]
    },
    {
        "name": "Attendee List",
        "slug": "attendee-list",
        "item_type": "component",
        "description": "List of event attendees with avatar, name, status, and actions.",
        "keywords": ["attendee", "list", "participants", "event", "rsvp"]
    },
    # Project Management Components
    {
        "name": "Task Card",
        "slug": "task-card",
        "item_type": "component",
        "description": "Kanban task card with title, assignee, due date, tags, and priority.",
        "keywords": ["task", "card", "kanban", "project", "todo"]
    },
    {
        "name": "Kanban Column",
        "slug": "kanban-column",
        "item_type": "component",
        "description": "Kanban board column with header, task count, and droppable area.",
        "keywords": ["kanban", "column", "board", "project", "workflow"]
    },
    {
        "name": "Team Avatars",
        "slug": "team-avatars",
        "item_type": "component",
        "description": "Stacked avatar group for team members with overflow indicator.",
        "keywords": ["avatar", "team", "stack", "members", "group"]
    },
    {
        "name": "Due Date Badge",
        "slug": "due-date-badge",
        "item_type": "component",
        "description": "Due date indicator with color coding for overdue/soon/future.",
        "keywords": ["due", "date", "badge", "deadline", "calendar"]
    },
    # Survey/Form Components
    {
        "name": "Question Builder",
        "slug": "question-builder",
        "item_type": "component",
        "description": "Survey question editor with type selector, options, and validation.",
        "keywords": ["question", "builder", "survey", "form", "editor"]
    },
    {
        "name": "Rating Scale",
        "slug": "rating-scale",
        "item_type": "component",
        "description": "Star/number rating input with hover effects and selection.",
        "keywords": ["rating", "stars", "scale", "feedback", "score"]
    },
    {
        "name": "Multiple Choice",
        "slug": "multiple-choice",
        "item_type": "component",
        "description": "Multiple choice question with radio/checkbox options and other field.",
        "keywords": ["choice", "options", "radio", "checkbox", "survey"]
    },
    # Internal Tools Components
    {
        "name": "Modal - Dialog",
        "slug": "modal-dialog",
        "item_type": "component",
        "description": "Modal popup dialog with header, content, actions, and overlay.",
        "keywords": ["modal", "dialog", "popup", "overlay", "window"]
    },
    {
        "name": "Tabs - Navigation",
        "slug": "tabs-navigation",
        "item_type": "component",
        "description": "Tab navigation component with active state and content panels.",
        "keywords": ["tabs", "navigation", "panels", "switch", "sections"]
    },
    {
        "name": "Accordion",
        "slug": "accordion",
        "item_type": "component",
        "description": "Collapsible accordion sections with open/close animation.",
        "keywords": ["accordion", "collapse", "expand", "faq", "sections"]
    },
    {
        "name": "Empty State",
        "slug": "empty-state",
        "item_type": "component",
        "description": "Empty state placeholder with icon, message, and action button.",
        "keywords": ["empty", "state", "placeholder", "no-data", "blank"]
    },
    {
        "name": "Loading Spinner",
        "slug": "loading-spinner",
        "item_type": "component",
        "description": "Loading indicator with spinner animation and optional text.",
        "keywords": ["loading", "spinner", "progress", "wait", "animation"]
    },
    {
        "name": "Export Button",
        "slug": "export-button",
        "item_type": "component",
        "description": "Export button with dropdown for format selection (CSV, PDF, Excel).",
        "keywords": ["export", "download", "button", "csv", "pdf"]
    },
]


def generate_component_code(spec):
    """Generate component code using Opus 4.5."""
    
    prompt = f"""
Generate a REUSABLE React TypeScript component for the following:

NAME: {spec['name']}
DESCRIPTION: {spec['description']}
KEYWORDS: {', '.join(spec['keywords'])}

REQUIREMENTS:
1. Self-contained component with TypeScript interfaces for props
2. Use Tailwind CSS for all styling
3. Include inline SVG icons where needed (no external icon libraries)
4. Export as default
5. Include brief comments explaining key parts
6. Make it visually polished and professional
7. Use sample/mock data if needed (hardcoded in component)
8. NO external dependencies except React
9. Use double quotes for all strings
10. Avoid contractions in text content

Return ONLY the component code (no markdown, no explanation).
"""

    try:
        response = client.messages.create(
            model=CODE_MODEL,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )
        
        code = response.content[0].text.strip()
        
        # Clean up markdown if present
        if code.startswith('```'):
            lines = code.split('\n')
            code = '\n'.join(lines[1:-1] if lines[-1] == '```' else lines[1:])
        
        # Sanitize code
        code = sanitize_code(code)
        
        return code
        
    except Exception as e:
        print(f"Error generating {spec['name']}: {e}")
        return None


def sanitize_code(code):
    """Fix common AI code generation mistakes."""
    if not code:
        return code
    
    # Smart/curly quotes to straight quotes
    replacements = {
        ''': "'",
        ''': "'",
        '"': '"',
        '"': '"',
        '—': '-',
        '–': '-',
        '…': '...',
        '\u00a0': ' ',
    }
    
    for bad, good in replacements.items():
        code = code.replace(bad, good)
    
    # Expand contractions
    contractions = {
        "I've": "I have", "I'm": "I am", "don't": "do not", 
        "doesn't": "does not", "won't": "will not", "can't": "cannot",
        "shouldn't": "should not", "couldn't": "could not", 
        "wouldn't": "would not", "it's": "it is", "that's": "that is",
        "what's": "what is", "there's": "there is"
    }
    
    for contraction, expanded in contractions.items():
        code = code.replace(contraction, expanded)
    
    return code


def save_to_library(spec, code):
    """Save component to the Faibric library."""
    
    # Check if already exists
    existing = LibraryItem.objects.filter(slug=spec['slug']).first()
    if existing:
        print(f"  Updating existing: {spec['name']}")
        existing.code = code
        existing.description = spec['description']
        existing.keywords = spec['keywords']
        existing.save()
        return existing.id
    
    # Create new
    item = LibraryItem.objects.create(
        name=spec['name'],
        slug=spec['slug'],
        item_type=spec['item_type'],
        language='typescript',
        code=code,
        description=spec['description'],
        keywords=spec['keywords'],
        tags=['generated', 'reusable', 'tailwind'],
        quality_score=0.85,
        usage_count=0,
        source='ai',
        is_active=True,
        is_public=True,
        is_deprecated=False,
        deprecation_note='',
        usage_example='',
        documentation='',
        embedding_model='',
        dependencies=[],
        source_url='',
    )
    
    print(f"  Created: {spec['name']} (ID: {item.id})")
    return item.id


def main():
    """Generate and save all components."""
    print("=" * 60)
    print("GENERATING LIBRARY COMPONENTS FOR 19 USE CASES")
    print("=" * 60)
    
    total = len(COMPONENTS_TO_GENERATE)
    success = 0
    failed = []
    
    for i, spec in enumerate(COMPONENTS_TO_GENERATE):
        print(f"\n[{i+1}/{total}] Generating: {spec['name']}")
        
        code = generate_component_code(spec)
        
        if code:
            save_to_library(spec, code)
            success += 1
            print(f"  ✓ Success ({len(code)} chars)")
        else:
            failed.append(spec['name'])
            print(f"  ✗ Failed")
    
    print("\n" + "=" * 60)
    print(f"COMPLETE: {success}/{total} components generated")
    if failed:
        print(f"FAILED: {', '.join(failed)}")
    print("=" * 60)
    
    # Show final library count
    count = LibraryItem.objects.filter(is_active=True).count()
    print(f"\nTotal library items: {count}")


if __name__ == '__main__':
    main()

