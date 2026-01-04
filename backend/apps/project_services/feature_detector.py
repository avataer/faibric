"""
Feature Detector
Analyzes user prompts to determine which project services are needed.
"""
import re
from typing import Dict, List, Set
from dataclasses import dataclass, field


@dataclass
class RequiredFeatures:
    """Features required for a project based on prompt analysis."""
    needs_database: bool = False
    needs_auth: bool = False
    needs_payments: bool = False
    needs_storage: bool = False
    needs_realtime: bool = False
    
    # Specific configurations
    database_tables: List[str] = field(default_factory=list)
    auth_providers: List[str] = field(default_factory=list)
    payment_type: str = ''  # 'one-time', 'subscription', ''
    storage_type: str = ''  # 'images', 'files', ''
    
    # Detected keywords for context
    detected_keywords: List[str] = field(default_factory=list)


class FeatureDetector:
    """
    Detects required features from user prompts.
    """
    
    # Keywords that indicate database need
    DATABASE_KEYWORDS = {
        'save', 'store', 'persist', 'remember', 'database', 'data',
        'list', 'collection', 'records', 'entries', 'items',
        'todo', 'task', 'note', 'bookmark', 'favorite',
        'blog', 'post', 'article', 'comment', 'review',
        'product', 'inventory', 'order', 'cart', 'wishlist',
        'booking', 'appointment', 'reservation', 'schedule',
        'contact', 'lead', 'customer', 'client', 'subscriber',
        'message', 'chat', 'conversation', 'thread',
        'project', 'issue', 'ticket', 'kanban', 'board',
        'event', 'calendar', 'reminder',
        'form submission', 'survey response', 'feedback',
    }
    
    # Keywords that indicate auth need
    AUTH_KEYWORDS = {
        'login', 'signin', 'sign in', 'sign-in',
        'signup', 'sign up', 'sign-up', 'register', 'registration',
        'user', 'account', 'profile', 'member', 'membership',
        'authentication', 'auth', 'password', 'credential',
        'protected', 'private', 'secure', 'admin', 'role',
        'dashboard', 'my account', 'settings page',
        'google login', 'github login', 'social login',
        'magic link', 'email verification',
    }
    
    # Keywords that indicate payment need
    PAYMENT_KEYWORDS = {
        'payment', 'pay', 'checkout', 'purchase', 'buy',
        'subscription', 'subscribe', 'plan', 'pricing',
        'stripe', 'credit card', 'billing',
        '$', 'price', 'cost', 'fee',
        'premium', 'pro', 'upgrade', 'tier',
        'saas', 'membership', 'paywall',
        'e-commerce', 'ecommerce', 'shop', 'store',
        'cart', 'order', 'invoice',
        'one-time', 'monthly', 'yearly', 'annual',
    }
    
    # Keywords that indicate storage need
    STORAGE_KEYWORDS = {
        'upload', 'file', 'image', 'photo', 'picture',
        'document', 'pdf', 'attachment', 'media',
        'avatar', 'profile picture', 'cover photo',
        'gallery', 'portfolio', 'album',
        'download', 'export', 'import',
        'drag and drop', 'file picker',
    }
    
    # Keywords that indicate realtime need
    REALTIME_KEYWORDS = {
        'real-time', 'realtime', 'real time', 'live',
        'notification', 'push', 'alert',
        'chat', 'messaging', 'instant',
        'collaborative', 'multiplayer', 'sync',
        'presence', 'online status', 'typing indicator',
    }
    
    def detect(self, prompt: str) -> RequiredFeatures:
        """
        Analyze a prompt and return required features.
        """
        prompt_lower = prompt.lower()
        features = RequiredFeatures()
        
        # Check database keywords
        for keyword in self.DATABASE_KEYWORDS:
            if keyword in prompt_lower:
                features.needs_database = True
                features.detected_keywords.append(f'db:{keyword}')
        
        # Check auth keywords
        for keyword in self.AUTH_KEYWORDS:
            if keyword in prompt_lower:
                features.needs_auth = True
                features.detected_keywords.append(f'auth:{keyword}')
        
        # Detect specific auth providers
        if 'google' in prompt_lower:
            features.auth_providers.append('google')
        if 'github' in prompt_lower:
            features.auth_providers.append('github')
        if 'magic link' in prompt_lower:
            features.auth_providers.append('magic_link')
        if not features.auth_providers and features.needs_auth:
            features.auth_providers = ['email', 'magic_link']
        
        # Check payment keywords
        for keyword in self.PAYMENT_KEYWORDS:
            if keyword in prompt_lower:
                features.needs_payments = True
                features.detected_keywords.append(f'pay:{keyword}')
        
        # Detect payment type
        if features.needs_payments:
            if any(word in prompt_lower for word in ['subscription', 'monthly', 'yearly', 'recurring']):
                features.payment_type = 'subscription'
            elif any(word in prompt_lower for word in ['one-time', 'once', 'single payment']):
                features.payment_type = 'one-time'
            else:
                features.payment_type = 'one-time'  # Default
        
        # Check storage keywords
        for keyword in self.STORAGE_KEYWORDS:
            if keyword in prompt_lower:
                features.needs_storage = True
                features.detected_keywords.append(f'storage:{keyword}')
        
        # Detect storage type
        if features.needs_storage:
            if any(word in prompt_lower for word in ['image', 'photo', 'picture', 'gallery', 'avatar']):
                features.storage_type = 'images'
            else:
                features.storage_type = 'files'
        
        # Check realtime keywords
        for keyword in self.REALTIME_KEYWORDS:
            if keyword in prompt_lower:
                features.needs_realtime = True
                features.detected_keywords.append(f'realtime:{keyword}')
        
        # Detect database tables
        if features.needs_database:
            features.database_tables = self._detect_tables(prompt_lower)
        
        return features
    
    def _detect_tables(self, prompt_lower: str) -> List[str]:
        """Detect what database tables are needed."""
        tables = []
        
        if any(word in prompt_lower for word in ['todo', 'task', 'checklist']):
            tables.append('todos')
        if any(word in prompt_lower for word in ['blog', 'post', 'article']):
            tables.append('posts')
            tables.append('comments')
        if any(word in prompt_lower for word in ['product', 'shop', 'store', 'e-commerce']):
            tables.append('products')
            tables.append('orders')
        if any(word in prompt_lower for word in ['user', 'profile', 'account']):
            tables.append('profiles')
        if any(word in prompt_lower for word in ['booking', 'appointment', 'reservation']):
            tables.append('bookings')
        if any(word in prompt_lower for word in ['message', 'chat', 'conversation']):
            tables.append('messages')
        if any(word in prompt_lower for word in ['project', 'kanban', 'board']):
            tables.append('projects')
            tables.append('tasks')
        if any(word in prompt_lower for word in ['contact', 'lead', 'subscriber']):
            tables.append('contacts')
        
        # Default table if none detected
        if not tables:
            tables.append('items')
        
        return tables
    
    def generate_feature_summary(self, features: RequiredFeatures) -> str:
        """Generate a human-readable summary of detected features."""
        lines = []
        
        if features.needs_database:
            tables = ', '.join(features.database_tables) if features.database_tables else 'custom'
            lines.append(f"Database: Supabase (tables: {tables})")
        
        if features.needs_auth:
            providers = ', '.join(features.auth_providers) if features.auth_providers else 'email'
            lines.append(f"Authentication: {providers}")
        
        if features.needs_payments:
            lines.append(f"Payments: Stripe ({features.payment_type})")
        
        if features.needs_storage:
            lines.append(f"Storage: {features.storage_type}")
        
        if features.needs_realtime:
            lines.append("Realtime: WebSocket subscriptions")
        
        if not lines:
            lines.append("Static site (no backend services)")
        
        return '\n'.join(lines)


# Singleton
feature_detector = FeatureDetector()



