from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.templates.models import Template


TEMPLATES = [
    # --- Internal Ops Dashboards (3) ---
    {
        "name": "Team Performance Tracker",
        "description": "Real-time dashboard for tracking team KPIs, sprint velocity, and individual performance metrics across departments.",
        "category": "internal_ops",
        "schema_template": {
            "models": {
                "Team": {
                    "fields": {
                        "id": "AutoField",
                        "name": "CharField(max_length=200)",
                        "department": "CharField(max_length=100)",
                        "created_at": "DateTimeField(auto_now_add=True)",
                    }
                },
                "Employee": {
                    "fields": {
                        "id": "AutoField",
                        "name": "CharField(max_length=200)",
                        "email": "EmailField(unique=True)",
                        "role": "CharField(max_length=100)",
                        "team": "ForeignKey(Team)",
                    }
                },
                "KPI": {
                    "fields": {
                        "id": "AutoField",
                        "employee": "ForeignKey(Employee)",
                        "metric_name": "CharField(max_length=200)",
                        "value": "DecimalField(max_digits=10, decimal_places=2)",
                        "target": "DecimalField(max_digits=10, decimal_places=2)",
                        "period": "DateField",
                    }
                },
            }
        },
        "api_template": {
            "endpoints": [
                {"method": "GET", "path": "/api/teams/", "description": "List all teams"},
                {"method": "GET", "path": "/api/teams/{id}/", "description": "Team detail with members"},
                {"method": "GET", "path": "/api/kpis/", "description": "List KPIs with filters"},
                {"method": "GET", "path": "/api/kpis/summary/", "description": "Aggregated KPI summary by team"},
                {"method": "POST", "path": "/api/kpis/", "description": "Record a new KPI entry"},
            ]
        },
        "ui_template": {
            "pages": ["Dashboard", "Teams", "Employee Detail"],
            "components": [
                {"name": "KPICard", "type": "stat-card", "props": ["metric_name", "value", "target", "trend"]},
                {"name": "TeamTable", "type": "data-table", "props": ["teams", "sortable", "filterable"]},
                {"name": "PerformanceChart", "type": "bar-chart", "props": ["data", "period", "groupBy"]},
                {"name": "SprintVelocity", "type": "line-chart", "props": ["sprints", "velocity"]},
            ],
            "layout": "sidebar",
        },
    },
    {
        "name": "Inventory Operations Hub",
        "description": "Internal dashboard for warehouse inventory management, stock levels, reorder alerts, and supplier tracking.",
        "category": "internal_ops",
        "schema_template": {
            "models": {
                "Warehouse": {
                    "fields": {
                        "id": "AutoField",
                        "name": "CharField(max_length=200)",
                        "location": "CharField(max_length=300)",
                    }
                },
                "Product": {
                    "fields": {
                        "id": "AutoField",
                        "sku": "CharField(max_length=50, unique=True)",
                        "name": "CharField(max_length=200)",
                        "category": "CharField(max_length=100)",
                    }
                },
                "StockLevel": {
                    "fields": {
                        "id": "AutoField",
                        "product": "ForeignKey(Product)",
                        "warehouse": "ForeignKey(Warehouse)",
                        "quantity": "IntegerField",
                        "reorder_point": "IntegerField",
                        "updated_at": "DateTimeField(auto_now=True)",
                    }
                },
                "Supplier": {
                    "fields": {
                        "id": "AutoField",
                        "name": "CharField(max_length=200)",
                        "contact_email": "EmailField",
                        "lead_time_days": "IntegerField",
                    }
                },
            }
        },
        "api_template": {
            "endpoints": [
                {"method": "GET", "path": "/api/warehouses/", "description": "List warehouses"},
                {"method": "GET", "path": "/api/products/", "description": "List products with stock levels"},
                {"method": "GET", "path": "/api/stock/low/", "description": "Products below reorder point"},
                {"method": "POST", "path": "/api/stock/adjust/", "description": "Adjust stock quantity"},
                {"method": "GET", "path": "/api/suppliers/", "description": "List suppliers"},
            ]
        },
        "ui_template": {
            "pages": ["Stock Overview", "Warehouses", "Suppliers", "Alerts"],
            "components": [
                {"name": "StockLevelGauge", "type": "gauge-chart", "props": ["current", "reorder_point", "max"]},
                {"name": "ProductTable", "type": "data-table", "props": ["products", "searchable", "filterable"]},
                {"name": "AlertBanner", "type": "alert", "props": ["low_stock_items", "severity"]},
                {"name": "WarehouseMap", "type": "map-view", "props": ["locations", "stock_summary"]},
            ],
            "layout": "sidebar",
        },
    },
    # --- Client Portals (2) ---
    {
        "name": "Project Delivery Portal",
        "description": "Client-facing portal for project status tracking, deliverable reviews, milestone approvals, and communication.",
        "category": "client_portal",
        "schema_template": {
            "models": {
                "Client": {
                    "fields": {
                        "id": "AutoField",
                        "company_name": "CharField(max_length=200)",
                        "contact_name": "CharField(max_length=200)",
                        "email": "EmailField",
                    }
                },
                "Project": {
                    "fields": {
                        "id": "AutoField",
                        "client": "ForeignKey(Client)",
                        "name": "CharField(max_length=200)",
                        "status": "CharField(choices=[active,paused,completed])",
                        "start_date": "DateField",
                        "target_date": "DateField",
                    }
                },
                "Milestone": {
                    "fields": {
                        "id": "AutoField",
                        "project": "ForeignKey(Project)",
                        "title": "CharField(max_length=200)",
                        "due_date": "DateField",
                        "is_approved": "BooleanField(default=False)",
                    }
                },
                "Deliverable": {
                    "fields": {
                        "id": "AutoField",
                        "milestone": "ForeignKey(Milestone)",
                        "title": "CharField(max_length=200)",
                        "file_url": "URLField",
                        "status": "CharField(choices=[pending,approved,rejected])",
                    }
                },
            }
        },
        "api_template": {
            "endpoints": [
                {"method": "GET", "path": "/api/projects/", "description": "List client projects"},
                {"method": "GET", "path": "/api/projects/{id}/milestones/", "description": "Project milestones"},
                {"method": "GET", "path": "/api/deliverables/{id}/", "description": "Deliverable detail"},
                {"method": "POST", "path": "/api/deliverables/{id}/approve/", "description": "Approve a deliverable"},
                {"method": "POST", "path": "/api/projects/{id}/messages/", "description": "Post a message"},
            ]
        },
        "ui_template": {
            "pages": ["My Projects", "Project Detail", "Deliverable Review", "Messages"],
            "components": [
                {"name": "ProjectCard", "type": "card", "props": ["project", "progress_pct", "status"]},
                {"name": "MilestoneTimeline", "type": "timeline", "props": ["milestones", "current"]},
                {"name": "DeliverableViewer", "type": "file-viewer", "props": ["file_url", "approval_controls"]},
                {"name": "MessageThread", "type": "chat", "props": ["messages", "onSend"]},
            ],
            "layout": "top-nav",
        },
    },
    {
        "name": "Client Billing Portal",
        "description": "Self-service portal where clients view invoices, payment history, download statements, and manage payment methods.",
        "category": "client_portal",
        "schema_template": {
            "models": {
                "ClientAccount": {
                    "fields": {
                        "id": "AutoField",
                        "company_name": "CharField(max_length=200)",
                        "billing_email": "EmailField",
                        "balance": "DecimalField(max_digits=12, decimal_places=2)",
                    }
                },
                "Invoice": {
                    "fields": {
                        "id": "AutoField",
                        "client": "ForeignKey(ClientAccount)",
                        "invoice_number": "CharField(max_length=50, unique=True)",
                        "amount": "DecimalField(max_digits=12, decimal_places=2)",
                        "status": "CharField(choices=[draft,sent,paid,overdue])",
                        "due_date": "DateField",
                        "issued_at": "DateTimeField",
                    }
                },
                "Payment": {
                    "fields": {
                        "id": "AutoField",
                        "invoice": "ForeignKey(Invoice)",
                        "amount": "DecimalField(max_digits=12, decimal_places=2)",
                        "method": "CharField(choices=[card,bank_transfer,paypal])",
                        "paid_at": "DateTimeField",
                    }
                },
            }
        },
        "api_template": {
            "endpoints": [
                {"method": "GET", "path": "/api/account/", "description": "Client account overview"},
                {"method": "GET", "path": "/api/invoices/", "description": "List invoices"},
                {"method": "GET", "path": "/api/invoices/{id}/pdf/", "description": "Download invoice PDF"},
                {"method": "GET", "path": "/api/payments/", "description": "Payment history"},
                {"method": "POST", "path": "/api/payments/", "description": "Make a payment"},
            ]
        },
        "ui_template": {
            "pages": ["Account Overview", "Invoices", "Payments", "Settings"],
            "components": [
                {"name": "BalanceSummary", "type": "stat-card", "props": ["balance", "overdue_amount"]},
                {"name": "InvoiceTable", "type": "data-table", "props": ["invoices", "sortable", "downloadable"]},
                {"name": "PaymentForm", "type": "form", "props": ["invoice", "payment_methods"]},
                {"name": "PaymentHistory", "type": "timeline", "props": ["payments", "filterable"]},
            ],
            "layout": "top-nav",
        },
    },
    # --- Admin Panels (2) ---
    {
        "name": "User Management Console",
        "description": "Admin panel for managing users, roles, permissions, and activity audit logs.",
        "category": "admin_panel",
        "schema_template": {
            "models": {
                "User": {
                    "fields": {
                        "id": "AutoField",
                        "email": "EmailField(unique=True)",
                        "full_name": "CharField(max_length=200)",
                        "is_active": "BooleanField(default=True)",
                        "date_joined": "DateTimeField(auto_now_add=True)",
                    }
                },
                "Role": {
                    "fields": {
                        "id": "AutoField",
                        "name": "CharField(max_length=100, unique=True)",
                        "permissions": "JSONField(default=list)",
                    }
                },
                "UserRole": {
                    "fields": {
                        "id": "AutoField",
                        "user": "ForeignKey(User)",
                        "role": "ForeignKey(Role)",
                        "assigned_at": "DateTimeField(auto_now_add=True)",
                    }
                },
                "AuditLog": {
                    "fields": {
                        "id": "AutoField",
                        "user": "ForeignKey(User)",
                        "action": "CharField(max_length=200)",
                        "resource": "CharField(max_length=200)",
                        "timestamp": "DateTimeField(auto_now_add=True)",
                        "details": "JSONField(default=dict)",
                    }
                },
            }
        },
        "api_template": {
            "endpoints": [
                {"method": "GET", "path": "/api/admin/users/", "description": "List users with roles"},
                {"method": "POST", "path": "/api/admin/users/", "description": "Create a user"},
                {"method": "PATCH", "path": "/api/admin/users/{id}/", "description": "Update user"},
                {"method": "POST", "path": "/api/admin/users/{id}/assign-role/", "description": "Assign role to user"},
                {"method": "GET", "path": "/api/admin/roles/", "description": "List roles and permissions"},
                {"method": "GET", "path": "/api/admin/audit-logs/", "description": "Search audit logs"},
            ]
        },
        "ui_template": {
            "pages": ["Users", "Roles", "Audit Logs"],
            "components": [
                {"name": "UserTable", "type": "data-table", "props": ["users", "searchable", "bulk_actions"]},
                {"name": "UserForm", "type": "form", "props": ["user", "roles", "onSave"]},
                {"name": "RoleEditor", "type": "permission-matrix", "props": ["role", "all_permissions"]},
                {"name": "AuditLogTable", "type": "data-table", "props": ["logs", "date_filter", "user_filter"]},
            ],
            "layout": "sidebar",
        },
    },
    {
        "name": "Content Moderation Panel",
        "description": "Admin panel for reviewing user-generated content, flagging violations, and managing moderation queues.",
        "category": "admin_panel",
        "schema_template": {
            "models": {
                "ContentItem": {
                    "fields": {
                        "id": "AutoField",
                        "author_id": "IntegerField",
                        "content_type": "CharField(choices=[post,comment,image,video])",
                        "body": "TextField",
                        "media_url": "URLField(blank=True)",
                        "created_at": "DateTimeField(auto_now_add=True)",
                    }
                },
                "ModerationReport": {
                    "fields": {
                        "id": "AutoField",
                        "content_item": "ForeignKey(ContentItem)",
                        "reporter_id": "IntegerField",
                        "reason": "CharField(choices=[spam,harassment,nsfw,misinformation,other])",
                        "description": "TextField(blank=True)",
                        "reported_at": "DateTimeField(auto_now_add=True)",
                    }
                },
                "ModerationDecision": {
                    "fields": {
                        "id": "AutoField",
                        "report": "ForeignKey(ModerationReport)",
                        "moderator_id": "IntegerField",
                        "action": "CharField(choices=[approve,remove,warn,ban])",
                        "notes": "TextField(blank=True)",
                        "decided_at": "DateTimeField(auto_now_add=True)",
                    }
                },
            }
        },
        "api_template": {
            "endpoints": [
                {"method": "GET", "path": "/api/moderation/queue/", "description": "List pending reports"},
                {"method": "GET", "path": "/api/moderation/reports/{id}/", "description": "Report detail with content"},
                {"method": "POST", "path": "/api/moderation/reports/{id}/decide/", "description": "Submit moderation decision"},
                {"method": "GET", "path": "/api/moderation/stats/", "description": "Moderation statistics"},
            ]
        },
        "ui_template": {
            "pages": ["Moderation Queue", "Report Detail", "Statistics"],
            "components": [
                {"name": "ReportQueue", "type": "list", "props": ["reports", "priority_sort", "filters"]},
                {"name": "ContentPreview", "type": "content-viewer", "props": ["content_item", "media_preview"]},
                {"name": "DecisionForm", "type": "form", "props": ["report", "action_options", "onSubmit"]},
                {"name": "ModerationStats", "type": "stat-card-grid", "props": ["total", "pending", "resolved_today"]},
            ],
            "layout": "sidebar",
        },
    },
    # --- E-commerce (2) ---
    {
        "name": "Product Catalog Storefront",
        "description": "Full e-commerce storefront with product listings, categories, search, cart, and checkout flow.",
        "category": "ecommerce",
        "schema_template": {
            "models": {
                "Category": {
                    "fields": {
                        "id": "AutoField",
                        "name": "CharField(max_length=200)",
                        "slug": "SlugField(unique=True)",
                        "parent": "ForeignKey(self, null=True)",
                    }
                },
                "Product": {
                    "fields": {
                        "id": "AutoField",
                        "name": "CharField(max_length=200)",
                        "slug": "SlugField(unique=True)",
                        "description": "TextField",
                        "price": "DecimalField(max_digits=10, decimal_places=2)",
                        "compare_at_price": "DecimalField(null=True)",
                        "category": "ForeignKey(Category)",
                        "image_url": "URLField",
                        "stock": "IntegerField(default=0)",
                        "is_active": "BooleanField(default=True)",
                    }
                },
                "Cart": {
                    "fields": {
                        "id": "AutoField",
                        "session_id": "CharField(max_length=100)",
                        "created_at": "DateTimeField(auto_now_add=True)",
                    }
                },
                "CartItem": {
                    "fields": {
                        "id": "AutoField",
                        "cart": "ForeignKey(Cart)",
                        "product": "ForeignKey(Product)",
                        "quantity": "IntegerField(default=1)",
                    }
                },
                "Order": {
                    "fields": {
                        "id": "AutoField",
                        "cart": "OneToOneField(Cart)",
                        "customer_email": "EmailField",
                        "shipping_address": "TextField",
                        "total": "DecimalField(max_digits=12, decimal_places=2)",
                        "status": "CharField(choices=[pending,processing,shipped,delivered])",
                        "created_at": "DateTimeField(auto_now_add=True)",
                    }
                },
            }
        },
        "api_template": {
            "endpoints": [
                {"method": "GET", "path": "/api/categories/", "description": "List categories"},
                {"method": "GET", "path": "/api/products/", "description": "List products with search and filters"},
                {"method": "GET", "path": "/api/products/{slug}/", "description": "Product detail"},
                {"method": "POST", "path": "/api/cart/items/", "description": "Add item to cart"},
                {"method": "PATCH", "path": "/api/cart/items/{id}/", "description": "Update cart item quantity"},
                {"method": "DELETE", "path": "/api/cart/items/{id}/", "description": "Remove from cart"},
                {"method": "POST", "path": "/api/checkout/", "description": "Create order from cart"},
            ]
        },
        "ui_template": {
            "pages": ["Home", "Category Listing", "Product Detail", "Cart", "Checkout", "Order Confirmation"],
            "components": [
                {"name": "ProductGrid", "type": "grid", "props": ["products", "columns", "onAddToCart"]},
                {"name": "ProductCard", "type": "card", "props": ["product", "show_price", "add_button"]},
                {"name": "CartDrawer", "type": "drawer", "props": ["cart_items", "total", "onCheckout"]},
                {"name": "CheckoutForm", "type": "multi-step-form", "props": ["steps", "onSubmit"]},
                {"name": "CategoryNav", "type": "sidebar-nav", "props": ["categories", "active"]},
            ],
            "layout": "top-nav",
        },
    },
    {
        "name": "Subscription Box Platform",
        "description": "E-commerce platform for recurring subscription boxes with plan management, billing cycles, and shipment tracking.",
        "category": "ecommerce",
        "schema_template": {
            "models": {
                "SubscriptionPlan": {
                    "fields": {
                        "id": "AutoField",
                        "name": "CharField(max_length=200)",
                        "description": "TextField",
                        "price_monthly": "DecimalField(max_digits=10, decimal_places=2)",
                        "price_annual": "DecimalField(max_digits=10, decimal_places=2)",
                        "features": "JSONField(default=list)",
                        "is_active": "BooleanField(default=True)",
                    }
                },
                "Subscriber": {
                    "fields": {
                        "id": "AutoField",
                        "email": "EmailField(unique=True)",
                        "name": "CharField(max_length=200)",
                        "plan": "ForeignKey(SubscriptionPlan)",
                        "billing_cycle": "CharField(choices=[monthly,annual])",
                        "status": "CharField(choices=[active,paused,cancelled])",
                        "next_billing_date": "DateField",
                        "shipping_address": "TextField",
                    }
                },
                "Shipment": {
                    "fields": {
                        "id": "AutoField",
                        "subscriber": "ForeignKey(Subscriber)",
                        "tracking_number": "CharField(max_length=100, blank=True)",
                        "status": "CharField(choices=[preparing,shipped,delivered])",
                        "shipped_at": "DateTimeField(null=True)",
                        "items": "JSONField(default=list)",
                    }
                },
            }
        },
        "api_template": {
            "endpoints": [
                {"method": "GET", "path": "/api/plans/", "description": "List subscription plans"},
                {"method": "POST", "path": "/api/subscribe/", "description": "Create subscription"},
                {"method": "GET", "path": "/api/subscription/", "description": "Current subscription detail"},
                {"method": "PATCH", "path": "/api/subscription/", "description": "Update plan or pause"},
                {"method": "GET", "path": "/api/shipments/", "description": "Shipment history"},
                {"method": "GET", "path": "/api/shipments/{id}/track/", "description": "Track shipment"},
            ]
        },
        "ui_template": {
            "pages": ["Plans", "Subscribe", "My Subscription", "Shipments", "Tracking"],
            "components": [
                {"name": "PlanSelector", "type": "pricing-table", "props": ["plans", "billing_toggle", "onSelect"]},
                {"name": "SubscriptionCard", "type": "card", "props": ["subscription", "actions"]},
                {"name": "ShipmentTracker", "type": "stepper", "props": ["shipment", "tracking_events"]},
                {"name": "BillingToggle", "type": "toggle", "props": ["monthly_price", "annual_price"]},
            ],
            "layout": "top-nav",
        },
    },
    # --- Internal Ops (1 more to reach 9 total) ---
    {
        "name": "HR Leave Management Dashboard",
        "description": "Internal HR dashboard for managing employee leave requests, approvals, team availability calendars, and policy compliance.",
        "category": "internal_ops",
        "schema_template": {
            "models": {
                "Employee": {
                    "fields": {
                        "id": "AutoField",
                        "name": "CharField(max_length=200)",
                        "email": "EmailField(unique=True)",
                        "department": "CharField(max_length=100)",
                        "manager": "ForeignKey(self, null=True)",
                        "annual_leave_balance": "IntegerField(default=20)",
                    }
                },
                "LeaveRequest": {
                    "fields": {
                        "id": "AutoField",
                        "employee": "ForeignKey(Employee)",
                        "leave_type": "CharField(choices=[annual,sick,personal,parental])",
                        "start_date": "DateField",
                        "end_date": "DateField",
                        "status": "CharField(choices=[pending,approved,rejected])",
                        "reason": "TextField(blank=True)",
                        "reviewed_by": "ForeignKey(Employee, null=True)",
                        "reviewed_at": "DateTimeField(null=True)",
                    }
                },
                "PublicHoliday": {
                    "fields": {
                        "id": "AutoField",
                        "name": "CharField(max_length=200)",
                        "date": "DateField",
                        "is_recurring": "BooleanField(default=True)",
                    }
                },
            }
        },
        "api_template": {
            "endpoints": [
                {"method": "GET", "path": "/api/leave/requests/", "description": "List leave requests with filters"},
                {"method": "POST", "path": "/api/leave/requests/", "description": "Submit a leave request"},
                {"method": "POST", "path": "/api/leave/requests/{id}/review/", "description": "Approve or reject"},
                {"method": "GET", "path": "/api/leave/calendar/", "description": "Team availability calendar"},
                {"method": "GET", "path": "/api/leave/balances/", "description": "Leave balances for team"},
                {"method": "GET", "path": "/api/holidays/", "description": "Public holidays"},
            ]
        },
        "ui_template": {
            "pages": ["Dashboard", "My Leave", "Team Calendar", "Approvals"],
            "components": [
                {"name": "LeaveBalanceCard", "type": "stat-card", "props": ["balance", "used", "pending"]},
                {"name": "LeaveRequestForm", "type": "form", "props": ["leave_types", "date_range", "onSubmit"]},
                {"name": "TeamCalendar", "type": "calendar", "props": ["events", "holidays", "month"]},
                {"name": "ApprovalQueue", "type": "list", "props": ["requests", "onApprove", "onReject"]},
            ],
            "layout": "sidebar",
        },
    },
]


class Command(BaseCommand):
    help = "Seed the templates library with 9 starter templates across 4 categories"

    def handle(self, *args, **options):
        created_count = 0
        existing_count = 0

        for data in TEMPLATES:
            slug = slugify(data["name"])
            _, created = Template.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": data["name"],
                    "description": data["description"],
                    "category": data["category"],
                    "schema_template": data["schema_template"],
                    "api_template": data["api_template"],
                    "ui_template": data["ui_template"],
                },
            )
            if created:
                created_count += 1
            else:
                existing_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeding complete: {created_count} created, {existing_count} already existed."
            )
        )
