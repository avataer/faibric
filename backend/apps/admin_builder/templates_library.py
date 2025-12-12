"""
Pre-built admin panel templates.
"""

TEMPLATES = {
    'ecommerce-dashboard': {
        'name': 'E-Commerce Dashboard',
        'slug': 'ecommerce-dashboard',
        'description': 'Complete e-commerce admin with orders, products, customers, and analytics.',
        'category': 'ecommerce',
        'thumbnail_url': '/templates/ecommerce-dashboard.png',
        'tags': ['ecommerce', 'orders', 'products', 'analytics'],
        'features': ['Order management', 'Product catalog', 'Customer list', 'Revenue charts', 'Inventory tracking'],
        'theme': {
            'primaryColor': '#6366F1',
            'secondaryColor': '#10B981',
            'fontFamily': 'Inter'
        },
        'pages': [
            {
                'name': 'Dashboard',
                'slug': 'dashboard',
                'title': 'Dashboard',
                'icon': '📊',
                'page_type': 'dashboard',
                'nav_order': 0,
                'layout': {
                    'rows': [
                        {
                            'columns': [
                                {'width': 3, 'widgets': ['total_revenue']},
                                {'width': 3, 'widgets': ['total_orders']},
                                {'width': 3, 'widgets': ['total_customers']},
                                {'width': 3, 'widgets': ['avg_order_value']}
                            ]
                        },
                        {
                            'columns': [
                                {'width': 8, 'widgets': ['revenue_chart']},
                                {'width': 4, 'widgets': ['top_products']}
                            ]
                        },
                        {
                            'columns': [
                                {'width': 12, 'widgets': ['recent_orders']}
                            ]
                        }
                    ]
                },
                'widgets': [
                    {'id': 'total_revenue', 'name': 'Total Revenue', 'widget_type': 'stat_card', 'config': {'label': 'Total Revenue', 'prefix': '$', 'value_key': 'total_revenue', 'change_key': 'revenue_change', 'icon': '💰'}},
                    {'id': 'total_orders', 'name': 'Total Orders', 'widget_type': 'stat_card', 'config': {'label': 'Total Orders', 'value_key': 'total_orders', 'icon': '📦'}},
                    {'id': 'total_customers', 'name': 'Customers', 'widget_type': 'stat_card', 'config': {'label': 'Customers', 'value_key': 'total_customers', 'icon': '👥'}},
                    {'id': 'avg_order_value', 'name': 'Avg Order Value', 'widget_type': 'stat_card', 'config': {'label': 'Avg Order', 'prefix': '$', 'value_key': 'avg_order_value', 'icon': '📈'}},
                    {'id': 'revenue_chart', 'name': 'Revenue Over Time', 'widget_type': 'chart_area', 'config': {'title': 'Revenue', 'x_axis': 'date', 'y_axis': 'revenue'}},
                    {'id': 'top_products', 'name': 'Top Products', 'widget_type': 'list', 'config': {'title': 'Top Selling Products', 'limit': 5}},
                    {'id': 'recent_orders', 'name': 'Recent Orders', 'widget_type': 'table', 'config': {'columns': ['order_number', 'customer', 'total', 'status', 'date']}}
                ]
            },
            {
                'name': 'Orders',
                'slug': 'orders',
                'title': 'Orders',
                'icon': '📦',
                'page_type': 'list',
                'nav_order': 1,
                'data_source': 'checkout_orders'
            },
            {
                'name': 'Products',
                'slug': 'products',
                'title': 'Products',
                'icon': '🏷️',
                'page_type': 'list',
                'nav_order': 2,
                'data_source': 'checkout_products'
            },
            {
                'name': 'Customers',
                'slug': 'customers',
                'title': 'Customers',
                'icon': '👥',
                'page_type': 'list',
                'nav_order': 3,
                'data_source': 'cabinet_users'
            }
        ],
        'data_sources': [
            {'name': 'Dashboard Stats', 'source_type': 'custom', 'config': {'endpoint': '/api/checkout/stats'}},
            {'name': 'Orders', 'source_type': 'checkout_orders'},
            {'name': 'Products', 'source_type': 'checkout_products'},
            {'name': 'Users', 'source_type': 'cabinet_users'}
        ]
    },
    
    'analytics-dashboard': {
        'name': 'Analytics Dashboard',
        'slug': 'analytics-dashboard',
        'description': 'Comprehensive analytics dashboard with user tracking, funnels, and reports.',
        'category': 'analytics',
        'thumbnail_url': '/templates/analytics-dashboard.png',
        'tags': ['analytics', 'metrics', 'charts', 'reports'],
        'features': ['Real-time metrics', 'Funnel analysis', 'User behavior', 'Custom reports'],
        'theme': {
            'primaryColor': '#8B5CF6',
            'secondaryColor': '#EC4899',
            'fontFamily': 'Poppins'
        },
        'pages': [
            {
                'name': 'Overview',
                'slug': 'overview',
                'title': 'Analytics Overview',
                'icon': '📈',
                'page_type': 'dashboard',
                'nav_order': 0,
                'layout': {
                    'rows': [
                        {'columns': [
                            {'width': 3, 'widgets': ['total_users']},
                            {'width': 3, 'widgets': ['active_users']},
                            {'width': 3, 'widgets': ['page_views']},
                            {'width': 3, 'widgets': ['bounce_rate']}
                        ]},
                        {'columns': [
                            {'width': 6, 'widgets': ['traffic_chart']},
                            {'width': 6, 'widgets': ['user_map']}
                        ]},
                        {'columns': [
                            {'width': 4, 'widgets': ['device_chart']},
                            {'width': 4, 'widgets': ['browser_chart']},
                            {'width': 4, 'widgets': ['referrer_list']}
                        ]}
                    ]
                }
            },
            {
                'name': 'Funnels',
                'slug': 'funnels',
                'title': 'Conversion Funnels',
                'icon': '🎯',
                'page_type': 'custom',
                'nav_order': 1
            },
            {
                'name': 'Events',
                'slug': 'events',
                'title': 'Event Log',
                'icon': '📋',
                'page_type': 'list',
                'nav_order': 2,
                'data_source': 'analytics_events'
            }
        ]
    },
    
    'crm-dashboard': {
        'name': 'CRM Dashboard',
        'slug': 'crm-dashboard',
        'description': 'Customer relationship management with contacts, deals, and pipeline.',
        'category': 'crm',
        'thumbnail_url': '/templates/crm-dashboard.png',
        'tags': ['crm', 'sales', 'contacts', 'pipeline'],
        'features': ['Contact management', 'Deal pipeline', 'Activity tracking', 'Email integration'],
        'theme': {
            'primaryColor': '#0EA5E9',
            'secondaryColor': '#F59E0B',
            'fontFamily': 'Roboto'
        },
        'pages': [
            {
                'name': 'Dashboard',
                'slug': 'dashboard',
                'title': 'Sales Dashboard',
                'icon': '💼',
                'page_type': 'dashboard',
                'nav_order': 0
            },
            {
                'name': 'Contacts',
                'slug': 'contacts',
                'title': 'Contacts',
                'icon': '👤',
                'page_type': 'list',
                'nav_order': 1
            },
            {
                'name': 'Deals',
                'slug': 'deals',
                'title': 'Deals Pipeline',
                'icon': '💰',
                'page_type': 'custom',
                'nav_order': 2
            },
            {
                'name': 'Activities',
                'slug': 'activities',
                'title': 'Activities',
                'icon': '📅',
                'page_type': 'list',
                'nav_order': 3
            }
        ]
    },
    
    'support-dashboard': {
        'name': 'Support Dashboard',
        'slug': 'support-dashboard',
        'description': 'Helpdesk and support ticket management system.',
        'category': 'support',
        'thumbnail_url': '/templates/support-dashboard.png',
        'tags': ['support', 'tickets', 'helpdesk', 'customers'],
        'features': ['Ticket management', 'SLA tracking', 'Knowledge base', 'Customer history'],
        'theme': {
            'primaryColor': '#14B8A6',
            'secondaryColor': '#F97316',
            'fontFamily': 'Inter'
        },
        'pages': [
            {
                'name': 'Dashboard',
                'slug': 'dashboard',
                'title': 'Support Dashboard',
                'icon': '🎫',
                'page_type': 'dashboard',
                'nav_order': 0,
                'layout': {
                    'rows': [
                        {'columns': [
                            {'width': 3, 'widgets': ['open_tickets']},
                            {'width': 3, 'widgets': ['pending_tickets']},
                            {'width': 3, 'widgets': ['resolved_today']},
                            {'width': 3, 'widgets': ['avg_response_time']}
                        ]},
                        {'columns': [
                            {'width': 8, 'widgets': ['tickets_chart']},
                            {'width': 4, 'widgets': ['priority_breakdown']}
                        ]},
                        {'columns': [
                            {'width': 12, 'widgets': ['recent_tickets']}
                        ]}
                    ]
                }
            },
            {
                'name': 'Tickets',
                'slug': 'tickets',
                'title': 'All Tickets',
                'icon': '📋',
                'page_type': 'list',
                'nav_order': 1,
                'data_source': 'cabinet_tickets'
            },
            {
                'name': 'Customers',
                'slug': 'customers',
                'title': 'Customers',
                'icon': '👥',
                'page_type': 'list',
                'nav_order': 2,
                'data_source': 'cabinet_users'
            }
        ]
    },
    
    'content-dashboard': {
        'name': 'Content Management',
        'slug': 'content-dashboard',
        'description': 'Blog and content management system with posts, categories, and media.',
        'category': 'cms',
        'thumbnail_url': '/templates/content-dashboard.png',
        'tags': ['cms', 'blog', 'content', 'media'],
        'features': ['Post editor', 'Category management', 'Media library', 'SEO tools'],
        'theme': {
            'primaryColor': '#EF4444',
            'secondaryColor': '#8B5CF6',
            'fontFamily': 'Merriweather'
        },
        'pages': [
            {
                'name': 'Dashboard',
                'slug': 'dashboard',
                'title': 'Content Dashboard',
                'icon': '📝',
                'page_type': 'dashboard',
                'nav_order': 0
            },
            {
                'name': 'Posts',
                'slug': 'posts',
                'title': 'Posts',
                'icon': '📄',
                'page_type': 'list',
                'nav_order': 1
            },
            {
                'name': 'Categories',
                'slug': 'categories',
                'title': 'Categories',
                'icon': '🏷️',
                'page_type': 'list',
                'nav_order': 2
            },
            {
                'name': 'Media',
                'slug': 'media',
                'title': 'Media Library',
                'icon': '🖼️',
                'page_type': 'list',
                'nav_order': 3,
                'data_source': 'storage_files'
            }
        ]
    },
    
    'project-dashboard': {
        'name': 'Project Management',
        'slug': 'project-dashboard',
        'description': 'Project and task management with kanban board and team collaboration.',
        'category': 'project',
        'thumbnail_url': '/templates/project-dashboard.png',
        'tags': ['project', 'tasks', 'kanban', 'team'],
        'features': ['Kanban board', 'Task management', 'Team members', 'Time tracking'],
        'theme': {
            'primaryColor': '#22C55E',
            'secondaryColor': '#3B82F6',
            'fontFamily': 'Inter'
        },
        'pages': [
            {
                'name': 'Dashboard',
                'slug': 'dashboard',
                'title': 'Project Overview',
                'icon': '📊',
                'page_type': 'dashboard',
                'nav_order': 0
            },
            {
                'name': 'Board',
                'slug': 'board',
                'title': 'Kanban Board',
                'icon': '📋',
                'page_type': 'custom',
                'nav_order': 1
            },
            {
                'name': 'Tasks',
                'slug': 'tasks',
                'title': 'All Tasks',
                'icon': '✅',
                'page_type': 'list',
                'nav_order': 2
            },
            {
                'name': 'Team',
                'slug': 'team',
                'title': 'Team Members',
                'icon': '👥',
                'page_type': 'list',
                'nav_order': 3
            }
        ]
    },
    
    'hr-dashboard': {
        'name': 'HR Management',
        'slug': 'hr-dashboard',
        'description': 'Human resources management with employees, leave, and payroll.',
        'category': 'hr',
        'thumbnail_url': '/templates/hr-dashboard.png',
        'tags': ['hr', 'employees', 'payroll', 'leave'],
        'features': ['Employee directory', 'Leave management', 'Attendance', 'Payroll'],
        'theme': {
            'primaryColor': '#F59E0B',
            'secondaryColor': '#6366F1',
            'fontFamily': 'Nunito'
        },
        'pages': [
            {
                'name': 'Dashboard',
                'slug': 'dashboard',
                'title': 'HR Dashboard',
                'icon': '👔',
                'page_type': 'dashboard',
                'nav_order': 0
            },
            {
                'name': 'Employees',
                'slug': 'employees',
                'title': 'Employees',
                'icon': '👥',
                'page_type': 'list',
                'nav_order': 1
            },
            {
                'name': 'Leave',
                'slug': 'leave',
                'title': 'Leave Requests',
                'icon': '🏖️',
                'page_type': 'list',
                'nav_order': 2
            },
            {
                'name': 'Payroll',
                'slug': 'payroll',
                'title': 'Payroll',
                'icon': '💵',
                'page_type': 'list',
                'nav_order': 3
            }
        ]
    },
    
    'finance-dashboard': {
        'name': 'Finance Dashboard',
        'slug': 'finance-dashboard',
        'description': 'Financial management with invoices, expenses, and reports.',
        'category': 'finance',
        'thumbnail_url': '/templates/finance-dashboard.png',
        'tags': ['finance', 'invoices', 'expenses', 'reports'],
        'features': ['Invoice management', 'Expense tracking', 'Financial reports', 'Tax management'],
        'theme': {
            'primaryColor': '#059669',
            'secondaryColor': '#DC2626',
            'fontFamily': 'IBM Plex Sans'
        },
        'pages': [
            {
                'name': 'Dashboard',
                'slug': 'dashboard',
                'title': 'Financial Overview',
                'icon': '💰',
                'page_type': 'dashboard',
                'nav_order': 0
            },
            {
                'name': 'Invoices',
                'slug': 'invoices',
                'title': 'Invoices',
                'icon': '📄',
                'page_type': 'list',
                'nav_order': 1
            },
            {
                'name': 'Expenses',
                'slug': 'expenses',
                'title': 'Expenses',
                'icon': '💸',
                'page_type': 'list',
                'nav_order': 2
            },
            {
                'name': 'Reports',
                'slug': 'reports',
                'title': 'Reports',
                'icon': '📊',
                'page_type': 'custom',
                'nav_order': 3
            }
        ]
    },
    
    'simple-dashboard': {
        'name': 'Simple Dashboard',
        'slug': 'simple-dashboard',
        'description': 'Minimal dashboard template for quick starts.',
        'category': 'dashboard',
        'thumbnail_url': '/templates/simple-dashboard.png',
        'tags': ['simple', 'minimal', 'starter'],
        'features': ['Stats cards', 'Charts', 'Quick actions'],
        'theme': {
            'primaryColor': '#3B82F6',
            'secondaryColor': '#10B981',
            'fontFamily': 'Inter'
        },
        'pages': [
            {
                'name': 'Home',
                'slug': 'home',
                'title': 'Dashboard',
                'icon': '🏠',
                'page_type': 'dashboard',
                'nav_order': 0,
                'layout': {
                    'rows': [
                        {'columns': [
                            {'width': 4, 'widgets': ['stat1']},
                            {'width': 4, 'widgets': ['stat2']},
                            {'width': 4, 'widgets': ['stat3']}
                        ]},
                        {'columns': [
                            {'width': 12, 'widgets': ['main_chart']}
                        ]}
                    ]
                }
            },
            {
                'name': 'Settings',
                'slug': 'settings',
                'title': 'Settings',
                'icon': '⚙️',
                'page_type': 'form',
                'nav_order': 1
            }
        ]
    },
    
    'social-dashboard': {
        'name': 'Social Media Dashboard',
        'slug': 'social-dashboard',
        'description': 'Social media analytics and management dashboard.',
        'category': 'social',
        'thumbnail_url': '/templates/social-dashboard.png',
        'tags': ['social', 'analytics', 'engagement', 'content'],
        'features': ['Multi-platform analytics', 'Engagement metrics', 'Content calendar', 'Audience insights'],
        'theme': {
            'primaryColor': '#E91E63',
            'secondaryColor': '#2196F3',
            'fontFamily': 'Montserrat'
        },
        'pages': [
            {
                'name': 'Dashboard',
                'slug': 'dashboard',
                'title': 'Social Overview',
                'icon': '📱',
                'page_type': 'dashboard',
                'nav_order': 0
            },
            {
                'name': 'Posts',
                'slug': 'posts',
                'title': 'Posts',
                'icon': '📝',
                'page_type': 'list',
                'nav_order': 1
            },
            {
                'name': 'Analytics',
                'slug': 'analytics',
                'title': 'Analytics',
                'icon': '📈',
                'page_type': 'custom',
                'nav_order': 2
            },
            {
                'name': 'Audience',
                'slug': 'audience',
                'title': 'Audience',
                'icon': '👥',
                'page_type': 'custom',
                'nav_order': 3
            }
        ]
    }
}


def get_all_templates():
    """Get all available templates."""
    return list(TEMPLATES.values())


def get_template(slug: str):
    """Get a specific template by slug."""
    return TEMPLATES.get(slug)


def get_templates_by_category(category: str):
    """Get templates filtered by category."""
    return [t for t in TEMPLATES.values() if t['category'] == category]









