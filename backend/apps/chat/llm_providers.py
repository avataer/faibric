"""
Multi-LLM providers for the chat service.
Supports OpenAI, Anthropic (Claude), Google Gemini, and xAI Grok.
"""
import json
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Generator
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Standardized response from any LLM."""
    content: str
    model: str
    tokens_used: int
    finish_reason: str = 'stop'


@dataclass
class ChatMessage:
    """A message in a conversation."""
    role: str  # 'system', 'user', 'assistant'
    content: str


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, api_key: str, model: str = None):
        self.api_key = api_key
        self.model = model or self.default_model
    
    @property
    @abstractmethod
    def default_model(self) -> str:
        pass
    
    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass
    
    @abstractmethod
    def chat(self, messages: List[ChatMessage], **kwargs) -> LLMResponse:
        """Send a chat completion request."""
        pass
    
    def _validate_api_key(self):
        if not self.api_key:
            raise ValueError(f"API key not configured for {self.provider_name}")


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT models."""
    
    @property
    def default_model(self) -> str:
        return 'gpt-4o-mini'
    
    @property
    def provider_name(self) -> str:
        return 'OpenAI'
    
    def chat(self, messages: List[ChatMessage], **kwargs) -> LLMResponse:
        self._validate_api_key()
        
        import openai
        
        client = openai.OpenAI(api_key=self.api_key)
        
        formatted_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=formatted_messages,
                max_tokens=kwargs.get('max_tokens', 1024),
                temperature=kwargs.get('temperature', 0.7),
            )
            
            return LLMResponse(
                content=response.choices[0].message.content,
                model=response.model,
                tokens_used=response.usage.total_tokens,
                finish_reason=response.choices[0].finish_reason or 'stop'
            )
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            raise


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude models."""
    
    @property
    def default_model(self) -> str:
        return 'claude-3-haiku-20240307'
    
    @property
    def provider_name(self) -> str:
        return 'Anthropic'
    
    def chat(self, messages: List[ChatMessage], **kwargs) -> LLMResponse:
        self._validate_api_key()
        
        import requests
        
        # Extract system message
        system_prompt = ""
        conversation = []
        
        for msg in messages:
            if msg.role == 'system':
                system_prompt = msg.content
            else:
                conversation.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": self.model,
                    "max_tokens": kwargs.get('max_tokens', 1024),
                    "system": system_prompt,
                    "messages": conversation
                },
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            
            return LLMResponse(
                content=data['content'][0]['text'],
                model=data['model'],
                tokens_used=data['usage']['input_tokens'] + data['usage']['output_tokens'],
                finish_reason=data['stop_reason'] or 'stop'
            )
        except Exception as e:
            logger.error(f"Anthropic error: {e}")
            raise


class GeminiProvider(BaseLLMProvider):
    """Google Gemini models."""
    
    @property
    def default_model(self) -> str:
        return 'gemini-1.5-flash'
    
    @property
    def provider_name(self) -> str:
        return 'Google Gemini'
    
    def chat(self, messages: List[ChatMessage], **kwargs) -> LLMResponse:
        self._validate_api_key()
        
        import requests
        
        # Convert messages to Gemini format
        # Gemini uses 'user' and 'model' roles, system goes in instruction
        system_instruction = ""
        contents = []
        
        for msg in messages:
            if msg.role == 'system':
                system_instruction = msg.content
            else:
                role = 'model' if msg.role == 'assistant' else 'user'
                contents.append({
                    "role": role,
                    "parts": [{"text": msg.content}]
                })
        
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"
            
            payload = {"contents": contents}
            if system_instruction:
                payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
            
            payload["generationConfig"] = {
                "maxOutputTokens": kwargs.get('max_tokens', 1024),
                "temperature": kwargs.get('temperature', 0.7),
            }
            
            response = requests.post(
                url,
                params={"key": self.api_key},
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            
            content = data['candidates'][0]['content']['parts'][0]['text']
            
            # Gemini doesn't return token counts in all cases
            tokens = data.get('usageMetadata', {}).get('totalTokenCount', 0)
            
            return LLMResponse(
                content=content,
                model=self.model,
                tokens_used=tokens,
                finish_reason=data['candidates'][0].get('finishReason', 'STOP').lower()
            )
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            raise


class GrokProvider(BaseLLMProvider):
    """xAI Grok models."""
    
    @property
    def default_model(self) -> str:
        return 'grok-beta'
    
    @property
    def provider_name(self) -> str:
        return 'xAI Grok'
    
    def chat(self, messages: List[ChatMessage], **kwargs) -> LLMResponse:
        self._validate_api_key()
        
        import requests
        
        formatted_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]
        
        try:
            # Grok uses OpenAI-compatible API
            response = requests.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json={
                    "model": self.model,
                    "messages": formatted_messages,
                    "max_tokens": kwargs.get('max_tokens', 1024),
                    "temperature": kwargs.get('temperature', 0.7),
                },
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            
            return LLMResponse(
                content=data['choices'][0]['message']['content'],
                model=data['model'],
                tokens_used=data['usage']['total_tokens'],
                finish_reason=data['choices'][0].get('finish_reason', 'stop')
            )
        except Exception as e:
            logger.error(f"Grok error: {e}")
            raise


# Model configurations
MODEL_CONFIGS = {
    'openai': {
        'gpt-4o': {'max_tokens': 4096, 'description': 'Most capable GPT-4 model'},
        'gpt-4o-mini': {'max_tokens': 4096, 'description': 'Fast and affordable'},
        'gpt-4-turbo': {'max_tokens': 4096, 'description': 'GPT-4 Turbo'},
        'gpt-3.5-turbo': {'max_tokens': 4096, 'description': 'Fast, legacy model'},
    },
    'anthropic': {
        'claude-3-5-sonnet-20241022': {'max_tokens': 4096, 'description': 'Most intelligent Claude'},
        'claude-3-haiku-20240307': {'max_tokens': 4096, 'description': 'Fast and affordable'},
        'claude-3-opus-20240229': {'max_tokens': 4096, 'description': 'Most capable Claude'},
    },
    'gemini': {
        'gemini-1.5-pro': {'max_tokens': 8192, 'description': 'Most capable Gemini'},
        'gemini-1.5-flash': {'max_tokens': 8192, 'description': 'Fast and affordable'},
        'gemini-1.0-pro': {'max_tokens': 2048, 'description': 'Stable Gemini 1.0'},
    },
    'grok': {
        'grok-beta': {'max_tokens': 4096, 'description': 'Grok beta model'},
        'grok-2': {'max_tokens': 4096, 'description': 'Grok 2'},
    }
}


def get_provider(provider_name: str, api_key: str, model: str = None) -> BaseLLMProvider:
    """
    Factory function to get the appropriate LLM provider.
    """
    providers = {
        'openai': OpenAIProvider,
        'anthropic': AnthropicProvider,
        'gemini': GeminiProvider,
        'grok': GrokProvider,
    }
    
    provider_class = providers.get(provider_name.lower())
    if not provider_class:
        raise ValueError(f"Unknown provider: {provider_name}")
    
    return provider_class(api_key=api_key, model=model)


def get_available_models() -> Dict[str, List[Dict[str, str]]]:
    """Get all available models organized by provider."""
    result = {}
    for provider, models in MODEL_CONFIGS.items():
        result[provider] = [
            {'id': model_id, **config}
            for model_id, config in models.items()
        ]
    return result









