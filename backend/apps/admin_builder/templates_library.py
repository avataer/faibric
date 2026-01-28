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
                'icon': '[chart]',
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
                    {'id': 'total_revenue', 'name': 'Total Revenue', 'widget_type': 'stat_card', 'config': {'label': 'Total Revenue', 'prefix': '$', 'value_key': 'total_revenue', 'change_key': 'revenue_change', 'icon': '[money]'}},
                    {'id': 'total_orders', 'name': 'Total Orders', 'widget_type': 'stat_card', 'config': {'label': 'Total Orders', 'value_key': 'total_orders', 'icon': '[box]'}},
                    {'id': 'total_customers', 'name': 'Customers', 'widget_type': 'stat_card', 'config': {'label': 'Customers', 'value_key': 'total_customers', 'icon': '👥'}},
                    {'id': 'avg_order_value', 'name': 'Avg Order Value', 'widget_type': 'stat_card', 'config': {'label': 'Avg Order', 'prefix': '$', 'value_key': 'avg_order_value', 'icon': '[trend]'}},
                    {'id': 'revenue_chart', 'name': 'Revenue Over Time', 'widget_type': 'chart_area', 'config': {'title': 'Revenue', 'x_axis': 'date', 'y_axis': 'revenue'}},
                    {'id': 'top_products', 'name': 'Top Products', 'widget_type': 'list', 'config': {'title': 'Top Selling Products', 'limit': 5}},
                    {'id': 'recent_orders', 'name': 'Recent Orders', 'widget_type': 'table', 'config': {'columns': ['order_number', 'customer', 'total', 'status', 'date']}}
                ]
            },
            {
                'name': 'Orders',
                'slug': 'orders',
                'title': 'Orders',
                'icon': '[box]',
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
                'icon': '[trend]',
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
                'icon': '[brief]',
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
                'icon': '[money]',
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
                'icon': '[note]',
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
                'icon': '[chart]',
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
                'icon': '[OK]',
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
                'icon': '[money]',
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
                'icon': '[chart]',
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
                'icon': '[gear]',
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
                'icon': '[note]',
                'page_type': 'list',
                'nav_order': 1
            },
            {
                'name': 'Analytics',
                'slug': 'analytics',
                'title': 'Analytics',
                'icon': '[trend]',
                'page_type': 'custom',
                'nav_order': 2
            },
            {
                'name': 'Audience',
                'slug': 'audience',
                'title': 'Audience',
                'icon': '[user]',
                'page_type': 'custom',
                'nav_order': 3
            }
        ]
    },

    'client-portal': {
        'name': 'Client Portal',
        'slug': 'client-portal',
        'description': 'Client-facing portal for law firms, accounting firms, and consultants.',
        'category': 'professional',
        'thumbnail_url': '/templates/client-portal.png',
        'tags': ['professional', 'clients', 'documents', 'billing'],
        'features': ['Client management', 'Document sharing', 'Messaging', 'Billing'],
        'theme': {
            'primaryColor': '#1E40AF',
            'secondaryColor': '#059669',
            'fontFamily': 'Inter'
        },
        'pages': [
            {
                'name': 'Dashboard',
                'slug': 'dashboard',
                'title': 'Client Portal Dashboard',
                'icon': '[chart]',
                'page_type': 'dashboard',
                'nav_order': 0,
                'layout': {
                    'rows': [
                        {'columns': [
                            {'width': 3, 'widgets': ['active_clients']},
                            {'width': 3, 'widgets': ['pending_documents']},
                            {'width': 3, 'widgets': ['unread_messages']},
                            {'width': 3, 'widgets': ['outstanding_invoices']}
                        ]},
                        {'columns': [
                            {'width': 8, 'widgets': ['recent_activity']},
                            {'width': 4, 'widgets': ['upcoming_deadlines']}
                        ]},
                        {'columns': [
                            {'width': 12, 'widgets': ['client_list']}
                        ]}
                    ]
                },
                'widgets': [
                    {'id': 'active_clients', 'name': 'Active Clients', 'widget_type': 'stat_card', 'config': {'label': 'Active Clients', 'value_key': 'active_clients', 'icon': '[user]'}},
                    {'id': 'pending_documents', 'name': 'Pending Documents', 'widget_type': 'stat_card', 'config': {'label': 'Pending Documents', 'value_key': 'pending_documents', 'icon': '[doc]'}},
                    {'id': 'unread_messages', 'name': 'Unread Messages', 'widget_type': 'stat_card', 'config': {'label': 'Unread Messages', 'value_key': 'unread_messages', 'icon': '[mail]'}},
                    {'id': 'outstanding_invoices', 'name': 'Outstanding Invoices', 'widget_type': 'stat_card', 'config': {'label': 'Outstanding', 'prefix': '$', 'value_key': 'outstanding_invoices', 'icon': '[money]'}},
                    {'id': 'recent_activity', 'name': 'Recent Activity', 'widget_type': 'list', 'config': {'title': 'Recent Activity', 'limit': 10}},
                    {'id': 'upcoming_deadlines', 'name': 'Upcoming Deadlines', 'widget_type': 'list', 'config': {'title': 'Upcoming Deadlines', 'limit': 5}},
                    {'id': 'client_list', 'name': 'Client List', 'widget_type': 'table', 'config': {'columns': ['name', 'company', 'status', 'last_activity']}}
                ]
            },
            {
                'name': 'Clients',
                'slug': 'clients',
                'title': 'Clients',
                'icon': '[user]',
                'page_type': 'list',
                'nav_order': 1,
                'data_source': 'portal_clients'
            },
            {
                'name': 'Documents',
                'slug': 'documents',
                'title': 'Documents',
                'icon': '[doc]',
                'page_type': 'list',
                'nav_order': 2,
                'data_source': 'portal_documents'
            },
            {
                'name': 'Messages',
                'slug': 'messages',
                'title': 'Messages',
                'icon': '[mail]',
                'page_type': 'list',
                'nav_order': 3,
                'data_source': 'portal_messages'
            },
            {
                'name': 'Invoices',
                'slug': 'invoices',
                'title': 'Invoices',
                'icon': '[money]',
                'page_type': 'list',
                'nav_order': 4,
                'data_source': 'portal_invoices'
            }
        ],
        'data_sources': [
            {'name': 'Dashboard Stats', 'source_type': 'custom', 'config': {'endpoint': '/api/portal/stats'}},
            {'name': 'Clients', 'source_type': 'portal_clients'},
            {'name': 'Documents', 'source_type': 'portal_documents'},
            {'name': 'Messages', 'source_type': 'portal_messages'},
            {'name': 'Invoices', 'source_type': 'portal_invoices'}
        ]
    },

    'healthcare-intake': {
        'name': 'Healthcare Patient Intake',
        'slug': 'healthcare-intake',
        'description': 'HIPAA-friendly patient intake and management system.',
        'category': 'healthcare',
        'thumbnail_url': '/templates/healthcare-intake.png',
        'tags': ['healthcare', 'patients', 'appointments', 'intake'],
        'features': ['Patient registration', 'Appointment scheduling', 'Form management'],
        'theme': {
            'primaryColor': '#0891B2',
            'secondaryColor': '#10B981',
            'fontFamily': 'Inter'
        },
        'pages': [
            {
                'name': 'Dashboard',
                'slug': 'dashboard',
                'title': 'Healthcare Dashboard',
                'icon': '[chart]',
                'page_type': 'dashboard',
                'nav_order': 0,
                'layout': {
                    'rows': [
                        {'columns': [
                            {'width': 4, 'widgets': ['todays_appointments']},
                            {'width': 4, 'widgets': ['pending_intakes']},
                            {'width': 4, 'widgets': ['patient_count']}
                        ]},
                        {'columns': [
                            {'width': 8, 'widgets': ['appointment_calendar']},
                            {'width': 4, 'widgets': ['intake_queue']}
                        ]},
                        {'columns': [
                            {'width': 12, 'widgets': ['recent_patients']}
                        ]}
                    ]
                },
                'widgets': [
                    {'id': 'todays_appointments', 'name': 'Today Appointments', 'widget_type': 'stat_card', 'config': {'label': 'Today Appointments', 'value_key': 'todays_appointments', 'icon': '[calendar]'}},
                    {'id': 'pending_intakes', 'name': 'Pending Intakes', 'widget_type': 'stat_card', 'config': {'label': 'Pending Intakes', 'value_key': 'pending_intakes', 'icon': '[doc]'}},
                    {'id': 'patient_count', 'name': 'Total Patients', 'widget_type': 'stat_card', 'config': {'label': 'Total Patients', 'value_key': 'patient_count', 'icon': '[user]'}},
                    {'id': 'appointment_calendar', 'name': 'Appointment Calendar', 'widget_type': 'calendar', 'config': {'title': 'Appointments'}},
                    {'id': 'intake_queue', 'name': 'Intake Queue', 'widget_type': 'list', 'config': {'title': 'Intake Queue', 'limit': 10}},
                    {'id': 'recent_patients', 'name': 'Recent Patients', 'widget_type': 'table', 'config': {'columns': ['name', 'dob', 'last_visit', 'status']}}
                ]
            },
            {
                'name': 'Patients',
                'slug': 'patients',
                'title': 'Patients',
                'icon': '[user]',
                'page_type': 'list',
                'nav_order': 1,
                'data_source': 'healthcare_patients'
            },
            {
                'name': 'Appointments',
                'slug': 'appointments',
                'title': 'Appointments',
                'icon': '[calendar]',
                'page_type': 'list',
                'nav_order': 2,
                'data_source': 'healthcare_appointments'
            },
            {
                'name': 'Intake Forms',
                'slug': 'intake-forms',
                'title': 'Intake Forms',
                'icon': '[doc]',
                'page_type': 'list',
                'nav_order': 3,
                'data_source': 'healthcare_intake_forms'
            },
            {
                'name': 'Medical Records',
                'slug': 'medical-records',
                'title': 'Medical Records',
                'icon': '[folder]',
                'page_type': 'list',
                'nav_order': 4,
                'data_source': 'healthcare_records'
            }
        ],
        'data_sources': [
            {'name': 'Dashboard Stats', 'source_type': 'custom', 'config': {'endpoint': '/api/healthcare/stats'}},
            {'name': 'Patients', 'source_type': 'healthcare_patients'},
            {'name': 'Appointments', 'source_type': 'healthcare_appointments'},
            {'name': 'Intake Forms', 'source_type': 'healthcare_intake_forms'},
            {'name': 'Medical Records', 'source_type': 'healthcare_records'}
        ]
    },

    'real-estate-portal': {
        'name': 'Real Estate Listings Portal',
        'slug': 'real-estate-portal',
        'description': 'Property management and listing portal for real estate agencies.',
        'category': 'realestate',
        'thumbnail_url': '/templates/real-estate-portal.png',
        'tags': ['realestate', 'properties', 'leads', 'listings'],
        'features': ['Property management', 'Lead tracking', 'MLS-style listings'],
        'theme': {
            'primaryColor': '#7C3AED',
            'secondaryColor': '#F59E0B',
            'fontFamily': 'Poppins'
        },
        'pages': [
            {
                'name': 'Dashboard',
                'slug': 'dashboard',
                'title': 'Real Estate Dashboard',
                'icon': '[chart]',
                'page_type': 'dashboard',
                'nav_order': 0,
                'layout': {
                    'rows': [
                        {'columns': [
                            {'width': 3, 'widgets': ['active_listings']},
                            {'width': 3, 'widgets': ['new_leads']},
                            {'width': 3, 'widgets': ['property_views']},
                            {'width': 3, 'widgets': ['sales_pipeline']}
                        ]},
                        {'columns': [
                            {'width': 8, 'widgets': ['listings_chart']},
                            {'width': 4, 'widgets': ['hot_properties']}
                        ]},
                        {'columns': [
                            {'width': 12, 'widgets': ['recent_leads']}
                        ]}
                    ]
                },
                'widgets': [
                    {'id': 'active_listings', 'name': 'Active Listings', 'widget_type': 'stat_card', 'config': {'label': 'Active Listings', 'value_key': 'active_listings', 'icon': '[home]'}},
                    {'id': 'new_leads', 'name': 'New Leads', 'widget_type': 'stat_card', 'config': {'label': 'New Leads', 'value_key': 'new_leads', 'icon': '[user]'}},
                    {'id': 'property_views', 'name': 'Property Views', 'widget_type': 'stat_card', 'config': {'label': 'Property Views', 'value_key': 'property_views', 'icon': '[eye]'}},
                    {'id': 'sales_pipeline', 'name': 'Sales Pipeline', 'widget_type': 'stat_card', 'config': {'label': 'Pipeline Value', 'prefix': '$', 'value_key': 'sales_pipeline', 'icon': '[money]'}},
                    {'id': 'listings_chart', 'name': 'Listings Performance', 'widget_type': 'chart_area', 'config': {'title': 'Listings Performance', 'x_axis': 'date', 'y_axis': 'views'}},
                    {'id': 'hot_properties', 'name': 'Hot Properties', 'widget_type': 'list', 'config': {'title': 'Hot Properties', 'limit': 5}},
                    {'id': 'recent_leads', 'name': 'Recent Leads', 'widget_type': 'table', 'config': {'columns': ['name', 'property_interest', 'source', 'date']}}
                ]
            },
            {
                'name': 'Properties',
                'slug': 'properties',
                'title': 'Properties',
                'icon': '[home]',
                'page_type': 'list',
                'nav_order': 1,
                'data_source': 'realestate_properties'
            },
            {
                'name': 'Leads',
                'slug': 'leads',
                'title': 'Leads',
                'icon': '[user]',
                'page_type': 'list',
                'nav_order': 2,
                'data_source': 'realestate_leads'
            },
            {
                'name': 'Map View',
                'slug': 'map-view',
                'title': 'Map View',
                'icon': '[map]',
                'page_type': 'custom',
                'nav_order': 3
            },
            {
                'name': 'Analytics',
                'slug': 'analytics',
                'title': 'Analytics',
                'icon': '[trend]',
                'page_type': 'custom',
                'nav_order': 4
            }
        ],
        'data_sources': [
            {'name': 'Dashboard Stats', 'source_type': 'custom', 'config': {'endpoint': '/api/realestate/stats'}},
            {'name': 'Properties', 'source_type': 'realestate_properties'},
            {'name': 'Leads', 'source_type': 'realestate_leads'}
        ]
    },

    'logistics-tracker': {
        'name': 'Logistics and Shipment Tracking',
        'slug': 'logistics-tracker',
        'description': 'Shipment tracking and fleet management dashboard.',
        'category': 'logistics',
        'thumbnail_url': '/templates/logistics-tracker.png',
        'tags': ['logistics', 'shipments', 'tracking', 'fleet'],
        'features': ['Shipment management', 'Real-time tracking', 'Driver management'],
        'theme': {
            'primaryColor': '#DC2626',
            'secondaryColor': '#0891B2',
            'fontFamily': 'Roboto'
        },
        'pages': [
            {
                'name': 'Dashboard',
                'slug': 'dashboard',
                'title': 'Logistics Dashboard',
                'icon': '[chart]',
                'page_type': 'dashboard',
                'nav_order': 0,
                'layout': {
                    'rows': [
                        {'columns': [
                            {'width': 3, 'widgets': ['in_transit']},
                            {'width': 3, 'widgets': ['deliveries_today']},
                            {'width': 3, 'widgets': ['on_time_percentage']},
                            {'width': 3, 'widgets': ['revenue']}
                        ]},
                        {'columns': [
                            {'width': 8, 'widgets': ['delivery_chart']},
                            {'width': 4, 'widgets': ['driver_status']}
                        ]},
                        {'columns': [
                            {'width': 12, 'widgets': ['active_shipments']}
                        ]}
                    ]
                },
                'widgets': [
                    {'id': 'in_transit', 'name': 'In Transit', 'widget_type': 'stat_card', 'config': {'label': 'In Transit', 'value_key': 'in_transit', 'icon': '[truck]'}},
                    {'id': 'deliveries_today', 'name': 'Deliveries Today', 'widget_type': 'stat_card', 'config': {'label': 'Deliveries Today', 'value_key': 'deliveries_today', 'icon': '[box]'}},
                    {'id': 'on_time_percentage', 'name': 'On Time', 'widget_type': 'stat_card', 'config': {'label': 'On Time', 'suffix': '%', 'value_key': 'on_time_percentage', 'icon': '[clock]'}},
                    {'id': 'revenue', 'name': 'Revenue', 'widget_type': 'stat_card', 'config': {'label': 'Revenue', 'prefix': '$', 'value_key': 'revenue', 'icon': '[money]'}},
                    {'id': 'delivery_chart', 'name': 'Delivery Performance', 'widget_type': 'chart_area', 'config': {'title': 'Delivery Performance', 'x_axis': 'date', 'y_axis': 'deliveries'}},
                    {'id': 'driver_status', 'name': 'Driver Status', 'widget_type': 'list', 'config': {'title': 'Driver Status', 'limit': 8}},
                    {'id': 'active_shipments', 'name': 'Active Shipments', 'widget_type': 'table', 'config': {'columns': ['tracking_number', 'origin', 'destination', 'status', 'eta']}}
                ]
            },
            {
                'name': 'Shipments',
                'slug': 'shipments',
                'title': 'Shipments',
                'icon': '[box]',
                'page_type': 'list',
                'nav_order': 1,
                'data_source': 'logistics_shipments'
            },
            {
                'name': 'Tracking Map',
                'slug': 'tracking-map',
                'title': 'Tracking Map',
                'icon': '[map]',
                'page_type': 'custom',
                'nav_order': 2
            },
            {
                'name': 'Fleet',
                'slug': 'fleet',
                'title': 'Fleet',
                'icon': '[truck]',
                'page_type': 'list',
                'nav_order': 3,
                'data_source': 'logistics_fleet'
            },
            {
                'name': 'Analytics',
                'slug': 'analytics',
                'title': 'Analytics',
                'icon': '[trend]',
                'page_type': 'custom',
                'nav_order': 4
            }
        ],
        'data_sources': [
            {'name': 'Dashboard Stats', 'source_type': 'custom', 'config': {'endpoint': '/api/logistics/stats'}},
            {'name': 'Shipments', 'source_type': 'logistics_shipments'},
            {'name': 'Fleet', 'source_type': 'logistics_fleet'}
        ]
    },

    'approval-workflow': {
        'name': 'Approval Workflows System',
        'slug': 'approval-workflow',
        'description': 'Multi-level approval system for expenses, PTO, and requests.',
        'category': 'workflow',
        'thumbnail_url': '/templates/approval-workflow.png',
        'tags': ['workflow', 'approvals', 'expenses', 'requests'],
        'features': ['Approval routing', 'SLA tracking', 'Escalation rules'],
        'theme': {
            'primaryColor': '#4F46E5',
            'secondaryColor': '#22C55E',
            'fontFamily': 'Inter'
        },
        'pages': [
            {
                'name': 'Dashboard',
                'slug': 'dashboard',
                'title': 'Approvals Dashboard',
                'icon': '[chart]',
                'page_type': 'dashboard',
                'nav_order': 0,
                'layout': {
                    'rows': [
                        {'columns': [
                            {'width': 4, 'widgets': ['queue_length']},
                            {'width': 4, 'widgets': ['avg_approval_time']},
                            {'width': 4, 'widgets': ['pending_by_type']}
                        ]},
                        {'columns': [
                            {'width': 8, 'widgets': ['approval_trend']},
                            {'width': 4, 'widgets': ['sla_status']}
                        ]},
                        {'columns': [
                            {'width': 12, 'widgets': ['pending_approvals']}
                        ]}
                    ]
                },
                'widgets': [
                    {'id': 'queue_length', 'name': 'Queue Length', 'widget_type': 'stat_card', 'config': {'label': 'Queue Length', 'value_key': 'queue_length', 'icon': '[list]'}},
                    {'id': 'avg_approval_time', 'name': 'Avg Approval Time', 'widget_type': 'stat_card', 'config': {'label': 'Avg Time', 'suffix': ' hrs', 'value_key': 'avg_approval_time', 'icon': '[clock]'}},
                    {'id': 'pending_by_type', 'name': 'Pending by Type', 'widget_type': 'chart_pie', 'config': {'title': 'By Type'}},
                    {'id': 'approval_trend', 'name': 'Approval Trend', 'widget_type': 'chart_area', 'config': {'title': 'Approval Trend', 'x_axis': 'date', 'y_axis': 'count'}},
                    {'id': 'sla_status', 'name': 'SLA Status', 'widget_type': 'list', 'config': {'title': 'SLA Status', 'limit': 5}},
                    {'id': 'pending_approvals', 'name': 'Pending Approvals', 'widget_type': 'table', 'config': {'columns': ['request_type', 'requester', 'amount', 'submitted', 'sla_remaining']}}
                ]
            },
            {
                'name': 'Pending Approvals',
                'slug': 'pending-approvals',
                'title': 'Pending Approvals',
                'icon': '[clock]',
                'page_type': 'list',
                'nav_order': 1,
                'data_source': 'workflow_pending'
            },
            {
                'name': 'My Requests',
                'slug': 'my-requests',
                'title': 'My Requests',
                'icon': '[user]',
                'page_type': 'list',
                'nav_order': 2,
                'data_source': 'workflow_my_requests'
            },
            {
                'name': 'Rules',
                'slug': 'rules',
                'title': 'Approval Rules',
                'icon': '[gear]',
                'page_type': 'list',
                'nav_order': 3,
                'data_source': 'workflow_rules'
            },
            {
                'name': 'History',
                'slug': 'history',
                'title': 'Approval History',
                'icon': '[folder]',
                'page_type': 'list',
                'nav_order': 4,
                'data_source': 'workflow_history'
            }
        ],
        'data_sources': [
            {'name': 'Dashboard Stats', 'source_type': 'custom', 'config': {'endpoint': '/api/workflow/stats'}},
            {'name': 'Pending Approvals', 'source_type': 'workflow_pending'},
            {'name': 'My Requests', 'source_type': 'workflow_my_requests'},
            {'name': 'Approval Rules', 'source_type': 'workflow_rules'},
            {'name': 'Approval History', 'source_type': 'workflow_history'}
        ]
    },

    'inventory-management': {
        'name': 'Inventory Management System',
        'slug': 'inventory-management',
        'description': 'Stock tracking and warehouse management system.',
        'category': 'inventory',
        'thumbnail_url': '/templates/inventory-management.png',
        'tags': ['inventory', 'stock', 'warehouse', 'reorder'],
        'features': ['Stock tracking', 'Reorder points', 'Supplier management'],
        'theme': {
            'primaryColor': '#EA580C',
            'secondaryColor': '#0D9488',
            'fontFamily': 'Inter'
        },
        'pages': [
            {
                'name': 'Dashboard',
                'slug': 'dashboard',
                'title': 'Inventory Dashboard',
                'icon': '[chart]',
                'page_type': 'dashboard',
                'nav_order': 0,
                'layout': {
                    'rows': [
                        {'columns': [
                            {'width': 3, 'widgets': ['total_skus']},
                            {'width': 3, 'widgets': ['low_stock_alerts']},
                            {'width': 3, 'widgets': ['warehouse_utilization']},
                            {'width': 3, 'widgets': ['reorder_count']}
                        ]},
                        {'columns': [
                            {'width': 8, 'widgets': ['stock_movement']},
                            {'width': 4, 'widgets': ['top_movers']}
                        ]},
                        {'columns': [
                            {'width': 12, 'widgets': ['low_stock_items']}
                        ]}
                    ]
                },
                'widgets': [
                    {'id': 'total_skus', 'name': 'Total SKUs', 'widget_type': 'stat_card', 'config': {'label': 'Total SKUs', 'value_key': 'total_skus', 'icon': '[box]'}},
                    {'id': 'low_stock_alerts', 'name': 'Low Stock Alerts', 'widget_type': 'stat_card', 'config': {'label': 'Low Stock Alerts', 'value_key': 'low_stock_alerts', 'icon': '[alert]'}},
                    {'id': 'warehouse_utilization', 'name': 'Warehouse Utilization', 'widget_type': 'stat_card', 'config': {'label': 'Utilization', 'suffix': '%', 'value_key': 'warehouse_utilization', 'icon': '[warehouse]'}},
                    {'id': 'reorder_count', 'name': 'Reorder Count', 'widget_type': 'stat_card', 'config': {'label': 'Reorder Needed', 'value_key': 'reorder_count', 'icon': '[refresh]'}},
                    {'id': 'stock_movement', 'name': 'Stock Movement', 'widget_type': 'chart_area', 'config': {'title': 'Stock Movement', 'x_axis': 'date', 'y_axis': 'units'}},
                    {'id': 'top_movers', 'name': 'Top Movers', 'widget_type': 'list', 'config': {'title': 'Top Moving Products', 'limit': 5}},
                    {'id': 'low_stock_items', 'name': 'Low Stock Items', 'widget_type': 'table', 'config': {'columns': ['sku', 'product_name', 'current_stock', 'reorder_point', 'warehouse']}}
                ]
            },
            {
                'name': 'Products',
                'slug': 'products',
                'title': 'Products',
                'icon': '[box]',
                'page_type': 'list',
                'nav_order': 1,
                'data_source': 'inventory_products'
            },
            {
                'name': 'Warehouses',
                'slug': 'warehouses',
                'title': 'Warehouses',
                'icon': '[warehouse]',
                'page_type': 'list',
                'nav_order': 2,
                'data_source': 'inventory_warehouses'
            },
            {
                'name': 'Stock Levels',
                'slug': 'stock-levels',
                'title': 'Stock Levels',
                'icon': '[trend]',
                'page_type': 'list',
                'nav_order': 3,
                'data_source': 'inventory_stock_levels'
            },
            {
                'name': 'Reorder Alerts',
                'slug': 'reorder-alerts',
                'title': 'Reorder Alerts',
                'icon': '[alert]',
                'page_type': 'list',
                'nav_order': 4,
                'data_source': 'inventory_reorder_alerts'
            }
        ],
        'data_sources': [
            {'name': 'Dashboard Stats', 'source_type': 'custom', 'config': {'endpoint': '/api/inventory/stats'}},
            {'name': 'Products', 'source_type': 'inventory_products'},
            {'name': 'Warehouses', 'source_type': 'inventory_warehouses'},
            {'name': 'Stock Levels', 'source_type': 'inventory_stock_levels'},
            {'name': 'Reorder Alerts', 'source_type': 'inventory_reorder_alerts'}
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













