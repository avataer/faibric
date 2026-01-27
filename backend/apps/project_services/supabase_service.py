"""
Supabase Integration Service
Auto-provision database, auth, and storage for projects.
"""
import os
import requests
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class TableDefinition:
    name: str
    columns: List[Dict[str, str]]
    enable_rls: bool = True


class SupabaseService:
    """
    Manages Supabase project provisioning and configuration.
    """
    
    # Supabase Management API
    MANAGEMENT_API = "https://api.supabase.com/v1"
    
    def __init__(self):
        self.access_token = os.environ.get('SUPABASE_ACCESS_TOKEN', '')
        self.org_id = os.environ.get('SUPABASE_ORG_ID', '')
    
    @property
    def headers(self) -> Dict[str, str]:
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
    
    def provision_project(self, project_name: str, region: str = 'us-east-1') -> Dict[str, Any]:
        """
        Create a new Supabase project for a Faibric customer project.
        
        Returns:
            {
                'id': 'project-id',
                'url': 'https://xxx.supabase.co',
                'anon_key': 'eyJ...',
                'service_key': 'eyJ...'
            }
        """
        if not self.access_token or not self.org_id:
            # Return mock for development
            return self._mock_provision(project_name)

        # Generate a secure database password
        import secrets
        db_pass = secrets.token_urlsafe(24)

        # Create project via Supabase Management API
        try:
            response = requests.post(
                f"{self.MANAGEMENT_API}/projects",
                headers=self.headers,
                json={
                    'name': f'faibric-{project_name[:30]}',
                    'organization_id': self.org_id,
                    'region': region,
                    'plan': 'free',
                    'db_pass': db_pass
                },
                timeout=60
            )

            if response.status_code != 201:
                # Fall back to mock if API fails
                print(f"[SUPABASE] API error, using mock: {response.status_code}")
                return self._mock_provision(project_name)
        except Exception as e:
            # Fall back to mock on any error
            print(f"[SUPABASE] Request failed, using mock: {e}")
            return self._mock_provision(project_name)
        
        project = response.json()
        
        # Wait for project to be ready
        project_id = project['id']
        api_keys = self._get_api_keys(project_id)
        
        return {
            'id': project_id,
            'url': f"https://{project_id}.supabase.co",
            'anon_key': api_keys.get('anon', ''),
            'service_key': api_keys.get('service_role', '')
        }
    
    def _get_api_keys(self, project_id: str) -> Dict[str, str]:
        """Get API keys for a Supabase project."""
        response = requests.get(
            f"{self.MANAGEMENT_API}/projects/{project_id}/api-keys",
            headers=self.headers
        )
        
        if response.status_code != 200:
            return {}
        
        keys = {}
        for key in response.json():
            keys[key['name']] = key['api_key']
        
        return keys
    
    def _mock_provision(self, project_name: str) -> Dict[str, Any]:
        """Mock provisioning for development/testing."""
        import hashlib
        project_id = hashlib.md5(project_name.encode()).hexdigest()[:12]
        
        return {
            'id': project_id,
            'url': f'https://{project_id}.supabase.co',
            'anon_key': f'eyJ_mock_anon_key_{project_id}',
            'service_key': f'eyJ_mock_service_key_{project_id}'
        }
    
    def create_table(self, project_url: str, service_key: str, table: TableDefinition) -> bool:
        """
        Create a table in a Supabase project using the REST API.
        """
        # Generate SQL
        columns_sql = []
        for col in table.columns:
            col_def = f"{col['name']} {col['type']}"
            if col.get('primary_key'):
                col_def += ' PRIMARY KEY'
            if col.get('default'):
                col_def += f" DEFAULT {col['default']}"
            if not col.get('nullable', True):
                col_def += ' NOT NULL'
            columns_sql.append(col_def)
        
        sql = f"""
        CREATE TABLE IF NOT EXISTS {table.name} (
            {', '.join(columns_sql)}
        );
        """
        
        if table.enable_rls:
            sql += f"\nALTER TABLE {table.name} ENABLE ROW LEVEL SECURITY;"
        
        # Execute via PostgREST RPC
        response = requests.post(
            f"{project_url}/rest/v1/rpc/exec_sql",
            headers={
                'apikey': service_key,
                'Authorization': f'Bearer {service_key}',
                'Content-Type': 'application/json'
            },
            json={'query': sql}
        )
        
        return response.status_code == 200
    
    def generate_schema_from_prompt(self, user_prompt: str) -> List[TableDefinition]:
        """
        Analyze user prompt and generate appropriate database schema.
        
        Examples:
        - "todo list" -> todos table with id, text, completed, created_at
        - "blog" -> posts, comments tables
        - "e-commerce" -> products, orders, customers tables
        """
        prompt_lower = user_prompt.lower()
        tables = []
        
        # Common patterns
        if any(word in prompt_lower for word in ['todo', 'task', 'checklist']):
            tables.append(TableDefinition(
                name='todos',
                columns=[
                    {'name': 'id', 'type': 'UUID', 'primary_key': True, 'default': 'gen_random_uuid()'},
                    {'name': 'user_id', 'type': 'UUID'},
                    {'name': 'text', 'type': 'TEXT', 'nullable': False},
                    {'name': 'completed', 'type': 'BOOLEAN', 'default': 'false'},
                    {'name': 'created_at', 'type': 'TIMESTAMPTZ', 'default': 'now()'},
                ]
            ))
        
        if any(word in prompt_lower for word in ['blog', 'post', 'article', 'content']):
            tables.append(TableDefinition(
                name='posts',
                columns=[
                    {'name': 'id', 'type': 'UUID', 'primary_key': True, 'default': 'gen_random_uuid()'},
                    {'name': 'user_id', 'type': 'UUID'},
                    {'name': 'title', 'type': 'TEXT', 'nullable': False},
                    {'name': 'content', 'type': 'TEXT'},
                    {'name': 'slug', 'type': 'TEXT'},
                    {'name': 'published', 'type': 'BOOLEAN', 'default': 'false'},
                    {'name': 'created_at', 'type': 'TIMESTAMPTZ', 'default': 'now()'},
                    {'name': 'updated_at', 'type': 'TIMESTAMPTZ', 'default': 'now()'},
                ]
            ))
            tables.append(TableDefinition(
                name='comments',
                columns=[
                    {'name': 'id', 'type': 'UUID', 'primary_key': True, 'default': 'gen_random_uuid()'},
                    {'name': 'post_id', 'type': 'UUID', 'nullable': False},
                    {'name': 'user_id', 'type': 'UUID'},
                    {'name': 'content', 'type': 'TEXT', 'nullable': False},
                    {'name': 'created_at', 'type': 'TIMESTAMPTZ', 'default': 'now()'},
                ]
            ))
        
        if any(word in prompt_lower for word in ['shop', 'store', 'e-commerce', 'product', 'cart']):
            tables.append(TableDefinition(
                name='products',
                columns=[
                    {'name': 'id', 'type': 'UUID', 'primary_key': True, 'default': 'gen_random_uuid()'},
                    {'name': 'name', 'type': 'TEXT', 'nullable': False},
                    {'name': 'description', 'type': 'TEXT'},
                    {'name': 'price', 'type': 'DECIMAL(10,2)', 'nullable': False},
                    {'name': 'image_url', 'type': 'TEXT'},
                    {'name': 'stock', 'type': 'INTEGER', 'default': '0'},
                    {'name': 'created_at', 'type': 'TIMESTAMPTZ', 'default': 'now()'},
                ]
            ))
            tables.append(TableDefinition(
                name='orders',
                columns=[
                    {'name': 'id', 'type': 'UUID', 'primary_key': True, 'default': 'gen_random_uuid()'},
                    {'name': 'user_id', 'type': 'UUID'},
                    {'name': 'status', 'type': 'TEXT', 'default': "'pending'"},
                    {'name': 'total', 'type': 'DECIMAL(10,2)'},
                    {'name': 'items', 'type': 'JSONB', 'default': "'[]'"},
                    {'name': 'created_at', 'type': 'TIMESTAMPTZ', 'default': 'now()'},
                ]
            ))
        
        if any(word in prompt_lower for word in ['user', 'profile', 'account', 'member']):
            tables.append(TableDefinition(
                name='profiles',
                columns=[
                    {'name': 'id', 'type': 'UUID', 'primary_key': True},
                    {'name': 'email', 'type': 'TEXT'},
                    {'name': 'name', 'type': 'TEXT'},
                    {'name': 'avatar_url', 'type': 'TEXT'},
                    {'name': 'bio', 'type': 'TEXT'},
                    {'name': 'created_at', 'type': 'TIMESTAMPTZ', 'default': 'now()'},
                ]
            ))
        
        if any(word in prompt_lower for word in ['booking', 'appointment', 'reservation', 'schedule']):
            tables.append(TableDefinition(
                name='bookings',
                columns=[
                    {'name': 'id', 'type': 'UUID', 'primary_key': True, 'default': 'gen_random_uuid()'},
                    {'name': 'user_id', 'type': 'UUID'},
                    {'name': 'service_name', 'type': 'TEXT'},
                    {'name': 'date', 'type': 'DATE', 'nullable': False},
                    {'name': 'time', 'type': 'TIME', 'nullable': False},
                    {'name': 'status', 'type': 'TEXT', 'default': "'pending'"},
                    {'name': 'notes', 'type': 'TEXT'},
                    {'name': 'created_at', 'type': 'TIMESTAMPTZ', 'default': 'now()'},
                ]
            ))
        
        # Default: generic items table
        if not tables:
            tables.append(TableDefinition(
                name='items',
                columns=[
                    {'name': 'id', 'type': 'UUID', 'primary_key': True, 'default': 'gen_random_uuid()'},
                    {'name': 'user_id', 'type': 'UUID'},
                    {'name': 'name', 'type': 'TEXT', 'nullable': False},
                    {'name': 'data', 'type': 'JSONB', 'default': "'{}'"},
                    {'name': 'created_at', 'type': 'TIMESTAMPTZ', 'default': 'now()'},
                ]
            ))
        
        return tables
    
    def generate_client_code(self, project_url: str, anon_key: str, tables: List[TableDefinition]) -> str:
        """
        Generate JavaScript/React code for Supabase client.
        """
        table_names = [t.name for t in tables]
        
        code = f'''
// Supabase Client - Auto-generated
const SUPABASE_URL = "{project_url}";
const SUPABASE_ANON_KEY = "{anon_key}";

// Initialize Supabase client
const supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);

// Auth helpers
const signUp = async (email, password) => {{
  const {{ data, error }} = await supabase.auth.signUp({{ email, password }});
  return {{ data, error }};
}};

const signIn = async (email, password) => {{
  const {{ data, error }} = await supabase.auth.signInWithPassword({{ email, password }});
  return {{ data, error }};
}};

const signOut = async () => {{
  await supabase.auth.signOut();
}};

const getUser = () => supabase.auth.getUser();

// Database helpers
'''
        
        for table in tables:
            table_name = table.name
            code += f'''
// {table_name} CRUD operations
const get{table_name.title()} = async () => {{
  const {{ data, error }} = await supabase.from("{table_name}").select("*").order("created_at", {{ ascending: false }});
  return {{ data, error }};
}};

const create{table_name.title()[:-1] if table_name.endswith('s') else table_name.title()} = async (item) => {{
  const {{ data, error }} = await supabase.from("{table_name}").insert(item).select();
  return {{ data, error }};
}};

const update{table_name.title()[:-1] if table_name.endswith('s') else table_name.title()} = async (id, updates) => {{
  const {{ data, error }} = await supabase.from("{table_name}").update(updates).eq("id", id).select();
  return {{ data, error }};
}};

const delete{table_name.title()[:-1] if table_name.endswith('s') else table_name.title()} = async (id) => {{
  const {{ error }} = await supabase.from("{table_name}").delete().eq("id", id);
  return {{ error }};
}};
'''
        
        return code


# Singleton instance
supabase_service = SupabaseService()



