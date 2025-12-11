"""
LLM Configuration for Faibric.

Primary: Claude Opus 4.5 for code generation
Secondary: Best LLM per task type
"""
from enum import Enum
from typing import Dict, Optional
from dataclasses import dataclass


class TaskType(Enum):
    """Types of AI tasks in Faibric."""
    CODE_GENERATION = "code_generation"
    CODE_MODIFICATION = "code_modification"
    CODE_ANALYSIS = "code_analysis"
    CODE_EXPLANATION = "code_explanation"
    CODE_DEBUG = "code_debug"
    AI_CHAT = "ai_chat"
    SUMMARIZATION = "summarization"
    EMBEDDING = "embedding"


@dataclass
class LLMConfig:
    """Configuration for an LLM."""
    provider: str
    model: str
    max_tokens: int
    temperature: float
    description: str
    cost_per_1k_input: float
    cost_per_1k_output: float


# LLM Configurations
LLMS = {
    # Anthropic Models
    "claude-opus-4.5": LLMConfig(
        provider="anthropic",
        model="claude-sonnet-4-20250514",  # Opus 4.5 model ID
        max_tokens=8192,
        temperature=0.2,
        description="Claude Opus 4.5 - Best for complex code generation",
        cost_per_1k_input=0.015,
        cost_per_1k_output=0.075,
    ),
    "claude-sonnet-4": LLMConfig(
        provider="anthropic",
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        temperature=0.3,
        description="Claude Sonnet 4 - Fast, good for chat",
        cost_per_1k_input=0.003,
        cost_per_1k_output=0.015,
    ),
    "claude-haiku-3.5": LLMConfig(
        provider="anthropic",
        model="claude-3-5-haiku-20241022",
        max_tokens=4096,
        temperature=0.3,
        description="Claude Haiku 3.5 - Ultra fast, good for simple tasks",
        cost_per_1k_input=0.0008,
        cost_per_1k_output=0.004,
    ),
    
    # OpenAI Models (for embeddings only)
    "text-embedding-3-small": LLMConfig(
        provider="openai",
        model="text-embedding-3-small",
        max_tokens=8191,
        temperature=0,
        description="OpenAI embeddings - Best for semantic search",
        cost_per_1k_input=0.00002,
        cost_per_1k_output=0,
    ),
}


# Task to LLM mapping - Optimized for quality and cost
TASK_LLM_MAP: Dict[TaskType, str] = {
    # Code tasks - Use Claude Opus 4.5 (best code quality)
    TaskType.CODE_GENERATION: "claude-opus-4.5",
    TaskType.CODE_MODIFICATION: "claude-opus-4.5",
    TaskType.CODE_ANALYSIS: "claude-opus-4.5",
    TaskType.CODE_DEBUG: "claude-opus-4.5",
    
    # Explanation - Opus for thorough explanations
    TaskType.CODE_EXPLANATION: "claude-opus-4.5",
    
    # Chat - Sonnet for speed + quality balance
    TaskType.AI_CHAT: "claude-sonnet-4",
    
    # Summarization - Haiku for speed (simpler task)
    TaskType.SUMMARIZATION: "claude-haiku-3.5",
    
    # Embeddings - OpenAI (best embedding model)
    TaskType.EMBEDDING: "text-embedding-3-small",
}


def get_llm_for_task(task_type: TaskType) -> LLMConfig:
    """Get the optimal LLM configuration for a task type."""
    llm_name = TASK_LLM_MAP.get(task_type, "claude-opus-4.5")
    return LLMS[llm_name]


def get_llm_by_name(name: str) -> Optional[LLMConfig]:
    """Get LLM configuration by name."""
    return LLMS.get(name)


# Provider API clients
class LLMClient:
    """Unified LLM client for all providers."""
    
    def __init__(self):
        self._anthropic_client = None
        self._openai_client = None
    
    @property
    def anthropic(self):
        if self._anthropic_client is None:
            import anthropic
            from django.conf import settings
            self._anthropic_client = anthropic.Anthropic(
                api_key=settings.ANTHROPIC_API_KEY
            )
        return self._anthropic_client
    
    @property
    def openai(self):
        if self._openai_client is None:
            import openai
            from django.conf import settings
            self._openai_client = openai.OpenAI(
                api_key=settings.OPENAI_API_KEY
            )
        return self._openai_client
    
    def generate(
        self,
        task_type: TaskType,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = None,
        temperature: float = None,
    ) -> Dict:
        """
        Generate a response using the optimal LLM for the task.
        
        Returns:
            {
                "content": str,
                "model": str,
                "input_tokens": int,
                "output_tokens": int,
                "provider": str,
            }
        """
        config = get_llm_for_task(task_type)
        
        if config.provider == "anthropic":
            return self._generate_anthropic(
                config,
                prompt,
                system_prompt,
                max_tokens or config.max_tokens,
                temperature if temperature is not None else config.temperature,
            )
        elif config.provider == "openai":
            return self._generate_openai(
                config,
                prompt,
                system_prompt,
                max_tokens or config.max_tokens,
                temperature if temperature is not None else config.temperature,
            )
        else:
            raise ValueError(f"Unknown provider: {config.provider}")
    
    def _generate_anthropic(
        self,
        config: LLMConfig,
        prompt: str,
        system_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> Dict:
        """Generate using Anthropic Claude."""
        message = self.anthropic.messages.create(
            model=config.model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt or "You are a helpful AI assistant.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return {
            "content": message.content[0].text,
            "model": config.model,
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
            "provider": "anthropic",
        }
    
    def _generate_openai(
        self,
        config: LLMConfig,
        prompt: str,
        system_prompt: str,
        max_tokens: int,
        temperature: float,
    ) -> Dict:
        """Generate using OpenAI."""
        response = self.openai.chat.completions.create(
            model=config.model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt or "You are a helpful AI assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        
        return {
            "content": response.choices[0].message.content,
            "model": config.model,
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "provider": "openai",
        }
    
    def embed(self, text: str) -> list:
        """Generate embeddings using OpenAI."""
        response = self.openai.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding


# Global client instance
llm_client = LLMClient()


# Convenience functions
def generate_code(prompt: str, system_prompt: str = "") -> Dict:
    """Generate code using Claude Opus 4.5."""
    return llm_client.generate(
        TaskType.CODE_GENERATION,
        prompt,
        system_prompt or "You are an expert software engineer. Generate clean, well-documented code.",
    )


def modify_code(prompt: str, code: str) -> Dict:
    """Modify existing code using Claude Opus 4.5."""
    full_prompt = f"Here is the existing code:\n\n```\n{code}\n```\n\nModification request: {prompt}"
    return llm_client.generate(
        TaskType.CODE_MODIFICATION,
        full_prompt,
        "You are an expert software engineer. Modify the code as requested, maintaining style and quality.",
    )


def analyze_code(code: str, question: str = "") -> Dict:
    """Analyze code using Claude Opus 4.5."""
    prompt = f"Analyze this code:\n\n```\n{code}\n```"
    if question:
        prompt += f"\n\nSpecific question: {question}"
    
    return llm_client.generate(
        TaskType.CODE_ANALYSIS,
        prompt,
        "You are an expert code analyst. Provide thorough analysis.",
    )


def chat(message: str, context: str = "") -> Dict:
    """AI chat using Claude Sonnet 4."""
    return llm_client.generate(
        TaskType.AI_CHAT,
        message,
        context or "You are a helpful AI assistant for a software development platform.",
    )


def embed_text(text: str) -> list:
    """Generate embeddings using OpenAI."""
    return llm_client.embed(text)







