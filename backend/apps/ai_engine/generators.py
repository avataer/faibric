"""
Code generators for different components
"""
import json
from .ai_client import AIClient


class SchemaGenerator:
    """Generate database schema and Django models"""
    
    def __init__(self):
        self.ai_client = AIClient()
    
    def generate_models(self, analysis, project_id=None):
        """
        Generate Django models based on AI analysis
        
        Args:
            analysis: Dict with app analysis from AI
            project_id: Project ID to broadcast progress to
        
        Returns:
            Dict mapping model names to generated code
        """
        models = analysis.get('models', [])
        relationships = analysis.get('relationships', [])
        
        generated_models = {}
        
        for model in models:
            model_name = model['name']
            fields = model['fields']
            
            # Filter relationships for this model
            model_relationships = [
                r for r in relationships 
                if r['from_model'] == model_name
            ]
            
            code = self.ai_client.generate_django_model(
                model_name=model_name,
                fields=fields,
                relationships=model_relationships,
                project_id=project_id
            )
            
            generated_models[model_name] = code
        
        return generated_models
    
    def create_schema_json(self, analysis):
        """Create JSON representation of database schema"""
        models = analysis.get('models', [])
        relationships = analysis.get('relationships', [])
        
        return {
            'models': models,
            'relationships': relationships
        }


class APIGenerator:
    """Generate REST API endpoints"""
    
    def __init__(self):
        self.ai_client = AIClient()
    
    def generate_serializers(self, analysis, project_id=None):
        """Generate DRF serializers for all models"""
        models = analysis.get('models', [])
        
        generated_serializers = {}
        
        for model in models:
            model_name = model['name']
            fields = model['fields']
            
            code = self.ai_client.generate_serializer(
                model_name=model_name,
                fields=fields,
                project_id=project_id
            )
            
            generated_serializers[model_name] = code
        
        return generated_serializers
    
    def generate_viewsets(self, analysis, project_id=None):
        """Generate DRF viewsets for all endpoints"""
        models = analysis.get('models', [])
        api_endpoints = analysis.get('api_endpoints', [])
        
        # Group endpoints by model
        endpoints_by_model = {}
        for endpoint in api_endpoints:
            # Try to infer model from path (simple heuristic)
            path_parts = endpoint['path'].strip('/').split('/')
            if len(path_parts) >= 2:
                resource = path_parts[-1] if path_parts[-1] != '{id}' else path_parts[-2]
                # Singularize and capitalize (simple approach)
                model_name = resource.rstrip('s').capitalize()
                
                if model_name not in endpoints_by_model:
                    endpoints_by_model[model_name] = []
                endpoints_by_model[model_name].append(endpoint)
        
        generated_viewsets = {}
        
        for model in models:
            model_name = model['name']
            endpoints = endpoints_by_model.get(model_name, [])
            
            code = self.ai_client.generate_viewset(
                model_name=model_name,
                endpoints=endpoints,
                permissions="IsAuthenticated",
                project_id=project_id
            )
            
            generated_viewsets[model_name] = code
        
        return generated_viewsets
    
    def combine_api_code(self, serializers, viewsets):
        """Combine all API code into single file"""
        code_parts = [
            "from rest_framework import serializers, viewsets, status",
            "from rest_framework.decorators import action",
            "from rest_framework.response import Response",
            "from rest_framework.permissions import IsAuthenticated",
            "from django.shortcuts import get_object_or_404",
            "from .models import *",
            "",
            "# Serializers",
            ""
        ]
        
        for model_name, code in serializers.items():
            code_parts.append(f"# {model_name} Serializer")
            code_parts.append(code)
            code_parts.append("")
        
        code_parts.append("# ViewSets")
        code_parts.append("")
        
        for model_name, code in viewsets.items():
            code_parts.append(f"# {model_name} ViewSet")
            code_parts.append(code)
            code_parts.append("")
        
        return "\n".join(code_parts)


class UIGenerator:
    """Generate React UI components"""
    
    def __init__(self):
        self.ai_client = AIClient()
    
    def generate_components(self, analysis, project_id=None):
        """Generate React components based on analysis"""
        ui_components = analysis.get('ui_components', [])
        models = analysis.get('models', [])
        styling = analysis.get('styling', {})
        
        generated_components = {}
        
        for component in ui_components:
            component_name = component['name']
            component_type = component.get('type', 'component')
            description = component.get('description', '')
            
            # Add styling requirements to description
            if styling:
                style_desc = f" Style requirements: background={styling.get('backgroundColor', 'white')}, text color={styling.get('textColor', 'black')}, font={styling.get('fontFamily', 'Arial')}."
                description = description + style_desc
            
            # Find related model data if it's a data component
            data_fields = []
            for model in models:
                if model['name'].lower() in component_name.lower():
                    data_fields = model['fields']
                    break
            
            code = self.ai_client.generate_react_component(
                component_name=component_name,
                component_type=component_type,
                description=description,
                data_fields=data_fields,
                project_id=project_id
            )
            
            generated_components[component_name] = code
        
        return generated_components
    
    def generate_app_structure(self, components):
        """Generate App.tsx - with or without routing based on component count"""
        
        # If only 1 component, don't use routing at all
        if len(components) == 1:
            component_name = list(components.keys())[0]
            app_code = f'''import React from 'react';
import {component_name} from './components/{component_name}';

function App() {{
  return <{component_name} />;
}}

export default App;
'''
            return app_code
        
        # Multiple components - use routing
        routes = []
        
        for component_name in components.keys():
            if 'Page' in component_name or 'List' in component_name:
                route_path = f"/{component_name.lower().replace('page', '').replace('list', '')}"
                routes.append({
                    'path': route_path,
                    'component': component_name
                })
        
        # If no routes or no root route, use first component as home
        has_root = any(r['path'] == '/' for r in routes)
        if not has_root and components:
            first_component = list(components.keys())[0]
            routes.insert(0, {
                'path': '/',
                'component': first_component
            })
        
        app_code = '''import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';

// Import components
'''
        
        for component_name in components.keys():
            app_code += f"import {component_name} from './components/{component_name}';\n"
        
        app_code += '''
function App() {
  return (
    <Router>
      <Routes>
'''
        
        for route in routes:
            app_code += f"        <Route path='{route['path']}' element={{<{route['component']} />}} />\n"
        
        app_code += '''      </Routes>
    </Router>
  );
}

export default App;
'''
        
        return app_code

