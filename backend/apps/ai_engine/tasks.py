"""
Celery tasks for async AI generation
"""
from celery import shared_task
from django.utils import timezone
from django.core.cache import cache
from .ai_client import AIClient
from .generators import SchemaGenerator, APIGenerator, UIGenerator


def broadcast_progress(project_id, step, message, progress):
    """Broadcast generation progress to Redis for real-time updates"""
    from django.utils import timezone
    
    # Get existing messages
    messages_key = f'project_messages_{project_id}'
    existing = cache.get(messages_key, [])
    
    # Add new message to list
    existing.append({
        'id': f'{project_id}_{len(existing)}',
        'type': 'action' if '✅' in message else 'thinking',
        'content': message,
        'timestamp': timezone.now().isoformat()
    })
    
    cache.set(messages_key, existing, timeout=3600)
    
    # Also update old progress format for compatibility
    cache.set(
        f'project_progress_{project_id}',
        {
            'step': step,
            'message': message,
            'progress': progress,
            'timestamp': timezone.now().isoformat()
        },
        timeout=3600
    )


@shared_task(bind=True, max_retries=3)
def generate_app_task(self, project_id):
    """
    Async task to generate complete app from project description
    """
    from apps.projects.models import Project, GeneratedModel, GeneratedAPI
    
    try:
        project = Project.objects.get(id=project_id)
        project.status = 'generating'
        project.save()
        
        broadcast_progress(project_id, 1, "🚀 Starting AI generation...", 5)
        
        # Initialize generators
        ai_client = AIClient()
        schema_gen = SchemaGenerator()
        api_gen = APIGenerator()
        ui_gen = UIGenerator()
        
        # Step 1: Analyze app description
        broadcast_progress(project_id, 2, "🧠 Analyzing your app description with AI...", 15)
        analysis = ai_client.analyze_app_description(project.user_prompt, project_id=project_id)
        project.ai_analysis = analysis
        project.save()
        
        broadcast_progress(project_id, 3, f"✅ Identified {len(analysis.get('models', []))} models and {len(analysis.get('api_endpoints', []))} API endpoints", 25)
        
        # Step 2: Generate database schema
        broadcast_progress(project_id, 4, "🗄️ Generating database models...", 35)
        generated_models = schema_gen.generate_models(analysis, project_id=project_id)
        schema_json = schema_gen.create_schema_json(analysis)
        project.database_schema = schema_json
        
        # Save individual models to database
        for idx, (model_name, model_code) in enumerate(generated_models.items()):
            broadcast_progress(project_id, 5, f"📝 Creating model: {model_name}", 40 + (idx * 5))
            model_data = next(
                (m for m in analysis['models'] if m['name'] == model_name),
                None
            )
            if model_data:
                GeneratedModel.objects.create(
                    project=project,
                    name=model_name,
                    fields=model_data['fields'],
                    relationships=[
                        r for r in analysis.get('relationships', [])
                        if r['from_model'] == model_name
                    ]
                )
        
        project.save()
        
        # Step 3: Generate API code
        broadcast_progress(project_id, 6, "🔌 Generating API endpoints and serializers...", 60)
        serializers = api_gen.generate_serializers(analysis, project_id=project_id)
        viewsets = api_gen.generate_viewsets(analysis, project_id=project_id)
        api_code = api_gen.combine_api_code(serializers, viewsets)
        project.api_code = api_code
        
        # Save individual API endpoints
        for endpoint in analysis.get('api_endpoints', []):
            GeneratedAPI.objects.create(
                project=project,
                path=endpoint['path'],
                method=endpoint['method'],
                handler_code="",  # Would be extracted from viewset
                description=endpoint.get('description', '')
            )
        
        project.save()
        broadcast_progress(project_id, 7, "✅ API layer complete", 75)
        
        # Step 4: Generate UI code
        broadcast_progress(project_id, 8, "🎨 Generating React components...", 85)
        components = ui_gen.generate_components(analysis, project_id=project_id)
        app_structure = ui_gen.generate_app_structure(components)
        
        # Combine all frontend code
        frontend_code = {
            'App.tsx': app_structure,
            'components': components
        }
        project.frontend_code = str(frontend_code)  # Store as JSON string
        project.save()
        
        broadcast_progress(project_id, 9, "✅ Frontend components generated", 95)
        
        # Mark as ready
        project.status = 'ready'
        project.save()
        
        broadcast_progress(project_id, 10, "🎉 App generation complete!", 100)
        
        # Clear progress after 5 seconds
        cache.delete(f'project_progress_{project_id}')
        
        return {
            'status': 'success',
            'project_id': project_id,
            'message': 'App generated successfully'
        }
        
    except Exception as e:
        # Mark project as failed
        error_message = str(e)
        broadcast_progress(project_id, -1, f"❌ Error: {error_message[:100]}", 0)
        
        try:
            project = Project.objects.get(id=project_id)
            project.status = 'failed'
            
            # Add user-friendly error message
            if 'api_key' in error_message.lower() or 'authentication' in error_message.lower():
                error_message = 'Invalid or missing OpenAI API key. Please check your configuration.'
            elif 'quota' in error_message.lower():
                error_message = 'OpenAI API quota exceeded. Please check your OpenAI account.'
            elif 'timeout' in error_message.lower():
                error_message = 'Request timed out. Please try again.'
            
            # Store error for user visibility
            if not project.ai_analysis:
                project.ai_analysis = {}
            if isinstance(project.ai_analysis, dict):
                project.ai_analysis['error'] = error_message
            
            project.save()
        except:
            pass
        
        # Don't retry on auth errors
        if 'api_key' in str(e).lower() or 'authentication' in str(e).lower():
            return {
                'status': 'failed',
                'project_id': project_id,
                'message': error_message
            }
        
        # Retry task for other errors
        raise self.retry(exc=e, countdown=60)


@shared_task
def refine_code_task(project_id, component_type, component_name, feedback):
    """
    Async task to refine specific code based on user feedback
    """
    from apps.projects.models import Project
    
    try:
        project = Project.objects.get(id=project_id)
        ai_client = AIClient()
        
        # Get original code based on component type
        if component_type == 'model':
            original_code = project.database_schema
        elif component_type == 'api':
            original_code = project.api_code
        elif component_type == 'ui':
            original_code = project.frontend_code
        else:
            return {'status': 'error', 'message': 'Invalid component type'}
        
        # Generate refined code
        refined_code = ai_client.refine_code(
            original_code=str(original_code),
            user_feedback=feedback
        )
        
        # Update project with refined code
        if component_type == 'model':
            project.database_schema = refined_code
        elif component_type == 'api':
            project.api_code = refined_code
        elif component_type == 'ui':
            project.frontend_code = refined_code
        
        project.save()
        
        return {
            'status': 'success',
            'message': 'Code refined successfully'
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }


# Import V2 tasks so they get registered with Celery
from .v2.tasks import generate_app_v2_task, quick_modify_task

