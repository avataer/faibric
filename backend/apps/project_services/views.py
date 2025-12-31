"""
Project Services API Views
"""
import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from .supabase_service import supabase_service
from .domain_service import domain_service
from .stripe_service import stripe_service
from .analytics_service import analytics_service
from .version_service import version_service


# ═══════════════════════════════════════════════════════════════════════════════
# DATABASE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@csrf_exempt
@require_http_methods(["POST"])
def provision_database(request):
    """Provision a new Supabase database for a project."""
    try:
        data = json.loads(request.body)
        project_id = data.get('project_id')
        project_name = data.get('project_name', 'project')
        
        if not project_id:
            return JsonResponse({'error': 'project_id required'}, status=400)
        
        result = supabase_service.provision_project(project_name)
        
        # Save to database
        from .models import ProjectDatabase
        from apps.projects.models import Project
        
        try:
            project = Project.objects.get(id=project_id)
            db, created = ProjectDatabase.objects.update_or_create(
                project=project,
                defaults={
                    'supabase_url': result.get('url', ''),
                    'supabase_anon_key': result.get('anon_key', ''),
                    'supabase_service_key': result.get('service_key', ''),
                    'status': 'active'
                }
            )
        except Project.DoesNotExist:
            pass
        
        return JsonResponse({
            'success': True,
            'url': result.get('url'),
            'anon_key': result.get('anon_key'),
            'status': 'active'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def manage_tables(request, project_id):
    """Get or create tables for a project database."""
    if request.method == "GET":
        from .models import ProjectDatabase
        try:
            db = ProjectDatabase.objects.get(project_id=project_id)
            return JsonResponse({'tables': db.tables})
        except ProjectDatabase.DoesNotExist:
            return JsonResponse({'tables': []})
    
    # POST - create tables
    try:
        data = json.loads(request.body)
        tables = data.get('tables', [])
        
        from .models import ProjectDatabase
        db = ProjectDatabase.objects.get(project_id=project_id)
        
        created = []
        for table_def in tables:
            from .supabase_service import TableDefinition
            table = TableDefinition(
                name=table_def['name'],
                columns=table_def['columns'],
                enable_rls=table_def.get('enable_rls', True)
            )
            success = supabase_service.create_table(
                db.supabase_url,
                db.supabase_service_key,
                table
            )
            if success:
                created.append(table_def['name'])
        
        # Update stored tables
        db.tables = tables
        db.save()
        
        return JsonResponse({'created': created})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@csrf_exempt
@require_http_methods(["GET", "POST"])
def configure_auth(request, project_id):
    """Configure authentication for a project."""
    from .models import ProjectAuth
    from apps.projects.models import Project
    
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return JsonResponse({'error': 'Project not found'}, status=404)
    
    if request.method == "GET":
        try:
            auth = ProjectAuth.objects.get(project=project)
            return JsonResponse({
                'email_password': auth.email_password,
                'magic_link': auth.magic_link,
                'google_oauth': auth.google_oauth,
                'github_oauth': auth.github_oauth,
                'status': auth.status
            })
        except ProjectAuth.DoesNotExist:
            return JsonResponse({'configured': False})
    
    # POST - configure
    try:
        data = json.loads(request.body)
        
        auth, created = ProjectAuth.objects.update_or_create(
            project=project,
            defaults={
                'email_password': data.get('email_password', True),
                'magic_link': data.get('magic_link', True),
                'google_oauth': data.get('google_oauth', False),
                'github_oauth': data.get('github_oauth', False),
                'google_client_id': data.get('google_client_id', ''),
                'google_client_secret': data.get('google_client_secret', ''),
                'github_client_id': data.get('github_client_id', ''),
                'github_client_secret': data.get('github_client_secret', ''),
                'status': 'active'
            }
        )
        
        return JsonResponse({'success': True, 'created': created})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def list_auth_providers(request, project_id):
    """List available auth providers for a project."""
    return JsonResponse({
        'providers': [
            {'id': 'email', 'name': 'Email & Password', 'requires_config': False},
            {'id': 'magic_link', 'name': 'Magic Link', 'requires_config': False},
            {'id': 'google', 'name': 'Google', 'requires_config': True},
            {'id': 'github', 'name': 'GitHub', 'requires_config': True},
            {'id': 'apple', 'name': 'Apple', 'requires_config': True},
        ]
    })


# ═══════════════════════════════════════════════════════════════════════════════
# DOMAIN ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@csrf_exempt
@require_http_methods(["GET"])
def list_domains(request, project_id):
    """List custom domains for a project."""
    from .models import ProjectDomain
    
    domains = ProjectDomain.objects.filter(project_id=project_id)
    return JsonResponse({
        'domains': [
            {
                'domain': d.domain,
                'is_primary': d.is_primary,
                'is_verified': d.is_verified,
                'ssl_status': d.ssl_status,
                'dns_records': d.dns_records
            }
            for d in domains
        ]
    })


@csrf_exempt
@require_http_methods(["POST"])
def add_domain(request, project_id):
    """Add a custom domain to a project."""
    try:
        data = json.loads(request.body)
        domain = data.get('domain', '').strip().lower()
        
        if not domain:
            return JsonResponse({'error': 'domain required'}, status=400)
        
        from apps.projects.models import Project
        from .models import ProjectDomain
        
        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return JsonResponse({'error': 'Project not found'}, status=404)
        
        # Check if domain already exists
        if ProjectDomain.objects.filter(domain=domain).exists():
            return JsonResponse({'error': 'Domain already in use'}, status=400)
        
        # Get Vercel project ID from deployment URL
        vercel_project_id = project.name.replace(' ', '-').lower()[:30]
        
        # Add domain via Vercel API
        status = domain_service.add_domain(vercel_project_id, domain)
        
        if status.error:
            return JsonResponse({'error': status.error}, status=400)
        
        # Save domain
        domain_obj = ProjectDomain.objects.create(
            project=project,
            domain=domain,
            is_verified=status.is_verified,
            ssl_status=status.ssl_status,
            dns_records=[
                {'type': r.type, 'name': r.name, 'value': r.value}
                for r in status.dns_records
            ]
        )
        
        # Generate instructions
        instructions = domain_service.generate_domain_instructions(status)
        
        return JsonResponse({
            'success': True,
            'domain': domain,
            'is_verified': status.is_verified,
            'dns_records': domain_obj.dns_records,
            'instructions': instructions
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def verify_domain(request, project_id, domain):
    """Check if domain is verified."""
    from apps.projects.models import Project
    from .models import ProjectDomain
    
    try:
        project = Project.objects.get(id=project_id)
        domain_obj = ProjectDomain.objects.get(project=project, domain=domain)
    except (Project.DoesNotExist, ProjectDomain.DoesNotExist):
        return JsonResponse({'error': 'Domain not found'}, status=404)
    
    vercel_project_id = project.name.replace(' ', '-').lower()[:30]
    status = domain_service.check_domain_status(vercel_project_id, domain)
    
    # Update status
    domain_obj.is_verified = status.is_verified
    domain_obj.ssl_status = status.ssl_status
    if status.is_verified:
        from django.utils import timezone
        domain_obj.verified_at = timezone.now()
    domain_obj.save()
    
    return JsonResponse({
        'is_verified': status.is_verified,
        'ssl_status': status.ssl_status
    })


@csrf_exempt
@require_http_methods(["DELETE"])
def remove_domain(request, project_id, domain):
    """Remove a custom domain."""
    from .models import ProjectDomain
    
    try:
        domain_obj = ProjectDomain.objects.get(project_id=project_id, domain=domain)
        domain_obj.delete()
        return JsonResponse({'success': True})
    except ProjectDomain.DoesNotExist:
        return JsonResponse({'error': 'Domain not found'}, status=404)


# ═══════════════════════════════════════════════════════════════════════════════
# PAYMENTS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@csrf_exempt
@require_http_methods(["POST"])
def connect_stripe(request, project_id):
    """Connect Stripe to a project."""
    try:
        data = json.loads(request.body)
        email = data.get('email', '')
        
        result = stripe_service.create_connect_account(project_id, email)
        
        if result.get('error'):
            return JsonResponse({'error': result['error']}, status=400)
        
        from .models import ProjectPayments
        from apps.projects.models import Project
        
        project = Project.objects.get(id=project_id)
        payments, created = ProjectPayments.objects.update_or_create(
            project=project,
            defaults={
                'stripe_account_id': result.get('account_id', ''),
                'stripe_account_status': result.get('status', 'pending')
            }
        )
        
        return JsonResponse({
            'success': True,
            'account_id': result.get('account_id'),
            'onboarding_url': result.get('onboarding_url')
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def manage_products(request, project_id):
    """Manage Stripe products for a project."""
    from .models import ProjectPayments
    
    try:
        payments = ProjectPayments.objects.get(project_id=project_id)
    except ProjectPayments.DoesNotExist:
        return JsonResponse({'error': 'Stripe not connected'}, status=400)
    
    if request.method == "GET":
        return JsonResponse({'products': payments.products})
    
    # POST - create product
    try:
        data = json.loads(request.body)
        
        from .stripe_service import ProductDefinition
        product = ProductDefinition(
            name=data.get('name', 'Product'),
            description=data.get('description', ''),
            price_cents=int(data.get('price_cents', 0)),
            currency=data.get('currency', 'usd'),
            recurring=data.get('recurring')
        )
        
        result = stripe_service.create_product(payments.stripe_account_id, product)
        
        if result.get('error'):
            return JsonResponse({'error': result['error']}, status=400)
        
        # Save product
        payments.products.append(result)
        payments.save()
        
        return JsonResponse({'success': True, 'product': result})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYTICS ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@csrf_exempt
@require_http_methods(["GET"])
def get_analytics(request, project_id):
    """Get analytics summary for a project."""
    from .models import AnalyticsEvent
    
    time_range = request.GET.get('range', '7d')
    
    events = AnalyticsEvent.objects.filter(project_id=project_id).values(
        'event_type', 'path', 'visitor_id', 'referrer', 'created_at'
    )
    
    events_list = [
        {
            'event_type': e['event_type'],
            'path': e['path'],
            'visitor_id': e['visitor_id'],
            'referrer': e['referrer'],
            'timestamp': e['created_at']
        }
        for e in events
    ]
    
    summary = analytics_service.calculate_summary(events_list, time_range)
    
    return JsonResponse({
        'total_pageviews': summary.total_pageviews,
        'total_visitors': summary.total_visitors,
        'pageviews_today': summary.pageviews_today,
        'visitors_today': summary.visitors_today,
        'top_pages': summary.top_pages,
        'traffic_sources': summary.traffic_sources,
        'pageviews_by_day': summary.pageviews_by_day
    })


@csrf_exempt
@require_http_methods(["POST"])
def track_event(request, project_id):
    """Track an analytics event."""
    try:
        data = json.loads(request.body)
        
        from .models import AnalyticsEvent
        
        event = AnalyticsEvent.objects.create(
            project_id=project_id,
            event_type=data.get('event_type', 'pageview'),
            path=data.get('path', '/'),
            visitor_id=data.get('visitor_id', ''),
            session_id=data.get('session_id', ''),
            referrer=data.get('referrer', ''),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            event_data=data.get('data', {})
        )
        
        return JsonResponse({'success': True, 'event_id': str(event.id)})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ═══════════════════════════════════════════════════════════════════════════════
# VERSION ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@csrf_exempt
@require_http_methods(["GET"])
def list_versions(request, project_id):
    """List versions for a project."""
    limit = int(request.GET.get('limit', 20))
    versions = version_service.get_versions(project_id, limit)
    
    return JsonResponse({
        'versions': [
            {
                'version_number': v.version_number,
                'created_at': v.created_at.isoformat(),
                'change_description': v.change_description,
                'is_deployed': v.is_deployed,
                'code_preview': v.code_preview
            }
            for v in versions
        ]
    })


@csrf_exempt
@require_http_methods(["GET"])
def get_version_diff(request, project_id):
    """Get diff between two versions."""
    from_version = int(request.GET.get('from', 1))
    to_version = int(request.GET.get('to', 1))
    
    diff = version_service.get_diff(project_id, from_version, to_version)
    
    return JsonResponse({
        'added_lines': diff.added_lines,
        'removed_lines': diff.removed_lines,
        'diff_html': diff.diff_html
    })


@csrf_exempt
@require_http_methods(["POST"])
def rollback_version(request, project_id):
    """Rollback to a specific version."""
    try:
        data = json.loads(request.body)
        version_number = int(data.get('version', 1))
        
        result = version_service.rollback(project_id, version_number)
        
        if result.get('error'):
            return JsonResponse({'error': result['error']}, status=400)
        
        return JsonResponse(result)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ═══════════════════════════════════════════════════════════════════════════════
# STORAGE ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@csrf_exempt
@require_http_methods(["GET", "POST"])
def manage_buckets(request, project_id):
    """Manage storage buckets for a project."""
    from .models import ProjectStorage
    
    if request.method == "GET":
        try:
            storage = ProjectStorage.objects.get(project_id=project_id)
            return JsonResponse({
                'buckets': storage.buckets,
                'storage_used': storage.storage_used_bytes,
                'storage_limit': storage.storage_limit_bytes
            })
        except ProjectStorage.DoesNotExist:
            return JsonResponse({'buckets': []})
    
    # POST - create bucket
    try:
        data = json.loads(request.body)
        bucket_name = data.get('name', 'files')
        
        from apps.projects.models import Project
        project = Project.objects.get(id=project_id)
        
        storage, created = ProjectStorage.objects.get_or_create(
            project=project,
            defaults={'status': 'active'}
        )
        
        storage.buckets.append({
            'name': bucket_name,
            'public': data.get('public', False),
            'created_at': str(data.get('created_at', ''))
        })
        storage.save()
        
        return JsonResponse({'success': True, 'bucket': bucket_name})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def upload_file(request, project_id):
    """Upload a file to project storage."""
    # Note: In production, this would upload to Supabase Storage or R2
    # For now, return a mock response
    return JsonResponse({
        'success': True,
        'url': f'https://storage.faibric.com/{project_id}/files/uploaded_file.png',
        'size': request.META.get('CONTENT_LENGTH', 0)
    })

