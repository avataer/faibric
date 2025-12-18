"""
Code Library Constants - Single source of truth for thresholds and policies.

ALL thresholds and scoring parameters MUST be defined here.
Do not hardcode values elsewhere.
"""

# =============================================================================
# RETRIEVAL THRESHOLDS
# =============================================================================

# Minimum score to consider a match "good enough" for reuse
REUSE_THRESHOLD_HIGH = 8.0  # Confident reuse - adapt with cheap model

# Score range for "gray zone" - requires gap list review
REUSE_THRESHOLD_LOW = 4.0   # Below this = generate new
GRAY_ZONE_MIN = 4.0
GRAY_ZONE_MAX = 8.0

# Semantic search minimum similarity
SEMANTIC_MIN_SCORE = 0.5

# Keyword match weights
KEYWORD_IN_TEXT_WEIGHT = 2
KEYWORD_IN_TAG_WEIGHT = 3
QUALITY_SCORE_BOOST_FACTOR = 0.5

# =============================================================================
# REGISTRATION POLICIES
# =============================================================================

# Minimum code length to save to library
MIN_CODE_LENGTH_FOR_LIBRARY = 500

# Maximum keywords/tags per item
MAX_KEYWORDS = 20
MAX_TAGS = 10

# Default quality score for AI-generated code
DEFAULT_AI_QUALITY_SCORE = 0.5

# =============================================================================
# VERSIONING POLICIES
# =============================================================================

# Valid version statuses
VERSION_STATUS_ACTIVE = 'active'
VERSION_STATUS_DEPRECATED = 'deprecated'
VERSION_STATUS_DRAFT = 'draft'

VALID_VERSION_STATUSES = [
    VERSION_STATUS_ACTIVE,
    VERSION_STATUS_DEPRECATED,
    VERSION_STATUS_DRAFT,
]

# Semver regex pattern
SEMVER_PATTERN = r'^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9]+))?$'

# =============================================================================
# DUPLICATE DETECTION
# =============================================================================

# Minimum similarity to consider as near-duplicate
DUPLICATE_SIMILARITY_THRESHOLD = 0.85

# Minimum code overlap percentage to flag as duplicate
DUPLICATE_CODE_OVERLAP_THRESHOLD = 0.80

# =============================================================================
# LOGGING & METRICS
# =============================================================================

# Log field names for structured logging
LOG_FIELD_REUSE_DECISION = 'reuse_decision'  # 'reused' | 'generated' | 'gray_zone'
LOG_FIELD_MATCH_SCORE = 'match_score'
LOG_FIELD_LIBRARY_ITEM_ID = 'library_item_id'
LOG_FIELD_THRESHOLD_USED = 'threshold_used'
LOG_FIELD_CANDIDATE_COUNT = 'candidate_count'

# =============================================================================
# MODEL SELECTION
# =============================================================================

# ALL code generation uses Opus 4.5 - no exceptions
# Haiku is only for classification, summarization, and admin questions
GENERATION_MODEL = "claude-sonnet-4-20250514"  # Opus 4.5 for ALL code
UTILITY_MODEL = "claude-3-5-haiku-20241022"    # Only for non-code tasks
