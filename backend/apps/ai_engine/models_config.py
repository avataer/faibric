import logging
logger = logging.getLogger(__name__)

AI_MODELS = {
    "claude-opus": {
        "id": "claude-opus-4-6",
        "name": "Claude Opus 4.6",
        "provider": "anthropic",
        "description": "Most powerful, best for complex apps",
        "credits_per_request": 3,
        "max_tokens": 8192,
    },
    "claude-sonnet": {
        "id": "claude-sonnet-4-5-20250929",
        "name": "Claude Sonnet 4.5",
        "provider": "anthropic",
        "description": "Balanced power and speed",
        "credits_per_request": 2,
        "max_tokens": 8192,
    },
    "claude-haiku": {
        "id": "claude-haiku-4-5-20251001",
        "name": "Claude Haiku 4.5",
        "provider": "anthropic",
        "description": "Fast and economical",
        "credits_per_request": 1,
        "max_tokens": 4096,
    },
    "gpt-4o": {
        "id": "gpt-4o",
        "name": "GPT-4o",
        "provider": "openai",
        "description": "OpenAI's most capable multimodal model",
        "credits_per_request": 2,
        "max_tokens": 4096,
    },
    "gemini-2-flash": {
        "id": "gemini-2.0-flash",
        "name": "Gemini 2.0 Flash",
        "provider": "google",
        "description": "Google's fast and efficient model",
        "credits_per_request": 1,
        "max_tokens": 8192,
    },
}

DEFAULT_MODEL = "claude-opus"

CODE_MODEL = AI_MODELS[DEFAULT_MODEL]["id"]
CODE_MODEL_NAME = AI_MODELS[DEFAULT_MODEL]["name"]

CHAT_MODEL = AI_MODELS["claude-haiku"]["id"]
CHAT_MODEL_NAME = AI_MODELS["claude-haiku"]["name"]

def get_model_config(model_key):
    return AI_MODELS.get(model_key, AI_MODELS[DEFAULT_MODEL])

def get_model_id(model_key):
    config = get_model_config(model_key)
    return config["id"]

def get_available_models():
    return [{"key": k, **v} for k, v in AI_MODELS.items()]

def get_code_model():
    return CODE_MODEL

def get_chat_model():
    return CHAT_MODEL

def get_model_by_provider(provider):
    """Get all models for a specific provider (anthropic, openai, google)."""
    return [{"key": k, **v} for k, v in AI_MODELS.items() if v["provider"] == provider]

logger.info(f"AI Models configured: CODE={CODE_MODEL}, CHAT={CHAT_MODEL}")
