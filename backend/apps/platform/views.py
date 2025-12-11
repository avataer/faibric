"""
Platform API - Database, Auth, Storage services for generated apps
"""
import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from .models import AppCollection, AppDocument, AppUser
import hashlib


# ============================================================================
# DATABASE SERVICE
# ============================================================================

@csrf_exempt
@require_http_methods(["GET", "POST"])
def db_collection(request, app_id, collection_name):
    """
    GET: List all documents in a collection
    POST: Create a new document
    """
    # Get or create collection
    collection, _ = AppCollection.objects.get_or_create(
        app_id=app_id,
        name=collection_name
    )
    
    if request.method == "GET":
        # Query parameters
        limit = int(request.GET.get('limit', 100))
        offset = int(request.GET.get('offset', 0))
        order_by = request.GET.get('order_by', '-created_at')
        
        # Filter by JSON fields
        filter_param = request.GET.get('filter')
        
        queryset = AppDocument.objects.filter(collection=collection)
        
        if filter_param:
            try:
                filters = json.loads(filter_param)
                for key, value in filters.items():
                    queryset = queryset.filter(data__contains={key: value})
            except json.JSONDecodeError:
                pass
        
        # Order and paginate
        if order_by.startswith('-'):
            queryset = queryset.order_by(order_by)
        else:
            queryset = queryset.order_by(order_by)
        
        documents = queryset[offset:offset + limit]
        
        return JsonResponse({
            'success': True,
            'count': queryset.count(),
            'documents': [
                {
                    'id': str(doc.id),
                    'data': doc.data,
                    'created_at': doc.created_at.isoformat(),
                    'updated_at': doc.updated_at.isoformat()
                }
                for doc in documents
            ]
        })
    
    elif request.method == "POST":
        try:
            body = json.loads(request.body)
            data = body.get('data', {})
            
            doc = AppDocument.objects.create(
                collection=collection,
                data=data
            )
            
            return JsonResponse({
                'success': True,
                'id': str(doc.id),
                'data': doc.data,
                'created_at': doc.created_at.isoformat()
            }, status=201)
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def db_document(request, app_id, collection_name, doc_id):
    """
    GET: Get a single document
    PUT: Update a document
    DELETE: Delete a document
    """
    try:
        collection = AppCollection.objects.get(app_id=app_id, name=collection_name)
        doc = AppDocument.objects.get(id=doc_id, collection=collection)
    except (AppCollection.DoesNotExist, AppDocument.DoesNotExist):
        return JsonResponse({'success': False, 'error': 'Not found'}, status=404)
    
    if request.method == "GET":
        return JsonResponse({
            'success': True,
            'id': str(doc.id),
            'data': doc.data,
            'created_at': doc.created_at.isoformat(),
            'updated_at': doc.updated_at.isoformat()
        })
    
    elif request.method == "PUT":
        try:
            body = json.loads(request.body)
            data = body.get('data', {})
            
            # Merge or replace
            if body.get('merge', False):
                doc.data.update(data)
            else:
                doc.data = data
            doc.save()
            
            return JsonResponse({
                'success': True,
                'id': str(doc.id),
                'data': doc.data,
                'updated_at': doc.updated_at.isoformat()
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    
    elif request.method == "DELETE":
        doc.delete()
        return JsonResponse({'success': True, 'deleted': True})


@csrf_exempt
@require_http_methods(["DELETE"])
def db_collection_delete(request, app_id, collection_name):
    """Delete all documents in a collection"""
    try:
        collection = AppCollection.objects.get(app_id=app_id, name=collection_name)
        count = collection.documents.count()
        collection.documents.all().delete()
        return JsonResponse({'success': True, 'deleted_count': count})
    except AppCollection.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Collection not found'}, status=404)


# ============================================================================
# AUTH SERVICE (Basic implementation)
# ============================================================================

@csrf_exempt
@require_http_methods(["POST"])
def auth_signup(request, app_id):
    """Create a new user for an app"""
    try:
        body = json.loads(request.body)
        email = body.get('email', '').lower().strip()
        password = body.get('password', '')
        name = body.get('name', '')
        
        if not email or not password:
            return JsonResponse({'success': False, 'error': 'Email and password required'}, status=400)
        
        # Check if user exists
        if AppUser.objects.filter(app_id=app_id, email=email).exists():
            return JsonResponse({'success': False, 'error': 'User already exists'}, status=409)
        
        # Hash password (simple - use bcrypt in production)
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        user = AppUser.objects.create(
            app_id=app_id,
            email=email,
            password_hash=password_hash,
            name=name
        )
        
        return JsonResponse({
            'success': True,
            'user': {
                'id': str(user.id),
                'email': user.email,
                'name': user.name
            }
        }, status=201)
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def auth_login(request, app_id):
    """Log in a user"""
    try:
        body = json.loads(request.body)
        email = body.get('email', '').lower().strip()
        password = body.get('password', '')
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        try:
            user = AppUser.objects.get(app_id=app_id, email=email, password_hash=password_hash)
        except AppUser.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Invalid credentials'}, status=401)
        
        if not user.is_active:
            return JsonResponse({'success': False, 'error': 'Account disabled'}, status=403)
        
        # Update last login
        from django.utils import timezone
        user.last_login = timezone.now()
        user.save()
        
        # Return simple token (use JWT in production)
        token = hashlib.sha256(f"{user.id}{timezone.now().isoformat()}".encode()).hexdigest()
        
        return JsonResponse({
            'success': True,
            'token': token,
            'user': {
                'id': str(user.id),
                'email': user.email,
                'name': user.name
            }
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)


@csrf_exempt
@require_http_methods(["GET"])
def auth_users(request, app_id):
    """List all users for an app (admin)"""
    users = AppUser.objects.filter(app_id=app_id)
    return JsonResponse({
        'success': True,
        'count': users.count(),
        'users': [
            {
                'id': str(u.id),
                'email': u.email,
                'name': u.name,
                'is_active': u.is_active,
                'created_at': u.created_at.isoformat()
            }
            for u in users
        ]
    })



