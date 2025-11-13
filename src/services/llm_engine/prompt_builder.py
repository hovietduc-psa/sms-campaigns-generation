"""
Prompt builder for LLM campaign generation.

This module provides sophisticated prompt templates that incorporate the complete FlowBuilder schema.
"""

import json
from typing import Any, Dict, List, Optional, Tuple

from src.core.config import get_settings
from src.core.logging import get_logger
from src.models.flow_schema import CampaignFlow
from src.services.llm_engine.llm_client import get_llm_client
from src.utils.constants import (
    DISCOUNT_TYPES,
    EVENT_ACTIONS,
    EVENT_TYPES,
    MESSAGE_TYPES,
    NODE_TYPES,
    PRODUCT_SELECTION_TYPES,
    TEMPLATE_VARIABLES,
    TIME_PERIODS,
)

logger = get_logger(__name__)
settings = get_settings()


class PromptBuilder:
    """
    Sophisticated prompt builder for campaign generation with FlowBuilder schema integration.
    """

    def __init__(self):
        """Initialize prompt builder."""
        self.system_prompt = self._build_system_prompt()
        self.few_shot_examples = self._build_few_shot_examples()
        self.schema_reference = self._build_schema_reference()

    async def build_prompt(
        self,
        campaign_description: str,
        complexity_level: str = "medium",
        include_examples: bool = True,
        max_examples: int = 1,
        use_template_sampling: bool = True,
        use_llm_classification: bool = True,
    ) -> Tuple[str, str]:
        """
        Build complete prompt for campaign generation.

        Args:
            campaign_description: Natural language campaign description
            complexity_level: Expected complexity ("simple", "medium", "complex")
            include_examples: Whether to include few-shot examples
            max_examples: Maximum number of examples to include (default: 1 for reduced noise)
            use_template_sampling: Whether to use template-based sampling (new) or complexity-based (legacy)
            use_llm_classification: Whether to use LLM for template classification (recommended)

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        # Select appropriate examples based on sampling method
        examples = []
        if include_examples:
            if use_template_sampling:
                if use_llm_classification:
                    # Use new LLM-based classification
                    examples = await self._select_examples_by_llm(
                        campaign_description=campaign_description,
                        max_examples=max_examples,
                        complexity_level=complexity_level
                    )
                else:
                    # Use keyword-based classification
                    examples = self._select_examples_by_keyword_fallback(
                        campaign_description=campaign_description,
                        max_examples=max_examples,
                        complexity_level=complexity_level
                    )
            else:
                # Legacy complexity-based selection
                examples = self._select_examples(complexity_level, max_examples)

        # Build user prompt
        user_prompt = self._build_user_prompt(
            campaign_description=campaign_description,
            examples=examples,
            complexity_level=complexity_level,
        )

        return self.system_prompt, user_prompt

    def _build_system_prompt(self) -> str:
        """Build comprehensive system prompt with FlowBuilder schema integration."""
        return f"""You are an expert SMS marketing flow builder with deep expertise in creating automated customer journeys. You will receive a campaign description and must output a JSON representing the campaign flow that strictly follows the FlowBuilder format defined in format_json_flowbuilder.md.

## 🚨 Critical Rules (MUST FOLLOW):

1. **🚨 IMMEDIATE REQUIREMENT - COUNTER-BASED IDs (NON-NEGOTIABLE)**:
   - EVERY step ID MUST use format: "name-001", "name-002", "name-003", etc.
   - Examples: "welcome-001", "vip-offer-002", "product-choice-003", "end-flow-004"
   - FAILURE to use this format will result in INVALID flow
   - This is the MOST IMPORTANT rule - ALL IDs must be counter-based!

2. **Output Format**: Output ONLY valid JSON. No explanations, no markdown, no text outside the JSON structure.

3. **Root JSON Structure**: Follow the FlowBuilder format exactly:
   - "name": string (required) - Campaign name
   - "description": string (required) - Campaign description
   - "initialStepID": string (required) - ID of the first node
   - "steps": array of node objects (required) - Each step must be one of the FlowBuilder node types

4. **Node Types**: Use ONLY these FlowBuilder node types:
   - "message" - Send SMS message
   - "delay" - Create delay
   - "segment" - Customer segmentation
   - "product_choice" - Product selection
   - "purchase" - Process order
   - "purchase_offer" - Send purchase offer
   - "reply_cart_choice" - Choose from cart
   - "no_reply" - Handle no response
   - "end" - End flow
   - "start" - Start flow
   - "property" - Update properties
   - "rate_limit" - Rate limiting
   - "limit" - Execution limit
   - "split" - Split branch
   - "reply" - Wait for reply
   - "experiment" - A/B Testing
   - "quiz" - Interactive quiz
   - "schedule" - Schedule
   - "split_group" - A/B testing branch
   - "split_range" - Time-based branch

5. **Required Base Fields**: Each node MUST have:
   - "id": unique string identifier
   - "type": one of the FlowBuilder node types above
   - "label": string - Display label for the node
   - "content": string - Node description
   - "events": array (optional) - Events array
   - "active": boolean (optional, default: true) - Node active status
   - "parameters": object (optional, default: {{}}) - Additional parameters

6. **🚨 CRITICAL: Counter-Based IDs (REQUIRED)**:
   - ALL step IDs MUST use counter-based format: "name-001", "name-002", "name-003"
   - This ensures UNIQUE nextStepID throughout the entire flow
   - NEVER use generic IDs like "step1", "node2", "message3"
   - Pattern: [descriptive-name]-[3-digit-number]

7. **🚨 CRITICAL: UNIQUE nextStepID Values (MANDATORY)**:
   - EVERY nextStepID in events MUST be UNIQUE throughout the entire campaign
   - NO duplicate nextStepID values allowed - each event must point to a different step
   - CORRECT: Event A -> nextStepID: "end-campaign-001", Event B -> nextStepID: "end-campaign-002"
   - VIOLATION: Multiple events pointing to same "end-node" is INVALID
   - 🚫 WRONG: {{"events": [{{"nextStepID": "end-node"}}, {{"nextStepID": "end-node"}}]}}
   - ✅ CORRECT: {{"events": [{{"nextStepID": "end-node-001"}}, {{"nextStepID": "end-node-002"}}]}}
   - ALWAYS verify that each nextStepID appears only ONCE in the entire flow

8. **🚨 CRITICAL: END Node Requirements (MANDATORY)**:
   - EVERY campaign MUST have at least one END node that is reachable from initialStepID
   - END nodes MUST have type: "end" and NO events array (terminates flow)
   - Use counter-based IDs for END nodes: "end-flow-001", "end-campaign-002"
   - All flow branches MUST eventually lead to an END node (no dead ends)
   - END nodes are the ONLY node type that can have an empty events array

9. **🚨 CRITICAL: Purchase Node Flow Requirements (MANDATORY)**:
   - PURCHASE nodes MUST come AFTER either a purchase_offer OR product_choice node
   - NEVER create purchase nodes without proper preceding offer/selection flow
   - REQUIRED Purchase Flow: message -> purchase_offer -> purchase -> thank_you -> end
   - ALTERNATIVE Purchase Flow: message -> product_choice -> purchase -> thank_you -> end
   - 🚫 WRONG: Creating purchase nodes directly after message nodes
   - ✅ CORRECT: Always include purchase_offer or product_choice before purchase

## 📋 Common Field Groups:

### Message Fields (Used by: message, product_choice, purchase_offer, reply_cart_choice)
- "messageType": string - "standard" | "personalized"
- "messageText": string (required) - Main SMS content

### Discount Fields (Used by: message, product_choice, purchase, purchase_offer)
- "discountType": string - "none" | "percentage" | "amount" | "code"
- "discountValue": string - Discount value (for percentage/amount)
- "discountCode": string - Discount code (for type="code")

### Product Array Fields (Used by: product_choice, purchase_offer, purchase, reply_cart_choice)
- Products array requires: id (string), productVariantId (for purchase), quantity (string), label (optional), uniqueId (number)

## 📋 Node-Specific Field Requirements:

### MESSAGE Node (Send SMS message) - REQUIRED FIELDS:
- Message Fields (see Common Field Groups)
- "addImage": boolean (default false) - Include image
- "imageUrl": string - Image URL when addImage = true
- "sendContactCard": boolean (default false) - Send contact card
- Discount Fields (see Common Field Groups)

### DELAY Node (Wait time) - REQUIRED FIELDS:
- "time": string (required) - Time value
- "period": string (required) - "Seconds" | "Minutes" | "Hours" | "Days"

### SEGMENT Node (Customer segmentation) - REQUIRED FIELDS:
- "conditions": array (required) - Array of condition objects
- Each condition requires: id, type, action, operator, filter, timePeriod, timePeriodType, etc.

### PRODUCT_CHOICE Node (Product selection) - REQUIRED FIELDS:
- Message Fields (see Common Field Groups)
- "productSelection": string (required) - "manually" | "automatically" | "popularity" | "recently_viewed"
- Product Array Fields (see Common Field Groups) - required when productSelection = "manually"
- "productImages": boolean (default true) - Send product images
- Discount Fields (see Common Field Groups)

### PURCHASE_OFFER Node (Send purchase offer) - REQUIRED FIELDS:
- Message Fields (see Common Field Groups)
- "cartSource": string (required) - "manual" | "latest"
- Product Array Fields (see Common Field Groups) - required when cartSource = "manual"
- "discount": boolean (default false) - Enable/disable discount
- "discountPercentage": string - When discountType = "percentage"
- "discountAmount": string - When discountType = "amount"
- "discountExpiry": boolean (default false) - Discount has expiry
- "discountExpiryDate": string - Expiry date when enabled
- "includeProductImage": boolean (default true) - Send product images
- "skipForRecentOrders": boolean (default true) - Skip for recent orders

### PURCHASE Node (Process purchase) - REQUIRED FIELDS:
- "cartSource": string (required) - "manual" | "latest"
- Product Array Fields (see Common Field Groups)
- Discount Fields (see Common Field Groups)
- "sendReminderForNonPurchasers": boolean (default false) - Send reminder

### REPLY_CART_CHOICE Node (Choose from cart) - REQUIRED FIELDS:
- Message Fields (see Common Field Groups)
- "cartSelection": string (required) - "manual" | "latest"
- "cartItems": array - When cartSelection = "manual"

### NO_REPLY Node (Handle no response) - REQUIRED FIELDS:
- "enabled": boolean (default true) - Enable/disable
- "value": number (required) - Wait time as number
- "unit": string (required) - "seconds" | "minutes" | "hours" | "days"

### PROPERTY Node (Update properties) - REQUIRED FIELDS:
- "properties": array (required) - Array of property objects
- Each property requires: name, value, id

### RATE_LIMIT Node (Rate limiting) - REQUIRED FIELDS:
- "occurrences": string (required) - Number of sends
- "timespan": string (required) - Time period
- "period": string (required) - "Minutes" | "Hours" | "Days"

### LIMIT Node (Execution limit) - REQUIRED FIELDS:
- "occurrences": string (required) - Number of times allowed
- "timespan": string (required) - Time period
- "period": string (required) - "Minutes" | "Hours" | "Days"

### SPLIT Node (Split branch) - REQUIRED FIELDS:
- "enabled": boolean (default true) - Enable/disable
- "action": string (required) - Split action
- "description": string - Split description

### REPLY Node (Wait for reply) - REQUIRED FIELDS:
- "enabled": boolean (default true) - Enable/disable
- "intent": string (required) - Reply intent
- "description": string - Reply description

### EXPERIMENT Node (A/B Testing) - REQUIRED FIELDS:
- "experimentName": string (required) - Experiment name
- "version": string (required) - Version

### QUIZ Node (Interactive quiz) - REQUIRED FIELDS:
- "questions": array (required) - Array of question objects
- Each question requires: id, question, type, options, correctAnswer, points

### SCHEDULE Node (Schedule) - REQUIRED FIELDS:
- No specific required fields beyond base fields

### SPLIT_GROUP Node (A/B testing branch) - REQUIRED FIELDS:
- "enabled": boolean (default true) - Enable/disable
- "action": string (required) - "control" | "variant"
- "description": string - Control/variant group description

### SPLIT_RANGE Node (Time-based branch) - REQUIRED FIELDS:
- "enabled": boolean (default true) - Enable/disable
- "action": string (required) - "schedule"
- "description": string - Scheduled time range description

### END Node (End flow) - REQUIRED FIELDS:
- No events array - end node terminates flow
- Only requires base fields: id, type, label, content, active, parameters

### START Node (Start flow) - REQUIRED FIELDS:
- Only requires base fields: id, type, label, content, active, parameters

## 🎪 Events Structure Requirements:

### Event Base Fields (All events):
- "type": string (required) - "reply" | "noreply" | "split" | "default"
- "nextStepID": string (required) - Reference to another node's ID
- "active": boolean (optional, default: true) - Event active status
- "parameters": object (optional, default: {{}}) - Event parameters

### Event Type Specific Fields:
- **type="reply"**: "intent": string (required), "description": string (optional)
- **type="noreply"**: "after": object (required) - {{"value": number, "unit": string}}
- **type="split"**: "label": string (required), "action": string (required)
- **type="default"**: No additional fields required

## 🎯 Template Variables Available:

### Personalization Variables:
- "{{brand_name}}" - Brand name
- "{{first_name}}" - Customer first name
- "{{last_name}}" - Customer last name
- "{{store_url}}" - Store URL
- "{{customer_timezone}}" - Customer timezone
- "{{agent_name}}" - Agent name
- "{{opt_in_terms}}" - Opt-in terms

### Product Variables:
- "{{Product List}}" - Product list with prices (product_choice)
- "{{Product List Without Prices}}" - Product list without prices (product_choice)
- "{{Discount Label}}" - Discount label (product_choice)
- "{{Cart List}}" - Cart products list (purchase_offer)
- "{{Purchase Link}}" - Purchase link (purchase_offer)
- "{{Personalized Products}}" - Personalized products (product_choice automatic)
- "{{VIP Product List}}" - VIP product list

## 🎯 Best Practices:

1. **Counter-based IDs**: Use format "name-001", "name-002", "name-003"
2. **Descriptive Labels**: "Welcome Message" instead of "Node 1"
3. **Clear Flow Logic**: Each node should have a clear purpose
4. **Handle All Paths**: Always have paths for reply, noreply, and split options
5. **Variables Usage**: Use {{{{variable}}}} in messageText
6. **Discount Strategy**: Use appropriate discount types consistently
7. **End Node**: Always end with END node
8. **Experiment Logic**: Use EXPERIMENT + SPLIT nodes for A/B testing
9. **Property Updates**: Use PROPERTY nodes for customer data tracking
10. **Rate Limiting**: Use RATE_LIMIT to control message frequency
11. **Structured Format**: Prefer structured fields (delay: {{value, unit}}) over legacy (time, period)

## 🚨 Critical Node Type Selection Rules:

- **Standalone REPLY nodes**: Use ONLY when handling responses WITHOUT sending a message first
- **Reply events in MESSAGE nodes**: Use when sending a message AND handling responses to that message
- **Standalone NO_REPLY nodes**: Use ONLY when handling timeouts WITHOUT sending a message first
- **No-reply events in MESSAGE nodes**: Use when sending a message AND handling timeouts
- **Key Principle**: If sending content to customer, use MESSAGE node with events. If only handling responses/timeouts, use standalone REPLY/NO_REPLY nodes.

## 📄 Common Campaign Templates:

### 1. Basic Welcome Campaign
Start -> Message -> Product Choice -> Purchase -> Thank You -> END

### 2. VIP Campaign with A/B Testing
Start -> Experiment (A/B) -> Message (Control/Variant) -> Segment -> VIP Products -> Purchase -> Thank You -> END

### 3. Flash Sale Campaign
Start -> Announce -> Product Choice -> Urgency Timer -> Purchase -> Thank You -> END

### 4. Re-engagement Campaign
Start -> Segment (Inactive) -> Special Offer -> Product Choice -> Purchase -> Thank You -> Property Update -> END

### 5. Quiz Marketing Campaign
Start -> Quiz -> Property Update -> Product Recommendation -> Purchase -> Thank You -> END

### 6. Drip Campaign with Rate Limit
Start -> Rate Limit -> Message 1 -> Delay -> Message 2 -> Delay -> Message 3 -> END

Remember: Your output must be perfect, valid JSON that follows the FlowBuilder format exactly with ALL 20 node types properly structured with their required fields."""

    def _build_user_prompt(
        self,
        campaign_description: str,
        examples: List[Dict[str, Any]],
        complexity_level: str,
    ) -> str:
        """Build user prompt with examples and instructions."""
        prompt_parts = []

        # Add campaign description
        prompt_parts.append(f"## Campaign Description")
        prompt_parts.append(f"Generate an SMS campaign flow for: \"{campaign_description}\"")
        prompt_parts.append(f"Expected complexity: {complexity_level}")
        prompt_parts.append("")

        # Add examples if provided
        if examples:
            prompt_parts.append("## Example Campaigns")
            prompt_parts.append("Study these examples to understand the expected format and quality:")

            for i, example in enumerate(examples, 1):
                prompt_parts.append(f"### Example {i}: {example['description']}")
                prompt_parts.append("```json")
                prompt_parts.append(json.dumps(example['flow'], indent=2))
                prompt_parts.append("```")
                prompt_parts.append("")

        # Add specific instructions based on description
        instructions = self._generate_specific_instructions(campaign_description, complexity_level)
        if instructions:
            prompt_parts.append("## Specific Instructions")
            prompt_parts.extend(instructions)
            prompt_parts.append("")

        # Add final output instruction
        prompt_parts.append("## Your Task")
        prompt_parts.append("Generate the complete JSON campaign flow based on the description above.")
        prompt_parts.append("Ensure your response is valid JSON that follows all the rules and schema requirements.")
        prompt_parts.append("")

        return "\n".join(prompt_parts)

    def _select_examples_by_template(
        self,
        campaign_description: str,
        max_examples: int,
        complexity_level: str = "medium"
    ) -> List[Dict[str, Any]]:
        """Legacy method - Use _select_examples_by_llm or _select_examples_by_keyword_fallback instead."""
        examples = self.few_shot_examples

        # Define template keywords for matching
        template_keywords = {
            "basic_welcome": ["welcome", "new customer", "onboard", "hello", "intro", "first purchase", "getting started"],
            "vip_campaign": ["vip", "premium", "exclusive", "loyalty", "special customer", "a/b test", "experiment"],
            "flash_sale": ["flash sale", "urgent", "limited time", "deadline", "quick sale", "promotion", "discount"],
            "re_engagement": ["reengage", "inactive", "come back", "return", "win back", "winback", "lost customers"],
            "quiz_marketing": ["quiz", "question", "preference", "personalize", "recommend", "interactive", "survey"],
            "drip_campaign": ["drip", "sequence", "multiple messages", "nurture", "follow up series", "automation", "campaign"],
            "birthday_campaign": ["birthday", "anniversary", "special day", "milestone", "personal", "celebration", "age", "date"],
            "referral_campaign": ["referral", "refer a friend", "share", "word of mouth", "customer acquisition", "invite", "recommend friend"],
            "loyalty_campaign": ["loyalty", "points", "rewards", "redemption", "member benefits", "vip club", "earn points", "redeem"],
            "cart_recovery": ["abandoned cart", "cart abandonment", "recovery", "incomplete purchase", "left items", "checkout", "forgot cart"],
            "product_launch": ["product launch", "new product", "pre-order", "release", "debut", "launch", "new arrival", "coming soon"],
            "seasonal_campaign": ["seasonal", "holiday", "christmas", "valentine", "summer", "winter", "festival", "special occasion", "event"]
        }

        # Determine best matching templates based on description
        description_lower = campaign_description.lower()
        template_scores = {}

        for template, keywords in template_keywords.items():
            score = sum(1 for keyword in keywords if keyword in description_lower)
            template_scores[template] = score

        # Sort templates by score (highest first)
        sorted_templates = sorted(template_scores.items(), key=lambda x: x[1], reverse=True)

        # Select examples from best matching templates
        selected_examples = []

        # First, try to get examples from the highest scoring templates
        for template, score in sorted_templates:
            if score > 0 and len(selected_examples) < max_examples:
                template_examples = [ex for ex in examples if ex.get("template_category") == template]
                selected_examples.extend(template_examples)

        # If no template matches or we need more examples, fall back to complexity-based selection
        if len(selected_examples) < max_examples:
            if complexity_level == "simple":
                complexity_examples = [ex for ex in examples if ex.get("complexity") == "simple"]
            elif complexity_level == "complex":
                complexity_examples = [ex for ex in examples if ex.get("complexity") in ["medium", "complex"]]
            else:
                complexity_examples = examples

            # Add complexity-based examples that aren't already selected
            for example in complexity_examples:
                if example not in selected_examples and len(selected_examples) < max_examples:
                    selected_examples.append(example)

        # If still no examples, return the first few examples
        if len(selected_examples) == 0:
            selected_examples = examples[:max_examples]

        return selected_examples[:max_examples]

    async def _classify_campaign_with_llm(self, campaign_description: str) -> List[str]:
        """
        Classify campaign description using LLM for more accurate template matching.

        Args:
            campaign_description: Natural language campaign description

        Returns:
            List of matched template categories sorted by confidence
        """
        # Define all available template categories with detailed descriptions
        template_descriptions = {
            "basic_welcome": "Welcome new customers with introductory offers and guide first purchase",
            "vip_campaign": "Exclusive campaigns for VIP/premium customers, often with A/B testing",
            "flash_sale": "Urgent, time-limited sales with countdowns and special discounts",
            "re_engagement": "Win-back campaigns targeting inactive customers who haven't purchased recently",
            "quiz_marketing": "Interactive quizzes to collect preferences and provide personalized recommendations",
            "drip_campaign": "Multi-message nurturing sequences sent over time",
            "birthday_campaign": "Personalized birthday or anniversary messages with special offers",
            "referral_campaign": "Customer referral programs encouraging word-of-mouth marketing",
            "loyalty_campaign": "Points-based loyalty systems with rewards and redemption",
            "cart_recovery": "Recover abandoned shopping carts with reminder messages",
            "product_launch": "New product announcements, pre-orders, and launch campaigns",
            "seasonal_campaign": "Holiday and seasonal promotions (Christmas, Valentine's, Black Friday, etc.)"
        }

        # Create the classification prompt for single best match
        prompt = f"""You are an expert SMS marketing classifier. Analyze the campaign description and identify the SINGLE best matching template category.

Campaign Description: "{campaign_description}"

Available Template Categories:
{json.dumps(template_descriptions, indent=2)}

Instructions:
1. Analyze the campaign description carefully
2. Identify the PRIMARY purpose and main characteristics
3. Choose the ONE template category that best matches
4. If multiple categories could apply, choose the most dominant one
5. Return ONLY the template category name as a JSON string

Example Output:
"basic_welcome"

Now classify this campaign:"""

        try:
            llm_client = get_llm_client()

            response = await llm_client.generate_text(
                prompt=prompt,
                max_tokens=100,
                temperature=0.1  # Low temperature for consistent classification
            )

            # Parse the LLM response for single best match
            response = response.strip()

            # Try to parse as JSON string or array
            try:
                if response.startswith('"') and response.endswith('"'):
                    # JSON string format
                    category = json.loads(response)
                    if category in template_descriptions:
                        return [category]
                elif response.startswith('[') and response.endswith(']'):
                    # JSON array format (backward compatibility)
                    categories = json.loads(response)
                    if isinstance(categories, list) and categories:
                        category = categories[0]  # Take first (best) match
                        if category in template_descriptions:
                            return [category]
            except json.JSONDecodeError:
                pass

            # Fallback: try to extract category from text response
            import re
            matches = re.findall(r'"(\w+)"', response)
            valid_categories = [cat for cat in matches if cat in template_descriptions]
            if valid_categories:
                return [valid_categories[0]]  # Return first match

        except Exception as e:
            logger.warning(f"LLM classification failed: {e}. Using fallback classification.")

        # If LLM fails, return empty list to trigger fallback
        return []

    async def _select_examples_by_llm(
        self,
        campaign_description: str,
        max_examples: int = 1,
        complexity_level: str = "medium"
    ) -> List[Dict[str, Any]]:
        """
        Select the best single few-shot example using LLM-based classification.

        Args:
            campaign_description: Natural language campaign description
            max_examples: Maximum number of examples to return (default: 1)
            complexity_level: Expected complexity level

        Returns:
            List containing the single best-matching few-shot example
        """
        examples = self.few_shot_examples

        try:
            # Get LLM classification (single best match)
            matched_categories = await self._classify_campaign_with_llm(campaign_description)

            if matched_categories and len(matched_categories) > 0:
                best_category = matched_categories[0]
                logger.info(f"LLM classified campaign as: {best_category}")

                # Find examples from the best-matched category
                category_examples = [
                    ex for ex in examples
                    if ex.get("template_category") == best_category
                ]

                if category_examples:
                    # For single sample, return the first example from the category
                    # In the future, we could add logic to select the best example within the category
                    return [category_examples[0]]
                else:
                    logger.warning(f"No examples found for category: {best_category}")
            else:
                logger.info("LLM classification returned no matches, using fallback")

        except Exception as e:
            logger.error(f"Error in LLM-based example selection: {e}")

        # Fallback to keyword-based classification
        logger.info("Using keyword-based fallback classification")
        fallback_examples = self._select_examples_by_keyword_fallback(
            campaign_description, max_examples, complexity_level
        )
        return fallback_examples[:max_examples] if fallback_examples else []

    def _select_examples_by_keyword_fallback(
        self,
        campaign_description: str,
        max_examples: int,
        complexity_level: str = "medium"
    ) -> List[Dict[str, Any]]:
        """
        Fallback method using original keyword-based classification.

        Args:
            campaign_description: Natural language campaign description
            max_examples: Maximum number of examples to return
            complexity_level: Expected complexity level

        Returns:
            List of selected few-shot examples
        """
        examples = self.few_shot_examples

        # Define template keywords for matching (improved version)
        template_keywords = {
            "basic_welcome": ["welcome", "new customer", "onboard", "hello", "intro", "first purchase", "getting started"],
            "vip_campaign": ["vip", "premium", "exclusive", "special customer", "a/b test", "experiment"],  # Removed "loyalty"
            "flash_sale": ["flash sale", "urgent", "limited time", "deadline", "quick sale", "promotion", "discount"],
            "re_engagement": ["reengage", "inactive", "come back", "return", "win back", "winback", "lost customers"],
            "quiz_marketing": ["quiz", "question", "preference", "personalize", "recommend", "interactive", "survey"],
            "drip_campaign": ["drip", "sequence", "multiple messages", "nurture", "follow up series", "automation"],  # Removed "campaign"
            "birthday_campaign": ["birthday", "anniversary", "special day", "milestone", "celebration", "age", "date"],  # Removed "personal"
            "referral_campaign": ["referral", "refer a friend", "share", "word of mouth", "customer acquisition", "invite", "recommend friend"],
            "loyalty_campaign": ["loyalty", "points", "rewards", "redemption", "member benefits", "earn points", "redeem"],  # Removed "vip club"
            "cart_recovery": ["abandoned cart", "cart abandonment", "recovery", "incomplete purchase", "left items", "checkout", "forgot cart"],
            "product_launch": ["product launch", "new product", "pre-order", "release", "debut", "launch", "new arrival", "coming soon"],
            "seasonal_campaign": ["seasonal", "holiday", "christmas", "valentine", "summer", "winter", "spring", "fall", "festival", "black friday", "cyber monday", "thanksgiving", "easter", "halloween", "new year", "special occasion", "event"]
        }

        # Determine best matching templates based on description
        description_lower = campaign_description.lower()
        template_scores = {}

        for template, keywords in template_keywords.items():
            score = sum(1 for keyword in keywords if keyword in description_lower)
            template_scores[template] = score

        # Sort templates by score (highest first)
        sorted_templates = sorted(template_scores.items(), key=lambda x: x[1], reverse=True)

        # Select examples from best matching templates
        selected_examples = []

        # First, try to get examples from the highest scoring templates
        for template, score in sorted_templates:
            if score > 0 and len(selected_examples) < max_examples:
                template_examples = [ex for ex in examples if ex.get("template_category") == template]
                selected_examples.extend(template_examples)

        # If no template matches or we need more examples, fall back to complexity-based selection
        if len(selected_examples) < max_examples:
            if complexity_level == "simple":
                complexity_examples = [ex for ex in examples if ex.get("complexity") == "simple"]
            elif complexity_level == "complex":
                complexity_examples = [ex for ex in examples if ex.get("complexity") in ["medium", "complex"]]
            else:
                complexity_examples = examples

            # Add complexity-based examples that aren't already selected
            for example in complexity_examples:
                if example not in selected_examples and len(selected_examples) < max_examples:
                    selected_examples.append(example)

        # If still no examples, return the first few examples
        if len(selected_examples) == 0:
            selected_examples = examples[:max_examples]

        return selected_examples[:max_examples]

    def _select_examples(self, complexity_level: str, max_examples: int) -> List[Dict[str, Any]]:
        """Legacy method - use _select_examples_by_template for new functionality."""
        examples = self.few_shot_examples

        # Filter examples by complexity
        if complexity_level == "simple":
            filtered = [ex for ex in examples if ex.get("complexity") == "simple"]
        elif complexity_level == "complex":
            filtered = [ex for ex in examples if ex.get("complexity") in ["medium", "complex"]]
        else:
            filtered = examples

        # Return up to max_examples
        return filtered[:max_examples]

    def _generate_specific_instructions(self, description: str, complexity_level: str) -> List[str]:
        """Generate specific instructions based on campaign description."""
        instructions = []
        description_lower = description.lower()

        # VIP campaigns
        if "vip" in description_lower:
            instructions.append("- Include VIP customer segmentation using customer_type property")
            instructions.append("- Add special VIP-only offers or content")

        # Cart recovery
        if "cart" in description_lower or "checkout" in description_lower:
            instructions.append("- Include cart abandonment detection using started_checkout event")
            instructions.append("- Use purchase_offer node for cart recovery")
            instructions.append("- Add discount incentives for cart completion")

        # First-time customers
        if "first" in description_lower or "new" in description_lower:
            instructions.append("- Focus on welcome and onboarding flows")
            instructions.append("- Include educational content about products/services")

        # Re-engagement
        if "reorder" in description_lower or "repeat" in description_lower:
            instructions.append("- Include purchase history conditions")
            instructions.append("- Add product recommendations based on past purchases")

        # Testing/Experiments
        if "test" in description_lower or "experiment" in description_lower or "ab" in description_lower:
            instructions.append("- Include experiment node with Group A and Group B branches")
            instructions.append("- Create different message variations for testing")

        # Time-sensitive campaigns
        if any(word in description_lower for word in ["urgent", "limited", "deadline", "expire"]):
            instructions.append("- Include clear urgency indicators in messages")
            instructions.append("- Add discount expiry dates where applicable")

        # Product recommendations
        if "recommend" in description_lower or "suggest" in description_lower:
            instructions.append("- Use product_choice node for interactive selection")
            instructions.append("- Include product images for better engagement")

        # E-commerce Purchase Processing
        if "purchase" in description_lower or "buy" in description_lower or "shop" in description_lower:
            instructions.append("- Include purchase node for transaction processing")
            instructions.append("- Add cartSource configuration (latest/manual)")
            instructions.append("- Set up purchase completion confirmation")
        # Professional Contact Features
        if "welcome" in description_lower or "professional" in description_lower:
            instructions.append("- Consider adding sendContactCard: True for professional appearance")
            instructions.append("- Include discountExpiry for time-sensitive offers")
        # Follow-up Timing
        if "followup" in description_lower or "reminder" in description_lower:
            instructions.append("- Use delay nodes for precise timing control")
            instructions.append("- Consider 2-24 hour timeouts for non-responders")
            instructions.append("- Add 5-30 minute delays before gentle follow-ups")
        # VIP Segmentation Enhancement
        if "vip" in description_lower and ("segment" in description_lower or "purchase" in description_lower):
            instructions.append("- Use event-based segmentation (placed_order) for dynamic VIP detection")
            instructions.append("- Include purchase_offer node for VIP customers with cart management")
            instructions.append("- Add product_choice node for regular customers")
        # Discount Management
        if "discount" in description_lower or "offer" in description_lower:
            instructions.append("- Include discountType, discountValue, and discountCode fields")
            instructions.append("- Set discountExpiry for time-limited offers")
            instructions.append("- Consider different discount tiers (10% for new, 20% for VIP)")

        # Adjust based on complexity
        if complexity_level == "simple":
            instructions.append("- Keep the flow simple: 2-4 nodes maximum")
            instructions.append("- Focus on one primary action or message")
        elif complexity_level == "complex":
            instructions.append("- Include multiple branches and conditional logic")
            instructions.append("- Add comprehensive follow-up sequences")
            instructions.append("- Consider multiple customer segments and paths")

        return instructions

    def _build_few_shot_examples(self) -> List[Dict[str, Any]]:
        """Build few-shot examples for the 6 required campaign templates using FlowBuilder format."""
        return [
            # Template 1: Basic Welcome Campaign
            # Start -> Message -> Product Choice -> Purchase -> Thank You -> END
            {
                "description": "Welcome campaign for new customers with introductory offer",
                "template_category": "basic_welcome",
                "complexity": "simple",
                "flow": {
                    "name": "Welcome Campaign for New Customers",
                    "description": "Send welcome message with discount, showcase popular products, and guide first purchase",
                    "initialStepID": "welcome-message-001",
                    "steps": [
                        # Step 1: Welcome Message
                        {
                            "id": "welcome-message-001",
                            "type": "message",
                            "label": "Welcome Message",
                            "content": "Send welcome message to new customers",
                            "messageType": "standard",
                            "messageText": "Hi {{first_name}}! Welcome to {{brand_name}}! Here are our popular products to get you started 🎉",
                            "addImage": False,
                            "sendContactCard": True,
                            "discountType": "percentage",
                            "discountValue": "10",
                            "discountCode": "WELCOME10",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "product-choice-002"
                                }
                            ]
                        },
                        # Step 2: Product Choice
                        {
                            "id": "product-choice-002",
                            "type": "product_choice",
                            "label": "Product Selection",
                            "content": "Show popular products to new customer",
                            "messageType": "standard",
                            "messageText": "Browse our bestsellers:\n\n{{Product List}}\n\nReply with number to purchase!",
                            "productSelection": "popularity",
                            "products": [
                                {
                                    "id": "product-001",
                                    "productVariantId": "product-001-variant",
                                    "quantity": "1",
                                    "label": "Bestseller Product 1",
                                    "uniqueId": 1
                                },
                                {
                                    "id": "product-002",
                                    "productVariantId": "product-002-variant",
                                    "quantity": "1",
                                    "label": "Bestseller Product 2",
                                    "uniqueId": 2
                                }
                            ],
                            "productImages": True,
                            "discountType": "percentage",
                            "discountValue": "10",
                            "discountCode": "WELCOME10",
                            "events": [
                                {
                                    "type": "reply",
                                    "intent": "buy",
                                    "description": "Customer wants to buy product",
                                    "nextStepID": "purchase-003"
                                }
                            ]
                        },
                        # Step 3: Purchase
                        {
                            "id": "purchase-003",
                            "type": "purchase",
                            "label": "Process Purchase",
                            "content": "Process customer purchase with welcome discount",
                            "cartSource": "latest",
                            "products": [],
                            "discountType": "percentage",
                            "discountValue": "10",
                            "discountCode": "WELCOME10",
                            "sendReminderForNonPurchasers": True,
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "thank-you-004"
                                }
                            ]
                        },
                        # Step 4: Thank You
                        {
                            "id": "thank-you-004",
                            "type": "message",
                            "label": "Thank You Message",
                            "content": "Send purchase confirmation and thank you",
                            "messageType": "standard",
                            "messageText": "Thank you {{first_name}}! Your order is confirmed. You saved 10% with WELCOME10! 🎁",
                            "addImage": False,
                            "sendContactCard": False,
                            "discountType": "none",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "end-flow-005"
                                }
                            ]
                        },
                        # Step 5: END
                        {
                            "id": "end-flow-005",
                            "type": "end",
                            "label": "Campaign End",
                            "content": "End of Basic Welcome Campaign"
                        }
                    ]
                }
            },
            # Template 2: VIP Campaign with A/B Testing
            # Start -> Experiment (A/B) -> Message (Control/Variant) -> Segment -> VIP Products -> Purchase -> Thank You -> END
            {
                "description": "VIP customer campaign with A/B testing for discount offers",
                "template_category": "vip_campaign",
                "complexity": "complex",
                "flow": {
                    "name": "VIP A/B Testing Campaign",
                    "description": "Test different discount offers for VIP customers with personalized product recommendations",
                    "initialStepID": "experiment-001",
                    "steps": [
                        # Step 1: Experiment (A/B)
                        {
                            "id": "experiment-001",
                            "type": "experiment",
                            "label": "VIP Offer A/B Test",
                            "content": "Test different VIP discount offers to see which performs better",
                            "experimentName": "VIP Discount Test",
                            "version": "1",
                            "events": [
                                {
                                    "type": "split",
                                    "label": "Control Group (15% off)",
                                    "action": "control",
                                    "nextStepID": "control-message-002",
                                },
                                {
                                    "type": "split",
                                    "label": "Variant Group (25% off)",
                                    "action": "variant",
                                    "nextStepID": "variant-message-003",
                                }
                            ]
                        },
                        # Step 2: Control Message
                        {
                            "id": "control-message-002",
                            "type": "split_group",
                            "label": "Control Group - 15% VIP Offer",
                            "content": "Control group receives 15% VIP discount offer",
                            "enabled": True,
                            "action": "control",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "segment-control-004"
                                }
                            ]
                        },
                        # Step 3: Variant Message
                        {
                            "id": "variant-message-003",
                            "type": "split_group",
                            "label": "Variant Group - 25% VIP Offer",
                            "content": "Variant group receives 25% VIP discount offer",
                            "enabled": True,
                            "action": "variant",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "segment-variant-005"
                                }
                            ]
                        },
                        # Step 4: Segment Control Group VIP Customers
                        {
                            "id": "segment-control-004",
                            "type": "segment",
                            "label": "Control Group VIP Segmentation",
                            "content": "Segment control group customers by VIP status",
                            "conditions": [
                                {
                                    "id": "vip-status-control-001",
                                    "type": "property",
                                    "action": "customer_type",
                                    "operator": "has",
                                    "filter": "vip",
                                    "timePeriod": "within the last 30 days",
                                    "timePeriodType": "relative",
                                    "filterTab": "productId",
                                    "cartFilterTab": "productId",
                                    "optInFilterTab": "keywords",
                                    "showFilterOptions": False,
                                    "showLinkFilterOptions": False,
                                    "showCartFilterOptions": False,
                                    "showOptInFilterOptions": False,
                                    "filterData": None
                                }
                            ],
                            "segmentDefinition": {},
                            "events": [
                                {
                                    "id": "vip-include-control-001",
                                    "type": "split",
                                    "label": "Include VIP Customers",
                                    "action": "include",
                                    "nextStepID": "vip-products-control-006",
                                },
                                {
                                    "id": "vip-exclude-control-001",
                                    "type": "split",
                                    "label": "Exclude Non-VIP",
                                    "action": "exclude",
                                    "nextStepID": "end-flow-010"
                                }
                            ]
                        },
                        # Step 5: Segment Variant Group VIP Customers
                        {
                            "id": "segment-variant-005",
                            "type": "segment",
                            "label": "Variant Group VIP Segmentation",
                            "content": "Segment variant group customers by VIP status",
                            "conditions": [
                                {
                                    "id": "vip-status-variant-001",
                                    "type": "property",
                                    "action": "customer_type",
                                    "operator": "has",
                                    "filter": "vip",
                                    "timePeriod": "within the last 30 days",
                                    "timePeriodType": "relative",
                                    "filterTab": "productId",
                                    "cartFilterTab": "productId",
                                    "optInFilterTab": "keywords",
                                    "showFilterOptions": False,
                                    "showLinkFilterOptions": False,
                                    "showCartFilterOptions": False,
                                    "showOptInFilterOptions": False,
                                    "filterData": None
                                }
                            ],
                            "segmentDefinition": {},
                            "events": [
                                {
                                    "id": "vip-include-variant-001",
                                    "type": "split",
                                    "label": "Include VIP Customers",
                                    "action": "include",
                                    "nextStepID": "vip-products-variant-007",
                                },
                                {
                                    "id": "vip-exclude-variant-001",
                                    "type": "split",
                                    "label": "Exclude Non-VIP",
                                    "action": "exclude",
                                    "nextStepID": "end-flow-011"
                                }
                            ]
                        },
                        # Step 6: Control Group VIP Products
                        {
                            "id": "vip-products-control-006",
                            "type": "product_choice",
                            "label": "Control Group VIP Products",
                            "content": "Show exclusive VIP products to control group",
                            "messageType": "standard",
                            "messageText": "As a valued VIP, enjoy 15% off our exclusive collection:\n\n{{Product List}}\n\nReply with number to purchase!",
                            "productSelection": "manually",
                            "products": [
                                {
                                    "id": "vip-product-001",
                                    "productVariantId": "vip-product-001-variant",
                                    "quantity": "1",
                                    "label": "VIP Exclusive Item 1",
                                    "uniqueId": 1
                                },
                                {
                                    "id": "vip-product-002",
                                    "productVariantId": "vip-product-002-variant",
                                    "quantity": "1",
                                    "label": "VIP Exclusive Item 2",
                                    "uniqueId": 2
                                }
                            ],
                            "productImages": True,
                            "discountType": "percentage",
                            "discountValue": "15",
                            "discountCode": "VIP15TEST",
                            "events": [
                                {
                                    "type": "reply",
                                    "intent": "buy",
                                    "description": "Customer wants to buy VIP product",
                                    "nextStepID": "vip-purchase-control-008"
                                }
                            ]
                        },
                        # Step 7: Variant Group VIP Products
                        {
                            "id": "vip-products-variant-007",
                            "type": "product_choice",
                            "label": "Variant Group VIP Products",
                            "content": "Show exclusive VIP products to variant group",
                            "messageType": "standard",
                            "messageText": "As a valued VIP, enjoy 25% off our exclusive collection:\n\n{{Product List}}\n\nReply with number to purchase!",
                            "productSelection": "manually",
                            "products": [
                                {
                                    "id": "vip-product-001",
                                    "productVariantId": "vip-product-001-variant",
                                    "quantity": "1",
                                    "label": "VIP Exclusive Item 1",
                                    "uniqueId": 1
                                },
                                {
                                    "id": "vip-product-002",
                                    "productVariantId": "vip-product-002-variant",
                                    "quantity": "1",
                                    "label": "VIP Exclusive Item 2",
                                    "uniqueId": 2
                                }
                            ],
                            "productImages": True,
                            "discountType": "percentage",
                            "discountValue": "25",
                            "discountCode": "VIP25TEST",
                            "events": [
                                {
                                    "type": "reply",
                                    "intent": "buy",
                                    "description": "Customer wants to buy VIP product",
                                    "nextStepID": "vip-purchase-variant-009"
                                }
                            ]
                        },
                        # Step 8: Control Group VIP Purchase
                        {
                            "id": "vip-purchase-control-008",
                            "type": "purchase",
                            "label": "Process Control Group VIP Purchase",
                            "content": "Process control group VIP customer purchase with 15% discount",
                            "cartSource": "latest",
                            "products": [],
                            "discountType": "percentage",
                            "discountValue": "15",
                            "discountCode": "VIP15TEST",
                            "sendReminderForNonPurchasers": True,
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "vip-thank-you-control-010"
                                }
                            ]
                        },
                        # Step 9: Variant Group VIP Purchase
                        {
                            "id": "vip-purchase-variant-009",
                            "type": "purchase",
                            "label": "Process Variant Group VIP Purchase",
                            "content": "Process variant group VIP customer purchase with 25% discount",
                            "cartSource": "latest",
                            "products": [],
                            "discountType": "percentage",
                            "discountValue": "25",
                            "discountCode": "VIP25TEST",
                            "sendReminderForNonPurchasers": True,
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "vip-thank-you-variant-011"
                                }
                            ]
                        },
                        # Step 10: Control Group Thank You
                        {
                            "id": "vip-thank-you-control-010",
                            "type": "message",
                            "label": "Control Group VIP Thank You",
                            "content": "Send control group VIP purchase confirmation",
                            "messageType": "standard",
                            "messageText": "Thank you {{first_name}}! Your VIP order is confirmed. Enjoy 15% off your exclusive products! 👑",
                            "addImage": False,
                            "sendContactCard": True,
                            "discountType": "none",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "end-flow-012"
                                }
                            ]
                        },
                        # Step 11: Variant Group Thank You
                        {
                            "id": "vip-thank-you-variant-011",
                            "type": "message",
                            "label": "Variant Group VIP Thank You",
                            "content": "Send variant group VIP purchase confirmation",
                            "messageType": "standard",
                            "messageText": "Thank you {{first_name}}! Your VIP order is confirmed. Enjoy 25% off your exclusive products! 👑",
                            "addImage": False,
                            "sendContactCard": True,
                            "discountType": "none",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "end-flow-013"
                                }
                            ]
                        },
                        # Step 12: END (Control Group Non-VIP Path)
                        {
                            "id": "end-flow-010",
                            "type": "end",
                            "label": "Control Group Non-VIP Path End",
                            "content": "End of control group non-VIP customer path"
                        },
                        # Step 13: END (Variant Group Non-VIP Path)
                        {
                            "id": "end-flow-011",
                            "type": "end",
                            "label": "Variant Group Non-VIP Path End",
                            "content": "End of variant group non-VIP customer path"
                        },
                        # Step 14: END (Control Group VIP Path)
                        {
                            "id": "end-flow-012",
                            "type": "end",
                            "label": "Control Group VIP Campaign End",
                            "content": "End of control group VIP A/B testing campaign"
                        },
                        # Step 15: END (Variant Group VIP Path)
                        {
                            "id": "end-flow-013",
                            "type": "end",
                            "label": "Variant Group VIP Campaign End",
                            "content": "End of variant group VIP A/B testing campaign"
                        }
                    ]
                }
            },
            # Template 3: Flash Sale Campaign
            # Start -> Announce -> Product Choice -> Urgency Timer -> Purchase -> Thank You -> END
            {
                "description": "Limited-time flash sale campaign with urgency messaging",
                "template_category": "flash_sale",
                "complexity": "medium",
                "flow": {
                    "name": "Flash Sale Campaign",
                    "description": "Announce urgent flash sale with time-limited discount and encourage immediate purchase",
                    "initialStepID": "flash-announce-001",
                    "steps": [
                        # Step 1: Announce Flash Sale
                        {
                            "id": "flash-announce-001",
                            "type": "message",
                            "label": "Flash Sale Announcement",
                            "content": "Announce flash sale to customers",
                            "messageType": "standard",
                            "messageText": "🔥 FLASH SALE! 30% off everything for the next 48 hours only! Use code FLASH30 at checkout!",
                            "addImage": True,
                            "imageUrl": "https://example.com/flash-sale-banner.jpg",
                            "sendContactCard": True,
                            "discountType": "percentage",
                            "discountValue": "30",
                            "discountCode": "FLASH30",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "product-choice-003"
                                }
                            ]
                        },
                        # Step 2: Product Choice
                        {
                            "id": "product-choice-003",
                            "type": "product_choice",
                            "label": "Flash Sale Products",
                            "content": "Show flash sale products",
                            "messageType": "standard",
                            "messageText": "Browse our flash sale deals:\n\n{{Product List}}\n\nReply with number to purchase! ⏰ Limited time!",
                            "productSelection": "popularity",
                            "products": [
                                {
                                    "id": "flash-product-001",
                                    "productVariantId": "flash-product-001-variant",
                                    "quantity": "1",
                                    "label": "Flash Deal Item 1",
                                    "uniqueId": 1
                                },
                                {
                                    "id": "flash-product-002",
                                    "productVariantId": "flash-product-002-variant",
                                    "quantity": "1",
                                    "label": "Flash Deal Item 2",
                                    "uniqueId": 2
                                }
                            ],
                            "productImages": True,
                            "discountType": "percentage",
                            "discountValue": "30",
                            "discountCode": "FLASH30",
                            "events": [
                                {
                                    "type": "reply",
                                    "intent": "buy",
                                    "description": "Customer wants to buy flash sale item",
                                    "nextStepID": "urgency-timer-003"
                                }
                            ]
                        },
                        # Step 3: Urgency Timer
                        {
                            "id": "urgency-timer-003",
                            "type": "delay",
                            "label": "Flash Sale Urgency Timer",
                            "content": "Create urgency with 2-hour timer",
                            "time": 2,
                            "period": "Hours",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "purchase-004"
                                }
                            ]
                        },
                        # Step 4: Purchase
                        {
                            "id": "purchase-004",
                            "type": "purchase",
                            "label": "Process Flash Sale Purchase",
                            "content": "Process customer purchase with flash sale discount",
                            "cartSource": "latest",
                            "products": [],
                            "discountType": "percentage",
                            "discountValue": "30",
                            "discountCode": "FLASH30",
                            "sendReminderForNonPurchasers": True,
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "thank-you-005"
                                }
                            ]
                        },
                        # Step 5: Thank You
                        {
                            "id": "thank-you-005",
                            "type": "message",
                            "label": "Flash Sale Thank You",
                            "content": "Send flash sale purchase confirmation",
                            "messageType": "standard",
                            "messageText": "🎉 Thank you {{first_name}}! Your flash sale order is confirmed. You saved 30% with FLASH30!",
                            "addImage": False,
                            "sendContactCard": True,
                            "discountType": "none",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "end-flow-006"
                                }
                            ]
                        },
                        # Step 6: END
                        {
                            "id": "end-flow-006",
                            "type": "end",
                            "label": "Flash Sale Campaign End",
                            "content": "End of Flash Sale Campaign"
                        }
                    ]
                }
            },
            # Template 4: Re-engagement Campaign
            # Start -> Segment (Inactive) -> Special Offer -> Product Choice -> Purchase -> Thank You -> Property Update -> END
            {
                "description": "Win-back campaign for inactive customers",
                "template_category": "re_engagement",
                "complexity": "medium",
                "flow": {
                    "name": "Re-engagement Campaign",
                    "description": "Target inactive customers with special offers and encourage them to return to make a purchase",
                    "initialStepID": "segment-inactive-001",
                    "steps": [
                        # Step 1: Segment (Inactive)
                        {
                            "id": "segment-inactive-001",
                            "type": "segment",
                            "label": "Inactive Customer Segment",
                            "content": "Identify customers who haven't purchased in 90 days",
                            "conditions": [
                                {
                                    "id": "inactive-check-001",
                                    "type": "property",
                                    "action": "last_purchase_date",
                                    "operator": "before",
                                    "filter": "90 days ago",
                                    "timePeriod": "within the last 90 days",
                                    "timePeriodType": "relative",
                                    "filterTab": "date",
                                    "cartFilterTab": "productId",
                                    "optInFilterTab": "keywords",
                                    "showFilterOptions": False,
                                    "showLinkFilterOptions": False,
                                    "showCartFilterOptions": False,
                                    "showOptInFilterOptions": False,
                                    "filterData": None
                                }
                            ],
                            "segmentDefinition": {},
                            "events": [
                                {
                                    "id": "inactive-include-001",
                                    "type": "split",
                                    "label": "Include Inactive",
                                    "action": "include",
                                    "nextStepID": "special-offer-002"
                                }
                            ]
                        },
                        # Step 2: Special Offer
                        {
                            "id": "special-offer-002",
                            "type": "message",
                            "label": "Re-engagement Special Offer",
                            "content": "Send special offer to inactive customers",
                            "messageType": "standard",
                            "messageText": "Hi {{first_name}}! We miss you! Here's a special 25% off to welcome you back. Use code COMEBACK25",
                            "addImage": False,
                            "sendContactCard": True,
                            "discountType": "percentage",
                            "discountValue": "25",
                            "discountCode": "COMEBACK25",
                            "discountExpiry": "2024-12-31T23:59:59",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "product-choice-004"
                                }
                            ]
                        },
                        # Step 3: Product Choice
                        {
                            "id": "product-choice-004",
                            "type": "product_choice",
                            "label": "Welcome Back Products",
                            "content": "Show popular products to returning customer",
                            "messageType": "standard",
                            "messageText": "Here are our most popular items since you've been gone:\n\n{{Product List}}\n\nReply with number to shop!",
                            "productSelection": "popularity",
                            "products": [
                                {
                                    "id": "popular-001",
                                    "productVariantId": "popular-001-variant",
                                    "quantity": "1",
                                    "label": "Popular Item 1",
                                    "uniqueId": 1
                                },
                                {
                                    "id": "popular-002",
                                    "productVariantId": "popular-002-variant",
                                    "quantity": "1",
                                    "label": "Popular Item 2",
                                    "uniqueId": 2
                                }
                            ],
                            "productImages": True,
                            "discountType": "percentage",
                            "discountValue": "25",
                            "discountCode": "COMEBACK25",
                            "events": [
                                {
                                    "type": "reply",
                                    "intent": "buy",
                                    "description": "Customer wants to buy product",
                                    "nextStepID": "purchase-005"
                                }
                            ]
                        },
                        # Step 4: Purchase
                        {
                            "id": "purchase-005",
                            "type": "purchase",
                            "label": "Process Welcome Back Purchase",
                            "content": "Process customer purchase with re-engagement discount",
                            "cartSource": "latest",
                            "products": [],
                            "discountType": "percentage",
                            "discountValue": "25",
                            "discountCode": "COMEBACK25",
                            "sendReminderForNonPurchasers": True,
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "thank-you-006"
                                }
                            ]
                        },
                        # Step 5: Thank You
                        {
                            "id": "thank-you-006",
                            "type": "message",
                            "label": "Re-engagement Thank You",
                            "content": "Send purchase confirmation",
                            "messageType": "standard",
                            "messageText": "Thank you {{first_name}}! Your order is confirmed. Welcome back! 🎁",
                            "addImage": False,
                            "sendContactCard": False,
                            "discountType": "none",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "property-update-006"
                                }
                            ]
                        },
                        # Step 6: Property Update
                        {
                            "id": "property-update-006",
                            "type": "property",
                            "label": "Update Customer Status",
                            "content": "Update customer status after re-engagement",
                            "action": "customer_reengaged",
                            "eventName": "customer_reengaged",
                            "enabled": True,
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "end-flow-007"
                                }
                            ]
                        },
                        # Step 7: END
                        {
                            "id": "end-flow-007",
                            "type": "end",
                            "label": "Re-engagement Campaign End",
                            "content": "End of Re-engagement Campaign"
                        }
                    ]
                }
            },
            # Template 5: Quiz Marketing Campaign
            # Start -> Quiz -> Property Update -> Product Recommendation -> Purchase -> Thank You -> END
            {
                "description": "Interactive quiz campaign for personalized product recommendations",
                "template_category": "quiz_marketing",
                "complexity": "medium",
                "flow": {
                    "name": "Quiz Marketing Campaign",
                    "description": "Engage customers with preference quiz and provide personalized product recommendations",
                    "initialStepID": "quiz-001",
                    "steps": [
                        # Step 1: Quiz Message
                        {
                            "id": "quiz-001",
                            "type": "message",
                            "label": "Product Preference Quiz",
                            "content": "Ask customer about product preferences",
                            "messageType": "standard",
                            "messageText": "What type of products are you most interested in?\\n\\n1. Electronics - Tech gadgets and electronics\\n2. Fashion - Clothing and accessories\\n3. Home & Living - Home decor and lifestyle products\\n\\nReply with 1, 2, or 3!",
                            "addImage": False,
                            "sendContactCard": False,
                            "discountType": "none",
                            "events": [
                                {
                                    "type": "reply",
                                    "intent": "1",
                                    "description": "Customer prefers electronics",
                                    "nextStepID": "property-electronics-002"
                                },
                                {
                                    "type": "reply",
                                    "intent": "2",
                                    "description": "Customer prefers fashion",
                                    "nextStepID": "property-fashion-003"
                                },
                                {
                                    "type": "reply",
                                    "intent": "3",
                                    "description": "Customer prefers home items",
                                    "nextStepID": "property-home-004"
                                }
                            ]
                        },
                        # Step 2: Property Update - Electronics
                        {
                            "id": "property-electronics-002",
                            "type": "property",
                            "label": "Store Electronics Preference",
                            "content": "Update customer electronics preference",
                            "action": "customer_preference",
                            "eventName": "preference_updated",
                            "enabled": True,
                            "property": "product_category",
                            "value": "electronics",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "product-electronics-005"
                                }
                            ]
                        },
                        # Step 3: Property Update - Fashion
                        {
                            "id": "property-fashion-003",
                            "type": "property",
                            "label": "Store Fashion Preference",
                            "content": "Update customer fashion preference",
                            "action": "customer_preference",
                            "eventName": "preference_updated",
                            "enabled": True,
                            "property": "product_category",
                            "value": "fashion",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "product-fashion-006"
                                }
                            ]
                        },
                        # Step 4: Property Update - Home
                        {
                            "id": "property-home-004",
                            "type": "property",
                            "label": "Store Home Preference",
                            "content": "Update customer home preference",
                            "action": "customer_preference",
                            "eventName": "preference_updated",
                            "enabled": True,
                            "property": "product_category",
                            "value": "home_living",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "product-home-007"
                                }
                            ]
                        },
                        # Step 5: Product Recommendation - Electronics
                        {
                            "id": "product-electronics-005",
                            "type": "product_choice",
                            "label": "Electronics Product Recommendations",
                            "content": "Show electronics products based on customer preferences",
                            "messageType": "standard",
                            "messageText": "Based on your electronics preferences, we recommend these products:\n\n{{Product List}}\n\nReply with number to purchase!",
                            "productSelection": "manually",
                            "products": [
                                {
                                    "id": "electronics-001",
                                    "productVariantId": "electronics-001-variant",
                                    "quantity": "1",
                                    "label": "Electronics Product 1",
                                    "uniqueId": 1
                                },
                                {
                                    "id": "electronics-002",
                                    "productVariantId": "electronics-002-variant",
                                    "quantity": "1",
                                    "label": "Electronics Product 2",
                                    "uniqueId": 2
                                }
                            ],
                            "productImages": True,
                            "discountType": "percentage",
                            "discountValue": "15",
                            "discountCode": "QUIZ15",
                            "events": [
                                {
                                    "type": "reply",
                                    "intent": "buy",
                                    "description": "Customer wants to buy electronics product",
                                    "nextStepID": "purchase-electronics-008"
                                }
                            ]
                        },
                        # Step 6: Product Recommendation - Fashion
                        {
                            "id": "product-fashion-006",
                            "type": "product_choice",
                            "label": "Fashion Product Recommendations",
                            "content": "Show fashion products based on customer preferences",
                            "messageType": "standard",
                            "messageText": "Based on your fashion preferences, we recommend these products:\n\n{{Product List}}\n\nReply with number to purchase!",
                            "productSelection": "manually",
                            "products": [
                                {
                                    "id": "fashion-001",
                                    "productVariantId": "fashion-001-variant",
                                    "quantity": "1",
                                    "label": "Fashion Product 1",
                                    "uniqueId": 1
                                },
                                {
                                    "id": "fashion-002",
                                    "productVariantId": "fashion-002-variant",
                                    "quantity": "1",
                                    "label": "Fashion Product 2",
                                    "uniqueId": 2
                                }
                            ],
                            "productImages": True,
                            "discountType": "percentage",
                            "discountValue": "15",
                            "discountCode": "QUIZ15",
                            "events": [
                                {
                                    "type": "reply",
                                    "intent": "buy",
                                    "description": "Customer wants to buy fashion product",
                                    "nextStepID": "purchase-fashion-009"
                                }
                            ]
                        },
                        # Step 7: Product Recommendation - Home
                        {
                            "id": "product-home-007",
                            "type": "product_choice",
                            "label": "Home Product Recommendations",
                            "content": "Show home products based on customer preferences",
                            "messageType": "standard",
                            "messageText": "Based on your home preferences, we recommend these products:\n\n{{Product List}}\n\nReply with number to purchase!",
                            "productSelection": "manually",
                            "products": [
                                {
                                    "id": "home-001",
                                    "productVariantId": "home-001-variant",
                                    "quantity": "1",
                                    "label": "Home Product 1",
                                    "uniqueId": 1
                                },
                                {
                                    "id": "home-002",
                                    "productVariantId": "home-002-variant",
                                    "quantity": "1",
                                    "label": "Home Product 2",
                                    "uniqueId": 2
                                }
                            ],
                            "productImages": True,
                            "discountType": "percentage",
                            "discountValue": "15",
                            "discountCode": "QUIZ15",
                            "events": [
                                {
                                    "type": "reply",
                                    "intent": "buy",
                                    "description": "Customer wants to buy home product",
                                    "nextStepID": "purchase-home-010"
                                }
                            ]
                        },
                        # Step 8: Purchase - Electronics
                        {
                            "id": "purchase-electronics-008",
                            "type": "purchase",
                            "label": "Process Quiz Purchase - Electronics",
                            "content": "Process customer electronics purchase with quiz discount",
                            "cartSource": "latest",
                            "products": [],
                            "discountType": "percentage",
                            "discountValue": "15",
                            "discountCode": "QUIZ15",
                            "sendReminderForNonPurchasers": True,
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "thank-you-electronics-011"
                                }
                            ]
                        },
                        # Step 9: Purchase - Fashion
                        {
                            "id": "purchase-fashion-009",
                            "type": "purchase",
                            "label": "Process Quiz Purchase - Fashion",
                            "content": "Process customer fashion purchase with quiz discount",
                            "cartSource": "latest",
                            "products": [],
                            "discountType": "percentage",
                            "discountValue": "15",
                            "discountCode": "QUIZ15",
                            "sendReminderForNonPurchasers": True,
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "thank-you-fashion-012"
                                }
                            ]
                        },
                        # Step 10: Purchase - Home
                        {
                            "id": "purchase-home-010",
                            "type": "purchase",
                            "label": "Process Quiz Purchase - Home",
                            "content": "Process customer home purchase with quiz discount",
                            "cartSource": "latest",
                            "products": [],
                            "discountType": "percentage",
                            "discountValue": "15",
                            "discountCode": "QUIZ15",
                            "sendReminderForNonPurchasers": True,
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "thank-you-home-013"
                                }
                            ]
                        },
                        # Step 11: Thank You - Electronics
                        {
                            "id": "thank-you-electronics-011",
                            "type": "message",
                            "label": "Electronics Quiz Thank You",
                            "content": "Send electronics purchase confirmation with personalized message",
                            "messageType": "standard",
                            "messageText": "Thank you {{first_name}}! Your electronics order is confirmed. We appreciate you taking our quiz! 🎁",
                            "addImage": False,
                            "sendContactCard": True,
                            "discountType": "none",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "end-flow-electronics-014"
                                }
                            ]
                        },
                        # Step 12: Thank You - Fashion
                        {
                            "id": "thank-you-fashion-012",
                            "type": "message",
                            "label": "Fashion Quiz Thank You",
                            "content": "Send fashion purchase confirmation with personalized message",
                            "messageType": "standard",
                            "messageText": "Thank you {{first_name}}! Your fashion order is confirmed. We appreciate you taking our quiz! 🎁",
                            "addImage": False,
                            "sendContactCard": True,
                            "discountType": "none",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "end-flow-fashion-015"
                                }
                            ]
                        },
                        # Step 13: Thank You - Home
                        {
                            "id": "thank-you-home-013",
                            "type": "message",
                            "label": "Home Quiz Thank You",
                            "content": "Send home purchase confirmation with personalized message",
                            "messageType": "standard",
                            "messageText": "Thank you {{first_name}}! Your home order is confirmed. We appreciate you taking our quiz! 🎁",
                            "addImage": False,
                            "sendContactCard": True,
                            "discountType": "none",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "end-flow-home-016"
                                }
                            ]
                        },
                        # Step 14: END - Electronics
                        {
                            "id": "end-flow-electronics-014",
                            "type": "end",
                            "label": "Electronics Quiz Campaign End",
                            "content": "End of Quiz Marketing Campaign for electronics customers"
                        },
                        # Step 15: END - Fashion
                        {
                            "id": "end-flow-fashion-015",
                            "type": "end",
                            "label": "Fashion Quiz Campaign End",
                            "content": "End of Quiz Marketing Campaign for fashion customers"
                        },
                        # Step 16: END - Home
                        {
                            "id": "end-flow-home-016",
                            "type": "end",
                            "label": "Home Quiz Campaign End",
                            "content": "End of Quiz Marketing Campaign for home customers"
                        }
                    ]
                }
            },
            # Template 6: Drip Campaign with Rate Limit
            # Start -> Rate Limit -> Message 1 -> Delay -> Message 2 -> Delay -> Message 3 -> END
            {
                "description": "Multi-message nurturing campaign with rate limiting",
                "template_category": "drip_campaign",
                "complexity": "medium",
                "flow": {
                    "name": "Multi-Message Drip Campaign",
                    "description": "Engage subscribers with valuable content over time using a nurturing sequence",
                    "initialStepID": "rate-limit-001",
                    "steps": [
                        # Step 1: Rate Limit
                        {
                            "id": "rate-limit-001",
                            "type": "rate_limit",
                            "label": "Rate Limit Drip Campaign",
                            "content": "Apply rate limiting for drip campaign",
                            "enabled": True,
                            "limit": 100,
                            "period": "daily",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "drip-message-1-002"
                                }
                            ]
                        },
                        # Step 2: Message 1
                        {
                            "id": "drip-message-1-002",
                            "type": "message",
                            "label": "Drip Message 1 - Introduction",
                            "content": "First message in drip campaign sequence",
                            "messageType": "standard",
                            "messageText": "Hi {{first_name}}! Welcome to our VIP insights. This week: {{weekly_topic}} 🎯",
                            "addImage": False,
                            "sendContactCard": False,
                            "discountType": "none",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "drip-delay-1-003"
                                }
                            ]
                        },
                        # Step 3: Delay 1
                        {
                            "id": "drip-delay-1-003",
                            "type": "delay",
                            "label": "Wait 3 Days",
                            "content": "Wait 3 days before next message",
                            "time": 3,
                            "period": "Days",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "drip-message-2-004"
                                }
                            ]
                        },
                        # Step 4: Message 2
                        {
                            "id": "drip-message-2-004",
                            "type": "message",
                            "label": "Drip Message 2 - Value Content",
                            "content": "Second message with valuable content",
                            "messageType": "standard",
                            "messageText": "Quick tip for {{first_name}}: {{pro_tip}} 💡 Reply LEARN for more insights!",
                            "addImage": False,
                            "sendContactCard": False,
                            "discountType": "none",
                            "events": [
                                {
                                    "id": "drip-2-response-001",
                                    "type": "reply",
                                    "intent": "learn",
                                    "description": "Customer wants more content",
                                    "nextStepID": "drip-bonus-006"
                                },
                                {
                                    "type": "default",
                                    "nextStepID": "drip-delay-2-005"
                                }
                            ]
                        },
                        # Step 5: Delay 2
                        {
                            "id": "drip-delay-2-005",
                            "type": "delay",
                            "label": "Wait 4 Days",
                            "content": "Wait 4 days before next message",
                            "time": 4,
                            "period": "Days",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "drip-message-3-007"
                                }
                            ]
                        },
                        # Step 6: Bonus Content (if customer responded)
                        {
                            "id": "drip-bonus-006",
                            "type": "message",
                            "label": "Bonus Content",
                            "content": "Send bonus content to engaged customer",
                            "messageType": "standard",
                            "messageText": "Great {{first_name}}! Here's your exclusive content: {{bonus_content}} 📚",
                            "addImage": False,
                            "sendContactCard": False,
                            "discountType": "none",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "drip-delay-bonus-010"
                                }
                            ]
                        },
                        # Step 7: Delay 2 Bonus Path
                        {
                            "id": "drip-delay-bonus-010",
                            "type": "delay",
                            "label": "Wait 2 Days After Bonus",
                            "content": "Wait 2 days after bonus content",
                            "time": 2,
                            "period": "Days",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "drip-message-3-bonus-011"
                                }
                            ]
                        },
                        # Step 8: Message 3
                        {
                            "id": "drip-message-3-007",
                            "type": "message",
                            "label": "Drip Message 3 - Special Offer",
                            "content": "Third message with special offer",
                            "messageType": "standard",
                            "messageText": "Hi {{first_name}}! As a valued subscriber, here's 15% off your next order: LOYALTY15 🎁",
                            "addImage": False,
                            "sendContactCard": True,
                            "discountType": "percentage",
                            "discountValue": "15",
                            "discountCode": "LOYALTY15",
                            "events": [
                                {
                                    "type": "reply",
                                    "intent": "shop",
                                    "description": "Customer wants to shop with discount",
                                    "nextStepID": "drip-purchase-008"
                                },
                                {
                                    "type": "default",
                                    "nextStepID": "drip-campaign-end-no-purchase-009"
                                }
                            ]
                        },
                        # Step 9: Message 3 Bonus Path
                        {
                            "id": "drip-message-3-bonus-011",
                            "type": "message",
                            "label": "Drip Message 3 - Special Offer (Bonus Path)",
                            "content": "Third message with special offer for engaged customers",
                            "messageType": "standard",
                            "messageText": "Hi {{first_name}}! Here's an extra 20% off for being so engaged: LOYALTY20 🎁",
                            "addImage": False,
                            "sendContactCard": True,
                            "discountType": "percentage",
                            "discountValue": "20",
                            "discountCode": "LOYALTY20",
                            "events": [
                                {
                                    "type": "reply",
                                    "intent": "shop",
                                    "description": "Customer wants to shop with bonus discount",
                                    "nextStepID": "drip-purchase-bonus-012"
                                },
                                {
                                    "type": "default",
                                    "nextStepID": "drip-campaign-end-no-purchase-bonus-013"
                                }
                            ]
                        },
                        # Step 10: Purchase (optional)
                        {
                            "id": "drip-purchase-008",
                            "type": "purchase",
                            "label": "Process Drip Campaign Purchase",
                            "content": "Process customer purchase with loyalty discount",
                            "cartSource": "latest",
                            "discountType": "percentage",
                            "discountValue": "15",
                            "discountCode": "LOYALTY15",
                            "sendReminderForNonPurchasers": False,
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "drip-campaign-end-after-purchase-014"
                                }
                            ]
                        },
                        # Step 11: Purchase Bonus Path (optional)
                        {
                            "id": "drip-purchase-bonus-012",
                            "type": "purchase",
                            "label": "Process Drip Campaign Purchase (Bonus Path)",
                            "content": "Process customer purchase with bonus discount",
                            "cartSource": "latest",
                            "discountType": "percentage",
                            "discountValue": "20",
                            "discountCode": "LOYALTY20",
                            "sendReminderForNonPurchasers": False,
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "drip-campaign-end-after-purchase-bonus-015"
                                }
                            ]
                        },
                        # Step 12: END (Standard Path - No Purchase)
                        {
                            "id": "drip-campaign-end-no-purchase-009",
                            "type": "end",
                            "label": "Drip Campaign End (No Purchase)",
                            "content": "End of Drip Campaign without purchase"
                        },
                        # Step 13: END (Bonus Path - No Purchase)
                        {
                            "id": "drip-campaign-end-no-purchase-bonus-013",
                            "type": "end",
                            "label": "Drip Campaign End (No Purchase - Bonus Path)",
                            "content": "End of Drip Campaign for engaged customers without purchase"
                        },
                        # Step 14: END (Standard Path - After Purchase)
                        {
                            "id": "drip-campaign-end-after-purchase-014",
                            "type": "end",
                            "label": "Drip Campaign End (After Purchase)",
                            "content": "End of Drip Campaign after successful purchase"
                        },
                        # Step 15: END (Bonus Path - After Purchase)
                        {
                            "id": "drip-campaign-end-after-purchase-bonus-015",
                            "type": "end",
                            "label": "Drip Campaign End (After Purchase - Bonus Path)",
                            "content": "End of Drip Campaign for engaged customers after successful purchase"
                        }
                    ]
                }
            },
            # Template 7: Birthday/Anniversary Campaign
            # Start -> Segment (Birthday) -> Personalized Message -> Special Offer -> Product Choice -> Purchase -> Thank You -> END
            {
                "description": "Personalized birthday/anniversary campaign with special offers",
                "template_category": "birthday_campaign",
                "complexity": "medium",
                "flow": {
                    "name": "Birthday/Anniversary Campaign",
                    "description": "Send personalized birthday/anniversary messages with special offers and birthday gifts",
                    "initialStepID": "segment-birthday-001",
                    "steps": [
                        # Step 1: Segment (Birthday/Anniversary)
                        {
                            "id": "segment-birthday-001",
                            "type": "segment",
                            "label": "Birthday/Anniversary Segment",
                            "content": "Identify customers with upcoming birthdays or anniversaries",
                            "conditions": [
                                {
                                    "id": "birthday-check-001",
                                    "type": "property",
                                    "action": "birthday",
                                    "operator": "within",
                                    "filter": "7 days",
                                    "timePeriod": "within the next 7 days",
                                    "timePeriodType": "relative",
                                    "filterTab": "date",
                                    "cartFilterTab": "productId",
                                    "optInFilterTab": "keywords",
                                    "showFilterOptions": False,
                                    "showLinkFilterOptions": False,
                                    "showCartFilterOptions": False,
                                    "showOptInFilterOptions": False,
                                    "filterData": None
                                }
                            ],
                            "segmentDefinition": {},
                            "events": [
                                {
                                    "id": "birthday-include-001",
                                    "type": "split",
                                    "label": "Include Birthday/Anniversary",
                                    "action": "include",
                                    "nextStepID": "birthday-message-002"
                                }
                            ]
                        },
                        # Step 2: Personalized Birthday Message
                        {
                            "id": "birthday-message-002",
                            "type": "message",
                            "label": "Birthday/Anniversary Message",
                            "content": "Send personalized birthday/anniversary message",
                            "messageType": "personalized",
                            "messageText": "Happy Birthday {{first_name}}! 🎂 As our valued customer, here's a special 25% off gift just for you!",
                            "addImage": True,
                            "imageUrl": "https://example.com/birthday-cake.jpg",
                            "sendContactCard": True,
                            "discountType": "percentage",
                            "discountValue": "25",
                            "discountCode": "BIRTHDAY25",
                            "discountExpiry": "2024-12-31T23:59:59",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "birthday-gift-003"
                                }
                            ]
                        },
                        # Step 3: Birthday Gift
                        {
                            "id": "birthday-gift-003",
                            "type": "product_choice",
                            "label": "Birthday Gift Selection",
                            "content": "Offer special birthday gifts",
                            "messageType": "personalized",
                            "messageText": "Choose your birthday gift:\n\n{{Product List}}\n\nReply with number to claim your gift! 🎁",
                            "productSelection": "manually",
                            "products": [
                                {
                                    "id": "birthday-gift-001",
                                    "productVariantId": "birthday-gift-001-variant",
                                    "quantity": "1",
                                    "label": "Birthday Special Item 1",
                                    "uniqueId": 1
                                },
                                {
                                    "id": "birthday-gift-002",
                                    "productVariantId": "birthday-gift-002-variant",
                                    "quantity": "1",
                                    "label": "Birthday Special Item 2",
                                    "uniqueId": 2
                                }
                            ],
                            "productImages": True,
                            "discountType": "percentage",
                            "discountValue": "25",
                            "discountCode": "BIRTHDAY25",
                            "events": [
                                {
                                    "type": "reply",
                                    "intent": "buy",
                                    "description": "Customer claims birthday gift",
                                    "nextStepID": "birthday-purchase-004"
                                }
                            ]
                        },
                        # Step 4: Birthday Purchase
                        {
                            "id": "birthday-purchase-004",
                            "type": "purchase",
                            "label": "Process Birthday Purchase",
                            "content": "Process birthday gift purchase with special discount",
                            "cartSource": "latest",
                            "products": [],
                            "discountType": "percentage",
                            "discountValue": "25",
                            "discountCode": "BIRTHDAY25",
                            "sendReminderForNonPurchasers": True,
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "birthday-thank-you-005"
                                }
                            ]
                        },
                        # Step 5: Thank You
                        {
                            "id": "birthday-thank-you-005",
                            "type": "message",
                            "label": "Birthday Thank You",
                            "content": "Send birthday wishes and confirmation",
                            "messageType": "personalized",
                            "messageText": "Happy Birthday again {{first_name}}! Thank you for celebrating with us! Enjoy your gift! 🎉",
                            "addImage": False,
                            "sendContactCard": False,
                            "discountType": "none",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "birthday-end-006"
                                }
                            ]
                        },
                        # Step 6: END
                        {
                            "id": "birthday-end-006",
                            "type": "end",
                            "label": "Birthday Campaign End",
                            "content": "End of Birthday Campaign"
                        }
                    ]
                }
            },
            # Template 8: Referral Campaign
            # Start -> Message -> Referral Instructions -> Property Update -> Thank You -> END
            {
                "description": "Customer referral campaign with rewards",
                "template_category": "referral_campaign",
                "complexity": "medium",
                "flow": {
                    "name": "Referral Campaign",
                    "description": "Encourage customers to refer friends and earn rewards",
                    "initialStepID": "referral-message-001",
                    "steps": [
                        # Step 1: Referral Message
                        {
                            "id": "referral-message-001",
                            "type": "message",
                            "label": "Referral Invitation",
                            "content": "Send referral invitation message",
                            "messageType": "standard",
                            "messageText": "Hi {{first_name}}! Share the love! Refer a friend and you both get 20% off your next order. Use code SHARE20!",
                            "addImage": False,
                            "sendContactCard": True,
                            "discountType": "percentage",
                            "discountValue": "20",
                            "discountCode": "SHARE20",
                            "events": [
                                {
                                    "type": "reply",
                                    "intent": "refer",
                                    "description": "Customer wants to refer friends",
                                    "nextStepID": "referral-instructions-002"
                                }
                            ]
                        },
                        # Step 2: Referral Instructions
                        {
                            "id": "referral-instructions-002",
                            "type": "message",
                            "label": "Referral Instructions",
                            "content": "Send referral instructions",
                            "messageType": "standard",
                            "messageText": "Share this link with friends: {{referral_link}}. They get 20% off and you get 20% off too!",
                            "addImage": False,
                            "sendContactCard": False,
                            "discountType": "none",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "property-update-003"
                                }
                            ]
                        },
                        # Step 3: Property Update
                        {
                            "id": "property-update-003",
                            "type": "property",
                            "label": "Track Referral Participation",
                            "content": "Update customer referral participation status",
                            "action": "referral_participation",
                            "eventName": "referral_initiated",
                            "enabled": True,
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "referral-thank-you-004"
                                }
                            ]
                        },
                        # Step 4: Thank You
                        {
                            "id": "referral-thank-you-004",
                            "type": "message",
                            "label": "Referral Thank You",
                            "content": "Send thank you message for participating",
                            "messageType": "standard",
                            "messageText": "Thanks for sharing! We'll notify you when your friends make a purchase. Happy sharing! 🎁",
                            "addImage": False,
                            "sendContactCard": False,
                            "discountType": "none",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "referral-end-005"
                                }
                            ]
                        },
                        # Step 5: END
                        {
                            "id": "referral-end-005",
                            "type": "end",
                            "label": "Referral Campaign End",
                            "content": "End of Referral Campaign"
                        }
                    ]
                }
            },
            # Template 9: Loyalty Points Campaign
            # Start -> Message -> Points Balance → Product Choice → Redeem → Thank You → END
            {
                "description": "Loyalty points campaign with rewards redemption",
                "template_category": "loyalty_campaign",
                "complexity": "medium",
                "flow": {
                    "name": "Loyalty Points Campaign",
                    "description": "Allow customers to redeem loyalty points for rewards",
                    "initialStepID": "loyalty-points-001",
                    "steps": [
                        # Step 1: Points Balance
                        {
                            "id": "loyalty-points-001",
                            "type": "message",
                            "label": "Loyalty Points Balance",
                            "content": "Send current points balance message",
                            "messageType": "personalized",
                            "messageText": "Hi {{first_name}}! You have {{points_balance}} loyalty points! Ready to redeem them for rewards?",
                            "addImage": False,
                            "sendContactCard": False,
                            "discountType": "none",
                            "events": [
                                {
                                    "type": "reply",
                                    "intent": "redeem",
                                    "description": "Customer wants to redeem points",
                                    "nextStepID": "loyalty-rewards-002"
                                }
                            ]
                        },
                        # Step 2: Loyalty Rewards
                        {
                            "id": "loyalty-rewards-002",
                            "type": "product_choice",
                            "label": "Loyalty Rewards Catalog",
                            "content": "Show available rewards for points redemption",
                            "messageType": "standard",
                            "messageText": "Redeem your points for these rewards:\n\n{{Product List}}\n\nReply with number to redeem!",
                            "productSelection": "manually",
                            "products": [
                                {
                                    "id": "reward-001",
                                    "productVariantId": "reward-001-variant",
                                    "quantity": "1",
                                    "label": "Reward Item 1 (500 points)",
                                    "uniqueId": 1
                                },
                                {
                                    "id": "reward-002",
                                    "productVariantId": "reward-002-variant",
                                    "quantity": "1",
                                    "label": "Reward Item 2 (1000 points)",
                                    "uniqueId": 2
                                }
                            ],
                            "productImages": True,
                            "discountType": "none",
                            "events": [
                                {
                                    "type": "reply",
                                    "intent": "buy",
                                    "description": "Customer wants to redeem reward",
                                    "nextStepID": "loyalty-redemption-003"
                                }
                            ]
                        },
                        # Step 3: Points Redemption
                        {
                            "id": "loyalty-redemption-003",
                            "type": "property",
                            "label": "Process Points Redemption",
                            "content": "Deduct points and record redemption",
                            "action": "points_redemption",
                            "eventName": "loyalty_points_used",
                            "enabled": True,
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "loyalty-thank-you-004"
                                }
                            ]
                        },
                        # Step 4: Thank You
                        {
                            "id": "loyalty-thank-you-004",
                            "type": "message",
                            "label": "Loyalty Thank You",
                            "content": "Send redemption confirmation",
                            "messageType": "standard",
                            "messageText": "Reward confirmed! Your points have been deducted. Keep earning more rewards! 🎉",
                            "addImage": False,
                            "sendContactCard": True,
                            "discountType": "none",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "loyalty-end-005"
                                }
                            ]
                        },
                        # Step 5: END
                        {
                            "id": "loyalty-end-005",
                            "type": "end",
                            "label": "Loyalty Campaign End",
                            "content": "End of Loyalty Points Campaign"
                        }
                    ]
                }
            },
            # Template 10: Abandoned Cart Recovery
            # Start -> Segment (Cart Abandoned) -> Urgency Message → Cart Recovery → Thank You → END
            {
                "description": "Abandoned cart recovery campaign",
                "template_category": "cart_recovery",
                "complexity": "medium",
                "flow": {
                    "name": "Abandoned Cart Recovery Campaign",
                    "description": "Recover abandoned carts with targeted reminder messages",
                    "initialStepID": "segment-abandoned-001",
                    "steps": [
                        # Step 1: Segment (Cart Abandoned)
                        {
                            "id": "segment-abandoned-001",
                            "type": "segment",
                            "label": "Abandoned Cart Segment",
                            "content": "Identify customers with abandoned carts",
                            "conditions": [
                                {
                                    "id": "cart-abandoned-001",
                                    "type": "property",
                                    "action": "cart_status",
                                    "operator": "equals",
                                    "filter": "abandoned",
                                    "timePeriod": "within the last 24 hours",
                                    "timePeriodType": "relative",
                                    "filterTab": "cart",
                                    "cartFilterTab": "status",
                                    "optInFilterTab": "keywords",
                                    "showFilterOptions": False,
                                    "showLinkFilterOptions": False,
                                    "showCartFilterOptions": False,
                                    "showOptInFilterOptions": False,
                                    "filterData": None
                                }
                            ],
                            "segmentDefinition": {},
                            "events": [
                                {
                                    "id": "cart-abandoned-include-001",
                                    "type": "split",
                                    "label": "Include Abandoned Carts",
                                    "action": "include",
                                    "nextStepID": "cart-reminder-002"
                                }
                            ]
                        },
                        # Step 2: Cart Reminder
                        {
                            "id": "cart-reminder-002",
                            "type": "message",
                            "label": "Cart Recovery Reminder",
                            "content": "Send abandoned cart reminder",
                            "messageType": "personalized",
                            "messageText": "Hi {{first_name}}! Did you forget something? Your cart is waiting: {{cart_items}}",
                            "addImage": False,
                            "sendContactCard": True,
                            "discountType": "percentage",
                            "discountValue": "15",
                            "discountCode": "CARTSAVE15",
                            "events": [
                                {
                                    "type": "reply",
                                    "intent": "complete",
                                    "description": "Customer wants to complete purchase",
                                    "nextStepID": "cart-urgency-003"
                                }
                            ]
                        },
                        # Step 3: Urgency Message
                        {
                            "id": "cart-urgency-003",
                            "type": "message",
                            "label": "Cart Recovery Urgency",
                            "content": "Send urgency message for abandoned cart",
                            "messageType": "standard",
                            "messageText": "⏰ Your cart expires soon! Complete your purchase now to save 15% with CARTSAVE15",
                            "addImage": False,
                            "sendContactCard": False,
                            "discountType": "percentage",
                            "discountValue": "15",
                            "discountCode": "CARTSAVE15",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "cart-recovery-004"
                                }
                            ]
                        },
                        # Step 4: Cart Recovery
                        {
                            "id": "cart-recovery-004",
                            "type": "purchase",
                            "label": "Process Cart Recovery Purchase",
                            "content": "Process recovered cart purchase with discount",
                            "cartSource": "latest",
                            "products": [],
                            "discountType": "percentage",
                            "discountValue": "15",
                            "discountCode": "CARTSAVE15",
                            "sendReminderForNonPurchasers": True,
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "cart-thank-you-005"
                                }
                            ]
                        },
                        # Step 5: Thank You
                        {
                            "id": "cart-thank-you-005",
                            "type": "message",
                            "label": "Cart Recovery Thank You",
                            "content": "Send purchase confirmation",
                            "messageType": "standard",
                            "messageText": "Thank you {{first_name}}! Your order is confirmed. Glad we could help you save 15%! 🛒",
                            "addImage": False,
                            "sendContactCard": False,
                            "discountType": "none",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "cart-recovery-end-006"
                                }
                            ]
                        },
                        # Step 6: END
                        {
                            "id": "cart-recovery-end-006",
                            "type": "end",
                            "label": "Cart Recovery Campaign End",
                            "content": "End of Abandoned Cart Recovery Campaign"
                        }
                    ]
                }
            },
            # Template 11: Product Launch Campaign
            # Start -> Teaser → Preview → Pre-order → Launch Confirmation → END
            {
                "description": "New product launch campaign with pre-orders",
                "template_category": "product_launch",
                "complexity": "complex",
                "flow": {
                    "name": "Product Launch Campaign",
                    "description": "Launch new product with teaser campaign and pre-orders",
                    "initialStepID": "launch-teaser-001",
                    "steps": [
                        # Step 1: Launch Teaser
                        {
                            "id": "launch-teaser-001",
                            "type": "message",
                            "label": "Product Launch Teaser",
                            "content": "Send teaser message about upcoming product launch",
                            "messageType": "standard",
                            "messageText": "🚀 Something amazing is coming soon! Be the first to know when we launch our new {{product_category}}!",
                            "addImage": True,
                            "imageUrl": "https://example.com/teaser-image.jpg",
                            "sendContactCard": False,
                            "discountType": "none",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "launch-preview-002"
                                }
                            ]
                        },
                        # Step 2: Product Preview
                        {
                            "id": "launch-preview-002",
                            "type": "message",
                            "label": "Product Preview",
                            "content": "Show preview of new product features",
                            "messageType": "standard",
                            "messageText": "Sneak peek! Our new {{product_name}} features {{key_features}}. Pre-order now with exclusive 20% off!",
                            "addImage": True,
                            "imageUrl": "https://example.com/product-preview.jpg",
                            "sendContactCard": True,
                            "discountType": "percentage",
                            "discountValue": "20",
                            "discountCode": "LAUNCH20",
                            "events": [
                                {
                                    "type": "reply",
                                    "intent": "preorder",
                                    "description": "Customer wants to pre-order",
                                    "nextStepID": "launch-preorder-003"
                                }
                            ]
                        },
                        # Step 3: Pre-order
                        {
                            "id": "launch-preorder-003",
                            "type": "purchase",
                            "label": "Process Pre-order",
                            "content": "Process pre-order with launch discount",
                            "cartSource": "manual",
                            "products": [
                                {
                                    "id": "new-product-001",
                                    "productVariantId": "new-product-001-variant",
                                    "quantity": "1",
                                    "label": "New Product Pre-order",
                                    "uniqueId": 1
                                }
                            ],
                            "discountType": "percentage",
                            "discountValue": "20",
                            "discountCode": "LAUNCH20",
                            "sendReminderForNonPurchasers": True,
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "launch-confirmation-004"
                                }
                            ]
                        },
                        # Step 4: Launch Confirmation
                        {
                            "id": "launch-confirmation-004",
                            "type": "message",
                            "label": "Pre-order Confirmation",
                            "content": "Send pre-order confirmation with ETA",
                            "messageType": "standard",
                            "messageText": "Thank you {{first_name}}! Your pre-order is confirmed. We'll notify you when your {{product_name}} ships!",
                            "addImage": False,
                            "sendContactCard": True,
                            "discountType": "none",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "launch-end-005"
                                }
                            ]
                        },
                        # Step 5: END
                        {
                            "id": "launch-end-005",
                            "type": "end",
                            "label": "Product Launch Campaign End",
                            "content": "End of Product Launch Campaign"
                        }
                    ]
                }
            },
            # Template 12: Seasonal/Holiday Campaign
            # Start -> Schedule → Seasonal Message → Holiday Offer → Countdown → END
            {
                "description": "Seasonal holiday campaign with scheduled messages",
                "template_category": "seasonal_campaign",
                "complexity": "complex",
                "flow": {
                    "name": "Seasonal Holiday Campaign",
                    "description": "Time-based seasonal campaign with holiday promotions",
                    "initialStepID": "seasonal-schedule-001",
                    "steps": [
                        # Step 1: Seasonal Schedule
                        {
                            "id": "seasonal-schedule-001",
                            "type": "schedule",
                            "label": "Holiday Season Schedule",
                            "content": "Schedule campaign for specific holiday period",
                            "enabled": True,
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "seasonal-message-002"
                                }
                            ]
                        },
                        # Step 2: Seasonal Message
                        {
                            "id": "seasonal-message-002",
                            "type": "message",
                            "label": "Seasonal Greeting",
                            "content": "Send seasonal greeting message",
                            "messageType": "standard",
                            "messageText": "🎄 Happy {{holiday_season}}! Get into the festive spirit with our special {{holiday}} offers!",
                            "addImage": True,
                            "imageUrl": "https://example.com/holiday-banner.jpg",
                            "sendContactCard": True,
                            "discountType": "percentage",
                            "discountValue": "30",
                            "discountCode": "HOLIDAY30",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "holiday-offers-003"
                                }
                            ]
                        },
                        # Step 3: Holiday Offers
                        {
                            "id": "holiday-offers-003",
                            "type": "product_choice",
                            "label": "Holiday Special Offers",
                            "content": "Show holiday-themed products and promotions",
                            "messageType": "standard",
                            "messageText": "Our {{holiday}} collection is here! 🎁 Browse our festive favorites:\n\n{{Product List}}\n\nSeasonal prices!",
                            "productSelection": "manually",
                            "products": [
                                {
                                    "id": "holiday-001",
                                    "productVariantId": "holiday-001-variant",
                                    "quantity": "1",
                                    "label": "Holiday Special 1",
                                    "uniqueId": 1
                                },
                                {
                                    "id": "holiday-002",
                                    "productVariantId": "holiday-002-variant",
                                    "quantity": "1",
                                    "label": "Holiday Special 2",
                                    "uniqueId": 2
                                }
                            ],
                            "productImages": True,
                            "discountType": "percentage",
                            "discountValue": "30",
                            "discountCode": "HOLIDAY30",
                            "events": [
                                {
                                    "type": "reply",
                                    "intent": "buy",
                                    "description": "Customer wants to buy holiday items",
                                    "nextStepID": "holiday-purchase-004"
                                }
                            ]
                        },
                        # Step 4: Holiday Purchase
                        {
                            "id": "holiday-purchase-004",
                            "type": "purchase",
                            "label": "Process Holiday Purchase",
                            "content": "Process holiday season purchase with special discount",
                            "cartSource": "latest",
                            "products": [],
                            "discountType": "percentage",
                            "discountValue": "30",
                            "discountCode": "HOLIDAY30",
                            "sendReminderForNonPurchasers": True,
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "holiday-thank-you-005"
                                }
                            ]
                        },
                        # Step 5: Holiday Thank You
                        {
                            "id": "holiday-thank-you-005",
                            "type": "message",
                            "label": "Holiday Thank You",
                            "content": "Send holiday purchase confirmation",
                            "messageType": "standard",
                            "messageText": "Thank you {{first_name}}! Happy {{holiday}}! Your order is confirmed with 30% savings! 🎄",
                            "addImage": False,
                            "sendContactCard": True,
                            "discountType": "none",
                            "events": [
                                {
                                    "type": "default",
                                    "nextStepID": "seasonal-end-006"
                                }
                            ]
                        },
                        # Step 6: END
                        {
                            "id": "seasonal-end-006",
                            "type": "end",
                            "label": "Seasonal Campaign End",
                            "content": "End of Seasonal Holiday Campaign"
                        }
                    ]
                }
            }
        ]
    def _build_schema_reference(self) -> str:
        """Build schema reference for validation."""
        return """
## Schema Reference

### Required JSON Structure:
```json
{
  "initialStepID": "first-node-id",
  "steps": [/* array of steps */],
  "metadata": {},
  "version": "1.0",
  "active": True
}
```

### SendMessage Step Example:
```json
{
  "id": "welcome-message",
  "type": "SendMessage",
  "config": {
    "recipient": {
      "phoneNumbers": ["+1234567890"],
      "contactId": "optional-contact-id"
    },
    "sender": {
      "name": "Your Brand",
      "phone": "+19999999999"
    },
    "content": {
      "text": "Hi {{first_name}}, welcome to our service!"
    }
  },
  "nextStepId": "next-step-id",
  "active": True
}
```

### Delay Step Example:
```json
{
  "id": "wait-period",
  "type": "Delay",
  "config": {
    "delayType": "relative",
    "duration": {
      "value": 1,
      "unit": "hours"
    }
  },
  "nextStepId": "next-step-id",
  "active": True
}
```

### Condition Step Example:
```json
{
  "id": "segment-check",
  "type": "Condition",
  "config": {
    "conditions": [
      {
        "id": "vip-check-001",
        "type": "property",
        "operator": "has",
        "propertyName": "customer_type",
        "propertyValue": "vip"
      }
    ],
    "operator": "AND"
  },
  "nextStepId": "vip-path",
  "active": True
}
```

### CRM Step Example:
```json
{
  "id": "add-to-crm",
  "type": "AddToCRM",
  "config": {
    "operation": "add",
    "crmSystem": "salesforce",
    "contactData": {
      "email": "customer@example.com",
      "name": "John Doe"
    }
  },
  "nextStepId": "next-step-id",
  "active": True
}
```
"""

    def _get_flowbuilder_node_types(self) -> str:
        """Get summary of available FlowBuilder node types."""
        type_descriptions = {
            "message": "Send SMS message",
            "delay": "Create delay",
            "segment": "Customer segmentation",
            "product_choice": "Product selection",
            "purchase": "Process order",
            "purchase_offer": "Send purchase offer",
            "reply_cart_choice": "Choose from cart",
            "no_reply": "Handle no response",
            "end": "End flow",
            "start": "Start flow",
            "property": "Update properties",
            "rate_limit": "Rate limiting",
            "limit": "Execution limit",
            "split": "Split branch",
            "reply": "Wait for reply",
            "experiment": "A/B Testing",
            "quiz": "Interactive quiz",
            "schedule": "Schedule",
            "split_group": "A/B testing branch",
            "split_range": "Time-based branch"
        }

        summary = []
        for node_type, description in type_descriptions.items():
            summary.append(f"- **{node_type}**: {description}")

        return "\n".join(summary)

    def _get_step_types_summary(self) -> str:
        """Get summary of available step types (deprecated - use _get_flowbuilder_node_types)."""
        return self._get_flowbuilder_node_types()

    def _get_variables_summary(self) -> str:
        """Get summary of available template variables."""
        variable_descriptions = {
            "{{brand_name}}": "Company/brand name",
            "{{first_name}}": "Customer's first name",
            "{{last_name}}": "Customer's last name",
            "{{store_url}}": "Website/store URL",
            "{{customer_timezone}}": "Customer's time zone",
            "{{agent_name}}": "Support agent name",
            "{{opt_in_terms}}": "Opt-in terms and conditions",
            "{{Product List}}": "List of products with prices",
            "{{Product List Without Prices}}": "List of products without prices",
            "{{Cart List}}": "Items in customer's cart",
            "{{Discount Label}}": "Discount offer text",
            "{{Purchase Link}}": "Direct purchase link",
            "{{Personalized Products}}": "AI-selected personalized products",
            "{{VIP Product List}}": "VIP-exclusive product recommendations"
        }

        summary = []
        for variable, description in variable_descriptions.items():
            summary.append(f"- {variable}: {description}")

        return "\n".join(summary)

    def _get_event_actions_summary(self) -> str:
        """Get summary of available event actions for segmentation."""
        action_descriptions = {
            "placed_order": "Customer completed a purchase",
            "clicked_link": "Customer clicked a link in message",
            "viewed_product": "Customer viewed a product page",
            "added_product_to_cart": "Customer added item to cart",
            "started_checkout": "Customer began checkout process"
        }

        summary = []
        for action, description in action_descriptions.items():
            summary.append(f"- **{action}**: {description}")

        return "\n".join(summary)

    def _get_product_selection_summary(self) -> str:
        """Get summary of product selection modes."""
        selection_descriptions = {
            "manually": "Specify exact products to offer",
            "automatically": "AI selects products based on customer behavior",
            "popularity": "Show most popular products",
            "recently_viewed": "Show products customer recently viewed"
        }

        summary = []
        for mode, description in selection_descriptions.items():
            summary.append(f"- **{mode}**: {description}")

        return "\n".join(summary)

    async def validate_prompt_length(self, system_prompt: str, user_prompt: str) -> Tuple[str, str]:
        """
        Validate and adjust prompt length to fit within token limits.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt

        Returns:
            Tuple of adjusted (system_prompt, user_prompt)
        """
        from .llm_client import get_llm_client

        llm_client = get_llm_client()

        # Estimate tokens
        system_tokens = await llm_client.estimate_tokens(system_prompt)
        user_tokens = await llm_client.estimate_tokens(user_prompt)
        total_tokens = system_tokens + user_tokens

        max_prompt_tokens = int(settings.OPENAI_MAX_TOKENS * 0.7)  # Reserve 30% for response

        if total_tokens <= max_prompt_tokens:
            return system_prompt, user_prompt

        # Need to truncate - prioritize system prompt, truncate user prompt
        excess_tokens = total_tokens - max_prompt_tokens
        max_user_tokens = user_tokens - excess_tokens

        if max_user_tokens < 1000:  # Minimum reasonable user prompt length
            logger.warning(
                "Prompt too long even after truncation",
                extra={
                    "total_tokens": total_tokens,
                    "max_tokens": max_prompt_tokens,
                    "excess_tokens": excess_tokens,
                }
            )
            # Return shortened versions
            system_prompt = await llm_client.truncate_prompt(system_prompt, max_prompt_tokens // 2)
            user_prompt = await llm_client.truncate_prompt(user_prompt, max_prompt_tokens // 2)
            return system_prompt, user_prompt

        # Truncate user prompt
        truncated_user_prompt = await llm_client.truncate_prompt(user_prompt, max_user_tokens)

        logger.info(
            "User prompt truncated to fit token limit",
            extra={
                "original_user_tokens": user_tokens,
                "truncated_user_tokens": await llm_client.estimate_tokens(truncated_user_prompt),
                "max_user_tokens": max_user_tokens,
            }
        )

        return system_prompt, truncated_user_prompt


# Global prompt builder instance
_prompt_builder: Optional[PromptBuilder] = None


def get_prompt_builder() -> PromptBuilder:
    """Get global prompt builder instance."""
    global _prompt_builder
    if _prompt_builder is None:
        _prompt_builder = PromptBuilder()
    return _prompt_builder