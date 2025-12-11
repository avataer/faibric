"""
Service Registry - Pre-configured API integrations
"""
import os

# Service configurations
# Each service defines how to authenticate and call its API
SERVICES = {
    # Weather
    'openweather': {
        'name': 'OpenWeather',
        'base_url': 'https://api.openweathermap.org/data/2.5',
        'auth_type': 'query_param',
        'auth_param': 'appid',
        'env_key': 'OPENWEATHER_API_KEY',
        'docs': 'https://openweathermap.org/api',
        'free_tier': '1000 calls/day',
        'example': {
            'endpoint': '/weather',
            'params': {'q': 'London', 'units': 'metric'}
        }
    },
    
    # Stocks & Finance
    'alpha_vantage': {
        'name': 'Alpha Vantage (Stocks)',
        'base_url': 'https://www.alphavantage.co',
        'auth_type': 'query_param',
        'auth_param': 'apikey',
        'env_key': 'ALPHA_VANTAGE_API_KEY',
        'docs': 'https://www.alphavantage.co/documentation/',
        'free_tier': '5 calls/min, 500/day',
        'example': {
            'endpoint': '/query',
            'params': {'function': 'GLOBAL_QUOTE', 'symbol': 'AAPL'}
        }
    },
    
    'finnhub': {
        'name': 'Finnhub (Stocks)',
        'base_url': 'https://finnhub.io/api/v1',
        'auth_type': 'query_param',
        'auth_param': 'token',
        'env_key': 'FINNHUB_API_KEY',
        'docs': 'https://finnhub.io/docs/api',
        'free_tier': '60 calls/min',
    },
    
    'exchangerate': {
        'name': 'Exchange Rate API',
        'base_url': 'https://v6.exchangerate-api.com/v6',
        'auth_type': 'path',  # Key is in the URL path
        'env_key': 'EXCHANGE_RATE_API_KEY',
        'docs': 'https://www.exchangerate-api.com/docs',
        'free_tier': '1500 calls/month',
    },
    
    # News
    'newsapi': {
        'name': 'News API',
        'base_url': 'https://newsapi.org/v2',
        'auth_type': 'header',
        'auth_header': 'X-Api-Key',
        'env_key': 'NEWS_API_KEY',
        'docs': 'https://newsapi.org/docs',
        'free_tier': '100 calls/day (dev only)',
        'example': {
            'endpoint': '/top-headlines',
            'params': {'country': 'us'}
        }
    },
    
    # Images
    'unsplash': {
        'name': 'Unsplash (Images)',
        'base_url': 'https://api.unsplash.com',
        'auth_type': 'header',
        'auth_header': 'Authorization',
        'auth_prefix': 'Client-ID ',
        'env_key': 'UNSPLASH_ACCESS_KEY',
        'docs': 'https://unsplash.com/documentation',
        'free_tier': '50 calls/hour',
    },
    
    'giphy': {
        'name': 'Giphy (GIFs)',
        'base_url': 'https://api.giphy.com/v1',
        'auth_type': 'query_param',
        'auth_param': 'api_key',
        'env_key': 'GIPHY_API_KEY',
        'docs': 'https://developers.giphy.com/docs/api',
        'free_tier': 'Unlimited with attribution',
    },
    
    # Entertainment
    'tmdb': {
        'name': 'TMDB (Movies)',
        'base_url': 'https://api.themoviedb.org/3',
        'auth_type': 'query_param',
        'auth_param': 'api_key',
        'env_key': 'TMDB_API_KEY',
        'docs': 'https://developers.themoviedb.org/3',
        'free_tier': 'Unlimited',
    },
    
    'spotify': {
        'name': 'Spotify',
        'base_url': 'https://api.spotify.com/v1',
        'auth_type': 'bearer',
        'env_key': 'SPOTIFY_ACCESS_TOKEN',
        'requires_oauth': True,
        'docs': 'https://developer.spotify.com/documentation/web-api',
    },
    
    # Utilities
    'ipinfo': {
        'name': 'IP Info (Geolocation)',
        'base_url': 'https://ipinfo.io',
        'auth_type': 'query_param',
        'auth_param': 'token',
        'env_key': 'IPINFO_TOKEN',
        'docs': 'https://ipinfo.io/developers',
        'free_tier': '50k calls/month',
    },
    
    # Food
    'spoonacular': {
        'name': 'Spoonacular (Recipes)',
        'base_url': 'https://api.spoonacular.com',
        'auth_type': 'query_param',
        'auth_param': 'apiKey',
        'env_key': 'SPOONACULAR_API_KEY',
        'docs': 'https://spoonacular.com/food-api',
        'free_tier': '150 calls/day',
    },
    
    # AI
    'openai': {
        'name': 'OpenAI',
        'base_url': 'https://api.openai.com/v1',
        'auth_type': 'bearer',
        'env_key': 'OPENAI_API_KEY',
        'docs': 'https://platform.openai.com/docs',
        'requires_user_key': False,  # Platform provides
    },
    
    # No-key services (free, no auth needed)
    'yahoo_finance': {
        'name': 'Yahoo Finance (No Key)',
        'base_url': 'https://query1.finance.yahoo.com/v8/finance',
        'auth_type': 'none',
        'headers': {'User-Agent': 'Mozilla/5.0'},
        'docs': 'Unofficial API - no key needed',
    },
    
    'coindesk': {
        'name': 'CoinDesk Bitcoin',
        'base_url': 'https://api.coindesk.com/v1',
        'auth_type': 'none',
        'docs': 'https://www.coindesk.com/coindesk-api',
    },
    
    'coingecko': {
        'name': 'CoinGecko (Crypto)',
        'base_url': 'https://api.coingecko.com/api/v3',
        'auth_type': 'none',
        'docs': 'https://www.coingecko.com/en/api',
        'free_tier': '10-50 calls/min',
    },
    
    'restcountries': {
        'name': 'REST Countries',
        'base_url': 'https://restcountries.com/v3.1',
        'auth_type': 'none',
        'docs': 'https://restcountries.com/',
    },
    
    'jsonplaceholder': {
        'name': 'JSON Placeholder (Test)',
        'base_url': 'https://jsonplaceholder.typicode.com',
        'auth_type': 'none',
        'docs': 'https://jsonplaceholder.typicode.com/',
    },
}


def get_service(name: str) -> dict:
    """Get service configuration by name"""
    return SERVICES.get(name.lower())


def get_api_key(service_config: dict) -> str:
    """Get API key for a service from environment"""
    env_key = service_config.get('env_key')
    if not env_key:
        return None
    return os.environ.get(env_key, '')


def list_services() -> list:
    """List all available services"""
    result = []
    for key, config in SERVICES.items():
        has_key = bool(get_api_key(config)) if config.get('env_key') else True
        result.append({
            'id': key,
            'name': config['name'],
            'docs': config.get('docs', ''),
            'free_tier': config.get('free_tier', 'Unknown'),
            'configured': has_key,
            'requires_user_key': config.get('requires_user_key', False),
        })
    return result



