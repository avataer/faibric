"""
Universal API Gateway - Proxy requests to any external API
"""
import json
import requests
import hashlib
from urllib.parse import urljoin, urlencode
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache

from .services import get_service, get_api_key, list_services, SERVICES
from .investment import calculate_investment, calculate_portfolio, get_stock_price_at_date


def build_url(base_url: str, endpoint: str, params: dict = None, 
              auth_type: str = None, auth_param: str = None, api_key: str = None) -> str:
    """Build the full URL with authentication"""
    
    # Handle path-based auth (e.g., exchangerate-api)
    if auth_type == 'path' and api_key:
        base_url = f"{base_url}/{api_key}"
    
    url = urljoin(base_url.rstrip('/') + '/', endpoint.lstrip('/'))
    
    if params or (auth_type == 'query_param' and api_key):
        query_params = params.copy() if params else {}
        if auth_type == 'query_param' and api_key and auth_param:
            query_params[auth_param] = api_key
        if query_params:
            url = f"{url}?{urlencode(query_params)}"
    
    return url


def build_headers(service_config: dict, api_key: str, extra_headers: dict = None) -> dict:
    """Build request headers with authentication"""
    headers = {
        'User-Agent': 'Faibric-Gateway/1.0',
        'Accept': 'application/json',
    }
    
    # Add service-specific headers
    if service_config.get('headers'):
        headers.update(service_config['headers'])
    
    # Add auth header
    auth_type = service_config.get('auth_type')
    if auth_type == 'bearer' and api_key:
        headers['Authorization'] = f'Bearer {api_key}'
    elif auth_type == 'header' and api_key:
        auth_header = service_config.get('auth_header', 'Authorization')
        auth_prefix = service_config.get('auth_prefix', '')
        headers[auth_header] = f'{auth_prefix}{api_key}'
    
    # Add extra headers
    if extra_headers:
        headers.update(extra_headers)
    
    return headers


def get_cache_key(service: str, endpoint: str, params: dict) -> str:
    """Generate cache key for request"""
    params_str = json.dumps(params or {}, sort_keys=True)
    key_data = f"{service}:{endpoint}:{params_str}"
    return f"gateway:{hashlib.md5(key_data.encode()).hexdigest()}"


@csrf_exempt
@require_http_methods(["POST", "GET"])
def gateway(request):
    """
    Universal API Gateway
    
    POST /api/gateway/
    
    For pre-configured services:
    {
        "service": "openweather",
        "endpoint": "/weather",
        "params": {"q": "London"}
    }
    
    For arbitrary URLs:
    {
        "url": "https://api.example.com/data",
        "method": "GET",
        "headers": {},
        "body": {}
    }
    """
    
    # Handle GET request (for simple proxying)
    if request.method == 'GET':
        return JsonResponse({
            'status': 'ok',
            'message': 'Faibric Universal Gateway',
            'services': list_services(),
            'usage': {
                'service_request': {
                    'method': 'POST',
                    'body': {
                        'service': 'openweather',
                        'endpoint': '/weather',
                        'params': {'q': 'London'}
                    }
                },
                'direct_request': {
                    'method': 'POST', 
                    'body': {
                        'url': 'https://api.example.com/data',
                        'method': 'GET'
                    }
                }
            }
        })
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    # Check if it's a service request or direct URL request
    if 'service' in data:
        # Special handling for investment service
        if data['service'] == 'investment':
            return handle_investment_request(data)
        return handle_service_request(data)
    elif 'url' in data:
        return handle_direct_request(data)
    else:
        return JsonResponse({
            'error': 'Must provide either "service" or "url"',
            'available_services': list(SERVICES.keys())
        }, status=400)


def handle_investment_request(data: dict) -> JsonResponse:
    """
    Handle investment calculation requests
    
    Examples:
        Single stock:
        { "service": "investment", "symbol": "AAPL", "amount": 10000, "start_date": "2024-01-02" }
        
        Portfolio:
        { "service": "investment", "portfolio": [
            { "symbol": "AAPL", "amount": 5000, "start_date": "2024-01-02" },
            { "symbol": "TSLA", "amount": 5000, "start_date": "2024-01-02" }
        ]}
        
        Just get current price:
        { "service": "investment", "action": "price", "symbol": "AAPL" }
    """
    try:
        action = data.get('action', 'calculate')
        
        if action == 'price':
            # Just get price
            symbol = data.get('symbol', 'AAPL')
            date = data.get('date')
            result = get_stock_price_at_date(symbol, date)
            return JsonResponse({'success': 'error' not in result, 'data': result})
        
        elif 'portfolio' in data:
            # Portfolio calculation
            result = calculate_portfolio(data['portfolio'])
            return JsonResponse({'success': True, 'data': result})
        
        elif 'symbol' in data:
            # Single stock calculation
            result = calculate_investment(
                symbol=data['symbol'],
                amount=float(data.get('amount', 10000)),
                start_date=data.get('start_date', '2024-01-02'),
                end_date=data.get('end_date')
            )
            return JsonResponse({'success': 'error' not in result, 'data': result})
        
        else:
            return JsonResponse({
                'success': False,
                'error': 'Must provide symbol or portfolio',
                'examples': {
                    'single_stock': {
                        'service': 'investment',
                        'symbol': 'AAPL',
                        'amount': 10000,
                        'start_date': '2024-01-02'
                    },
                    'portfolio': {
                        'service': 'investment',
                        'portfolio': [
                            {'symbol': 'AAPL', 'amount': 5000, 'start_date': '2024-01-02'},
                            {'symbol': 'TSLA', 'amount': 5000, 'start_date': '2024-01-02'}
                        ]
                    }
                }
            }, status=400)
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def handle_service_request(data: dict) -> JsonResponse:
    """Handle request to a pre-configured service"""
    
    service_name = data.get('service', '').lower()
    endpoint = data.get('endpoint', '')
    params = data.get('params', {})
    method = data.get('method', 'GET').upper()
    body = data.get('body')
    cache_ttl = data.get('cache_ttl', 60)  # Default 60 seconds
    
    # Get service config
    service_config = get_service(service_name)
    if not service_config:
        return JsonResponse({
            'error': f'Unknown service: {service_name}',
            'available_services': list(SERVICES.keys())
        }, status=400)
    
    # Get API key
    api_key = get_api_key(service_config)
    auth_type = service_config.get('auth_type', 'none')
    
    if auth_type != 'none' and not api_key:
        return JsonResponse({
            'error': f'API key not configured for {service_name}',
            'hint': f'Set {service_config.get("env_key")} environment variable',
            'docs': service_config.get('docs', '')
        }, status=503)
    
    # Check cache for GET requests
    cache_key = get_cache_key(service_name, endpoint, params)
    if method == 'GET' and cache_ttl > 0:
        cached = cache.get(cache_key)
        if cached:
            cached['_cached'] = True
            return JsonResponse(cached)
    
    # Build URL and headers
    url = build_url(
        service_config['base_url'],
        endpoint,
        params if method == 'GET' else None,
        auth_type,
        service_config.get('auth_param'),
        api_key
    )
    
    headers = build_headers(service_config, api_key)
    
    # Make request
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=30)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=body or params, timeout=30)
        elif method == 'PUT':
            response = requests.put(url, headers=headers, json=body, timeout=30)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers, timeout=30)
        else:
            return JsonResponse({'error': f'Unsupported method: {method}'}, status=400)
        
        # Parse response
        try:
            result = response.json()
        except:
            result = {'data': response.text}
        
        # Wrap response
        gateway_response = {
            'success': response.ok,
            'status_code': response.status_code,
            'service': service_name,
            'data': result,
            '_cached': False
        }
        
        # Cache successful GET responses
        if method == 'GET' and response.ok and cache_ttl > 0:
            cache.set(cache_key, gateway_response, cache_ttl)
        
        return JsonResponse(gateway_response, status=200 if response.ok else response.status_code)
        
    except requests.Timeout:
        return JsonResponse({
            'error': 'Request timed out',
            'service': service_name
        }, status=504)
    except requests.RequestException as e:
        return JsonResponse({
            'error': f'Request failed: {str(e)}',
            'service': service_name
        }, status=502)


def handle_direct_request(data: dict) -> JsonResponse:
    """Handle direct URL request (arbitrary API)"""
    
    url = data.get('url')
    method = data.get('method', 'GET').upper()
    headers = data.get('headers', {})
    body = data.get('body')
    params = data.get('params', {})
    timeout = data.get('timeout', 30)
    
    if not url:
        return JsonResponse({'error': 'URL is required'}, status=400)
    
    # Security: Block internal URLs
    blocked_patterns = ['localhost', '127.0.0.1', '0.0.0.0', '192.168.', '10.', '172.']
    for pattern in blocked_patterns:
        if pattern in url.lower():
            return JsonResponse({
                'error': 'Internal URLs are not allowed',
                'hint': 'Use service name for internal Faibric APIs'
            }, status=403)
    
    # Add default headers
    request_headers = {
        'User-Agent': 'Faibric-Gateway/1.0',
        'Accept': 'application/json',
    }
    request_headers.update(headers)
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=request_headers, params=params, timeout=timeout)
        elif method == 'POST':
            response = requests.post(url, headers=request_headers, json=body, timeout=timeout)
        elif method == 'PUT':
            response = requests.put(url, headers=request_headers, json=body, timeout=timeout)
        elif method == 'DELETE':
            response = requests.delete(url, headers=request_headers, timeout=timeout)
        else:
            return JsonResponse({'error': f'Unsupported method: {method}'}, status=400)
        
        # Parse response
        try:
            result = response.json()
        except:
            result = {'data': response.text}
        
        return JsonResponse({
            'success': response.ok,
            'status_code': response.status_code,
            'url': url,
            'data': result
        }, status=200 if response.ok else response.status_code)
        
    except requests.Timeout:
        return JsonResponse({'error': 'Request timed out', 'url': url}, status=504)
    except requests.RequestException as e:
        return JsonResponse({'error': f'Request failed: {str(e)}', 'url': url}, status=502)


@csrf_exempt
@require_http_methods(["GET"])
def services_list(request):
    """List all available services and their status"""
    return JsonResponse({
        'services': list_services()
    })

