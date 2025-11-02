"""
Constants used throughout the application.
"""

from typing import Dict

# HTTP Error Response Codes
ERROR_RESPONSES: Dict[int, str] = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    422: "UNPROCESSABLE_ENTITY",
    429: "TOO_MANY_REQUESTS",
    500: "INTERNAL_SERVER_ERROR",
    502: "BAD_GATEWAY",
    503: "SERVICE_UNAVAILABLE",
    504: "GATEWAY_TIMEOUT",
}

# FlowBuilder Node Types - Based on format_json_flowbuilder.md
NODE_TYPES = {
    "MESSAGE": "message",
    "SEGMENT": "segment",
    "DELAY": "delay",
    "SCHEDULE": "schedule",
    "EXPERIMENT": "experiment",
    "RATE_LIMIT": "rate_limit",
    "REPLY": "reply",
    "NO_REPLY": "no_reply",
    "SPLIT": "split",
    "SPLIT_GROUP": "split_group",
    "SPLIT_RANGE": "split_range",
    "PROPERTY": "property",
    "PRODUCT_CHOICE": "product_choice",
    "PURCHASE_OFFER": "purchase_offer",
    "PURCHASE": "purchase",
    "LIMIT": "limit",
    "END": "end",
}

# Event Types
EVENT_TYPES = {
    "DEFAULT": "default",
    "REPLY": "reply",
    "NOREPLY": "noreply",
    "SPLIT": "split",
}

# Discount Types
DISCOUNT_TYPES = {
    "NONE": "none",
    "PERCENTAGE": "percentage",
    "AMOUNT": "amount",
    "CODE": "code",
}

# Time Periods
TIME_PERIODS = {
    "SECONDS": "Seconds",
    "MINUTES": "Minutes",
    "HOURS": "Hours",
    "DAYS": "Days",
}

# Message Types
MESSAGE_TYPES = {
    "STANDARD": "standard",
    "PERSONALIZED": "personalized",
}

# Product Selection Types
PRODUCT_SELECTION_TYPES = {
    "AUTOMATICALLY": "automatically",
    "POPULARITY": "popularity",
    "RECENTLY_VIEWED": "recently_viewed",
    "MANUALLY": "manually",
}

# Cart Sources
CART_SOURCES = {
    "MANUAL": "manual",
    "LATEST": "latest",
}

# Condition Types
CONDITION_TYPES = {
    "EVENT": "event",
    "PROPERTY": "property",
    "REFILL": "refill",
}

# Event Actions
EVENT_ACTIONS = {
    "PLACED_ORDER": "placed_order",
    "CLICKED_LINK": "clicked_link",
    "VIEWED_PRODUCT": "viewed_product",
    "ADDED_PRODUCT_TO_CART": "added_product_to_cart",
    "STARTED_CHECKOUT": "started_checkout",
}

# Template Variables
TEMPLATE_VARIABLES = {
    "BRAND_NAME": "{{brand_name}}",
    "STORE_URL": "{{store_url}}",
    "FIRST_NAME": "{{first_name}}",
    "CUSTOMER_TIMEZONE": "{{customer_timezone}}",
    "AGENT_NAME": "{{agent_name}}",
    "OPT_IN_TERMS": "{{opt_in_terms}}",
    "PRODUCT_LIST": "{{Product List}}",
    "PRODUCT_LIST_WITHOUT_PRICES": "{{Product List Without Prices}}",
    "DISCOUNT_LABEL": "{{Discount Label}}",
    "CART_LIST": "{{Cart List}}",
    "PURCHASE_LINK": "{{Purchase Link}}",
}

# Validation Rules
MAX_MESSAGE_LENGTH = 1600  # SMS message character limit
MAX_DISCOUNT_VALUE = 100  # Maximum discount percentage
MAX_DELAY_DAYS = 365  # Maximum delay in days
MAX_RATE_LIMIT_REQUESTS = 1000  # Maximum rate limit requests

# API Rate Limits
DEFAULT_RATE_LIMIT_REQUESTS = 100
DEFAULT_RATE_LIMIT_WINDOW = 60  # seconds

# Cache Keys
CAMPAIGN_GENERATION_CACHE_KEY = "campaign_generation:{campaign_hash}"
LLM_RESPONSE_CACHE_KEY = "llm_response:{prompt_hash}"
VALIDATION_CACHE_KEY = "validation:{flow_hash}"

# Logging Constants
LOG_CONTEXT_REQUEST_ID = "request_id"
LOG_CONTEXT_USER_ID = "user_id"
LOG_CONTEXT_CAMPAIGN_ID = "campaign_id"
LOG_CONTEXT_GENERATION_TIME = "generation_time_ms"
LOG_CONTEXT_TOKENS_USED = "tokens_used"
LOG_CONTEXT_MODEL_USED = "model_used"