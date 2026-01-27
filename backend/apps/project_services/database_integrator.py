"""
Database Integrator - Auto-provision database during build pipeline.

Detects when user requests need database functionality,
provisions Supabase, and injects client code into generated apps.
"""

import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Keywords that indicate database needs
DATABASE_KEYWORDS = {
    'todo': ['todo', 'task', 'checklist', 'to-do', 'tasks'],
    'blog': ['blog', 'post', 'article', 'news', 'cms'],
    'ecommerce': ['shop', 'store', 'e-commerce', 'ecommerce', 'product', 'cart', 'checkout', 'order'],
    'booking': ['booking', 'appointment', 'reservation', 'schedule', 'calendar'],
    'social': ['social', 'feed', 'timeline', 'follow', 'like', 'comment'],
    'auth': ['login', 'signup', 'sign up', 'register', 'authentication', 'user account', 'members'],
    'crm': ['crm', 'customer', 'contact', 'lead', 'client management'],
    'inventory': ['inventory', 'stock', 'warehouse', 'supplies'],
    'analytics': ['dashboard', 'analytics', 'metrics', 'tracking', 'reports'],
}

# Features that require persistent storage
STORAGE_PATTERNS = [
    r'\bsave\b.*\bdata\b',
    r'\bstore\b.*\b(user|customer|item)',
    r'\bpersist\b',
    r'\bdatabase\b',
    r'\bsupabase\b',
    r'\bbackend\b.*\bdata\b',
    r'\buser.*\bsubmit',
    r'\bform.*\bsave\b',
    r'\bcrud\b',
    r'\bcreate.*\bread.*\bupdate.*\bdelete\b',
]


def detect_database_needs(prompt: str) -> Dict[str, bool]:
    """
    Analyze user prompt to determine database requirements.

    Returns dict indicating which database features are needed:
    {
        'needs_database': bool,
        'needs_auth': bool,
        'category': str (todo, blog, ecommerce, etc.),
        'tables': list of table names
    }
    """
    prompt_lower = prompt.lower()
    result = {
        'needs_database': False,
        'needs_auth': False,
        'category': None,
        'tables': [],
        'reasons': []
    }

    # Check for explicit database keywords
    for category, keywords in DATABASE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in prompt_lower:
                result['needs_database'] = True
                result['category'] = category
                result['reasons'].append(f"Keyword '{keyword}' detected")

                # Auth category implies auth needed
                if category == 'auth':
                    result['needs_auth'] = True

                break
        if result['category']:
            break

    # Check for storage patterns
    for pattern in STORAGE_PATTERNS:
        if re.search(pattern, prompt_lower):
            result['needs_database'] = True
            result['reasons'].append(f"Pattern '{pattern}' matched")
            break

    # Features that imply auth
    auth_indicators = ['login', 'signup', 'sign up', 'register', 'user account', 'profile', 'members', 'private']
    if any(indicator in prompt_lower for indicator in auth_indicators):
        result['needs_auth'] = True
        result['reasons'].append("Auth indicators detected")

    logger.info(f"[DB_INTEGRATOR] Analysis: needs_db={result['needs_database']}, "
                f"needs_auth={result['needs_auth']}, category={result['category']}")

    return result


def provision_database_for_project(
    project,
    user_prompt: str,
    session_token: str = None
) -> Optional[Dict]:
    """
    Provision Supabase database for a project if needed.

    Args:
        project: Django Project model instance
        user_prompt: The user's original request
        session_token: For logging events

    Returns:
        Database info dict or None if not needed
    """
    from .supabase_service import SupabaseService
    from .models import ProjectDatabase

    # Check if project already has database
    try:
        existing_db = ProjectDatabase.objects.get(project=project)
        if existing_db.status == 'active':
            logger.info(f"[DB_INTEGRATOR] Project already has database: {existing_db.supabase_url}")
            return {
                'url': existing_db.supabase_url,
                'anon_key': existing_db.supabase_anon_key,
                'tables': existing_db.tables or []
            }
    except ProjectDatabase.DoesNotExist:
        pass

    # Analyze if database is needed
    needs = detect_database_needs(user_prompt)

    if not needs['needs_database']:
        logger.info(f"[DB_INTEGRATOR] No database needed for: {user_prompt[:50]}")
        return None

    logger.info(f"[DB_INTEGRATOR] Provisioning database for: {user_prompt[:50]}")

    try:
        # Provision Supabase
        service = SupabaseService()
        project_name = project.name.replace(' ', '_').lower()[:30]

        supabase_info = service.provision_project(project_name)

        # Generate schema based on prompt
        tables = service.generate_schema_from_prompt(user_prompt)
        table_names = [t.name for t in tables]

        # Create tables in Supabase
        for table in tables:
            service.create_table(
                supabase_info['url'],
                supabase_info['service_key'],
                table
            )

        # Save to database model
        db_record = ProjectDatabase.objects.create(
            project=project,
            supabase_url=supabase_info['url'],
            supabase_anon_key=supabase_info['anon_key'],
            supabase_service_key=supabase_info['service_key'],
            tables=table_names,
            status='active'
        )

        logger.info(f"[DB_INTEGRATOR] Database provisioned: {supabase_info['url']} with tables: {table_names}")

        return {
            'url': supabase_info['url'],
            'anon_key': supabase_info['anon_key'],
            'tables': table_names,
            'needs_auth': needs['needs_auth']
        }

    except Exception as e:
        logger.error(f"[DB_INTEGRATOR] Failed to provision database: {e}")
        return None


def generate_database_client_code(db_info: Dict, user_prompt: str) -> str:
    """
    Generate Supabase client code to inject into the app.

    Returns JavaScript code block to prepend to App.jsx.
    """
    from .supabase_service import SupabaseService, TableDefinition

    service = SupabaseService()
    tables = service.generate_schema_from_prompt(user_prompt)

    # Generate the client code
    client_code = service.generate_client_code(
        db_info['url'],
        db_info['anon_key'],
        tables
    )

    # Add Supabase script tag instruction (for the deployer to add to index.html)
    supabase_script = '''
// NOTE: Add this to index.html <head>:
// <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
'''

    return supabase_script + client_code


def inject_database_code(app_code: str, db_info: Dict, user_prompt: str) -> Tuple[str, Dict]:
    """
    Inject Supabase client code into generated app code.

    Returns (modified_code, metadata)
    """
    if not db_info:
        return app_code, {}

    # Generate client code
    client_code = generate_database_client_code(db_info, user_prompt)

    # Find the right place to inject (after initial comments, before first component)
    # Look for "// Main App Component" or first component definition
    inject_patterns = [
        r'(// Main App Component)',
        r'(// LIBRARY COMPONENTS)',
        r'(const \w+Section)',
        r'(function \w+Section)',
    ]

    injected = False
    for pattern in inject_patterns:
        match = re.search(pattern, app_code)
        if match:
            insert_pos = match.start()
            app_code = app_code[:insert_pos] + client_code + "\n\n" + app_code[insert_pos:]
            injected = True
            break

    if not injected:
        # Fallback: prepend to beginning
        app_code = client_code + "\n\n" + app_code

    metadata = {
        'database_injected': True,
        'supabase_url': db_info['url'],
        'tables': db_info.get('tables', []),
        'needs_auth': db_info.get('needs_auth', False)
    }

    logger.info(f"[DB_INTEGRATOR] Injected database code: {len(client_code)} chars")

    return app_code, metadata


def get_supabase_html_head() -> str:
    """
    Return the script tag to add to index.html for Supabase.
    """
    return '<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>'


class DatabaseIntegrator:
    """
    High-level class for database integration in build pipeline.

    Usage in build_service.py:
        from apps.project_services.database_integrator import DatabaseIntegrator

        db_integrator = DatabaseIntegrator(project, user_prompt)
        if db_integrator.needs_database:
            db_info = db_integrator.provision()
            app_code = db_integrator.inject_code(app_code)
    """

    def __init__(self, project, user_prompt: str, session_token: str = None):
        self.project = project
        self.user_prompt = user_prompt
        self.session_token = session_token
        self.db_info = None
        self._needs = None

    @property
    def needs(self) -> Dict:
        if self._needs is None:
            self._needs = detect_database_needs(self.user_prompt)
        return self._needs

    @property
    def needs_database(self) -> bool:
        return self.needs['needs_database']

    @property
    def needs_auth(self) -> bool:
        return self.needs['needs_auth']

    def provision(self) -> Optional[Dict]:
        """Provision database and return info."""
        if not self.needs_database:
            return None

        self.db_info = provision_database_for_project(
            self.project,
            self.user_prompt,
            self.session_token
        )
        return self.db_info

    def inject_code(self, app_code: str) -> Tuple[str, Dict]:
        """Inject database client code into app."""
        if not self.db_info:
            return app_code, {}

        return inject_database_code(app_code, self.db_info, self.user_prompt)

    def get_html_head_additions(self) -> List[str]:
        """Get additional script tags for index.html."""
        if not self.db_info:
            return []
        return [get_supabase_html_head()]
