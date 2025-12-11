"""
Stock data API - fetches real stock prices
"""
import os
import requests
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.core.cache import cache
import json

# Free stock data sources
YAHOO_FINANCE_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
ALPHA_VANTAGE_URL = "https://www.alphavantage.co/query"


def get_stock_yahoo(symbol):
    """Fetch stock data from Yahoo Finance (no API key needed)"""
    try:
        url = YAHOO_FINANCE_URL.format(symbol=symbol)
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=5)
        data = response.json()
        
        result = data.get('chart', {}).get('result', [{}])[0]
        meta = result.get('meta', {})
        
        return {
            'symbol': symbol,
            'price': meta.get('regularMarketPrice', 0),
            'previousClose': meta.get('previousClose', 0),
            'change': meta.get('regularMarketPrice', 0) - meta.get('previousClose', 0),
            'changePercent': ((meta.get('regularMarketPrice', 0) - meta.get('previousClose', 0)) / meta.get('previousClose', 1)) * 100 if meta.get('previousClose') else 0,
            'marketState': meta.get('marketState', 'CLOSED'),
            'currency': meta.get('currency', 'USD'),
        }
    except Exception as e:
        print(f"Yahoo Finance error for {symbol}: {e}")
        return None


def get_stock_alphavantage(symbol):
    """Fetch stock data from Alpha Vantage (requires API key)"""
    api_key = os.environ.get('ALPHA_VANTAGE_API_KEY', '')
    if not api_key:
        return None
    
    try:
        params = {
            'function': 'GLOBAL_QUOTE',
            'symbol': symbol,
            'apikey': api_key
        }
        response = requests.get(ALPHA_VANTAGE_URL, params=params, timeout=5)
        data = response.json()
        
        quote = data.get('Global Quote', {})
        if not quote:
            return None
        
        price = float(quote.get('05. price', 0))
        prev_close = float(quote.get('08. previous close', 0))
        
        return {
            'symbol': symbol,
            'price': price,
            'previousClose': prev_close,
            'change': float(quote.get('09. change', 0)),
            'changePercent': float(quote.get('10. change percent', '0%').replace('%', '')),
            'marketState': 'REGULAR' if price != prev_close else 'CLOSED',
            'currency': 'USD',
        }
    except Exception as e:
        print(f"Alpha Vantage error for {symbol}: {e}")
        return None


@csrf_exempt
@require_http_methods(["GET"])
def get_stocks(request):
    """
    Get real stock prices
    
    Query params:
        symbols: Comma-separated stock symbols (e.g., AAPL,GOOGL,MSFT)
    
    Returns JSON with stock data
    """
    symbols_param = request.GET.get('symbols', 'AAPL,GOOGL,MSFT,TSLA,AMZN')
    symbols = [s.strip().upper() for s in symbols_param.split(',')]
    
    # Check cache first (cache for 30 seconds)
    cache_key = f"stocks_{','.join(sorted(symbols))}"
    cached = cache.get(cache_key)
    if cached:
        return JsonResponse(cached, safe=False)
    
    results = []
    for symbol in symbols[:10]:  # Limit to 10 symbols
        # Try Yahoo first (no API key needed)
        data = get_stock_yahoo(symbol)
        
        # Fallback to Alpha Vantage if Yahoo fails
        if not data:
            data = get_stock_alphavantage(symbol)
        
        if data:
            results.append(data)
        else:
            # Return placeholder if both fail
            results.append({
                'symbol': symbol,
                'price': 0,
                'error': 'Unable to fetch data'
            })
    
    # Add metadata
    response_data = {
        'stocks': results,
        'source': 'yahoo_finance',
        'cached': False,
        'timestamp': __import__('datetime').datetime.now().isoformat()
    }
    
    # Cache for 30 seconds
    cache.set(cache_key, response_data, 30)
    
    return JsonResponse(response_data)


@csrf_exempt
@require_http_methods(["GET"])
def get_stock_detail(request, symbol):
    """Get detailed data for a single stock"""
    symbol = symbol.upper()
    
    data = get_stock_yahoo(symbol)
    if not data:
        data = get_stock_alphavantage(symbol)
    
    if data:
        return JsonResponse(data)
    else:
        return JsonResponse({'error': f'Unable to fetch data for {symbol}'}, status=404)



