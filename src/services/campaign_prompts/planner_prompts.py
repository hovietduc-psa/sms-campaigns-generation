"""
Prompts for campaign planning and structure generation.
"""
from typing import Dict, Any, List, Optional


CAMPAIGN_PLANNER_SYSTEM_PROMPT = """You are an expert SMS marketing campaign designer with deep knowledge of:
- Customer journey optimization
- SMS marketing best practices
- Conversion rate optimization
- Multi-step campaign flows
- Event-driven marketing automation
- FlowBuilder schema compliance

Your task is to design optimal SMS campaign structures that maximize engagement and conversion while adhering to SMS constraints (160 chars per message) and FlowBuilder JSON schema requirements.

Key Principles:
1. Keep campaigns simple (3-7 steps optimal)
2. Always include no-reply fallbacks (6-24 hours)
3. Use clear call-to-actions in every message
4. Respect quiet hours and frequency limits
5. Personalize with customer variables
6. Include graceful exit points (End steps)
7. Plan for common user responses
8. Generate FlowBuilder compliant JSON structures

Available Step Types (FlowBuilder compliant):
- message: Send SMS with content, discount options, image settings
- delay: Wait with time/period/delay structure
- segment: Route using conditions array (not segmentDefinition)
- schedule: Time-based execution with label/content
- experiment: A/B tests with experimentName/version/content
- rate_limit: Frequency control with occurrences/timespan/period
- property: Set customer properties with properties array
- reply: Handle intent-based responses
- no_reply: Timeout handling with after structure
- split: Branch conditions with label/action
- product_choice: Customer product selection
- purchase_offer: Present purchase offers
- purchase: Complete transactions
- end: Terminate campaign flow with label

FlowBuilder Event Types:
- reply: Customer responds with intent
- noreply: No response with after object
- default: Direct connection flow
- split: Branch conditions with label/action

Critical FlowBuilder Requirements:
1. Message steps: Use 'content' field (not just 'text')
2. Delay steps: Must have 'time', 'period', and 'delay' object
3. Segment steps: Must use 'conditions' array, not 'segmentDefinition'
4. Rate_limit steps: Must have 'occurrences', 'timespan', 'period', and 'rateLimit' object
5. All steps: Should have 'label' and 'content' for display
6. Events: Must have proper types and required fields

JSON Structure Requirements:
{
  "initialStepID": "step_id",
  "steps": [
    {
      "id": "unique_step_id",
      "type": "step_type",
      "label": "Display label",
      "content": "Display content",
      "...": "other required fields for step type",
      "events": [
        {
          "id": "event_id",
          "type": "event_type",
          "nextStepID": "next_step_id",
          "...": "other required event fields"
        }
      ]
    }
  ]
}
"""


INTENT_EXTRACTOR_SYSTEM_PROMPT = """You are an expert at understanding marketing campaign intent from natural language descriptions.

Extract and structure the following from campaign descriptions:
1. Campaign type (promotional, abandoned_cart, win_back, welcome, etc.)
2. Primary goals (increase_revenue, re_engage, build_loyalty, etc.)
3. Target audience criteria
4. Key products or categories mentioned
5. Discount/offer information
6. Timing constraints

Be precise and thorough. If information is missing, use reasonable defaults for SMS campaigns."""


def get_campaign_planning_prompt(
    description: str,
    intent: Dict[str, Any],
    similar_templates: List[Dict[str, Any]],
    merchant_context: Dict[str, Any],
    constraints: Optional[Dict[str, Any]] = None
) -> str:
    """
    Build comprehensive campaign planning prompt.

    Args:
        description: Natural language campaign description
        intent: Extracted campaign intent
        similar_templates: Similar template campaigns for inspiration
        merchant_context: Merchant information
        constraints: Generation constraints (max_steps, budget, etc.)

    Returns:
        Formatted prompt for campaign planning
    """
    # Format similar templates
    templates_text = ""
    if similar_templates:
        templates_text = "\n\nSimilar Successful Campaigns (for inspiration):\n"
        for i, template in enumerate(similar_templates[:2], 1):
            templates_text += f"\nTemplate {i}: {template.get('name', 'Unnamed')}\n"
            templates_text += f"Type: {template.get('category', 'N/A')}\n"
            templates_text += f"Performance: {template.get('avg_conversion_rate', 'N/A')} conversion rate\n"
            templates_text += f"Structure: {len(template.get('template_json', {}).get('steps', []))} steps\n"

    # Format constraints
    constraints_text = ""
    if constraints:
        constraints_text = "\n\nConstraints:\n"
        if 'max_steps' in constraints:
            constraints_text += f"- Maximum steps: {constraints['max_steps']}\n"
        if 'budget_per_customer' in constraints:
            constraints_text += f"- Budget per customer: ${constraints['budget_per_customer']}\n"
        if 'max_messages' in constraints:
            constraints_text += f"- Maximum messages: {constraints['max_messages']}\n"

    prompt = f"""Design an SMS marketing campaign based on this description:

**Campaign Description:**
{description}

**Detected Intent:**
- Type: {intent.get('campaign_type', 'unknown')}
- Goals: {', '.join(intent.get('goals', ['increase engagement']))}
- Target Audience: {intent.get('target_audience', 'all customers')}
- Products: {', '.join(intent.get('key_products', ['general catalog']))}
- Discount Info: {intent.get('discount_info', 'none specified')}

**Merchant Context:**
- Name: {merchant_context.get('name', 'Store')}
- Industry: {merchant_context.get('industry', 'retail')}
- Brand Voice: {merchant_context.get('brand_voice', 'friendly and professional')}
{templates_text}
{constraints_text}

**Design Requirements:**

1. **Campaign Structure:** Design a complete flow with:
   - initialStepID: ID of first step to execute
   - steps: Array of campaign steps

2. **Step Design Guidelines:**
   - Start with an engaging message (use variables like {{{{merchant.name}}}}, {{{{customer.first_name}}}})
   - Include appropriate delays between messages (1-24 hours typical)
   - Add no-reply handlers (typically 6-12 hours after message)
   - Use segments to personalize based on customer data
   - Include clear exit points (End step)
   - Keep total steps to 3-7 for optimal conversion

3. **Event Handlers:** Each interactive step should have:
   - reply events with intent and description
   - noreply events with 'after' object {{"value": 6, "unit": "hours"}}
   - default events for direct connections
   - split events with label and action for branches
   - Clear nextStepID for all events

4. **FlowBuilder Compliance Requirements:**
   - Message steps: Must have 'content' field (primary display field)
   - Delay steps: Must have 'time', 'period', and 'delay' object
   - Segment steps: Must use 'conditions' array (not segmentDefinition)
   - Rate_limit steps: Must have 'occurrences', 'timespan', 'period', and 'rateLimit' object
   - Experiment steps: Must have 'experimentName', 'version', and 'content'
   - End steps: Must have 'label' field
   - All steps: Should have 'label' and 'content' for display
   - Events: Must use correct FlowBuilder types (reply, noreply, default, split)

5. **Best Practices:**
   - Messages under 160 chars (single SMS)
   - Clear CTAs in every message
   - Personalization where appropriate
   - Respectful follow-up timing
   - Graceful campaign conclusion

**Output Format:**
Return a JSON structure with strict FlowBuilder compliance:
{{
  "campaign_name": "Descriptive name",
  "campaign_type": "{intent.get('campaign_type', 'promotional')}",
  "initialStepID": "step_001",
  "steps": [
    {{
      "id": "step_001",
      "type": "message",
      "label": "Welcome Message",
      "content": "Outline of message content for {{first_name}}",
      "text": "Legacy text field (backward compatibility)",
      "addImage": false,
      "discountType": "none",
      "events": [
        {{
          "id": "event_001",
          "type": "reply",
          "intent": "yes",
          "description": "Customer wants to proceed",
          "nextStepID": "step_002"
        }},
        {{
          "id": "event_002",
          "type": "noreply",
          "after": {{"value": 6, "unit": "hours"}},
          "nextStepID": "step_003"
        }}
      ]
    }},
    {{
      "id": "step_002",
      "type": "delay",
      "time": "5",
      "period": "Minutes",
      "delay": {{"value": "5", "unit": "Minutes"}},
      "events": [
        {{
          "id": "event_003",
          "type": "default",
          "nextStepID": "step_004"
        }}
      ]
    }},
    {{
      "id": "step_end",
      "type": "end",
      "label": "End"
    }}
  ]
}}

**FlowBuilder Schema Validation:**
- initialStepID must exist in steps array
- All step IDs must be unique
- All nextStepID references must be valid
- Required fields must be present for each step type
- Event types must be valid FlowBuilder types

Focus on creating a conversion-optimized flow that feels natural and respectful to customers."""

    return prompt


def get_intent_extraction_prompt(description: str) -> str:
    """
    Build prompt for extracting campaign intent.

    Args:
        description: Natural language campaign description

    Returns:
        Formatted prompt for intent extraction
    """
    return f"""Analyze this campaign description and extract structured intent:

Description: {description}

Extract and return as JSON:
{{
  "campaign_type": "promotional|abandoned_cart|win_back|welcome|post_purchase|birthday|seasonal|reorder_reminder|product_launch|custom",
  "goals": ["increase_revenue", "re_engage", "build_loyalty", etc.],
  "target_audience": {{
    "description": "text description",
    "criteria": {{
      // Any mentioned criteria like last_purchase, total_spent, etc.
    }}
  }},
  "key_products": ["product names or categories mentioned"],
  "discount_info": {{
    "type": "percentage|fixed|free_shipping|null",
    "value": number or null,
    "code": "promo code if mentioned or null"
  }},
  "timing": {{
    "immediate": true|false,
    "delays_mentioned": ["any timing mentioned"],
    "seasonal": "holiday or season if mentioned"
  }},
  "confidence": 0.0-1.0
}}

Be precise. Use null for missing information."""


# Campaign type specific prompt templates (FlowBuilder compliant)
CAMPAIGN_TYPE_GUIDELINES = {
    "promotional": """
Promotional Campaign Guidelines (FlowBuilder compliant):
- Start with attention-grabbing offer using message step with content field
- Create urgency with discount settings (discountType, discountValue, discountExpiry)
- Use delay step with proper time/period/delay structure for follow-ups
- Include reply events with intent and description for engagement
- Use noreply events with after object for timing
- End step with label field
FlowBuilder Structure:
  - message (content, discountType, discountValue)
    - reply (intent: "shop") → purchase_flow
    - noreply (after: {value: 6, unit: "hours"}) → reminder
  - delay (time: "5", period: "Minutes", delay: {value: "5", unit: "Minutes"})
  - end (label: "End")
""",
    "abandoned_cart": """
Abandoned Cart Campaign Guidelines (FlowBuilder compliant):
- Use delay step first (1-2 hours)
- Message steps with content field for reminders
- Use segment step with conditions array for VIP vs regular customers
- Purchase offer steps with cartSource and discount settings
- Track purchase events with default event type
- Use proper FlowBuilder event types (reply, noreply, default)
FlowBuilder Structure:
  - delay (time: "2", period: "Hours", delay: {value: "2", unit: "Hours"})
  - message (content: "Items left in cart")
    - reply (intent: "complete") → purchase_flow
    - noreply (after: {value: 24, unit: "hours"}) → enhanced_offer
  - segment (conditions: [...])
    - split (label: "include", action: "include") → vip_offer
    - split (label: "exclude", action: "exclude") → regular_offer
  - end (label: "End")
""",
    "win_back": """
Win-back Campaign Guidelines (FlowBuilder compliant):
- Use segment step with conditions array based on purchase history
- Message steps with personalized content using customer variables
- Property step to set customer re-engagement status
- Use reply events with intent and description
- Include no_reply events with proper after structure
- Add experiment step for A/B testing different offers
FlowBuilder Structure:
  - segment (conditions: [{type: "event", action: "placed_order", ...}])
    - split (label: "VIP", action: "include") → vip_message
    - split (label: "Regular", action: "exclude") → regular_message
  - message (content: "We miss you! Here's 15% off")
    - reply (intent: "shop", description: "Customer wants to shop") → purchase_flow
    - noreply (after: {value: 12, unit: "hours"}) → final_offer
  - property (properties: [{name: "winback_attempt", value: "2024-10-21"}])
  - end (label: "End")
""",
    "welcome": """
Welcome Campaign Guidelines (FlowBuilder compliant):
- Message step with content field and discount settings
- Use sendContactCard option for contact information
- Reply events with intent for engagement tracking
- Delay step with proper FlowBuilder structure for timing
- Rate_limit step with occurrences/timespan/period for frequency control
FlowBuilder Structure:
  - message (content: "Welcome {{first_name}}! Here's 10% off",
           discountType: "percentage", discountValue: "10", sendContactCard: true)
    - reply (intent: "shop", description: "New customer wants to shop") → product_choice
    - noreply (after: {value: 24, unit: "hours"}) → gentle_reminder
  - rate_limit (occurrences: "3", timespan: "7", period: "Days",
              rateLimit: {limit: "3", period: "Days"})
  - end (label: "End")
""",
    "product_launch": """
Product Launch Campaign Guidelines (FlowBuilder compliant):
- Use experiment step for A/B testing different messages
- Message steps with content field and product images
- Product choice steps with proper FlowBuilder structure
- Schedule step with label/content for launch timing
- Split steps with label/action for audience segmentation
FlowBuilder Structure:
  - experiment (experimentName: "Launch Messaging Test", version: "1", content: "Launch Test(v1)")
    - split (label: "Group A", action: "include") → message_a
    - split (label: "Group B", action: "include") → message_b
  - message (content: "New product launched!", addImage: true, imageUrl: "...")
    - reply (intent: "learn", description: "Customer wants details") → product_choice
  - product_choice (productSelection: "popularity", productImages: true)
    - reply (intent: "buy", description: "Customer wants to purchase") → purchase_offer
  - end (label: "End")
""",
}


def get_campaign_type_guidelines(campaign_type: str) -> str:
    """Get campaign type specific guidelines."""
    return CAMPAIGN_TYPE_GUIDELINES.get(
        campaign_type,
        "Follow general SMS marketing best practices."
    )