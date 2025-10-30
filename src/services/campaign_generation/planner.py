"""
Campaign Planner Service - Uses GPT-4o to plan campaign structures.
"""
import json
import re
import time
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI
import logging

from ...models.campaign_generation import CampaignIntent, GenerationRequest
from ..campaign_prompts import (
    CAMPAIGN_PLANNER_SYSTEM_PROMPT,
    INTENT_EXTRACTOR_SYSTEM_PROMPT,
    get_campaign_planning_prompt,
    get_intent_extraction_prompt,
    get_campaign_type_guidelines,
)

logger = logging.getLogger(__name__)


class CampaignPlanner:
    """
    AI-powered campaign planning service using GPT-4o.

    Responsibilities:
    - Extract intent from natural language descriptions
    - Find similar templates for inspiration
    - Generate optimal campaign structure
    - Plan step sequences and event handlers
    """

    def __init__(
        self,
        openai_client: AsyncOpenAI,
        template_manager: Optional[Any] = None,
        use_groq: bool = False,
        planning_model: str = "gpt-4o",
        intent_model: str = "gpt-4o-mini"
    ):
        """
        Initialize Campaign Planner.

        Args:
            openai_client: Async OpenAI client
            template_manager: Optional template manager for finding similar campaigns
            use_groq: Whether using GROQ instead of OpenAI
        """
        self.client = openai_client
        self.templates = template_manager
        self.use_groq = use_groq

        # Use provided models or fall back to defaults
        if use_groq:
            # Use GROQ models (override with passed models for flexibility)
            self.planning_model = planning_model if planning_model != "gpt-4o" else "llama-3.3-70b-versatile"
            self.intent_model = intent_model if intent_model != "gpt-4o-mini" else "llama-3.3-70b-versatile"
        else:
            # Use OpenAI/OpenRouter models
            self.planning_model = planning_model
            self.intent_model = intent_model

    async def plan_campaign_structure(
        self,
        request: GenerationRequest,
        merchant_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate campaign structure from natural language description.

        This is the main entry point for campaign planning.

        Args:
            request: Generation request with description and constraints
            merchant_context: Merchant information (name, industry, brand_voice, etc.)

        Returns:
            Campaign plan dict with structure, steps outline, and metadata

        Raises:
            Exception: If planning fails
        """
        start_time = time.time()

        logger.info(f"Planning campaign for merchant {request.merchant_id}")
        logger.info(f"Description: {request.description[:100]}...")

        try:
            # Step 1: Extract intent from description
            intent = await self._extract_intent(request.description)
            logger.info(f"Extracted intent type: {type(intent.campaign_type)}, value: {intent.campaign_type}")

            # Step 2: Find similar templates (if template manager available)
            similar_templates = []
            if self.templates and request.use_template:
                try:
                    # Handle both enum (OpenAI) and string (GROQ) types for campaign_type
                    logger.info(f"DEBUG: Before hasattr check, campaign_type type: {type(intent.campaign_type)}")
                    campaign_type_str = intent.campaign_type.value if hasattr(intent.campaign_type, 'value') else intent.campaign_type
                    logger.info(f"DEBUG: After conversion, campaign_type_str: {campaign_type_str}")
                    similar_templates = await self.templates.search_similar(
                        query=request.description,
                        campaign_type=campaign_type_str,
                        top_k=3
                    )
                    logger.info(f"Found {len(similar_templates)} similar templates")
                except Exception as e:
                    logger.error(f"Template search failed: {e}, continuing without templates", exc_info=True)

            # Step 3: Build planning prompt
            try:
                logger.info("DEBUG: About to call intent.dict()")
                intent_dict = intent.dict()
                logger.info(f"DEBUG: intent.dict() successful: {type(intent_dict)}")
            except Exception as e:
                logger.error(f"DEBUG: intent.dict() failed: {e}", exc_info=True)
                raise

            planning_prompt = get_campaign_planning_prompt(
                description=request.description,
                intent=intent_dict,
                similar_templates=similar_templates,
                merchant_context=merchant_context,
                constraints=request.constraints
            )

            # Add campaign type specific guidelines
            # Handle both enum (OpenAI) and string (GROQ) types
            logger.info(f"DEBUG: Getting campaign type guidelines, type: {type(intent.campaign_type)}")
            campaign_type_value = intent.campaign_type.value if hasattr(intent.campaign_type, 'value') else intent.campaign_type
            logger.info(f"DEBUG: campaign_type_value: {campaign_type_value}")
            type_guidelines = get_campaign_type_guidelines(campaign_type_value)
            planning_prompt += f"\n\n{type_guidelines}"

            # Step 4: Call GPT-4o for campaign planning
            logger.info("Calling GPT-4o for campaign planning...")
            response = await self.client.chat.completions.create(
                model=self.planning_model,
                messages=[
                    {"role": "system", "content": CAMPAIGN_PLANNER_SYSTEM_PROMPT},
                    {"role": "user", "content": planning_prompt}
                ],
                temperature=0.7,
                max_tokens=2500,
                response_format={"type": "json_object"}  # Ensure JSON response
            )

            # Step 5: Parse the plan
            plan_text = response.choices[0].message.content
            campaign_plan = json.loads(plan_text)

            # Step 6: Validate basic structure
            self._validate_plan_structure(campaign_plan)

            # Calculate cost
            input_tokens = response.usage.prompt_tokens
            output_tokens = response.usage.completion_tokens
            # GPT-4o pricing: $2.50 per 1M input, $10 per 1M output
            cost_usd = (input_tokens / 1_000_000 * 2.5) + (output_tokens / 1_000_000 * 10)

            duration = time.time() - start_time

            # Add metadata to plan
            campaign_plan["_metadata"] = {
                "intent": intent.dict(),
                "model": self.planning_model,
                "tokens_used": input_tokens + output_tokens,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost_usd": round(cost_usd, 6),
                "duration_seconds": round(duration, 2),
                "template_used": similar_templates[0]["template_id"] if similar_templates else None,
                "template_similarity": similar_templates[0]["similarity_score"] if similar_templates else None
            }

            logger.info(f"Campaign planned successfully in {duration:.2f}s")
            logger.info(f"Plan cost: ${cost_usd:.4f}, tokens: {input_tokens + output_tokens}")

            return campaign_plan

        except Exception as e:
            logger.error(f"Campaign planning failed: {e}", exc_info=True)
            # Return a basic fallback plan
            return {
                "name": "Fallback Campaign",
                "description": "Basic campaign structure due to planning error",
                "steps": [
                    {
                        "id": "step_001",
                        "type": "message",
                        "label": "Initial Message",
                        "content": request.description[:200] + "...",
                        "nextStepID": "step_end"
                    },
                    {
                        "id": "step_end",
                        "type": "end",
                        "label": "End Campaign"
                    }
                ],
                "initialStepID": "step_001",
                "_metadata": {
                    "fallback": True,
                    "error": str(e)
                }
            }

    def create_audience_segments(self, audience_criteria: Dict[str, Any]) -> List[Dict]:
        """Convert audience criteria to SEGMENT nodes."""
        segments = []

        if not audience_criteria or not audience_criteria.get('behavioral_criteria'):
            return segments

        behavioral_criteria = audience_criteria['behavioral_criteria']
        logical_operator = audience_criteria.get('logical_operator', 'AND')
        description = audience_criteria.get('description', 'Target customers')

        # Create segment node
        segment = {
            "id": "segment_001",
            "type": "segment",
            "label": description[:100],  # Truncate if too long
            "conditions": [],
            "segmentDefinition": {
                "operator": logical_operator,
                "segments": []
            }
        }

        # Convert behavioral criteria to FlowBuilder conditions
        for i, condition in enumerate(behavioral_criteria, 1):
            # Map action to FlowBuilder format
            action_mapping = {
                'engaged': 'clicked_link',
                'placed_order': 'placed_order',
                'added_product_to_cart': 'added_product_to_cart',
                'started_checkout': 'started_checkout'
            }

            flow_action = action_mapping.get(condition.get('action', ''), 'clicked_link')

            # Create condition for new format
            segment_condition = {
                "id": i,
                "type": "event",
                "operator": condition.get('operator', 'has'),
                "action": flow_action,
                "filter": self._get_filter_for_action(flow_action),
                "timePeriod": f"within the last {condition.get('timeframe', '30 days')}",
                "timePeriodType": "relative",
                "showTimePeriodOptions": False,
                "filterTab": "allEvents"
            }
            segment["conditions"].append(segment_condition)

            # Add to legacy format
            legacy_segment = {
                "type": "inclusion" if condition.get('include', True) else "exclusion",
                "customerAction": {
                    "action": flow_action,
                    "timeframe": condition.get('timeframe', '30d')
                }
            }
            segment["segmentDefinition"]["segments"].append(legacy_segment)

        segments.append(segment)
        return segments

    def create_schedule_node(self, scheduling_info: Dict[str, Any]) -> Optional[Dict]:
        """Create SCHEDULE node from extracted scheduling information."""
        if not scheduling_info or not scheduling_info.get('datetime'):
            return None

        schedule_node = {
            "id": "schedule_001",
            "type": "schedule",
            "datetime": scheduling_info.get('datetime'),
            "timezone": scheduling_info.get('timezone', 'UTC'),
            "label": scheduling_info.get('date_expression', 'Campaign Start'),
            "active": True,
            "parameters": {},
            "events": [
                {
                    "id": "evt_scheduled",
                    "type": "default",
                    "nextStepID": "step_001",  # Connect to first message step
                    "active": True,
                    "parameters": {}
                }
            ]
        }

        return schedule_node

    def _get_filter_for_action(self, action: str) -> str:
        """Map actions to FlowBuilder filters."""
        filter_map = {
            "clicked_link": "all clicks",
            "placed_order": "all orders",
            "added_product_to_cart": "all cart updates",
            "started_checkout": "all checkout updates",
            "viewed_product": "all product views"
        }
        return filter_map.get(action, "all events")

    def create_product_choice_node(self, product_details: Dict[str, Any]) -> Optional[Dict]:
        """Create PRODUCT_CHOICE node for product-specific campaigns."""
        if not product_details or not product_details.get('products'):
            return None

        products = product_details['products']

        # Create product list for PRODUCT_CHOICE node
        product_list = []
        for i, product in enumerate(products, 1):
            product_dict = {
                "id": f"product_{i:03d}",
                "name": product.get('name', f"Product {i}"),
                "url": product.get('url', ''),
                "price": product.get('price', ''),
                "image": product.get('image_url', ''),
                "description": product.get('description', f"High-quality product {i}")
            }
            product_list.append(product_dict)

        # Create product choice node
        product_choice_node = {
            "id": "product_choice_001",
            "type": "product_choice",
            "label": "Select Product",
            "content": "Which product would you like to learn more about?",
            "messageType": "standard",
            "messageText": "Reply with the product number or name to get details",
            "productSelection": "manually",
            "productSelectionPrompt": "Choose from our selection:",
            "products": product_list,
            "productImages": True,
            "customTotals": False,
            "discountExpiry": False,
            "discount": "None",
            "productChoiceConfig": {},
            "events": [
                {
                    "id": "evt_product_select",
                    "type": "reply",
                    "nextStepID": "product_details_001",
                    "active": True,
                    "parameters": {}
                }
            ]
        }

        return product_choice_node

    def create_property_node(self, condition, context: Dict[str, Any]) -> Optional[Dict]:
        """Create PROPERTY node for conditional logic based on customer attributes."""
        # Parse simple conditions like "if customer is VIP" or "if purchase_count > 5"
        conditions = self._parse_property_conditions(condition, context)

        if not conditions:
            return None

        # Handle label and content for both dict and string conditions
        if isinstance(condition, dict):
            field = condition.get('field', '')
            operator = condition.get('operator', 'equals')
            value = condition.get('value', '')
            condition_str = f"{field} {operator} {value}"
            label = condition.get('label', f"Property: {field}")
            content = condition.get('description', f"Checking if {field} {operator} {value}")
        else:
            condition_str = condition
            label = f"Customer Property Check: {condition}"
            content = f"Checking customer properties: {condition}"

        property_node = {
            "id": "property_001",
            "type": "property",
            "label": label,
            "content": content,
            "properties": conditions,
            "propertyConfig": {},
            "events": [
                {
                    "id": "evt_property_met",
                    "type": "default",
                    "nextStepID": "property_true_001",
                    "active": True,
                    "parameters": {}
                }
            ]
        }

        return property_node

    def _parse_property_conditions(self, condition, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse condition string or dictionary into property definitions."""
        conditions = []

        # Handle dictionary condition from LLM extraction
        if isinstance(condition, dict):
            field = condition.get('field', '')
            operator = condition.get('operator', 'equals')
            value = condition.get('value', '')

            if field and value:
                conditions.append({
                    "name": field,
                    "value": value,
                    "operator": operator
                })
            return conditions

        # Handle string condition (original logic)
        if not isinstance(condition, str):
            return conditions

        # Common customer property patterns
        property_patterns = [
            (r'customer is (VIP|premium|vip|premium)', 'customer_type'),
            (r'customer (has|purchased) (\d+) or more (times|items?)', 'purchase_count'),
            (r'customer has been (active|loyal|engaged)', 'customer_status'),
            (r'customer (prefers|likes) ([^\s]+)', 'preference'),
        ]

        for pattern, property_name in property_patterns:
            if re.search(pattern, condition.lower()):
                if property_name == 'customer_type':
                    value = re.search(r'(VIP|premium|vip|premium)', condition.lower())
                    if value:
                        conditions.append({
                            "name": "customer_type",
                            "value": value.group().upper(),
                            "operator": "equals"
                        })
                elif property_name == 'purchase_count':
                    count_match = re.search(r'(\d+)', condition)
                    if count_match:
                        conditions.append({
                            "name": "purchase_count",
                            "value": int(count_match.group(1)),
                            "operator": "greater_than_or_equal"
                        })
                elif property_name == 'customer_status':
                    if 'active' in condition.lower():
                        conditions.append({
                            "name": "customer_status",
                            "value": "active",
                            "operator": "equals"
                        })
                    elif 'loyal' in condition.lower():
                        conditions.append({
                            "name": "customer_status",
                            "value": "loyal",
                            "operator": "equals"
                        })
                elif property_name == 'preference':
                    preference_match = re.search(r'(prefers|likes)\s+([^\s]+)', condition.lower())
                    if preference_match:
                        conditions.append({
                            "name": "preference",
                            "value": preference_match.group(2).strip(),
                            "operator": "contains"
                        })

        # Add extracted details as properties if available
        if 'extracted_details' in context:
            details = context['extracted_details']
            if details.get('target_audience'):
                conditions.append({
                    "name": "audience_segment",
                    "value": details['target_audience'],
                    "operator": "equals"
                })

        return conditions

    def create_experiment_node(self, variants: List[Dict[str, Any]], context: Dict[str, Any]) -> Optional[Dict]:
        """
        Create EXPERIMENT node for A/B testing functionality.

        Args:
            variants: List of test variants with content and settings
            context: Campaign context for metadata

        Returns:
            EXPERIMENT node configuration or None if no variants
        """
        if not variants or len(variants) < 2:
            return None

        # Create experiment variants
        experiment_variants = []
        for i, variant in enumerate(variants[:2]):  # Support up to 2 variants for simplicity
            percentage = 50 if len(variants) == 2 else 100 // len(variants)

            experiment_variants.append({
                "id": f"variant_{chr(65 + i)}",  # A, B, C...
                "name": variant.get('name', f'Variant {chr(65 + i)}'),
                "percentage": percentage,
                "nextStepID": variant.get('next_step_id', f"message_variant_{chr(65 + i).lower()}")
            })

        # Create experiment node
        experiment_node = {
            "id": "experiment_001",
            "type": "experiment",
            "label": context.get('experiment_name', 'A/B Test: Message Variant'),
            "description": context.get('experiment_description', 'Testing different message approaches'),
            "variants": experiment_variants,
            "events": [
                {
                    "id": "evt_experiment_complete",
                    "type": "default",
                    "active": True,
                    "parameters": {}
                }
            ],
            "experimentConfig": {
                "type": "ab_test",
                "traffic_split": "equal",
                "success_metrics": context.get('success_metrics', ['conversion_rate', 'click_rate']),
                "duration_days": context.get('duration_days', 7)
            }
        }

        logger.info(f"Created EXPERIMENT node with {len(experiment_variants)} variants")
        return experiment_node

    def create_rate_limit_node(self, limits: Dict[str, Any], context: Dict[str, Any]) -> Optional[Dict]:
        """
        Create RATE_LIMIT node for compliance features.

        Args:
            limits: Rate limiting configuration
            context: Campaign context

        Returns:
            RATE_LIMIT node configuration or None if no limits
        """
        if not limits:
            # Apply default limits for compliance
            limits = {
                'daily': 10,
                'hourly': 1,
                'cooldown': 60
            }

        rate_limit_node = {
            "id": "rate_limit_001",
            "type": "rate_limit",
            "label": "Message Rate Limiting",
            "description": "Ensure compliance with messaging regulations",
            "max_per_day": limits.get('daily', 10),
            "max_per_hour": limits.get('hourly', 1),
            "cooldown_minutes": limits.get('cooldown', 60),
            "events": [
                {
                    "id": "evt_rate_limit_passed",
                    "type": "default",
                    "nextStepID": "rate_limit_passed_001",
                    "active": True,
                    "parameters": {}
                }
            ],
            "rateLimitConfig": {
                "timezone": context.get('timezone', 'UTC'),
                "business_hours_only": limits.get('business_hours_only', False),
                "weekend_exclusion": limits.get('weekend_exclusion', False),
                "compliance_mode": True
            }
        }

        logger.info(f"Created RATE_LIMIT node: {rate_limit_node['max_per_day']}/day, {rate_limit_node['max_per_hour']}/hour")
        return rate_limit_node

    def create_split_node(self, split_criteria: Dict[str, Any], context: Dict[str, Any]) -> Optional[Dict]:
        """
        Create SPLIT node for audience division.

        Args:
            split_criteria: Configuration for audience splitting
            context: Campaign context

        Returns:
            SPLIT node configuration or None if no split criteria
        """
        if not split_criteria:
            return None

        # Default to 50/50 split if not specified
        split_a_percent = split_criteria.get('split_a_percent', 50)
        split_b_percent = 100 - split_a_percent

        split_node = {
            "id": "split_001",
            "type": "split",
            "label": split_criteria.get('description', 'Audience Split'),
            "description": split_criteria.get('detailed_description', 'Split audience for targeted messaging'),
            "splits": [
                {
                    "id": "split_a",
                    "name": split_criteria.get('split_a_name', 'Group A'),
                    "percentage": split_a_percent,
                    "nextStepID": split_criteria.get('split_a_next', 'path_a'),
                    "criteria": split_criteria.get('split_a_criteria', 'Random selection')
                },
                {
                    "id": "split_b",
                    "name": split_criteria.get('split_b_name', 'Group B'),
                    "percentage": split_b_percent,
                    "nextStepID": split_criteria.get('split_b_next', 'path_b'),
                    "criteria": split_criteria.get('split_b_criteria', 'Random selection')
                }
            ],
            "events": [
                {
                    "id": "evt_split_complete",
                    "type": "default",
                    "active": True,
                    "parameters": {}
                }
            ],
            "splitConfig": {
                "split_type": split_criteria.get('split_type', 'random'),
                "random_seed": split_criteria.get('random_seed', None),
                "balance_check": True
            }
        }

        logger.info(f"Created SPLIT node: {split_a_percent}%/{split_b_percent}% split")
        return split_node

    def create_delay_node(self, delay_config: Dict[str, Any], context: Dict[str, Any]) -> Optional[Dict]:
        """
        Create DELAY node for timing control.

        Args:
            delay_config: Delay timing configuration
            context: Campaign context

        Returns:
            DELAY node configuration or None if no delay
        """
        if not delay_config:
            return None

        # Parse delay time
        delay_minutes = delay_config.get('minutes', 0)
        delay_hours = delay_config.get('hours', 0)
        delay_days = delay_config.get('days', 0)

        total_minutes = delay_minutes + (delay_hours * 60) + (delay_days * 24 * 60)

        if total_minutes <= 0:
            return None

        delay_node = {
            "id": "delay_001",
            "type": "delay",
            "label": delay_config.get('label', 'Wait Period'),
            "description": delay_config.get('description', f'Delay of {total_minutes} minutes'),
            "minutes": total_minutes,
            "events": [
                {
                    "id": "evt_delay_complete",
                    "type": "default",
                    "nextStepID": delay_config.get('next_step_id', 'after_delay'),
                    "active": True,
                    "parameters": {}
                }
            ],
            "delayConfig": {
                "business_hours_only": delay_config.get('business_hours_only', False),
                "timezone": context.get('timezone', 'UTC'),
                "max_wait_days": delay_config.get('max_wait_days', 7)
            }
        }

        logger.info(f"Created DELAY node: {total_minutes} minutes")
        return delay_node

    
    async def _extract_intent(self, description: str) -> CampaignIntent:
        """
        Extract structured intent from natural language description.

        Args:
            description: Natural language campaign description

        Returns:
            CampaignIntent with extracted information

        Raises:
            Exception: If intent extraction fails
        """
        try:
            logger.info("Extracting campaign intent...")

            prompt = get_intent_extraction_prompt(description)

            if self.use_groq:
                # GROQ doesn't support structured outputs, use JSON mode
                response = await self.client.chat.completions.create(
                    model=self.intent_model,
                    messages=[
                        {"role": "system", "content": INTENT_EXTRACTOR_SYSTEM_PROMPT + "\nReturn ONLY valid JSON matching the CampaignIntent schema."},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.3
                )
                intent_data = json.loads(response.choices[0].message.content)
                intent = CampaignIntent(**intent_data)
            else:
                # Use OpenAI's structured output with Pydantic model
                response = await self.client.beta.chat.completions.parse(
                    model=self.intent_model,
                    messages=[
                        {"role": "system", "content": INTENT_EXTRACTOR_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {
                            "name": "CampaignIntent",
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "campaign_type": {"type": "string"},
                                    "target_audience": {
                                        "type": "object",
                                        "additionalProperties": False
                                    }
                                },
                                "required": ["campaign_type"],
                                "additionalProperties": False
                            }
                        }
                    },
                    temperature=0.3  # Lower temperature for more consistent extraction
                )
                intent = response.choices[0].message.parsed

            if not intent:
                raise Exception("No intent extracted from description")

            logger.info(f"Intent extracted: {intent.campaign_type} (confidence: {intent.confidence:.2f})")

            return intent

        except Exception as e:
            logger.error(f"Intent extraction failed: {e}")
            # Return default intent
            logger.info("DEBUG: Creating fallback CampaignIntent")
            try:
                fallback_intent = CampaignIntent(
                    campaign_type="promotional",
                    goals=["engage", "convert"],
                    target_audience={"description": "all customers"},
                    key_products=[],
                    confidence=0.5
                )
                logger.info(f"DEBUG: Fallback intent created, campaign_type type: {type(fallback_intent.campaign_type)}")
                return fallback_intent
            except Exception as fallback_error:
                logger.error(f"DEBUG: Fallback intent creation failed: {fallback_error}", exc_info=True)
                raise

    def _validate_plan_structure(self, plan: Dict[str, Any]) -> None:
        """
        Validate that the campaign plan has required structure.

        Args:
            plan: Campaign plan dict

        Raises:
            ValueError: If plan structure is invalid
        """
        if "steps" not in plan:
            raise ValueError("Campaign plan missing 'steps' array")

        if "initialStepID" not in plan:
            # Try to infer from first step
            if plan["steps"]:
                plan["initialStepID"] = plan["steps"][0].get("id", "step_001")
            else:
                raise ValueError("Campaign plan missing 'initialStepID' and has no steps")

        if not plan["steps"]:
            raise ValueError("Campaign plan has no steps")

        # Validate each step has required fields
        for i, step in enumerate(plan["steps"]):
            if "id" not in step:
                raise ValueError(f"Step {i} missing 'id' field")
            if "type" not in step:
                raise ValueError(f"Step {i} ({step.get('id', 'unknown')}) missing 'type' field")

        logger.info(f"Plan structure validated: {len(plan['steps'])} steps")

    async def refine_plan(
        self,
        plan: Dict[str, Any],
        feedback: str,
        merchant_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Refine an existing campaign plan based on feedback.

        Args:
            plan: Current campaign plan
            feedback: User feedback or requirements
            merchant_context: Merchant information

        Returns:
            Refined campaign plan
        """
        try:
            logger.info("Refining campaign plan...")

            prompt = f"""Refine this campaign plan based on the following feedback:

**Current Plan:**
```json
{json.dumps(plan, indent=2)}
```

**Feedback:**
{feedback}

**Merchant Context:**
- Name: {merchant_context.get('name', 'Store')}
- Brand Voice: {merchant_context.get('brand_voice', 'professional')}

Update the plan to address the feedback while maintaining the overall structure and best practices.
Return the complete refined plan as JSON."""

            response = await self.client.chat.completions.create(
                model=self.planning_model,
                messages=[
                    {"role": "system", "content": CAMPAIGN_PLANNER_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2500,
                response_format={"type": "json_object"}
            )

            refined_plan = json.loads(response.choices[0].message.content)
            self._validate_plan_structure(refined_plan)

            logger.info("Plan refined successfully")
            return refined_plan

        except Exception as e:
            logger.error(f"Plan refinement failed: {e}")
            raise


# Factory function
def create_campaign_planner(
    openai_api_key: str,
    template_manager: Optional[Any] = None
) -> CampaignPlanner:
    """
    Factory function to create CampaignPlanner instance.

    Args:
        openai_api_key: OpenAI API key
        template_manager: Optional template manager

    Returns:
        Configured CampaignPlanner instance
    """
    client = AsyncOpenAI(api_key=openai_api_key)
    return CampaignPlanner(client, template_manager)