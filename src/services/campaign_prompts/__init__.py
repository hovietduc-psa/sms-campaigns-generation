"""
Campaign generation prompts.
"""
from .planner_prompts import (
    CAMPAIGN_PLANNER_SYSTEM_PROMPT,
    INTENT_EXTRACTOR_SYSTEM_PROMPT,
    get_campaign_planning_prompt,
    get_intent_extraction_prompt,
    get_campaign_type_guidelines,
)
from .generator_prompts import (
    CONTENT_GENERATOR_SYSTEM_PROMPT,
    get_message_generation_prompt,
    get_segment_generation_prompt,
    get_purchase_offer_prompt,
    get_ai_prompt_generation,
    get_message_template,
    get_content_validation_prompt,
)

__all__ = [
    # System prompts
    "CAMPAIGN_PLANNER_SYSTEM_PROMPT",
    "INTENT_EXTRACTOR_SYSTEM_PROMPT",
    "CONTENT_GENERATOR_SYSTEM_PROMPT",
    # Planner prompts
    "get_campaign_planning_prompt",
    "get_intent_extraction_prompt",
    "get_campaign_type_guidelines",
    # Generator prompts
    "get_message_generation_prompt",
    "get_segment_generation_prompt",
    "get_purchase_offer_prompt",
    "get_ai_prompt_generation",
    "get_message_template",
    "get_content_validation_prompt",
]