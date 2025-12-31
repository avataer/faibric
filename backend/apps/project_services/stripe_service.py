"""
Stripe Payment Integration Service
Handle payment setup for customer projects.
"""
import os
import stripe
from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class ProductDefinition:
    name: str
    description: str
    price_cents: int
    currency: str = 'usd'
    recurring: Optional[str] = None  # 'month', 'year', None for one-time


@dataclass
class CheckoutConfig:
    product_id: str
    price_id: str
    success_url: str
    cancel_url: str
    mode: str  # 'payment' or 'subscription'


class StripeService:
    """
    Manages Stripe Connect accounts and payment setup.
    """
    
    def __init__(self):
        self.api_key = os.environ.get('STRIPE_SECRET_KEY', '')
        self.connect_client_id = os.environ.get('STRIPE_CONNECT_CLIENT_ID', '')
        
        if self.api_key:
            stripe.api_key = self.api_key
    
    def create_connect_account(self, project_id: str, email: str) -> Dict[str, Any]:
        """
        Create a Stripe Connect Express account for a project owner.
        """
        if not self.api_key:
            return self._mock_create_account(project_id)
        
        try:
            account = stripe.Account.create(
                type='express',
                email=email,
                metadata={'faibric_project_id': project_id},
                capabilities={
                    'card_payments': {'requested': True},
                    'transfers': {'requested': True},
                },
            )
            
            return {
                'account_id': account.id,
                'status': 'pending',
                'onboarding_url': self._get_onboarding_url(account.id)
            }
        except stripe.error.StripeError as e:
            return {'error': str(e)}
    
    def _get_onboarding_url(self, account_id: str) -> str:
        """Get the Stripe Connect onboarding URL."""
        try:
            link = stripe.AccountLink.create(
                account=account_id,
                refresh_url='https://faibric.com/stripe/refresh',
                return_url='https://faibric.com/stripe/complete',
                type='account_onboarding',
            )
            return link.url
        except stripe.error.StripeError:
            return ''
    
    def create_product(self, account_id: str, product: ProductDefinition) -> Dict[str, Any]:
        """
        Create a Stripe product and price.
        """
        if not self.api_key:
            return self._mock_create_product(product)
        
        try:
            # Create product
            stripe_product = stripe.Product.create(
                name=product.name,
                description=product.description,
                stripe_account=account_id if account_id else None
            )
            
            # Create price
            price_data = {
                'product': stripe_product.id,
                'unit_amount': product.price_cents,
                'currency': product.currency,
            }
            
            if product.recurring:
                price_data['recurring'] = {'interval': product.recurring}
            
            stripe_price = stripe.Price.create(
                **price_data,
                stripe_account=account_id if account_id else None
            )
            
            return {
                'product_id': stripe_product.id,
                'price_id': stripe_price.id,
                'name': product.name,
                'price_cents': product.price_cents,
                'recurring': product.recurring
            }
        except stripe.error.StripeError as e:
            return {'error': str(e)}
    
    def generate_checkout_code(self, config: CheckoutConfig) -> str:
        """
        Generate JavaScript code for Stripe Checkout integration.
        """
        return f'''
// Stripe Checkout Integration
const STRIPE_PUBLISHABLE_KEY = "pk_test_YOUR_KEY";  // Replace with your key

const initStripe = () => {{
  return Stripe(STRIPE_PUBLISHABLE_KEY);
}};

const checkout = async () => {{
  const stripe = initStripe();
  
  // Create checkout session via your backend
  const response = await fetch("/api/create-checkout-session", {{
    method: "POST",
    headers: {{ "Content-Type": "application/json" }},
    body: JSON.stringify({{
      priceId: "{config.price_id}",
      mode: "{config.mode}"
    }})
  }});
  
  const {{ sessionId }} = await response.json();
  
  // Redirect to Stripe Checkout
  const {{ error }} = await stripe.redirectToCheckout({{ sessionId }});
  
  if (error) {{
    console.error("Checkout error:", error);
  }}
}};

// Checkout button component
const CheckoutButton = ({{ label = "Subscribe", className = "" }}) => (
  <button 
    onClick={{checkout}}
    className={{`bg-indigo-600 text-white px-6 py-3 rounded-lg hover:bg-indigo-700 ${{className}}`}}
  >
    {{label}}
  </button>
);
'''
    
    def generate_products_from_prompt(self, user_prompt: str) -> List[ProductDefinition]:
        """
        Analyze user prompt and generate product definitions.
        
        Examples:
        - "$29/month subscription" -> ProductDefinition with recurring='month'
        - "$99 one-time" -> ProductDefinition with recurring=None
        """
        import re
        
        products = []
        prompt_lower = user_prompt.lower()
        
        # Find price patterns
        price_patterns = [
            r'\$(\d+(?:\.\d{2})?)\s*(?:per\s+|/)?(month|year|yearly|annual)?',
            r'(\d+(?:\.\d{2})?)\s*(?:dollars?|usd)\s*(?:per\s+|/)?(month|year|yearly|annual)?',
        ]
        
        for pattern in price_patterns:
            matches = re.findall(pattern, prompt_lower)
            for match in matches:
                price = float(match[0])
                interval = match[1] if len(match) > 1 else None
                
                recurring = None
                if interval in ['month', 'monthly']:
                    recurring = 'month'
                elif interval in ['year', 'yearly', 'annual']:
                    recurring = 'year'
                
                # Determine product name from context
                name = "Subscription" if recurring else "One-time Purchase"
                if 'pro' in prompt_lower:
                    name = "Pro Plan"
                elif 'premium' in prompt_lower:
                    name = "Premium Plan"
                elif 'basic' in prompt_lower:
                    name = "Basic Plan"
                elif 'starter' in prompt_lower:
                    name = "Starter Plan"
                
                products.append(ProductDefinition(
                    name=name,
                    description=f"{'Monthly' if recurring == 'month' else 'Annual' if recurring == 'year' else 'One-time'} access",
                    price_cents=int(price * 100),
                    recurring=recurring
                ))
        
        return products
    
    def _mock_create_account(self, project_id: str) -> Dict[str, Any]:
        """Mock account creation for development."""
        return {
            'account_id': f'acct_mock_{project_id[:8]}',
            'status': 'pending',
            'onboarding_url': 'https://connect.stripe.com/setup/mock'
        }
    
    def _mock_create_product(self, product: ProductDefinition) -> Dict[str, Any]:
        """Mock product creation for development."""
        import hashlib
        prod_id = hashlib.md5(product.name.encode()).hexdigest()[:8]
        
        return {
            'product_id': f'prod_mock_{prod_id}',
            'price_id': f'price_mock_{prod_id}',
            'name': product.name,
            'price_cents': product.price_cents,
            'recurring': product.recurring
        }


# Singleton
stripe_service = StripeService()

