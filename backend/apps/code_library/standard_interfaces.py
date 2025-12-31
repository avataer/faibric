"""
Standard Component Interfaces

These are the pre-defined "contracts" for common component types.
Every component in the library should implement one of these interfaces.

INTERFACE CATEGORIES:
1. STRUCTURAL - Layout, Navigation, Footer
2. CONTENT - Cards, Tables, Lists, Charts
3. INTERACTIVE - Forms, Modals, Buttons
4. DATA - Data fetchers, placeholders
5. MARKETING - Hero, CTA, Pricing, Testimonials
"""

from typing import List, Tuple

from .connectors import (
    ComponentInterface,
    Connector,
    ConnectorType,
    DataSchema,
    EventSignature,
    StyleSlot,
    data_input,
    data_output,
    event_output,
    state_reader,
    state_writer,
    style_slot_connector,
)


# =============================================================================
# 1. STRUCTURAL COMPONENTS
# =============================================================================

LAYOUT_INTERFACE = ComponentInterface(
    component_type="layout",
    variant="*",
    version="1.0.0",
    
    inputs=[
        data_input(
            name="theme",
            typescript_type="Theme",
            required=False,
            description="Theme configuration",
            default={"mode": "light", "primaryColor": "#3B82F6"}
        ),
        data_input(
            name="sidebarCollapsed",
            typescript_type="boolean",
            required=False,
            description="Whether sidebar is collapsed",
            default=False
        ),
    ],
    
    outputs=[
        event_output(
            name="onThemeChange",
            params=[("theme", "Theme")],
            description="Emitted when theme changes"
        ),
    ],
    
    slots=["navigation", "main", "sidebar", "footer"],
    
    required_state=["currentView"],
    
    style_slots=[
        StyleSlot(
            name="container",
            description="Main layout container",
            default_classes="min-h-screen bg-gray-50 dark:bg-gray-900"
        ),
        StyleSlot(
            name="sidebar",
            description="Sidebar container",
            default_classes="w-64 bg-white dark:bg-gray-800 border-r"
        ),
        StyleSlot(
            name="main",
            description="Main content area",
            default_classes="flex-1 p-6"
        ),
    ],
    
    theme_tokens=["background", "surface", "border"],
)


NAVIGATION_INTERFACE = ComponentInterface(
    component_type="navigation",
    variant="*",
    version="1.0.0",
    
    inputs=[
        state_reader(
            name="currentView",
            typescript_type="string",
            description="Currently active view/page"
        ),
        data_input(
            name="items",
            typescript_type="NavItem[]",
            required=False,
            description="Navigation items - NO EMOJIS, use text labels only",
            example=[
                {"id": "dashboard", "label": "Dashboard"},
                {"id": "analytics", "label": "Analytics"},
                {"id": "settings", "label": "Settings"},
            ]
        ),
        data_input(
            name="user",
            typescript_type="User | null",
            required=False,
            description="Current user info"
        ),
    ],
    
    outputs=[
        event_output(
            name="onNavigate",
            params=[("viewId", "string")],
            description="Emitted when user clicks a nav item"
        ),
        event_output(
            name="onLogout",
            params=[],
            description="Emitted when user clicks logout"
        ),
    ],
    
    provided_state=["currentView"],
    
    style_slots=[
        StyleSlot(
            name="container",
            description="Navigation container",
            default_classes="flex flex-col h-full"
        ),
        StyleSlot(
            name="item",
            description="Navigation item",
            default_classes="px-4 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
        ),
        StyleSlot(
            name="itemActive",
            description="Active navigation item",
            default_classes="bg-blue-500 text-white"
        ),
    ],
    
    theme_tokens=["primary", "text", "textMuted"],
)


FOOTER_INTERFACE = ComponentInterface(
    component_type="footer",
    variant="*",
    version="1.0.0",
    
    inputs=[
        data_input(
            name="links",
            typescript_type="FooterLink[]",
            required=False,
            description="Footer navigation links"
        ),
        data_input(
            name="companyName",
            typescript_type="string",
            required=False,
            default="Company"
        ),
        data_input(
            name="socialLinks",
            typescript_type="SocialLink[]",
            required=False
        ),
    ],
    
    outputs=[],
    
    style_slots=[
        StyleSlot(
            name="container",
            description="Footer container",
            default_classes="bg-gray-900 text-white py-12"
        ),
    ],
)


# =============================================================================
# 2. CONTENT COMPONENTS
# =============================================================================

CARD_INTERFACE = ComponentInterface(
    component_type="card",
    variant="*",
    version="1.0.0",
    
    inputs=[
        data_input(
            name="title",
            typescript_type="string",
            required=True,
            description="Card title"
        ),
        data_input(
            name="subtitle",
            typescript_type="string",
            required=False
        ),
        data_input(
            name="image",
            typescript_type="string",
            required=False,
            description="Image URL"
        ),
        data_input(
            name="data",
            typescript_type="Record<string, any>",
            required=False,
            description="Card data payload"
        ),
        data_input(
            name="loading",
            typescript_type="boolean",
            required=False,
            default=False
        ),
    ],
    
    outputs=[
        event_output(
            name="onClick",
            params=[("data", "Record<string, any>")],
            description="Emitted when card is clicked"
        ),
        event_output(
            name="onAction",
            params=[("action", "string"), ("data", "Record<string, any>")],
            description="Emitted for card actions (edit, delete, etc.)"
        ),
    ],
    
    slots=["content", "actions", "badge"],
    
    style_slots=[
        StyleSlot(
            name="container",
            description="Card container",
            default_classes="bg-white dark:bg-gray-800 rounded-xl shadow-lg overflow-hidden"
        ),
        StyleSlot(
            name="header",
            description="Card header",
            default_classes="p-4 border-b dark:border-gray-700"
        ),
        StyleSlot(
            name="body",
            description="Card body",
            default_classes="p-4"
        ),
    ],
)


TABLE_INTERFACE = ComponentInterface(
    component_type="table",
    variant="*",
    version="1.0.0",
    
    inputs=[
        data_input(
            name="data",
            typescript_type="T[]",
            required=True,
            description="Array of items to display",
            placeholder_symbol="#"
        ),
        data_input(
            name="columns",
            typescript_type="Column[]",
            required=False,
            description="Column definitions (auto-detected if not provided)",
            example=[
                {"key": "name", "label": "Name", "type": "text"},
                {"key": "value", "label": "Value", "type": "currency"},
            ]
        ),
        data_input(
            name="loading",
            typescript_type="boolean",
            required=False,
            default=False
        ),
        data_input(
            name="sortable",
            typescript_type="boolean",
            required=False,
            default=True
        ),
        data_input(
            name="pagination",
            typescript_type="{ page: number; pageSize: number; total: number }",
            required=False
        ),
    ],
    
    outputs=[
        event_output(
            name="onRowClick",
            params=[("row", "T"), ("index", "number")],
            description="Emitted when a row is clicked"
        ),
        event_output(
            name="onSort",
            params=[("column", "string"), ("direction", "'asc' | 'desc'")],
            description="Emitted when sorting changes"
        ),
        event_output(
            name="onPageChange",
            params=[("page", "number")],
            description="Emitted when page changes"
        ),
    ],
    
    style_slots=[
        StyleSlot(
            name="container",
            description="Table container",
            default_classes="overflow-x-auto rounded-lg border dark:border-gray-700"
        ),
        StyleSlot(
            name="header",
            description="Table header",
            default_classes="bg-gray-50 dark:bg-gray-800"
        ),
        StyleSlot(
            name="row",
            description="Table row",
            default_classes="border-b dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700/50"
        ),
        StyleSlot(
            name="cell",
            description="Table cell",
            default_classes="px-4 py-3"
        ),
    ],
)


LIST_INTERFACE = ComponentInterface(
    component_type="list",
    variant="*",
    version="1.0.0",
    
    inputs=[
        data_input(
            name="items",
            typescript_type="ListItem[]",
            required=True,
            description="List items"
        ),
        data_input(
            name="loading",
            typescript_type="boolean",
            required=False,
            default=False
        ),
        data_input(
            name="emptyMessage",
            typescript_type="string",
            required=False,
            default="No items"
        ),
    ],
    
    outputs=[
        event_output(
            name="onItemClick",
            params=[("item", "ListItem"), ("index", "number")]
        ),
        event_output(
            name="onItemAction",
            params=[("action", "string"), ("item", "ListItem")]
        ),
    ],
    
    slots=["item", "empty"],
    
    style_slots=[
        StyleSlot(
            name="container",
            description="List container",
            default_classes="divide-y dark:divide-gray-700"
        ),
        StyleSlot(
            name="item",
            description="List item",
            default_classes="p-4 hover:bg-gray-50 dark:hover:bg-gray-800 cursor-pointer"
        ),
    ],
)


CHART_INTERFACE = ComponentInterface(
    component_type="chart",
    variant="*",
    version="1.0.0",
    
    inputs=[
        data_input(
            name="data",
            typescript_type="ChartData[]",
            required=True,
            description="Chart data points",
            placeholder_symbol="$",
            example=[
                {"label": "Jan", "value": 100},
                {"label": "Feb", "value": 200},
            ]
        ),
        data_input(
            name="type",
            typescript_type="'line' | 'bar' | 'pie' | 'area' | 'donut'",
            required=False,
            default="line"
        ),
        data_input(
            name="title",
            typescript_type="string",
            required=False
        ),
        data_input(
            name="loading",
            typescript_type="boolean",
            required=False,
            default=False
        ),
        data_input(
            name="colors",
            typescript_type="string[]",
            required=False,
            default=["#3B82F6", "#10B981", "#F59E0B", "#EF4444"]
        ),
    ],
    
    outputs=[
        event_output(
            name="onDataPointClick",
            params=[("point", "ChartData"), ("index", "number")]
        ),
        event_output(
            name="onLegendClick",
            params=[("series", "string")]
        ),
    ],
    
    style_slots=[
        StyleSlot(
            name="container",
            description="Chart container",
            default_classes="bg-white dark:bg-gray-800 rounded-xl p-4"
        ),
    ],
)


STATS_INTERFACE = ComponentInterface(
    component_type="stats",
    variant="*",
    version="1.0.0",
    
    inputs=[
        data_input(
            name="stats",
            typescript_type="StatItem[]",
            required=True,
            description="Statistics to display",
            placeholder_symbol="$",
            example=[
                {"label": "Revenue", "value": 50000, "change": 12.5, "format": "currency"},
                {"label": "Users", "value": 1234, "change": -5.2, "format": "number"},
            ]
        ),
        data_input(
            name="loading",
            typescript_type="boolean",
            required=False,
            default=False
        ),
        data_input(
            name="columns",
            typescript_type="number",
            required=False,
            default=4,
            description="Number of columns in grid"
        ),
    ],
    
    outputs=[
        event_output(
            name="onStatClick",
            params=[("stat", "StatItem")]
        ),
    ],
    
    style_slots=[
        StyleSlot(
            name="container",
            description="Stats grid container",
            default_classes="grid gap-4"
        ),
        StyleSlot(
            name="card",
            description="Individual stat card",
            default_classes="bg-white dark:bg-gray-800 rounded-xl p-6 shadow"
        ),
        StyleSlot(
            name="value",
            description="Stat value",
            default_classes="text-3xl font-bold"
        ),
        StyleSlot(
            name="change.positive",
            description="Positive change indicator",
            default_classes="text-green-500"
        ),
        StyleSlot(
            name="change.negative",
            description="Negative change indicator",
            default_classes="text-red-500"
        ),
    ],
)


# =============================================================================
# 3. INTERACTIVE COMPONENTS
# =============================================================================

FORM_INTERFACE = ComponentInterface(
    component_type="form",
    variant="*",
    version="1.0.0",
    
    inputs=[
        data_input(
            name="fields",
            typescript_type="FormField[]",
            required=False,
            description="Form field definitions",
            example=[
                {"name": "email", "label": "Email", "type": "email", "required": True},
                {"name": "password", "label": "Password", "type": "password", "required": True},
            ]
        ),
        data_input(
            name="initialValues",
            typescript_type="Record<string, any>",
            required=False,
            default={}
        ),
        data_input(
            name="loading",
            typescript_type="boolean",
            required=False,
            default=False
        ),
        data_input(
            name="submitLabel",
            typescript_type="string",
            required=False,
            default="Submit"
        ),
    ],
    
    outputs=[
        event_output(
            name="onSubmit",
            params=[("values", "Record<string, any>")],
            description="Emitted on form submission"
        ),
        event_output(
            name="onChange",
            params=[("field", "string"), ("value", "any")],
            description="Emitted when any field changes"
        ),
        event_output(
            name="onValidationError",
            params=[("errors", "Record<string, string>")]
        ),
    ],
    
    slots=["header", "footer", "actions"],
    
    style_slots=[
        StyleSlot(
            name="container",
            description="Form container",
            default_classes="space-y-4"
        ),
        StyleSlot(
            name="field",
            description="Form field wrapper",
            default_classes="space-y-1"
        ),
        StyleSlot(
            name="input",
            description="Input element",
            default_classes="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
        ),
        StyleSlot(
            name="label",
            description="Field label",
            default_classes="block text-sm font-medium text-gray-700 dark:text-gray-300"
        ),
        StyleSlot(
            name="error",
            description="Error message",
            default_classes="text-sm text-red-500"
        ),
    ],
)


MODAL_INTERFACE = ComponentInterface(
    component_type="modal",
    variant="*",
    version="1.0.0",
    
    inputs=[
        state_reader(
            name="isOpen",
            typescript_type="boolean",
            description="Whether modal is open"
        ),
        data_input(
            name="title",
            typescript_type="string",
            required=False
        ),
        data_input(
            name="size",
            typescript_type="'sm' | 'md' | 'lg' | 'xl' | 'full'",
            required=False,
            default="md"
        ),
        data_input(
            name="closeOnOverlay",
            typescript_type="boolean",
            required=False,
            default=True
        ),
    ],
    
    outputs=[
        event_output(
            name="onClose",
            params=[],
            description="Emitted when modal should close"
        ),
        event_output(
            name="onConfirm",
            params=[],
            description="Emitted on confirm action"
        ),
    ],
    
    slots=["content", "footer"],
    
    required_state=["isOpen"],
    
    style_slots=[
        StyleSlot(
            name="overlay",
            description="Modal backdrop",
            default_classes="fixed inset-0 bg-black/50 backdrop-blur-sm"
        ),
        StyleSlot(
            name="container",
            description="Modal container",
            default_classes="bg-white dark:bg-gray-800 rounded-xl shadow-2xl"
        ),
        StyleSlot(
            name="header",
            description="Modal header",
            default_classes="p-4 border-b dark:border-gray-700"
        ),
        StyleSlot(
            name="body",
            description="Modal body",
            default_classes="p-4"
        ),
    ],
)


BUTTON_INTERFACE = ComponentInterface(
    component_type="button",
    variant="*",
    version="1.0.0",
    
    inputs=[
        data_input(
            name="label",
            typescript_type="string",
            required=True
        ),
        data_input(
            name="variant",
            typescript_type="'primary' | 'secondary' | 'outline' | 'ghost' | 'danger'",
            required=False,
            default="primary"
        ),
        data_input(
            name="size",
            typescript_type="'sm' | 'md' | 'lg'",
            required=False,
            default="md"
        ),
        data_input(
            name="loading",
            typescript_type="boolean",
            required=False,
            default=False
        ),
        data_input(
            name="disabled",
            typescript_type="boolean",
            required=False,
            default=False
        ),
        data_input(
            name="icon",
            typescript_type="string",
            required=False
        ),
    ],
    
    outputs=[
        event_output(
            name="onClick",
            params=[],
            description="Emitted when button is clicked"
        ),
    ],
    
    style_slots=[
        StyleSlot(
            name="base",
            description="Base button styles",
            default_classes="inline-flex items-center justify-center font-medium rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2"
        ),
        StyleSlot(
            name="primary",
            description="Primary variant",
            default_classes="bg-blue-500 text-white hover:bg-blue-600 focus:ring-blue-500"
        ),
        StyleSlot(
            name="secondary",
            description="Secondary variant",
            default_classes="bg-gray-100 text-gray-900 hover:bg-gray-200 focus:ring-gray-500"
        ),
    ],
)


# =============================================================================
# 4. DATA COMPONENTS
# =============================================================================

DATA_FETCHER_INTERFACE = ComponentInterface(
    component_type="data_fetcher",
    variant="*",
    version="1.0.0",
    
    inputs=[
        data_input(
            name="endpoint",
            typescript_type="string",
            required=True,
            description="API endpoint to fetch from",
            example="/simple/price?ids=bitcoin&vs_currencies=usd"
        ),
        data_input(
            name="service",
            typescript_type="'coingecko' | 'yahoo_finance' | 'restcountries' | 'custom'",
            required=True,
            description="Gateway service to use"
        ),
        data_input(
            name="refreshInterval",
            typescript_type="number",
            required=False,
            default=0,
            description="Auto-refresh interval in ms (0 = no refresh)"
        ),
        data_input(
            name="projectId",
            typescript_type="string",
            required=False,
            description="Project ID for customer API key lookup"
        ),
    ],
    
    outputs=[
        data_output(
            name="data",
            typescript_type="T",
            description="Fetched data"
        ),
        state_writer(
            name="loading",
            typescript_type="boolean",
            description="Loading state"
        ),
        state_writer(
            name="error",
            typescript_type="Error | null",
            description="Error state"
        ),
    ],
    
    provided_state=["loading", "error"],
)


DATA_PLACEHOLDER_INTERFACE = ComponentInterface(
    component_type="data_placeholder",
    variant="*",
    version="1.0.0",
    
    inputs=[
        data_input(
            name="symbol",
            typescript_type="string",
            required=False,
            default="$",
            description="Symbol to show before placeholder (e.g., '$', '€', '%')"
        ),
        data_input(
            name="width",
            typescript_type="string",
            required=False,
            default="4rem"
        ),
    ],
    
    outputs=[
        event_output(
            name="onActivate",
            params=[],
            description="Emitted when 'Turn On Real Values' is clicked"
        ),
    ],
    
    style_slots=[
        StyleSlot(
            name="container",
            description="Placeholder container",
            default_classes="inline-flex items-center gap-2"
        ),
        StyleSlot(
            name="value",
            description="Placeholder value",
            default_classes="text-gray-400 font-mono bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded"
        ),
        StyleSlot(
            name="link",
            description="Activation link",
            default_classes="text-xs text-blue-500 hover:text-blue-700 underline cursor-pointer"
        ),
    ],
)


# =============================================================================
# 5. MARKETING COMPONENTS
# =============================================================================

HERO_INTERFACE = ComponentInterface(
    component_type="hero",
    variant="*",
    version="1.0.0",
    
    inputs=[
        data_input(
            name="headline",
            typescript_type="string",
            required=True
        ),
        data_input(
            name="subheadline",
            typescript_type="string",
            required=False
        ),
        data_input(
            name="backgroundImage",
            typescript_type="string",
            required=False
        ),
        data_input(
            name="ctaLabel",
            typescript_type="string",
            required=False,
            default="Get Started"
        ),
        data_input(
            name="ctaSecondaryLabel",
            typescript_type="string",
            required=False
        ),
    ],
    
    outputs=[
        event_output(
            name="onCtaClick",
            params=[]
        ),
        event_output(
            name="onSecondaryCtaClick",
            params=[]
        ),
    ],
    
    slots=["media", "badge"],
    
    style_slots=[
        StyleSlot(
            name="container",
            description="Hero container",
            default_classes="relative min-h-[600px] flex items-center justify-center"
        ),
        StyleSlot(
            name="content",
            description="Content wrapper",
            default_classes="text-center max-w-4xl mx-auto px-6"
        ),
        StyleSlot(
            name="headline",
            description="Headline text",
            default_classes="text-5xl md:text-7xl font-bold tracking-tight"
        ),
    ],
)


CTA_INTERFACE = ComponentInterface(
    component_type="cta",
    variant="*",
    version="1.0.0",
    
    inputs=[
        data_input(
            name="headline",
            typescript_type="string",
            required=True
        ),
        data_input(
            name="description",
            typescript_type="string",
            required=False
        ),
        data_input(
            name="buttonLabel",
            typescript_type="string",
            required=False,
            default="Get Started"
        ),
    ],
    
    outputs=[
        event_output(
            name="onClick",
            params=[]
        ),
    ],
    
    style_slots=[
        StyleSlot(
            name="container",
            description="CTA container",
            default_classes="bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl p-12 text-center text-white"
        ),
    ],
)


PRICING_INTERFACE = ComponentInterface(
    component_type="pricing",
    variant="*",
    version="1.0.0",
    
    inputs=[
        data_input(
            name="plans",
            typescript_type="PricingPlan[]",
            required=True,
            placeholder_symbol="$",
            example=[
                {"name": "Basic", "price": 9, "features": ["Feature 1", "Feature 2"]},
                {"name": "Pro", "price": 29, "features": ["All Basic", "Feature 3"], "popular": True},
            ]
        ),
        data_input(
            name="billingPeriod",
            typescript_type="'monthly' | 'yearly'",
            required=False,
            default="monthly"
        ),
    ],
    
    outputs=[
        event_output(
            name="onSelectPlan",
            params=[("plan", "PricingPlan")]
        ),
        event_output(
            name="onBillingChange",
            params=[("period", "'monthly' | 'yearly'")]
        ),
    ],
    
    style_slots=[
        StyleSlot(
            name="container",
            description="Pricing container",
            default_classes="grid md:grid-cols-3 gap-8"
        ),
        StyleSlot(
            name="card",
            description="Plan card",
            default_classes="bg-white dark:bg-gray-800 rounded-2xl p-8 shadow-lg"
        ),
        StyleSlot(
            name="popular",
            description="Popular plan highlight",
            default_classes="ring-2 ring-blue-500 scale-105"
        ),
    ],
)


TESTIMONIAL_INTERFACE = ComponentInterface(
    component_type="testimonial",
    variant="*",
    version="1.0.0",
    
    inputs=[
        data_input(
            name="testimonials",
            typescript_type="Testimonial[]",
            required=True,
            example=[
                {"quote": "Amazing product!", "author": "John", "role": "CEO", "avatar": "url"},
            ]
        ),
        data_input(
            name="autoplay",
            typescript_type="boolean",
            required=False,
            default=True
        ),
    ],
    
    outputs=[
        event_output(
            name="onTestimonialClick",
            params=[("testimonial", "Testimonial")]
        ),
    ],
    
    style_slots=[
        StyleSlot(
            name="container",
            description="Testimonial container",
            default_classes="bg-gray-50 dark:bg-gray-900 py-16"
        ),
        StyleSlot(
            name="quote",
            description="Quote text",
            default_classes="text-2xl italic text-gray-700 dark:text-gray-300"
        ),
    ],
)


FEATURE_INTERFACE = ComponentInterface(
    component_type="feature",
    variant="*",
    version="1.0.0",
    
    inputs=[
        data_input(
            name="features",
            typescript_type="Feature[]",
            required=True,
            example=[
                {"title": "Fast", "description": "Lightning fast", "icon": "[CRITICAL]"},
            ]
        ),
        data_input(
            name="columns",
            typescript_type="number",
            required=False,
            default=3
        ),
    ],
    
    outputs=[],
    
    style_slots=[
        StyleSlot(
            name="container",
            description="Features grid",
            default_classes="grid md:grid-cols-3 gap-8"
        ),
        StyleSlot(
            name="card",
            description="Feature card",
            default_classes="text-center p-6"
        ),
        StyleSlot(
            name="icon",
            description="Feature icon",
            default_classes="text-4xl mb-4"
        ),
    ],
)


GALLERY_INTERFACE = ComponentInterface(
    component_type="gallery",
    variant="*",
    version="1.0.0",
    
    inputs=[
        data_input(
            name="images",
            typescript_type="GalleryImage[]",
            required=True,
            example=[
                {"src": "url", "alt": "Image 1", "caption": "Beautiful sunset"},
            ]
        ),
        data_input(
            name="columns",
            typescript_type="number",
            required=False,
            default=3
        ),
        data_input(
            name="lightbox",
            typescript_type="boolean",
            required=False,
            default=True
        ),
    ],
    
    outputs=[
        event_output(
            name="onImageClick",
            params=[("image", "GalleryImage"), ("index", "number")]
        ),
    ],
    
    style_slots=[
        StyleSlot(
            name="container",
            description="Gallery grid",
            default_classes="grid gap-4"
        ),
        StyleSlot(
            name="image",
            description="Image wrapper",
            default_classes="aspect-square overflow-hidden rounded-lg"
        ),
    ],
)


# =============================================================================
# INTERFACE REGISTRY
# =============================================================================

INTERFACE_REGISTRY = {
    # Structural
    "layout": LAYOUT_INTERFACE,
    "navigation": NAVIGATION_INTERFACE,
    "footer": FOOTER_INTERFACE,
    
    # Content
    "card": CARD_INTERFACE,
    "table": TABLE_INTERFACE,
    "list": LIST_INTERFACE,
    "chart": CHART_INTERFACE,
    "stats": STATS_INTERFACE,
    
    # Interactive
    "form": FORM_INTERFACE,
    "modal": MODAL_INTERFACE,
    "button": BUTTON_INTERFACE,
    
    # Data
    "data_fetcher": DATA_FETCHER_INTERFACE,
    "data_placeholder": DATA_PLACEHOLDER_INTERFACE,
    
    # Marketing
    "hero": HERO_INTERFACE,
    "cta": CTA_INTERFACE,
    "pricing": PRICING_INTERFACE,
    "testimonial": TESTIMONIAL_INTERFACE,
    "feature": FEATURE_INTERFACE,
    "gallery": GALLERY_INTERFACE,
}


# =============================================================================
# INTERFACE CACHE (Optimization #3)
# =============================================================================

from functools import lru_cache
from typing import Tuple

# Cache for cloned interfaces - avoids repeated object creation
_interface_cache: dict = {}

def _get_cache_key(component_type: str, variant: str) -> str:
    """Generate cache key for interface lookup."""
    return f"{component_type}:{variant}"


def get_interface(component_type: str, variant: str = "*") -> ComponentInterface:
    """
    Get the standard interface for a component type.
    
    Uses LRU cache to avoid repeated cloning of interface objects.
    Cache is invalidated only on server restart.
    """
    cache_key = _get_cache_key(component_type, variant)
    
    # Check cache first
    if cache_key in _interface_cache:
        return _interface_cache[cache_key]
    
    interface = INTERFACE_REGISTRY.get(component_type)
    if interface:
        # Clone and customize for variant
        cloned = ComponentInterface(
            component_type=component_type,
            variant=variant,
            version=interface.version,
            inputs=interface.inputs.copy(),
            outputs=interface.outputs.copy(),
            slots=interface.slots.copy(),
            required_state=interface.required_state.copy(),
            provided_state=interface.provided_state.copy(),
            requires_components=interface.requires_components.copy(),
            incompatible_with=interface.incompatible_with.copy(),
            style_slots=interface.style_slots.copy(),
            theme_tokens=interface.theme_tokens.copy(),
        )
        
        # Store in cache
        _interface_cache[cache_key] = cloned
        return cloned
    
    return None


def get_interface_cached_count() -> int:
    """Get the number of cached interfaces (for monitoring)."""
    return len(_interface_cache)


def clear_interface_cache():
    """Clear the interface cache (for testing or cache invalidation)."""
    global _interface_cache
    _interface_cache = {}


def list_interfaces() -> List[str]:
    """List all available interface types."""
    return list(INTERFACE_REGISTRY.keys())

