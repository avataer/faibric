"""
Investment Calculator Service
Calculates investment returns using real stock data
"""
import requests
from datetime import datetime, timedelta
from django.core.cache import cache


def get_stock_price_at_date(symbol: str, date_str: str = None) -> dict:
    """
    Get stock price at a specific date or current price
    Returns: { symbol, price, date, currency }
    """
    try:
        # Yahoo Finance API
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        if date_str:
            # Parse date and get historical price
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
            # Get range that includes the date
            start_ts = int((target_date - timedelta(days=5)).timestamp())
            end_ts = int((target_date + timedelta(days=5)).timestamp())
            
            params = {
                'period1': start_ts,
                'period2': end_ts,
                'interval': '1d'
            }
        else:
            # Get current price
            params = {'range': '1d', 'interval': '1d'}
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        data = response.json()
        
        if 'chart' not in data or 'result' not in data['chart'] or not data['chart']['result']:
            return {'error': f'No data for {symbol}'}
        
        result = data['chart']['result'][0]
        meta = result.get('meta', {})
        
        if date_str:
            # Get historical price from timestamps
            timestamps = result.get('timestamp', [])
            closes = result.get('indicators', {}).get('quote', [{}])[0].get('close', [])
            
            if timestamps and closes:
                # Find closest date
                for i, ts in enumerate(timestamps):
                    ts_date = datetime.fromtimestamp(ts)
                    if ts_date.date() >= target_date.date():
                        price = closes[i] if i < len(closes) else closes[-1]
                        if price:
                            return {
                                'symbol': symbol.upper(),
                                'price': round(price, 2),
                                'date': ts_date.strftime("%Y-%m-%d"),
                                'currency': meta.get('currency', 'USD')
                            }
            
            # Fallback to first available
            if closes:
                price = next((p for p in closes if p), None)
                if price:
                    return {
                        'symbol': symbol.upper(),
                        'price': round(price, 2),
                        'date': date_str,
                        'currency': meta.get('currency', 'USD')
                    }
        else:
            # Current price
            price = meta.get('regularMarketPrice')
            if price:
                return {
                    'symbol': symbol.upper(),
                    'price': round(price, 2),
                    'date': datetime.now().strftime("%Y-%m-%d"),
                    'currency': meta.get('currency', 'USD')
                }
        
        return {'error': f'Could not get price for {symbol}'}
        
    except Exception as e:
        return {'error': str(e)}


def calculate_investment(symbol: str, amount: float, start_date: str, end_date: str = None) -> dict:
    """
    Calculate investment return
    
    Args:
        symbol: Stock ticker (AAPL, TSLA, etc.)
        amount: Amount invested in USD
        start_date: When you bought (YYYY-MM-DD)
        end_date: When to check value (YYYY-MM-DD or None for today)
    
    Returns: {
        symbol, invested_amount, 
        start_price, start_date,
        end_price, end_date,
        current_value, profit_loss, percent_change,
        shares_owned
    }
    """
    # Get start price
    start_data = get_stock_price_at_date(symbol, start_date)
    if 'error' in start_data:
        return start_data
    
    # Get end price
    end_data = get_stock_price_at_date(symbol, end_date)
    if 'error' in end_data:
        return end_data
    
    start_price = start_data['price']
    end_price = end_data['price']
    
    # Calculate
    shares = amount / start_price
    current_value = shares * end_price
    profit_loss = current_value - amount
    percent_change = ((end_price - start_price) / start_price) * 100
    
    return {
        'symbol': symbol.upper(),
        'invested_amount': round(amount, 2),
        'shares_owned': round(shares, 4),
        'start_price': round(start_price, 2),
        'start_date': start_data['date'],
        'end_price': round(end_price, 2),
        'end_date': end_data['date'],
        'current_value': round(current_value, 2),
        'profit_loss': round(profit_loss, 2),
        'percent_change': round(percent_change, 2),
        'currency': start_data.get('currency', 'USD')
    }


def calculate_portfolio(investments: list) -> dict:
    """
    Calculate multiple investments
    
    Args:
        investments: [
            { "symbol": "AAPL", "amount": 5000, "start_date": "2024-01-02" },
            { "symbol": "TSLA", "amount": 3000, "start_date": "2024-01-02" },
        ]
    
    Returns: {
        stocks: [ individual calculations ],
        total_invested, total_current_value, total_profit_loss, total_percent_change
    }
    """
    results = []
    total_invested = 0
    total_current = 0
    
    for inv in investments:
        result = calculate_investment(
            symbol=inv['symbol'],
            amount=inv['amount'],
            start_date=inv['start_date'],
            end_date=inv.get('end_date')
        )
        results.append(result)
        
        if 'error' not in result:
            total_invested += result['invested_amount']
            total_current += result['current_value']
    
    total_profit = total_current - total_invested
    total_percent = ((total_current - total_invested) / total_invested * 100) if total_invested > 0 else 0
    
    return {
        'stocks': results,
        'total_invested': round(total_invested, 2),
        'total_current_value': round(total_current, 2),
        'total_profit_loss': round(total_profit, 2),
        'total_percent_change': round(total_percent, 2)
    }



