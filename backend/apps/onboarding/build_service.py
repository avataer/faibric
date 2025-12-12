"""
BuildService - Runs app generation and deployment in-process.
No Celery worker needed - faster deploys, simpler architecture.
"""
import logging
from django.db import connection

logger = logging.getLogger(__name__)


class BuildService:
    """
    Handles the complete build flow:
    1. Create project from session
    2. Generate app with AI (with streaming progress)
    3. Deploy to Render.com
    """
    
    @classmethod
    def build_from_session(cls, session_token: str):
        """
        Complete build flow for a session.
        Called from background thread - must handle its own DB connections.
        """
        # Close any stale connections from parent thread
        connection.close()
        
        from .models import LandingSession, SessionEvent
        from apps.projects.models import Project
        from apps.ai_engine.v2.generator import AIGeneratorV2
        from apps.deployment.render_deployer import RenderDeployer
        import secrets
        
        try:
            session = LandingSession.objects.get(session_token=session_token)
            
            # Step 1: Create project if needed
            if not session.converted_to_project:
                project = cls._create_project(session)
            else:
                project = session.converted_to_project
            
            cls._add_event(session, '🚀 Starting build...')
            
            # Step 2: Generate with AI (streaming)
            cls._add_event(session, '🤖 AI is analyzing your request...')
            
            generator = AIGeneratorV2()
            result = generator.generate_app(
                user_prompt=project.user_prompt or project.description,
                project_id=project.id,
                session=session
            )
            
            # Store generated code
            cls._store_generated_code(project, result)
            cls._add_event(session, '✅ Code generated!')
            
            # Step 3: Deploy to Render
            cls._add_event(session, '☁️ Deploying to Render.com...')
            
            deployer = RenderDeployer()
            deploy_result = deployer.deploy_react_app(project)
            
            # Update project with URL
            project.deployment_url = deploy_result.get('url', '')
            project.status = 'deployed'
            project.save()
            
            # Update session
            session.status = 'deployed'
            session.save()
            
            cls._add_event(session, f"🎉 Live at: {deploy_result.get('url')}")
            
            logger.info(f"✅ Build complete: {deploy_result.get('url')}")
            return {'success': True, 'url': deploy_result.get('url')}
            
        except Exception as e:
            logger.exception(f"Build failed: {e}")
            try:
                session = LandingSession.objects.get(session_token=session_token)
                cls._add_event(session, f"❌ Build failed: {str(e)[:200]}")
                session.status = 'failed'
                session.save()
            except:
                pass
            return {'success': False, 'error': str(e)}
    
    @classmethod
    def _create_project(cls, session):
        """Create project and user/tenant if needed."""
        from django.contrib.auth import get_user_model
        from apps.tenants.models import Tenant, TenantMembership
        from apps.projects.models import Project
        import secrets
        
        # Create user if needed
        if not session.converted_to_user:
            User = get_user_model()
            username = f"user_{secrets.token_hex(4)}"
            email = session.email or f"{username}@faibric.app"
            
            user = User.objects.create_user(
                username=username,
                email=email,
                password=None,
            )
            
            tenant = Tenant.objects.create(
                name=f"{username}'s Workspace",
                slug=f"ws-{secrets.token_hex(4)}",
                owner=user,
            )
            TenantMembership.objects.create(
                tenant=tenant,
                user=user,
                role='owner',
                is_active=True,
            )
            
            session.converted_to_user = user
            session.converted_to_tenant = tenant
            session.save()
        
        # Create project
        clean_name = session.initial_request[:50].replace(':', '').replace('/', ' ')
        project = Project.objects.create(
            tenant=session.converted_to_tenant,
            user=session.converted_to_user,
            name=clean_name,
            description=session.initial_request,
            user_prompt=session.initial_request,
            status='generating',
        )
        
        session.converted_to_project = project
        session.save()
        
        cls._add_event(session, f"📁 Created project: {clean_name[:30]}...")
        return project
    
    @classmethod
    def _store_generated_code(cls, project, result):
        """Store generated components in project."""
        if 'frontend' in result:
            components = result['frontend']
        else:
            components = result.get('components', {})
        
        frontend_code = {
            'App.tsx': '',
            'components': {}
        }
        
        for name, code in components.items():
            clean_name = name.replace('components/', '')
            if clean_name in ('App', 'App.tsx'):
                frontend_code['App.tsx'] = code
            else:
                frontend_code['components'][clean_name] = code
        
        # Create App.tsx if missing
        if not frontend_code['App.tsx'] and frontend_code['components']:
            comp_imports = '\n'.join([f"import {c} from './components/{c}';" for c in frontend_code['components'].keys()])
            comp_uses = '\n        '.join([f"<{c} />" for c in frontend_code['components'].keys()])
            frontend_code['App.tsx'] = f"""import React from 'react';
{comp_imports}

function App() {{
  return (
    <div style={{{{ fontFamily: "-apple-system, BlinkMacSystemFont, 'SF Pro Display', system-ui, sans-serif" }}}}>
        {comp_uses}
    </div>
  );
}}

export default App;
"""
        
        project.frontend_code = str(frontend_code)
        project.status = 'ready'
        project.save()
    
    @classmethod
    def _add_event(cls, session, message: str):
        """Add progress event to session."""
        from .models import SessionEvent
        try:
            SessionEvent.objects.create(
                session=session,
                event_type='build_progress',
                event_data={'message': message, 'progress': 0},
            )
            logger.info(f"📢 {message}")
        except Exception as e:
            logger.error(f"Failed to add event: {e}")
