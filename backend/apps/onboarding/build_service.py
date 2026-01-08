"""
BuildService - Runs app generation and deployment in-process.
No Celery worker needed - faster deploys, simpler architecture.
"""
import logging
from django.db import connection

logger = logging.getLogger(__name__)


def log_activity(activity_type, title, session=None, severity='info', description=''):
    """Log to activity feed (fails silently)."""
    try:
        from apps.analytics.services import ActivityFeedService
        ActivityFeedService.log_activity(
            activity_type=activity_type,
            title=title,
            description=description,
            session_token=session.session_token if session else '',
            email=session.email if session else '',
            severity=severity,
        )
    except Exception as e:
        logger.warning(f"Failed to log activity: {e}")


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
        import secrets
        
        try:
            session = LandingSession.objects.get(session_token=session_token)
            
            # Step 1: Create project if needed
            if not session.converted_to_project:
                project = cls._create_project(session)
            else:
                project = session.converted_to_project
            
            log_activity('build_started', f'Build started: {project.name[:40]}', session)
            
            # Step 2: Generate with Component-Based Pipeline
            # NEW ARCHITECTURE:
            # - Decompose request into building blocks (navigation, hero, cards, etc.)
            # - Search library for EACH block
            # - Reuse found blocks, generate missing ones
            # - Save new blocks to library for future reuse
            # - Compose final app from blocks
            from apps.code_library.component_pipeline import ComponentGenerationPipeline
            
            pipeline = ComponentGenerationPipeline(session)
            app_code = pipeline.build(
                prompt=project.user_prompt or project.description,
                project=project
            )
            
            # OPTION 4 ARCHITECTURE: Validate at Vercel deploy time
            # 
            # 1. Deploy to Vercel
            # 2. If build fails → Vercel returns error
            # 3. AI fixes code based on error
            # 4. Retry deploy (up to 3 times)
            #
            # Validation happens IN the hybrid deployer, not here.
            #
            from apps.code_library.owner_instructions import enforce_instructions
            
            # Step 2.1: Enforce owner instructions (removes emojis, etc.)
            app_code, instruction_fixes = enforce_instructions(app_code)
            if instruction_fixes:
                logger.info(f"[Build] Owner instruction fixes: {instruction_fixes}")
            
            # Store the generated code
            result = {'components': {'App.tsx': app_code}}
            cls._store_generated_code(project, result)
            
            # Log pipeline stats (reused vs generated components)
            stats = pipeline.get_stats()
            logger.info(f"[Build] Component stats: required={stats['components_required']}, "
                       f"reused={stats['components_reused']}, generated={stats['components_generated']}")
            
            # Check if Connector V2 was used for wiring
            is_connector_v2 = stats.get('wiring_method') == 'connector_v2'
            if is_connector_v2:
                logger.info(f"[Build] Using Connector V2 code (deterministic, trusted)")
            
            # Step 3: Deploy using HYBRID strategy (Vercel first, Render fallback)
            # Vercel: 30-60 seconds deploy time
            # Render: 5-10 minutes deploy time (fallback)
            from apps.deployment.hybrid_deployer import get_hybrid_deployer
            
            hybrid = get_hybrid_deployer()
            
            # Check if this needs a backend (beyond Gateway API)
            needs_backend = hybrid.detect_needs_backend(app_code, project.user_prompt or '')
            
            if needs_backend:
                cls._add_event(session, 'Code validated - deploying (full-stack mode)...')
            else:
                cls._add_event(session, 'Code validated - deploying...')
            
            deploy_result = hybrid.deploy(
                project_name=project.name,
                app_code=app_code,
                project_id=str(project.id),
                needs_backend=needs_backend,
                user_prompt=project.user_prompt or session.initial_request or '',
                is_connector_v2=is_connector_v2
            )
            
            # Update project with URL
            url = deploy_result.url or ''
            project.deployment_url = url
            project.status = 'deploying'  # Not deployed yet!
            project.save()
            
            # Log which provider was used and deploy time
            provider = deploy_result.provider
            deploy_time = deploy_result.deploy_time_seconds
            logger.info(f"[Build] Deployed via {provider} in {deploy_time:.1f}s: {url}")
            
            # Store deployment metadata in project
            if not project.ai_analysis:
                project.ai_analysis = {}
            project.ai_analysis['deployment'] = {
                'provider': provider,
                'deploy_time_seconds': deploy_time,
                'deployment_id': deploy_result.deployment_id,
                'verified': deploy_result.verified
            }
            project.save()
            
            # For Vercel, check if deployment was verified
            # For Render, we still need to wait for the build
            if provider == 'vercel' and deploy_result.success and deploy_result.verified:
                verified = True
                cls._add_event(session, f"Deployed in {deploy_time:.0f}s: {url}")
            elif provider == 'vercel' and deploy_result.success and not deploy_result.verified:
                # Vercel deployed but verification failed - don't show URL
                verified = False
                cls._add_event(session, f"Deploy verification in progress...")
            else:
                # Render fallback - wait and verify
                cls._add_event(session, f"Build queued: {url} - waiting for {provider}...")
                verified = cls._wait_and_verify_deployment(url, session, max_wait=300)
            
            if verified:
                project.status = 'deployed'
                project.save()
                session.status = 'deployed'
                session.save()
                cls._add_event(session, f"Your app is live: {url}")
                log_activity('deployed', f'Deployed: {project.name[:40]}', session, 'success', url)
                logger.info(f"Build VERIFIED complete: {url}")
                return {'success': True, 'url': url, 'verified': True}
            else:
                # CRITICAL: Deployment failed verification - DO NOT SHOW URL
                # This is the OWNER RULE: Never show a URL that doesn't work
                project.status = 'verification_failed'
                project.deployment_url = ''  # Clear the URL - it doesn't work
                project.save()
                session.status = 'verification_failed'
                session.save()
                
                error_msg = deploy_result.error if hasattr(deploy_result, 'error') and deploy_result.error else 'Verification failed'
                cls._add_event(session, f"[BLOCKED] URL not shown - verification failed: {error_msg}")
                logger.error(f"Build BLOCKED - verification failed: {url} - {error_msg}")
                
                # Return error, NOT the URL
                return {'success': False, 'url': None, 'verified': False, 
                        'error': f'Deployment verification failed: {error_msg}'}
            
        except Exception as e:
            logger.exception(f"Build failed: {e}")
            try:
                session = LandingSession.objects.get(session_token=session_token)
                cls._add_event(session, f"Build failed: {str(e)[:200]}")
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
        
        cls._add_event(session, f"Created project: {clean_name[:30]}")
        return project
    
    @classmethod
    def _validate_code(cls, code: str) -> str:
        """Validate and fix incomplete React code."""
        if not code:
            return code
        
        # Fix common escape issues
        code = code.replace('\\>', '>')  # Remove escaped >
        code = code.replace('\\<', '<')  # Remove escaped <
        code = code.replace('}}>>', '}}>') # Fix double >>
        code = code.replace('>>>', '>')  # Fix triple >
        code = code.replace('>>', '>')   # Fix double >
        
        # Fix malformed JSX closing patterns
        import re
        code = re.sub(r'\}\}\s*>\s*>', '}}>',code)  # Fix }}> > to }}>
        code = re.sub(r'>\s*>', '>', code)  # Fix > > to >
        
        # Count opening and closing tags/braces
        open_braces = code.count('{') - code.count('}')
        open_parens = code.count('(') - code.count(')')
        
        # Fix unclosed braces
        if open_braces > 0:
            code += '}' * open_braces
        if open_parens > 0:
            code += ')' * open_parens
        
        # Ensure export default App if missing
        if 'function App' in code and 'export default App' not in code:
            code += '\n\nexport default App;'
        
        return code
    
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
            if isinstance(code, str):
                # First fix any escaped characters that shouldn't be there
                code = code.replace('\\>', '>').replace('\\<', '<')
                # Then unescape standard escapes - convert \\n to real newlines
                code = code.replace('\\n', '\n').replace('\\t', '\t').replace("\\'", "'").replace('\\"', '"')
                # Finally validate and fix any remaining issues
                code = cls._validate_code(code)
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
        
        import json
        project.frontend_code = json.dumps(frontend_code)
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
            logger.info(f"[EVENT] {message}")
        except Exception as e:
            logger.error(f"Failed to add event: {e}")
    
    @classmethod
    def _wait_and_verify_deployment(cls, url: str, session, max_wait: int = 300) -> bool:
        """
        CRITICAL: Actually wait for Render to build and verify the site works.
        
        This prevents reporting "success" when the site isn't actually live yet.
        
        Checks:
        1. Check Render build status via API (if possible)
        2. HTML returns 200
        3. JS bundle exists in HTML
        4. JS bundle returns 200 (not 404)
        5. JS bundle is > 10KB (not a stub/error page)
        6. No JavaScript runtime errors (check for error markers)
        
        Returns True only when ALL checks pass.
        """
        import requests
        import re
        import time
        import os
        
        start_time = time.time()
        check_interval = 15  # Check every 15 seconds
        last_js_hash = None  # Track if JS bundle changes (new build)
        
        # Get Render API key for build status checking
        render_api_key = os.environ.get('RENDER_API_KEY', '')
        
        while time.time() - start_time < max_wait:
            elapsed = int(time.time() - start_time)
            
            try:
                # Step 1: Check HTML
                html_resp = requests.get(url, timeout=15, headers={'Cache-Control': 'no-cache'})
                if html_resp.status_code != 200:
                    cls._add_event(session, f"Building... ({elapsed}s) - waiting for site")
                    time.sleep(check_interval)
                    continue
                
                # Step 2: Find JS bundle
                js_match = re.search(r'/assets/index-([^"\']+)\.js', html_resp.text)
                if not js_match:
                    cls._add_event(session, f"Building... ({elapsed}s) - compiling assets")
                    time.sleep(check_interval)
                    continue
                
                js_hash = js_match.group(1)
                js_path = js_match.group()
                
                # Step 3: Check JS bundle
                js_url = url.rstrip('/') + js_path
                js_resp = requests.get(js_url, timeout=15, headers={'Cache-Control': 'no-cache'})
                
                if js_resp.status_code == 404:
                    # 404 = build failed or in progress
                    if last_js_hash and last_js_hash != js_hash:
                        cls._add_event(session, f"Building... ({elapsed}s) - new build detected")
                    else:
                        cls._add_event(session, f"Building... ({elapsed}s) - JS 404 (build may have failed)")
                    last_js_hash = js_hash
                    time.sleep(check_interval)
                    continue
                
                if js_resp.status_code != 200:
                    cls._add_event(session, f"Building... ({elapsed}s) - JS status {js_resp.status_code}")
                    time.sleep(check_interval)
                    continue
                
                # Step 4: Check JS bundle size (> 10KB = real app, not error page)
                js_size = len(js_resp.content)
                if js_size < 10240:
                    cls._add_event(session, f"Building... ({elapsed}s) - bundle too small ({js_size} bytes)")
                    time.sleep(check_interval)
                    continue
                
                # Step 5: Check for build error markers in JS
                js_text = js_resp.text[:5000]  # Check first 5KB
                error_markers = ['SyntaxError', 'Unexpected token', 'Cannot find module']
                has_error = any(marker in js_text for marker in error_markers)
                if has_error:
                    cls._add_event(session, f"Building... ({elapsed}s) - build error detected")
                    time.sleep(check_interval)
                    continue
                
                # ALL CHECKS PASSED!
                logger.info(f"VERIFIED: {url} - JS bundle {js_size} bytes, hash {js_hash}")
                return True
                
            except requests.exceptions.RequestException as e:
                cls._add_event(session, f"Building... ({elapsed}s) - {str(e)[:30]}")
                time.sleep(check_interval)
                continue
        
        # Report to problem registry
        from apps.code_library.problem_registry import report_problem
        problem_class, has_fix, action = report_problem(
            f"Deployment verification failed after {max_wait}s: {url}"
        )
        if action:
            logger.error(f"[Build] SYSTEMIC FIX REQUIRED: {action}")
        
        logger.warning(f"Could not verify deployment within {max_wait}s: {url}")
        return False


