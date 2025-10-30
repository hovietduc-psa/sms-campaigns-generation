"""
Prompts for campaign content generation.
"""
from typing import Dict, Any


CONTENT_GENERATOR_SYSTEM_PROMPT = """You are an expert SMS copywriter specializing in:
- Concise, engaging messaging (160 chars or less)
- Conversion-optimized copy
- Clear calls-to-action
- Brand voice consistency
- Personalization and segmentation
- FlowBuilder schema compliance

SMS Writing Rules:
1. Keep messages under 160 characters when possible
2. Use proper, professional English - NO abbreviations or text-speak
3. Write complete words (use "what" not "wht", "for" not "4", "you" not "u", "are" not "r")
4. Include ONE clear call-to-action per message
5. Personalize with variables ({{customer.first_name}}, {{merchant.name}}, etc.)
6. Create urgency without being pushy
7. Match the merchant's brand voice
8. Make every word count while maintaining professionalism

FlowBuilder Content Generation Rules:
1. Always populate 'content' field as the primary display field
2. Set appropriate 'label' fields for step identification
3. Generate proper 'discountType', 'discountValue', 'discountCode' when needed
4. Create 'after' objects with value/unit structure for noreply events
5. Generate 'delay' objects with value/unit for delay steps
6. Create 'rateLimit' objects with limit/period for rate limit steps
7. Use 'conditions' arrays for segment steps, not segmentDefinition
8. Set 'experimentName', 'version', 'content' for experiment steps

Never use emojis unless explicitly requested. Focus on clarity, conversion, and FlowBuilder compliance."""


def get_message_generation_prompt(
    step_plan: Dict[str, Any],
    campaign_context: Dict[str, Any],
    merchant_context: Dict[str, Any],
    previous_messages: list = None
) -> str:
    """
    Build prompt for generating message text.

    Args:
        step_plan: Plan for this specific step
        campaign_context: Overall campaign context
        merchant_context: Merchant information
        previous_messages: Previous messages in sequence for context

    Returns:
        Formatted prompt for message generation
    """
    previous_context = ""
    if previous_messages:
        previous_context = "\n\n**Previous Messages in Campaign:**\n"
        for i, msg in enumerate(previous_messages[-2:], 1):  # Last 2 messages for context
            previous_context += f"{i}. \"{msg}\"\n"

    # Extract structured requirements if available
    structured_reqs = merchant_context.get('structured_requirements', {})
    content_reqs = merchant_context.get('content_requirements', structured_reqs)

    # Build specific requirements section
    specific_requirements = ""
    if content_reqs:
        specific_requirements = "\n**SPECIFIC REQUIREMENTS - MUST BE FOLLOWED EXACTLY:**\n"

        if content_reqs.get('cta'):
            specific_requirements += f"- EXACT Call-to-Action: \"{content_reqs['cta']}\"\n"

        if content_reqs.get('store_link'):
            specific_requirements += f"- Store Link: {content_reqs['store_link']}\n"

        if content_reqs.get('offer'):
            offer = content_reqs['offer']
            if offer.get('type') == 'percentage_discount':
                specific_requirements += f"- Offer: {offer.get('value', '')}% off\n"
            elif offer.get('type') == 'fixed_amount':
                specific_requirements += f"- Offer: ${offer.get('value', '')} off\n"
            elif offer.get('type') == 'code':
                specific_requirements += f"- Offer: Discount code {offer.get('code', '')}\n"
            if offer.get('scope'):
                specific_requirements += f"- Offer Scope: {offer['scope']}\n"

    # Use the store link from structured requirements if available
    store_url = content_reqs.get('store_link') if content_reqs.get('store_link') else merchant_context.get('url', 'website')

    prompt = f"""Generate SMS message content for this campaign step.

**Campaign Context:**
- Type: {campaign_context.get('type', 'promotional')}
- Goal: {campaign_context.get('goal', 'engage and convert')}
- Target Audience: {campaign_context.get('audience', 'customers')}
- Overall Tone: {merchant_context.get('brand_voice', 'friendly and professional')}

**This Step:**
- Purpose: {step_plan.get('purpose', 'engage customer')}
- Position: {step_plan.get('position_in_flow', 'middle')} of campaign
- Text Outline: {step_plan.get('text_outline', 'N/A')}
{previous_context}

**Merchant:**
- Name: {merchant_context.get('name', 'Store')}
- Industry: {merchant_context.get('industry', 'retail')}
- Website: {store_url}
- Brand Voice: {merchant_context.get('brand_voice', 'friendly and professional')}
{specific_requirements}

**Available Variables:**
- {{{{merchant.name}}}} - Merchant name
- {{{{merchant.url}}}} - Store URL ({store_url})
- {{{{customer.first_name}}}} - Customer's first name
- {{{{customer.last_name}}}} - Customer's last name
- {{{{customer.full_name}}}} - Customer's full name
- {{{{customer.email}}}} - Customer's email
- {{{{customer.phone}}}} - Customer's phone number
- {{{{customer.segment}}}} - Customer segment (VIP, regular, etc.)
- {{{{customer.tier}}}} - Customer loyalty tier
- {{{{customer.points}}}} - Customer loyalty points
- {{{{cart.item_count}}}} - Number of items in cart
- {{{{cart.total}}}} - Cart total
- {{{{cart.items}}}} - List of cart items
- {{{{cart.abandoned_value}}}} - Value of abandoned cart
- {{{{cart.days_abandoned}}}} - Days since cart abandonment
- {{{{customer.last_purchase_date}}}} - Last purchase date
- {{{{customer.last_purchase_amount}}}} - Last purchase amount
- {{{{customer.total_purchases}}}} - Total lifetime purchases
- {{{{customer.days_since_last_purchase}}}} - Days since last purchase
- {{{{customer.birthday}}}} - Customer's birthday
- {{{{customer.anniversary}}}} - Customer anniversary date
- {{{{customer.preferences}}}} - Customer preferences
- {{{{customer.location}}}} - Customer location
- {{{{discount.code}}}} - Promo code
- {{{{discount.amount}}}} - Discount amount
- {{{{discount.percentage}}}} - Discount percentage
- {{{{discount.expiry_date}}}} - Discount expiry date
- {{{{campaign.name}}}} - Campaign name
- {{{{campaign.type}}}} - Campaign type
- {{{{current.date}}}} - Current date
- {{{{current.time}}}} - Current time
- {{{{current.day_of_week}}}} - Current day of week

**Personalization Guidelines:**
1. Use customer name in greeting (first name preferred, full name for formal campaigns)
2. Reference relevant purchase history when appropriate
3. Mention cart contents for abandoned cart campaigns
4. Use loyalty status/tier information for VIP campaigns
5. Reference geographic location for local offers
6. Use time-based triggers (birthday, anniversary) when relevant

**Requirements:**
1. Keep under 160 characters (single SMS) - CRITICAL
2. Include ONE clear call-to-action
3. Use 3-5 personalization variables where natural and relevant
4. Match the {merchant_context.get('brand_voice', 'friendly')} tone
5. Make it conversational, not salesy
6. Create urgency if appropriate for step purpose
7. Use dynamic content based on customer segment and behavior
8. CRITICAL: If specific requirements are listed above, follow them EXACTLY

**Output:**
Return ONLY the SMS message text, nothing else. No explanations, no quotes, just the message."""

    return prompt


def get_segment_generation_prompt(
    step_plan: Dict[str, Any],
    campaign_context: Dict[str, Any]
) -> str:
    """
    Build prompt for generating segment conditions.

    Args:
        step_plan: Plan for this segment step
        campaign_context: Campaign context

    Returns:
        Formatted prompt for segment generation
    """
    prompt = f"""Generate segment conditions for this campaign step.

**Campaign Context:**
- Type: {campaign_context.get('type', 'promotional')}
- Target Audience: {campaign_context.get('audience', 'all customers')}

**Segment Purpose:**
{step_plan.get('purpose', 'Route customers based on criteria')}

**Segment Criteria Outline:**
{step_plan.get('segment_outline', 'Needs definition')}

**Available Customer Fields:**
- customer.total_purchases (number)
- customer.total_spent (number in USD)
- customer.last_purchase_days_ago (number)
- customer.vip_status (boolean)
- customer.email_subscribed (boolean)
- customer.location (string: city, state, country)
- customer.tags (array of strings)
- cart.item_count (number)
- cart.total (number)

**Output Format:**
Return a JSON segment definition:
{{
  "conditions": [
    {{
      "field": "customer.total_purchases",
      "operator": "greater_than|less_than|equals|contains",
      "value": value
    }}
  ],
  "logic": "AND|OR"  // if multiple conditions
}}

Example for "VIP customers":
{{
  "conditions": [
    {{
      "field": "customer.total_spent",
      "operator": "greater_than",
      "value": 500
    }}
  ]
}}

Return ONLY valid JSON, nothing else."""

    return prompt


def get_purchase_offer_prompt(
    step_plan: Dict[str, Any],
    campaign_context: Dict[str, Any],
    merchant_context: Dict[str, Any]
) -> str:
    """
    Build prompt for generating purchase offer step.

    Args:
        step_plan: Plan for this purchase offer step
        campaign_context: Campaign context
        merchant_context: Merchant information

    Returns:
        Formatted prompt for purchase offer generation
    """
    prompt = f"""Generate a compelling purchase offer message for SMS.

**Campaign Context:**
- Type: {campaign_context.get('type', 'promotional')}
- Current Position: {step_plan.get('position_in_flow', 'closing')}

**Offer Details:**
- Discount Type: {step_plan.get('discount_type', 'percentage')}
- Discount Amount: {step_plan.get('discount_value', '10%')}
- Purpose: {step_plan.get('purpose', 'drive purchase')}

**Merchant:**
- Name: {merchant_context.get('name', 'Store')}
- Brand Voice: {merchant_context.get('brand_voice', 'friendly and professional')}

**Requirements:**
1. Create urgency without being pushy
2. Clearly state the offer value
3. Include discount code if applicable
4. Make checkout easy (include link)
5. Keep under 160 characters
6. Use {{{{discount.code}}}} and {{{{merchant.url}}}} variables

**Output:**
Return ONLY the offer message text, nothing else."""

    return prompt


def get_ai_prompt_generation(
    step_plan: Dict[str, Any],
    campaign_context: Dict[str, Any]
) -> str:
    """
    Generate an AI prompt for handled/AI-generated message steps.

    This creates a prompt that will be stored in the campaign and used
    at execution time to generate dynamic content.

    Args:
        step_plan: Plan for this AI-handled step
        campaign_context: Campaign context

    Returns:
        AI prompt to be stored in campaign
    """
    purpose = step_plan.get('purpose', 'respond to customer')

    prompt = f"""Generate a personalized SMS response based on:

Purpose: {purpose}
Context: {campaign_context.get('type', 'promotional')} campaign
Tone: {campaign_context.get('tone', 'friendly')}

Use customer data and conversation context to create a natural, helpful response under 160 characters.
Include relevant product information or offers when appropriate."""

    return prompt


# Message type templates
MESSAGE_TYPE_TEMPLATES = {
    "initial_offer": "Hi {{customer.first_name}}! {{merchant.name}}: {offer_text}. Use code {{discount.code}} at {{merchant.url}}",
    "follow_up": "{{customer.first_name}}, just a reminder: {reminder_text}. Shop now: {{merchant.url}}",
    "cart_reminder": "You left {item_count} items! Complete your order at {{merchant.url}}. Questions? Just reply!",
    "thank_you": "Thanks {{customer.first_name}}! Your order is confirmed. Track it at {{merchant.url}}/orders",
    "engagement": "Hi {{customer.first_name}}! {engagement_text}. Reply YES if interested!",
}


def get_message_template(message_type: str, **kwargs) -> str:
    """
    Get a message template with placeholder substitution.

    Args:
        message_type: Type of message template
        **kwargs: Values to substitute in template

    Returns:
        Formatted template string
    """
    template = MESSAGE_TYPE_TEMPLATES.get(message_type, "")
    return template.format(**kwargs) if template else ""


# Validation prompts
def get_content_validation_prompt(generated_content: str, requirements: Dict[str, Any]) -> str:
    """
    Generate prompt for validating generated content.

    Args:
        generated_content: Content to validate
        requirements: Requirements to check against

    Returns:
        Validation prompt
    """
    return f"""Review this SMS message for quality and compliance:

Message: "{generated_content}"

Requirements:
- Length: Under {requirements.get('max_length', 160)} characters ({'PASS' if len(generated_content) <= requirements.get('max_length', 160) else 'FAIL'})
- Has CTA: {requirements.get('needs_cta', True)}
- Brand voice: {requirements.get('brand_voice', 'professional')}
- Personalization: Should use variables

Issues to check:
1. Is it under character limit?
2. Is there a clear call-to-action?
3. Does it match brand voice?
4. Are variables used correctly?
5. Is it conversational and natural?
6. Any spelling/grammar issues?

Return JSON:
{{
  "is_valid": true/false,
  "issues": ["list of critical issues"],
  "suggestions": ["list of improvements"],
  "revised_message": "improved version if needed"
}}"""