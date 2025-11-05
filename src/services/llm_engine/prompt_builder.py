"""
Prompt builder for LLM campaign generation.

This module provides sophisticated prompt templates that incorporate the complete FlowBuilder schema.
"""

import json
from typing import Any, Dict, List, Optional, Tuple

from src.core.config import get_settings
from src.core.logging import get_logger
from src.models.flow_schema import CampaignFlow
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

    def build_prompt(
        self,
        campaign_description: str,
        complexity_level: str = "medium",
        include_examples: bool = True,
        max_examples: int = 2,
    ) -> Tuple[str, str]:
        """
        Build complete prompt for campaign generation.

        Args:
            campaign_description: Natural language campaign description
            complexity_level: Expected complexity ("simple", "medium", "complex")
            include_examples: Whether to include few-shot examples
            max_examples: Maximum number of examples to include

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        # Select appropriate examples based on complexity
        examples = []
        if include_examples:
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
        return f"""You are an expert SMS marketing flow builder with deep expertise in creating automated customer journeys. You will receive a campaign description and must output a JSON representing the campaign flow that strictly follows the FlowBuilder format.

## Critical Rules (MUST FOLLOW):

1. **Output Format**: Output ONLY valid JSON. No explanations, no markdown, no text outside the JSON structure.

2. **Schema Structure**: Follow the FlowBuilder format exactly:
   - "initialStepID": string (required) - ID of the first node
   - "steps": array of node objects (required) - Each step must be one of the 7 FlowBuilder node types

3. **Node Types**: Use ONLY these 7 FlowBuilder node types:
   - "message" - Send SMS message
   - "segment" - Customer segmentation
   - "delay" - Create delay
   - "product_choice" - Product selection
   - "purchase_offer" - Send purchase offer
   - "purchase" - Process order
   - "end" - End flow

4. **Required Fields**: Each node MUST have:
   - "id": unique string identifier
   - "type": one of the 7 node types above
   - "label": string - Display label for the node
   - "content": string - Node description
   - "active": boolean (default True)
   - "parameters": {{}} (empty object if no custom parameters)

5. **Message Node Fields**: All "message" type nodes MUST include:
   - "messageText": string (required) - Main SMS content
   - "text": string - Backward compatibility - same as messageText
   - "addImage": boolean (default false) - Attach image
   - "imageUrl": string - Image URL when addImage = true
   - "sendContactCard": boolean (default false) - Send contact card
   - "discountType": string (default "none") - "none" | "percentage" | "amount" | "code"
   - "discountValue": string - Discount value when type != "none"
   - "discountCode": string - Discount code when type = "code"
   - "discountEmail": string - Email restriction (optional)
   - "discountExpiry": string - Expiry date (optional)

6. **Product Choice Node Fields**: All "product_choice" type nodes MUST include:
   - "messageType": string (required) - "standard" | "personalized"
   - "messageText": string (required) - Message text with product list
   - "text": string - Backward compatibility
   - "prompt": string - Alternative to messageText
   - "productSelection": string (required) - "manually" | "automatically" | "popularity" | "recently_viewed"
   - "productSelectionPrompt": string - When productSelection = "automatically"
   - "products": array - When productSelection = "manually"
     - "id": string (required) - Required product ID
     - "label": string - Optional product label
     - "showLabel": boolean - Whether to show label
     - "uniqueId": number - Internal tracking ID
   - "productImages": boolean (default true) - Send product images
   - "customTotals": boolean (default false) - Add custom totals
   - "customTotalsAmount": string - Custom shipping amount
   - "discountExpiry": boolean (default false) - Discount has expiry
   - "discountExpiryDate": string - Expiry date when enabled
   - "discount": string (default "None") - "None" | "10%" | "$5" | "SAVE20"

7. **Delay Node Fields**: All "delay" type nodes MUST include:
   - "time": string (required) - Time value
   - "period": string (required) - "Seconds" | "Minutes" | "Hours" | "Days"

8. **Purchase Offer Node Fields**: All "purchase_offer" type nodes MUST include:
   - "messageType": string (required) - "standard" | "personalized"
   - "messageText": string (required) - Message text with cart list
   - "text": string - Backward compatibility
   - "cartSource": string (required) - "manual" | "latest"
   - "products": array - When cartSource = "manual"
     - "productVariantId": string (required) - Required product variant ID
     - "quantity": string (required) - Required quantity as string
     - "uniqueId": number - Internal tracking ID
   - "discount": boolean (default false) - Enable/disable discount
   - "discountType": string - When discount = true: "percentage" | "amount" | "code"
   - "discountPercentage": string - When discountType = "percentage"
   - "discountAmount": string - When discountType = "amount"
   - "discountCode": string - When discountType = "code"
   - "discountAmountLabel": string - Optional label for code discount
   - "discountEmail": string - Optional email restriction
   - "discountExpiry": boolean (default false) - Discount has expiry
   - "discountExpiryDate": string - Expiry date when enabled
   - "customTotals": boolean (default false) - Add custom totals
   - "shippingAmount": string - Custom shipping amount when customTotals = true
   - "includeProductImage": boolean (default true) - Send product images
   - "skipForRecentOrders": boolean (default true) - Skip for recent orders

9. **Purchase Node Fields**: All "purchase" type nodes MUST include:
    - "cartSource": string (required) - "manual" | "latest"
    - "products": array - Product list when cartSource = "manual"
    - "discount": boolean (default false) - Add discount to order
    - "customTotals": boolean (default false) - Add custom totals
    - "shippingAmount": string - Custom shipping amount when customTotals = true
    - "sendReminderForNonPurchasers": boolean (default false) - Send reminder
    - "allowAutomaticPayment": boolean (default false) - Auto payment

10. **End Node Fields**: All "end" type nodes MUST include:
    - "label": string - Display label
    - "content": string - Node description
    - No events array - end node terminates flow

11. **Events Structure**: Most nodes need "events" array with:
   - "type": string (required) - "reply" | "noreply" | "split" | "default"
   - "nextStepID": string (required) - Reference to another node's ID
   - "intent": string - When type = "reply": intent name
   - "description": string - Optional description for better intent matching
   - "after": object - When type = "noreply": {{"value": number, "unit": string}}
   - "label": string - When type = "split": display label
   - "action": string - When type = "split": split action
   - "active": boolean (default true)
   - "parameters": {{}} (default empty object)

12. **Template Variables Available**:
   - "{{brand_name}}" - Brand name
   - "{{store_url}}" - Store URL
   - "{{first_name}}" - Customer first name
   - "{{customer_timezone}}" - Customer timezone
   - "{{agent_name}}" - Agent name
   - "{{opt_in_terms}}" - Opt-in terms
   - "{{Product List}}" - Product list with prices (product_choice)
   - "{{Product List Without Prices}}" - Product list without prices (product_choice)
   - "{{Discount Label}}" - Discount label (product_choice)
   - "{{Cart List}}" - Cart products list (purchase_offer)
   - "{{Purchase Link}}" - Purchase link (purchase_offer)
   - "{{Personalized Products}}" - Personalized products (product_choice automatic)
   - "{{VIP Product List}}" - VIP product list

13. **ID Generation**: Generate unique, human-readable IDs for every node (e.g., "welcome-message", "vip-check", "cart-reminder").

14. **Reference Integrity**:
   - `initialStepID` must point to the ID of the first node in the steps array
   - Every `nextStepID` must reference an existing node ID within the same workflow
   - Ensure no orphaned nodes - all nodes must be reachable from the initial step

15. **Flow Completeness**: Every branch must eventually lead to an END node. No dead ends.

16. **Marketing Best Practices**:
   - Use personalization variables like {{first_name}}, {{brand_name}}
   - Keep messages concise and engaging
   - Include appropriate delays (typically 1-24 hours)
   - Add value propositions and clear CTAs

14. **Critical Node Type Selection Rules**:
   - **Standalone REPLY nodes**: Use ONLY when you need to handle customer responses WITHOUT sending a message first. Examples: After a delay, after a split, or as a standalone response handler.
   - **Reply events in MESSAGE nodes**: Use when you want to send a message AND immediately handle responses to that specific message.
   - **Standalone NO_REPLY nodes**: Use ONLY when you need to handle timeouts WITHOUT sending a message first. Examples: After a REPLY node, after a PROPERTY node.
   - **No-reply events in MESSAGE nodes**: Use when you send a message AND want to handle timeouts for that specific message.
   - **Key Principle**: If you need to send content to the customer, use a MESSAGE node with events. If you only need to handle responses/timeouts without sending content, use standalone REPLY/NO_REPLY nodes.

## Available Node Types:

{self._get_flowbuilder_node_types()}

## Available Variables for Personalization:

{self._get_variables_summary()}

## Node Structure Examples:

### MESSAGE Node:
```json
{{
  "id": "welcome-message",
  "type": "message",
  "content": "Hi {{first_name}}! Welcome to {{brand_name}}! 🎉",
  "text": "Hi {{first_name}}! Welcome to {{brand_name}}! 🎉",
  "addImage": False,
  "sendContactCard": False,
  "discountType": "none",
  "handled": False,
  "aiGenerated": False,
  "active": True,
  "parameters": {{}},
  "events": [
    {{
      "id": "welcome-reply",
      "type": "reply",
      "intent": "yes",
      "description": "Customer wants to continue",
      "nextStepID": "next-step-id",
      "active": True,
      "parameters": {{}}
    }}
  ]
}}
```

### SEGMENT Node:
```json
{{
  "id": "vip-segment",
  "type": "segment",
  "label": "VIP Customer Check",
  "conditions": [
    {{
      "id": 1,
      "type": "property",
      "operator": "has",
      "propertyName": "customer_type",
      "propertyValue": "vip",
      "timePeriod": "within the last 30 Days"
    }}
  ],
  "active": True,
  "parameters": {{}},
  "events": [
    {{
      "id": "vip-yes",
      "type": "split",
      "label": "include",
      "action": "include",
      "nextStepID": "vip-flow",
      "active": True,
      "parameters": {{}}
    }},
    {{
      "id": "vip-no",
      "type": "split",
      "label": "exclude",
      "action": "exclude",
      "nextStepID": "regular-flow",
      "active": True,
      "parameters": {{}}
    }}
  ]
}}
```

### DELAY Node:
```json
{{
  "id": "wait-period",
  "type": "delay",
  "time": "2",
  "period": "Hours",
  "delay": {{
    "value": "2",
    "unit": "Hours"
  }},
  "active": True,
  "parameters": {{}},
  "events": [
    {{
      "id": "delay-complete",
      "type": "default",
      "nextStepID": "next-step-id",
      "active": True,
      "parameters": {{}}
    }}
  ]
}}
```

### PRODUCT_CHOICE Node:
```json
{{
  "id": "product-selection",
  "type": "product_choice",
  "messageType": "standard",
  "messageText": "Reply to buy:\\n\\n{{Product List}}",
  "text": "Reply to buy:\\n\\n{{Product List}}",
  "productSelection": "popularity",
  "productImages": True,
  "discount": "None",
  "active": True,
  "parameters": {{}},
  "events": [
    {{
      "id": "buy-reply",
      "type": "reply",
      "intent": "buy",
      "nextStepID": "purchase-process",
      "active": True,
      "parameters": {{}}
    }},
    {{
      "id": "no-reply",
      "type": "noreply",
      "after": {{
        "value": 2,
        "unit": "hours"
      }},
      "nextStepID": "followup-message",
      "active": True,
      "parameters": {{}}
    }}
  ]
}}
```

### EXPERIMENT Node:
```json
{{
  "id": "welcome-test",
  "type": "experiment",
  "label": "Welcome Message Test",
  "experimentName": "Welcome Message Test",
  "version": "1",
  "content": "Display content: Welcome Message Test(v1)",
  "active": True,
  "parameters": {{}},
  "events": [
    {{
      "id": "event-group-a",
      "type": "split",
      "label": "Group A",
      "nextStepID": "welcome-group-a",
      "active": True,
      "parameters": {{}}
    }},
    {{
      "id": "event-group-b",
      "type": "split",
      "label": "Group B",
      "nextStepID": "welcome-group-b",
      "active": True,
      "parameters": {{}}
    }}
  ]
}}
```

### RATE_LIMIT Node:
```json
{{
  "id": "message-throttle",
  "type": "rate_limit",
  "occurrences": "12",
  "timespan": "11",
  "period": "Minutes",
  "rateLimit": {{
    "limit": "12",
    "period": "Minutes"
  }},
  "content": "Display content: 12 times every 11 minutes",
  "active": True,
  "parameters": {{}},
  "events": [
    {{
      "id": "rate-limit-pass",
      "type": "default",
      "nextStepID": "next-step-id",
      "active": True,
      "parameters": {{}}
    }}
  ]
}}
```

### END Node:
```json
{{
  "id": "end-flow",
  "type": "end",
  "label": "End",
  "active": True,
  "parameters": {{}},
  "events": []
}}
```

## Quality Standards:

1. **Logical Flow**: Create realistic customer journeys with appropriate timing
2. **Message Quality**: Engaging, personalized content with clear CTAs
3. **Branch Logic**: Meaningful segmentation with clear conditions
4. **Event Handling**: Proper reply, noreply, and split events
5. **Flow Completion**: Ensure all paths lead to END nodes

Remember: Your output must be perfect, valid JSON that follows the FlowBuilder format exactly with the 16 defined node types."""

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

    def _select_examples(self, complexity_level: str, max_examples: int) -> List[Dict[str, Any]]:
        """Select appropriate few-shot examples based on complexity."""
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
        """Build few-shot examples for different campaign types using FlowBuilder format."""
        return [
            {
                "description": "welcome message for new customers (simple)",
                "complexity": "simple",
                "flow": {
                    "initialStepID": "welcome-message",
                    "steps": [
                        {
                            "id": "welcome-message",
                            "type": "message",
                            "content": "Hi {{first_name}}! Welcome to {{brand_name}}! We're excited to have you join us! 🎉",
                            "text": "Hi {{first_name}}! Welcome to {{brand_name}}! We're excited to have you join us! 🎉",
                            "addImage": False,
                            "sendContactCard": False,
                            "discountType": "none",
                            "handled": False,
                            "aiGenerated": False,
                            "active": True,
                            "parameters": {},
                            "events": [
                                {
                                    "id": "welcome-reply",
                                    "type": "reply",
                                    "intent": "yes",
                                    "description": "Customer wants to continue",
                                    "nextStepID": "end-node",
                                    "active": True,
                                    "parameters": {}
                                },
                                {
                                    "id": "welcome-noreply",
                                    "type": "noreply",
                                    "after": {
                                        "value": 2,
                                        "unit": "hours"
                                    },
                                    "nextStepID": "follow-up-message",
                                    "active": True,
                                    "parameters": {}
                                }
                            ]
                        },
                        {
                            "id": "follow-up-message",
                            "type": "message",
                            "content": "How are you enjoying our service so far? We're here to help if you have any questions!",
                            "text": "How are you enjoying our service so far? We're here to help if you have any questions!",
                            "addImage": False,
                            "sendContactCard": False,
                            "discountType": "none",
                            "handled": False,
                            "aiGenerated": False,
                            "active": True,
                            "parameters": {},
                            "events": [
                                {
                                    "id": "followup-end",
                                    "type": "default",
                                    "nextStepID": "end-node",
                                    "active": True,
                                    "parameters": {}
                                }
                            ]
                        },
                        {
                            "id": "end-node",
                            "type": "end",
                            "label": "End",
                            "active": True,
                            "parameters": {},
                            "events": []
                        }
                    ]
                }
            },
            {
                "description": "VIP customer special offer with segmentation (medium)",
                "complexity": "medium",
                "flow": {
                    "initialStepID": "vip-check",
                    "steps": [
                        {
                            "id": "vip-check",
                            "type": "segment",
                            "label": "VIP Customer Check",
                            "conditions": [
                                {
                                    "id": 1,
                                    "type": "property",
                                    "operator": "has",
                                    "propertyName": "customer_type",
                                    "propertyValue": "vip",
                                    "timePeriod": "within the last 30 Days"
                                }
                            ],
                            "active": True,
                            "parameters": {},
                            "events": [
                                {
                                    "id": "vip-yes",
                                    "type": "split",
                                    "label": "include",
                                    "action": "include",
                                    "nextStepID": "vip-offer",
                                    "active": True,
                                    "parameters": {}
                                },
                                {
                                    "id": "vip-no",
                                    "type": "split",
                                    "label": "exclude",
                                    "action": "exclude",
                                    "nextStepID": "regular-offer",
                                    "active": True,
                                    "parameters": {}
                                }
                            ]
                        },
                        {
                            "id": "vip-offer",
                            "type": "message",
                            "content": "Hi {{first_name}}! As one of our VIPs, enjoy 20% off your next order. Use code VIP20 at checkout. Limited time offer! 👑",
                            "text": "Hi {{first_name}}! As one of our VIPs, enjoy 20% off your next order. Use code VIP20 at checkout. Limited time offer! 👑",
                            "discountType": "percentage",
                            "discountValue": "20",
                            "discountCode": "VIP20",
                            "addImage": False,
                            "sendContactCard": False,
                            "handled": False,
                            "aiGenerated": False,
                            "active": True,
                            "parameters": {},
                            "events": [
                                {
                                    "id": "vip-reply",
                                    "type": "reply",
                                    "intent": "yes",
                                    "description": "Customer wants VIP offer",
                                    "nextStepID": "end-node",
                                    "active": True,
                                    "parameters": {}
                                }
                            ]
                        },
                        {
                            "id": "regular-offer",
                            "type": "message",
                            "content": "Hi {{first_name}}! Check out our latest products at {{store_url}}. Special offers available!",
                            "text": "Hi {{first_name}}! Check out our latest products at {{store_url}}. Special offers available!",
                            "addImage": False,
                            "sendContactCard": False,
                            "discountType": "none",
                            "handled": False,
                            "aiGenerated": False,
                            "active": True,
                            "parameters": {},
                            "events": [
                                {
                                    "id": "regular-end",
                                    "type": "default",
                                    "nextStepID": "end-node",
                                    "active": True,
                                    "parameters": {}
                                }
                            ]
                        },
                        {
                            "id": "end-node",
                            "type": "end",
                            "label": "End",
                            "active": True,
                            "parameters": {},
                            "events": []
                        }
                    ]
                }
            },
            {
                "description": "interactive menu with standalone REPLY nodes (medium)",
                "complexity": "medium",
                "flow": {
                    "initialStepID": "menu-question",
                    "steps": [
                        {
                            "id": "menu-question",
                            "type": "message",
                            "content": "Hi {{first_name}}! Would you like to receive our special offers? Reply YES or NO",
                            "text": "Hi {{first_name}}! Would you like to receive our special offers? Reply YES or NO",
                            "addImage": False,
                            "sendContactCard": False,
                            "discountType": "none",
                            "handled": False,
                            "aiGenerated": False,
                            "active": True,
                            "parameters": {},
                            "events": [
                                {
                                    "id": "menu-yes",
                                    "type": "default",
                                    "nextStepID": "reply-yes-handler",
                                    "active": True,
                                    "parameters": {}
                                },
                                {
                                    "id": "menu-no",
                                    "type": "default",
                                    "nextStepID": "reply-no-handler",
                                    "active": True,
                                    "parameters": {}
                                }
                            ]
                        },
                        {
                            "id": "reply-yes-handler",
                            "type": "reply",
                            "enabled": True,
                            "intent": "yes",
                            "description": "Customer wants to receive special offers",
                            "label": "Yes",
                            "replyConfig": {},
                            "active": True,
                            "parameters": {},
                            "events": [
                                {
                                    "id": "yes-confirmed",
                                    "type": "default",
                                    "nextStepID": "special-offers",
                                    "active": True,
                                    "parameters": {}
                                }
                            ]
                        },
                        {
                            "id": "reply-no-handler",
                            "type": "reply",
                            "enabled": True,
                            "intent": "no",
                            "description": "Customer does not want special offers",
                            "label": "No",
                            "replyConfig": {},
                            "active": True,
                            "parameters": {},
                            "events": [
                                {
                                    "id": "no-confirmed",
                                    "type": "default",
                                    "nextStepID": "end-node",
                                    "active": True,
                                    "parameters": {}
                                }
                            ]
                        },
                        {
                            "id": "special-offers",
                            "type": "message",
                            "content": "Great! Here are our special offers just for you: {{Discount Label}}",
                            "text": "Great! Here are our special offers just for you: {{Discount Label}}",
                            "addImage": False,
                            "sendContactCard": False,
                            "discountType": "percentage",
                            "discountValue": "20",
                            "discountCode": "SPECIAL20",
                            "handled": False,
                            "aiGenerated": False,
                            "active": True,
                            "parameters": {},
                            "events": [
                                {
                                    "id": "offers-end",
                                    "type": "default",
                                    "nextStepID": "end-node",
                                    "active": True,
                                    "parameters": {}
                                }
                            ]
                        },
                        {
                            "id": "end-node",
                            "type": "end",
                            "label": "End",
                            "active": True,
                            "parameters": {},
                            "events": []
                        }
                    ]
                }
            },
            {
                "description": "timeout response with standalone NO_REPLY node (medium)",
                "complexity": "medium",
                "flow": {
                    "initialStepID": "initial-question",
                    "steps": [
                        {
                            "id": "initial-question",
                            "type": "message",
                            "content": "Hi {{first_name}}! How are you enjoying our service? Please reply with your feedback.",
                            "text": "Hi {{first_name}}! How are you enjoying our service? Please reply with your feedback.",
                            "addImage": False,
                            "sendContactCard": False,
                            "discountType": "none",
                            "handled": False,
                            "aiGenerated": False,
                            "active": True,
                            "parameters": {},
                            "events": [
                                {
                                    "id": "question-timeout",
                                    "type": "default",
                                    "nextStepID": "no-reply-handler",
                                    "active": True,
                                    "parameters": {}
                                }
                            ]
                        },
                        {
                            "id": "no-reply-handler",
                            "type": "no_reply",
                            "enabled": True,
                            "value": 2,
                            "unit": "hours",
                            "label": "No Reply",
                            "content": "Display content: 2 hours",
                            "after": {
                                "value": 2,
                                "unit": "hours"
                            },
                            "seconds": 7200,
                            "period": "Hours",
                            "noReplyConfig": {},
                            "active": True,
                            "parameters": {},
                            "events": [
                                {
                                    "id": "timeout-followup",
                                    "type": "default",
                                    "nextStepID": "followup-message",
                                    "active": True,
                                    "parameters": {}
                                }
                            ]
                        },
                        {
                            "id": "followup-message",
                            "type": "message",
                            "content": "We noticed you haven't responded. Is there anything we can help you with? Reply HELP for assistance.",
                            "text": "We noticed you haven't responded. Is there anything we can help you with? Reply HELP for assistance.",
                            "addImage": False,
                            "sendContactCard": False,
                            "discountType": "none",
                            "handled": False,
                            "aiGenerated": False,
                            "active": True,
                            "parameters": {},
                            "events": [
                                {
                                    "id": "followup-end",
                                    "type": "default",
                                    "nextStepID": "end-node",
                                    "active": True,
                                    "parameters": {}
                                }
                            ]
                        },
                        {
                            "id": "end-node",
                            "type": "end",
                            "label": "End",
                            "active": True,
                            "parameters": {},
                            "events": []
                        }
                    ]
                }
            },
            {
                "description": "customer segmentation with standalone SPLIT nodes (medium)",
                "complexity": "medium",
                "flow": {
                    "initialStepID": "customer-split",
                    "steps": [
                        {
                            "id": "customer-split",
                            "type": "split",
                            "enabled": True,
                            "label": "include",
                            "action": "include",
                            "description": "Include customers in Group A for testing",
                            "content": "Display content: include",
                            "splitConfig": {},
                            "active": True,
                            "parameters": {},
                            "events": [
                                {
                                    "id": "split-group-a",
                                    "type": "default",
                                    "nextStepID": "group-a-message",
                                    "active": True,
                                    "parameters": {}
                                }
                            ]
                        },
                        {
                            "id": "group-a-message",
                            "type": "message",
                            "content": "Welcome to Group A! You'll receive our premium offers.",
                            "text": "Welcome to Group A! You'll receive our premium offers.",
                            "addImage": False,
                            "sendContactCard": False,
                            "discountType": "percentage",
                            "discountValue": "25",
                            "discountCode": "GROUPA25",
                            "handled": False,
                            "aiGenerated": False,
                            "active": True,
                            "parameters": {},
                            "events": [
                                {
                                    "id": "group-a-end",
                                    "type": "default",
                                    "nextStepID": "end-node",
                                    "active": True,
                                    "parameters": {}
                                }
                            ]
                        },
                        {
                            "id": "end-node",
                            "type": "end",
                            "label": "End",
                            "active": True,
                            "parameters": {},
                            "events": []
                        }
                    ]
                }
            },
            {
                "description": "customer preference tracking with PROPERTY node (medium)",
                "complexity": "medium",
                "flow": {
                    "initialStepID": "preference-setter",
                    "steps": [
                        {
                            "id": "preference-setter",
                            "type": "message",
                            "content": "Hi {{first_name}}! What's your preferred product category? Reply ELECTRONICS, FASHION, or HOME.",
                            "text": "Hi {{first_name}}! What's your preferred product category? Reply ELECTRONICS, FASHION, or HOME.",
                            "addImage": False,
                            "sendContactCard": False,
                            "discountType": "none",
                            "handled": False,
                            "aiGenerated": False,
                            "active": True,
                            "parameters": {},
                            "events": [
                                {
                                    "id": "preference-captured",
                                    "type": "default",
                                    "nextStepID": "property-updater",
                                    "active": True,
                                    "parameters": {}
                                }
                            ]
                        },
                        {
                            "id": "property-updater",
                            "type": "property",
                            "label": "Customer Property Step",
                            "content": "Display content: Customer Property Step",
                            "properties": [
                                {
                                    "id": 1,
                                    "name": "preferred_category",
                                    "value": "electronics"
                                },
                                {
                                    "id": 2,
                                    "name": "last_interaction",
                                    "value": "category_selection"
                                }
                            ],
                            "propertyConfig": {},
                            "active": True,
                            "parameters": {},
                            "events": [
                                {
                                    "id": "property-confirmation",
                                    "type": "default",
                                    "nextStepID": "category-confirmation",
                                    "active": True,
                                    "parameters": {}
                                }
                            ]
                        },
                        {
                            "id": "category-confirmation",
                            "type": "message",
                            "content": "Thanks! We've noted your preference for {{preferred_category}}. We'll send you relevant updates!",
                            "text": "Thanks! We've noted your preference for {{preferred_category}}. We'll send you relevant updates!",
                            "addImage": False,
                            "sendContactCard": False,
                            "discountType": "none",
                            "handled": False,
                            "aiGenerated": False,
                            "active": True,
                            "parameters": {},
                            "events": [
                                {
                                    "id": "confirmation-end",
                                    "type": "default",
                                    "nextStepID": "end-node",
                                    "active": True,
                                    "parameters": {}
                                }
                            ]
                        },
                        {
                            "id": "end-node",
                            "type": "end",
                            "label": "End",
                            "active": True,
                            "parameters": {},
                            "events": []
                        }
                    ]
                }
            },
            {
                "description": "usage limitation with LIMIT node (medium)",
                "complexity": "medium",
                "flow": {
                    "initialStepID": "limit-check",
                    "steps": [
                        {
                            "id": "limit-check",
                            "type": "limit",
                            "occurrences": "5",
                            "timespan": "1",
                            "period": "Hours",
                            "limit": {
                                "value": "5",
                                "period": "Hours"
                            },
                            "content": "Display content: 5 times every 1 hour",
                            "active": True,
                            "parameters": {},
                            "events": [
                                {
                                    "id": "limit-passed",
                                    "type": "default",
                                    "nextStepID": "limited-message",
                                    "active": True,
                                    "parameters": {}
                                }
                            ]
                        },
                        {
                            "id": "limited-message",
                            "type": "message",
                            "content": "Hi {{first_name}}! Here's your exclusive offer (limited to 5 per hour).",
                            "text": "Hi {{first_name}}! Here's your exclusive offer (limited to 5 per hour).",
                            "addImage": False,
                            "sendContactCard": False,
                            "discountType": "percentage",
                            "discountValue": "15",
                            "discountCode": "LIMITED15",
                            "handled": False,
                            "aiGenerated": False,
                            "active": True,
                            "parameters": {},
                            "events": [
                                {
                                    "id": "limited-end",
                                    "type": "default",
                                    "nextStepID": "end-node",
                                    "active": True,
                                    "parameters": {}
                                }
                            ]
                        },
                        {
                            "id": "end-node",
                            "type": "end",
                            "label": "End",
                            "active": True,
                            "parameters": {},
                            "events": []
                        }
                    ]
                }
            },
            {
                "description": "professional e-commerce VIP campaign with purchase processing (complex)",
                "complexity": "complex",
                "flow": {
                    "initialStepID": "welcome-message",
                    "steps": [
                        {
                            "id": "welcome-message",
                            "type": "message",
                            "content": "Hi {{first_name}}! Welcome to our store. Would you like to see our new products?",
                            "text": "Hi {{first_name}}! Welcome to our store. Would you like to see our new products?",
                            "addImage": False,
                            "sendContactCard": True,
                            "discountType": "percentage",
                            "discountValue": "10",
                            "discountExpiry": "2024-12-31T23:59:59",
                            "handled": False,
                            "aiGenerated": False,
                            "active": True,
                            "parameters": {},
                            "events": [
                                {
                                    "id": "welcome-reply",
                                    "type": "reply",
                                    "intent": "yes",
                                    "description": "Customer wants to see new products",
                                    "nextStepID": "segment-check",
                                    "active": True,
                                    "parameters": {}
                                },
                                {
                                    "id": "welcome-noreply",
                                    "type": "noreply",
                                    "after": {
                                        "value": 24,
                                        "unit": "hours"
                                    },
                                    "nextStepID": "followup-delay",
                                    "active": True,
                                    "parameters": {}
                                }
                            ]
                        },
                        {
                            "id": "segment-check",
                            "type": "segment",
                            "label": "VIP Customer Check",
                            "conditions": [
                                {
                                    "id": 1,
                                    "type": "event",
                                    "operator": "has",
                                    "action": "placed_order",
                                    "filter": "all orders",
                                    "timePeriod": "within the last 30 Days",
                                    "timePeriodType": "relative"
                                }
                            ],
                            "active": True,
                            "parameters": {},
                            "events": [
                                {
                                    "id": "vip-yes",
                                    "type": "split",
                                    "label": "include",
                                    "action": "include",
                                    "nextStepID": "vip-offer",
                                    "active": True,
                                    "parameters": {}
                                },
                                {
                                    "id": "vip-no",
                                    "type": "split",
                                    "label": "exclude",
                                    "action": "exclude",
                                    "nextStepID": "regular-products",
                                    "active": True,
                                    "parameters": {}
                                }
                            ]
                        },
                        {
                            "id": "vip-offer",
                            "type": "purchase_offer",
                            "label": "VIP Special Offer",
                            "messageType": "personalized",
                            "messageText": "Hi {{first_name}}! As a VIP customer, here's an exclusive offer just for you:\\n\\n{{Cart List}}\\n\\nReply YES to claim your special discount!",
                            "cartSource": "manual",
                            "products": [
                                {
                                    "productVariantId": "vip-123",
                                    "quantity": "1",
                                    "uniqueId": 1
                                }
                            ],
                            "discount": True,
                            "discountType": "percentage",
                            "discountPercentage": "20",
                            "discountExpiry": True,
                            "discountExpiryDate": "2024-12-31T23:59:59",
                            "includeProductImage": True,
                            "skipForRecentOrders": True,
                            "active": True,
                            "parameters": {},
                            "events": [
                                {
                                    "id": "vip-buy",
                                    "type": "reply",
                                    "intent": "yes",
                                    "nextStepID": "purchase-process",
                                    "active": True,
                                    "parameters": {}
                                },
                                {
                                    "id": "vip-noreply",
                                    "type": "noreply",
                                    "after": {
                                        "value": 2,
                                        "unit": "hours"
                                    },
                                    "nextStepID": "followup-message",
                                    "active": True,
                                    "parameters": {}
                                }
                            ]
                        },
                        {
                            "id": "regular-products",
                            "type": "product_choice",
                            "messageType": "standard",
                            "messageText": "Reply to buy:\\n\\n{{Product List}}",
                            "productSelection": "popularity",
                            "productImages": True,
                            "active": True,
                            "parameters": {},
                            "events": [
                                {
                                    "id": "regular-buy",
                                    "type": "reply",
                                    "intent": "buy",
                                    "nextStepID": "purchase-process",
                                    "active": True,
                                    "parameters": {}
                                }
                            ]
                        },
                        {
                            "id": "purchase-process",
                            "type": "purchase",
                            "cartSource": "latest",
                            "discount": False,
                            "customTotals": False,
                            "sendReminderForNonPurchasers": True,
                            "allowAutomaticPayment": False,
                            "active": True,
                            "parameters": {},
                            "events": [
                                {
                                    "id": "purchase-complete",
                                    "type": "default",
                                    "nextStepID": "end-node",
                                    "active": True,
                                    "parameters": {}
                                }
                            ]
                        },
                        {
                            "id": "followup-delay",
                            "type": "delay",
                            "time": "5",
                            "period": "Minutes",
                            "delay": {
                                "value": "5",
                                "unit": "Minutes"
                            },
                            "active": True,
                            "parameters": {},
                            "events": [
                                {
                                    "id": "followup-event",
                                    "type": "default",
                                    "nextStepID": "followup-message",
                                    "active": True,
                                    "parameters": {}
                                }
                            ]
                        },
                        {
                            "id": "followup-message",
                            "type": "message",
                            "content": "Just leaving this with you. You might be busy. Reach out when you're ready!",
                            "text": "Just leaving this with you. You might be busy. Reach out when you're ready!",
                            "handled": False,
                            "aiGenerated": False,
                            "active": True,
                            "parameters": {},
                            "events": [
                                {
                                    "id": "followup-end",
                                    "type": "default",
                                    "nextStepID": "end-node",
                                    "active": True,
                                    "parameters": {}
                                }
                            ]
                        },
                        {
                            "id": "end-node",
                            "type": "end",
                            "label": "End",
                            "active": True,
                            "parameters": {},
                            "events": []
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
        "id": 1,
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
            "segment": "Customer segmentation",
            "delay": "Create delay",
            "product_choice": "Product selection",
            "purchase_offer": "Send purchase offer",
            "purchase": "Process order",
            "end": "End flow"
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
            "{{store_url}}": "Website/store URL",
            "{{customer_timezone}}": "Customer's time zone",
            "{{agent_name}}": "Support agent name",
            "{{opt_in_terms}}": "Opt-in terms and conditions",
            "{{Product List}}": "List of products with prices",
            "{{Cart List}}": "Items in customer's cart",
            "{{Discount Label}}": "Discount offer text",
            "{{Purchase Link}}": "Direct purchase link"
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