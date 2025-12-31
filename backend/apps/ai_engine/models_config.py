"""
FAIBRIC AI MODEL CONFIGURATION
==============================
THIS IS THE SINGLE SOURCE OF TRUTH FOR ALL AI MODELS.
DO NOT DEFINE MODEL IDs ANYWHERE ELSE.

Models:
- CODE: Claude Opus 4.5 (claude-opus-4-5-20251101) - BEST for code generation
- CHAT: Claude Haiku 4.5 (claude-haiku-4-5-20251001) - Fast for user chat

NEVER CHANGE THESE WITHOUT EXPLICIT APPROVAL FROM ABRAM.
"""

# ============================================================
# OFFICIAL MODEL IDs - DO NOT CHANGE
# ============================================================

# Claude Opus 4.5 - For ALL code generation
CODE_MODEL = "claude-opus-4-5-20251101"
CODE_MODEL_NAME = "Claude Opus 4.5"

# Claude Haiku 4.5 - For chat, classification, summaries
CHAT_MODEL = "claude-haiku-4-5-20251001"
CHAT_MODEL_NAME = "Claude Haiku 4.5"

# ============================================================
# VALIDATION - Runs on import to catch errors early
# ============================================================

def validate_models():
    """Validate model IDs are correct format."""
    errors = []
    
    # Opus 4.5 must contain 'opus-4-5'
    if 'opus-4-5' not in CODE_MODEL:
        errors.append(f"CODE_MODEL '{CODE_MODEL}' does not contain 'opus-4-5' - WRONG MODEL!")
    
    # Haiku 4.5 must contain 'haiku-4-5'  
    if 'haiku-4-5' not in CHAT_MODEL:
        errors.append(f"CHAT_MODEL '{CHAT_MODEL}' does not contain 'haiku-4-5' - WRONG MODEL!")
    
    # Models must not be sonnet (common mistake)
    if 'sonnet' in CODE_MODEL.lower():
        errors.append(f"CODE_MODEL '{CODE_MODEL}' contains 'sonnet' - MUST BE OPUS!")
    
    if errors:
        error_msg = "\n".join(errors)
        raise ValueError(f"MODEL CONFIGURATION ERROR:\n{error_msg}")
    
    return True

# Run validation on import
validate_models()

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_code_model() -> str:
    """Get the model for code generation (Opus 4.5)."""
    return CODE_MODEL

def get_chat_model() -> str:
    """Get the model for chat/classification (Haiku 4.5)."""
    return CHAT_MODEL

def get_model_for_task(task: str) -> str:
    """Get the appropriate model for a task type."""
    code_tasks = ['code', 'generate', 'build', 'create', 'modify', 'fix', 'debug']
    chat_tasks = ['chat', 'classify', 'summarize', 'explain']
    
    task_lower = task.lower()
    
    for t in code_tasks:
        if t in task_lower:
            return CODE_MODEL
    
    for t in chat_tasks:
        if t in task_lower:
            return CHAT_MODEL
    
    # Default to Opus for unknown tasks (better quality)
    return CODE_MODEL


# ============================================================
# STARTUP MESSAGE
# ============================================================
import logging
logger = logging.getLogger(__name__)
logger.info(f"AI Models configured: CODE={CODE_MODEL}, CHAT={CHAT_MODEL}")

