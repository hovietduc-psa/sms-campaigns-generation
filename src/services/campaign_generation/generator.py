"""
Content Generator Service - Uses GPT-4o-mini to generate campaign content.
"""
import json
import time
from typing import Dict, Any, List, Optional
from openai import AsyncOpenAI
import logging

from ...models.campaign import (
    Campaign,
    MessageStep,
    SegmentStep,
    DelayStep,
    ConditionStep,
    EndStep,
    PurchaseOfferStep,
    ProductChoiceStep,
    RateLimitStep,
    LimitStep,
    PurchaseStep,
    ScheduleStep,
    ExperimentStep,
    SplitStep,
    CampaignEvent,
    EventType,
    StepType,
)
from ..campaign_prompts import (
    CONTENT_GENERATOR_SYSTEM_PROMPT,
    get_message_generation_prompt,
    get_segment_generation_prompt,
    get_purchase_offer_prompt,
    get_ai_prompt_generation,
)

logger = logging.getLogger(__name__)


class ContentGenerator:
    """
    Generate content for campaign steps using GPT-4o-mini.

    Responsibilities:
    - Generate message text for each message step
    - Create AI prompts for handled/AI-generated steps
    - Generate segment conditions
    - Create purchase offer content
    - Transform campaign plan into complete Campaign object
    """

    def __init__(self, openai_client: AsyncOpenAI, use_groq: bool = False, content_model: str = "gpt-4o-mini"):
        """
        Initialize Content Generator.

        Args:
            openai_client: Async OpenAI client
            use_groq: Whether using GROQ instead of OpenAI
            content_model: Model to use for content generation
        """
        self.client = openai_client
        self.use_groq = use_groq

        # Use provided model or fall back to defaults
        if use_groq:
            # Use GROQ models (override with passed model for flexibility)
            self.content_model = content_model if content_model != "gpt-4o-mini" else "llama-3.3-70b-versatile"
        else:
            # Use OpenAI/OpenRouter models
            self.content_model = content_model

        self.total_cost = 0.0
        self.total_tokens = 0
        self.request_context = None

    async def generate_campaign_content(
        self,
        campaign_plan: Dict[str, Any],
        merchant_context: Dict[str, Any]
    ) -> Campaign:
        """
        Fill in content for all steps in the campaign plan.

        This takes the intermediate plan from CampaignPlanner and generates
        the final Campaign object with all content.

        Args:
            campaign_plan: Campaign structure from planner
            merchant_context: Merchant information

        Returns:
            Complete Campaign object ready for validation

        Raises:
            Exception: If content generation fails
        """
        start_time = time.time()
        self.total_cost = 0.0
        self.total_tokens = 0

        logger.info("Generating content for campaign...")
        logger.info(f"Plan has {len(campaign_plan.get('steps', []))} steps")

        try:
            steps_with_content = []
            previous_messages = []

            # Extract campaign context
            campaign_context = {
                "type": campaign_plan.get("campaign_type", "promotional"),
                "name": campaign_plan.get("campaign_name", "Campaign"),
                "goal": campaign_plan.get("_metadata", {}).get("intent", {}).get("goals", ["engage"])[0] if campaign_plan.get("_metadata") else "engage",
                "audience": campaign_plan.get("_metadata", {}).get("intent", {}).get("target_audience", {}).get("description", "customers") if campaign_plan.get("_metadata") else "customers",
                "tone": merchant_context.get("brand_voice", "friendly and professional")
            }

            # Process each step in the plan
            for i, step_plan in enumerate(campaign_plan["steps"]):
                step_type = step_plan.get("type")
                step_id = step_plan.get("id")

                logger.info(f"Generating content for step {i+1}/{len(campaign_plan['steps'])}: {step_id} ({step_type})")

                # Add position context
                step_plan["position_in_flow"] = "initial" if i == 0 else ("closing" if i == len(campaign_plan["steps"]) - 1 else "middle")

                # Generate step based on type
                if step_type == "message":
                    step = await self._generate_message_step(
                        step_plan,
                        campaign_context,
                        merchant_context,
                        previous_messages
                    )
                    if step.text:
                        previous_messages.append(step.text)

                elif step_type == "segment":
                    step = await self._generate_segment_step(step_plan, campaign_context)

                elif step_type == "delay":
                    step = self._create_delay_step(step_plan)

                elif step_type == "condition":
                    step = self._create_condition_step(step_plan)

                elif step_type == "purchase_offer":
                    step = await self._generate_purchase_offer_step(
                        step_plan,
                        campaign_context,
                        merchant_context
                    )

                elif step_type == "purchase":
                    step = self._create_purchase_step(step_plan)

                elif step_type == "product_choice":
                    step = self._create_product_choice_step(step_plan)

                elif step_type == "experiment":
                    step = self._create_experiment_step(step_plan)

                elif step_type == "schedule":
                    step = self._create_schedule_step(step_plan)

                elif step_type == "rate_limit":
                    step = self._create_rate_limit_step(step_plan)

                elif step_type == "limit":
                    step = self._create_limit_step(step_plan)

                elif step_type == "split":
                    step = self._create_split_step(step_plan)

                elif step_type == "end":
                    step = self._create_end_step(step_plan)

                else:
                    # Default: create base step for unsupported types
                    logger.warning(f"Unsupported step type: {step_type}, creating base step")
                    step = self._create_base_step(step_plan)

                steps_with_content.append(step)

            # Build final campaign object
            campaign = Campaign(
                initialStepID=campaign_plan["initialStepID"],
                steps=steps_with_content
            )

            duration = time.time() - start_time

            logger.info(f"Content generation completed in {duration:.2f}s")
            logger.info(f"Total cost: ${self.total_cost:.4f}, tokens: {self.total_tokens}")

            return campaign

        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            raise

    async def _generate_message_step(
        self,
        step_plan: Dict[str, Any],
        campaign_context: Dict[str, Any],
        merchant_context: Dict[str, Any],
        previous_messages: List[str]
    ) -> MessageStep:
        """
        Generate message text for a message step.

        Args:
            step_plan: Step plan from planner
            campaign_context: Campaign context
            merchant_context: Merchant information
            previous_messages: Previous messages for context

        Returns:
            MessageStep with generated content
        """
        # Check if this should be AI-generated (handled) or static
        should_be_handled = step_plan.get("handled", False) or step_plan.get("aiGenerated", False)

        if should_be_handled:
            # Generate AI prompt for runtime generation
            prompt = get_ai_prompt_generation(step_plan, campaign_context)
            message_text = None
        else:
            # Generate static message text
            prompt_text = get_message_generation_prompt(
                step_plan,
                campaign_context,
                merchant_context,
                previous_messages
            )

            response = await self.client.chat.completions.create(
                model=self.content_model,
                messages=[
                    {"role": "system", "content": CONTENT_GENERATOR_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt_text}
                ],
                temperature=0.7,
                max_tokens=200  # SMS messages are short
            )

            message_text = response.choices[0].message.content.strip()

            # Track cost
            self._track_usage(response.usage)

            # Ensure message is not too long
            if len(message_text) > 320:  # 2 SMS limit
                logger.warning(f"Generated message too long ({len(message_text)} chars), truncating")
                message_text = message_text[:317] + "..."

            prompt = None

        # Parse events
        events = self._parse_events(step_plan.get("events", []))

        return MessageStep(
            id=step_plan["id"],
            type=StepType.MESSAGE,
            text=message_text,
            prompt=prompt,
            handled=should_be_handled,
            aiGenerated=True,
            parameters=step_plan.get("parameters", {}),
            active=step_plan.get("active", True),
            events=events
        )

    async def _generate_segment_step(
        self,
        step_plan: Dict[str, Any],
        campaign_context: Dict[str, Any]
    ) -> SegmentStep:
        """
        Generate segment conditions with FlowBuilder compliance.

        Args:
            step_plan: Step plan from planner
            campaign_context: Campaign context

        Returns:
            SegmentStep with proper conditions array
        """
        # Extract structured audience requirements if available
        structured_audience = campaign_context.get('merchant_context', {}).get('structured_requirements', {}).get('target_audience', {})

        # Check if segment definition already provided
        segment_def = None
        conditions_array = []

        if "segmentDefinition" in step_plan and step_plan["segmentDefinition"]:
            segment_def = step_plan["segmentDefinition"]
        else:
            # Generate segment definition using LLM with enhanced context
            prompt_text = get_segment_generation_prompt(step_plan, campaign_context)

            response = await self.client.chat.completions.create(
                model=self.content_model,
                messages=[
                    {"role": "system", "content": CONTENT_GENERATOR_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt_text}
                ],
                temperature=0.5,
                max_tokens=300,
                response_format={"type": "json_object"}
            )

            segment_def = json.loads(response.choices[0].message.content)
            self._track_usage(response.usage)

        # Convert segmentDefinition to FlowBuilder conditions array
        if segment_def:
            conditions_array = self._convert_segment_definition_to_conditions(segment_def, structured_audience)

        # Generate default conditions if empty
        if not conditions_array:
            conditions_array = self._generate_default_conditions(structured_audience)

        events = self._parse_events(step_plan.get("events", []))

        # Ensure events have proper split structure
        events = self._enhance_segment_events(events)

        return SegmentStep(
            id=step_plan["id"],
            type=StepType.SEGMENT,
            conditions=conditions_array,
            segmentDefinition=segment_def,  # Keep for backward compatibility
            label=step_plan.get("label", "Customer Segmentation"),
            parameters=step_plan.get("parameters", {}),
            active=step_plan.get("active", True),
            events=events
        )

    def _convert_segment_definition_to_conditions(self, segment_def: Dict[str, Any], structured_audience: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert legacy segmentDefinition to FlowBuilder conditions array.

        Args:
            segment_def: Legacy segment definition
            structured_audience: Structured audience requirements

        Returns:
            List of FlowBuilder condition objects
        """
        conditions = []

        # Extract conditions from legacy segmentDefinition
        if "conditions" in segment_def:
            legacy_conditions = segment_def["conditions"]
            for i, cond in enumerate(legacy_conditions):
                flowbuilder_condition = {
                    "id": i + 1,
                    "type": "event",
                    "operator": "has",
                    "action": "placed_order",
                    "filter": "all orders"
                }

                # Map legacy fields to FlowBuilder format
                if "field" in cond:
                    field = cond["field"]
                    if "last_purchase" in field:
                        flowbuilder_condition["action"] = "placed_order"
                        flowbuilder_condition["filter"] = "all orders"

                        # Set time period
                        if "operator" in cond and cond["operator"] == "less_than":
                            if "value" in cond:
                                days = cond["value"]
                                flowbuilder_condition["timePeriod"] = f"within the last {days} Days"
                                flowbuilder_condition["timePeriodType"] = "relative"
                                flowbuilder_condition["customTimeValue"] = str(days)
                                flowbuilder_condition["customTimeUnit"] = "Days"
                    elif "email_subscribed" in field:
                        flowbuilder_condition["type"] = "property"
                        flowbuilder_condition["propertyName"] = "email_subscribed"
                        flowbuilder_condition["propertyOperator"] = "with a value of"
                        flowbuilder_condition["propertyValue"] = cond.get("value", True)
                        flowbuilder_condition["showPropertyValueInput"] = False
                        flowbuilder_condition["showPropertyOperatorOptions"] = False

                conditions.append(flowbuilder_condition)

        # Add conditions from structured audience requirements
        if structured_audience:
            if structured_audience.get("engagement_period_days"):
                days = structured_audience["engagement_period_days"]
                conditions.append({
                    "id": len(conditions) + 1,
                    "type": "event",
                    "operator": "has",
                    "action": "clicked_link",
                    "filter": "all clicks",
                    "timePeriod": f"within the last {days} Days",
                    "timePeriodType": "relative",
                    "customTimeValue": str(days),
                    "customTimeUnit": "Days"
                })

            if structured_audience.get("exclusion_period_days"):
                days = structured_audience["exclusion_period_days"]
                conditions.append({
                    "id": len(conditions) + 1,
                    "type": "event",
                    "operator": "has_not",
                    "action": "placed_order",
                    "filter": "all orders",
                    "timePeriod": f"within the last {days} Days",
                    "timePeriodType": "relative",
                    "customTimeValue": str(days),
                    "customTimeUnit": "Days"
                })

        return conditions

    def _generate_default_conditions(self, structured_audience: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate default conditions when no specific ones provided."""
        conditions = []

        # Default to engaged customers in last 30 days
        conditions.append({
            "id": 1,
            "type": "event",
            "operator": "has",
            "action": "clicked_link",
            "filter": "all clicks",
            "timePeriod": "within the last 30 Days",
            "timePeriodType": "relative",
            "customTimeValue": "30",
            "customTimeUnit": "Days"
        })

        # Exclude recent purchasers
        conditions.append({
            "id": 2,
            "type": "event",
            "operator": "has_not",
            "action": "placed_order",
            "filter": "all orders",
            "timePeriod": "within the last 30 Days",
            "timePeriodType": "relative",
            "customTimeValue": "30",
            "customTimeUnit": "Days"
        })

        return conditions

    def _enhance_segment_events(self, events: List[CampaignEvent]) -> List[CampaignEvent]:
        """Enhance segment events with proper split structure."""
        enhanced_events = []

        # Ensure we have include and exclude events
        include_event = None
        exclude_event = None

        for event in events:
            if hasattr(event, 'action'):
                if event.action == "include" or event.nextStepID:
                    include_event = event
                elif event.action == "exclude":
                    exclude_event = event
            else:
                # Default to include for events without action
                include_event = event

        # Create include event if missing
        if not include_event:
            include_event = CampaignEvent(
                id="event_include",
                type="split",
                label="include",
                action="include",
                description="Include customers who meet segment criteria",
                nextStepID="step_003",  # Default next step
                active=True,
                parameters={}
            )

        # Create exclude event if missing (common for segments)
        if not exclude_event:
            exclude_event = CampaignEvent(
                id="event_exclude",
                type="split",
                label="exclude",
                action="exclude",
                description="Exclude customers who don't meet segment criteria",
                nextStepID="step_end",  # Default to end
                active=True,
                parameters={}
            )

        # Add proper labels if missing
        if hasattr(include_event, 'label') and not include_event.label:
            include_event.label = "include"
        if hasattr(exclude_event, 'label') and not exclude_event.label:
            exclude_event.label = "exclude"

        enhanced_events.append(include_event)
        if exclude_event:
            enhanced_events.append(exclude_event)

        return enhanced_events

    async def _generate_purchase_offer_step(
        self,
        step_plan: Dict[str, Any],
        campaign_context: Dict[str, Any],
        merchant_context: Dict[str, Any]
    ) -> PurchaseOfferStep:
        """
        Generate purchase offer content with FlowBuilder compliance.

        Args:
            step_plan: Step plan from planner
            campaign_context: Campaign context
            merchant_context: Merchant information

        Returns:
            PurchaseOfferStep with proper FlowBuilder structure
        """
        # Extract structured offer information
        structured_offer = merchant_context.get('structured_requirements', {}).get('offer', {})
        offer_type = structured_offer.get('type', 'percentage_discount')
        offer_value = structured_offer.get('value', 10)
        offer_scope = structured_offer.get('scope', 'sitewide')

        # Generate offer text with enhanced context
        prompt_text = get_purchase_offer_prompt(
            step_plan,
            campaign_context,
            merchant_context
        )

        response = await self.client.chat.completions.create(
            model=self.content_model,
            messages=[
                {"role": "system", "content": CONTENT_GENERATOR_SYSTEM_PROMPT},
                {"role": "user", "content": prompt_text}
            ],
            temperature=0.7,
            max_tokens=300,
            response_format={"type": "text"}
        )

        offer_text = response.choices[0].message.content.strip()
        self._track_usage(response.usage)

        events = self._parse_events(step_plan.get("events", []))

        # Handle products field - convert placeholder strings to proper format
        products = step_plan.get("products", [])

        if isinstance(products, str):
            # Handle placeholder strings like "[ insert product name ]"
            if "[ insert" in products.lower() or products.strip() == "":
                products = []
            else:
                # Try to parse as JSON if it's a string representation
                try:
                    import json
                    products = json.loads(products)
                except (json.JSONDecodeError, ValueError):
                    # If parsing fails, create a placeholder product object
                    products = [{
                        "id": "placeholder_product",
                        "label": products,
                        "showLabel": True,
                        "uniqueId": 1
                    }]
        elif isinstance(products, list):
            # Handle list containing placeholder strings
            valid_products = []
            for item in products:
                if isinstance(item, str):
                    # Handle placeholder strings in list
                    if "[ insert" in item.lower() or item.strip() == "":
                        # Skip placeholder strings
                        continue
                    else:
                        # Create a proper product object for the string
                        valid_products.append({
                            "id": "placeholder_product",
                            "label": item,
                            "showLabel": True,
                            "uniqueId": len(valid_products) + 1
                        })
                elif isinstance(item, dict):
                    # Already a proper product object
                    valid_products.append(item)
                # Skip other types
            products = valid_products

        # Ensure products is a list
        if not isinstance(products, list):
            products = []

        # Ensure proper purchase offer structure
        return PurchaseOfferStep(
            id=step_plan["id"],
            type=StepType.PURCHASE_OFFER,
            label=step_plan.get("label", "Purchase Offer"),
            content=offer_text,
            messageType="standard",
            messageText=offer_text,
            cartSource=step_plan.get("cartSource", "latest_cart"),
            products=products,

            # Discount configuration
            discount=structured_offer is not None,
            discountType=offer_type.replace("_discount", "") if offer_type != "percentage_discount" else "percentage",
            discountPercentage=str(offer_value) if offer_type == "percentage_discount" else "",
            discountAmount=str(offer_value) if offer_type == "fixed_amount" else "",
            discountCode=structured_offer.get('code', '') if offer_type == "code" else "",
            discountAmountLabel="",
            discountEmail="",
            discountExpiry=structured_offer.get('expiry') is not None,
            discountExpiryDate=structured_offer.get('expiry', ''),

            # Additional options
            customTotals=False,
            shippingAmount="",
            includeProductImage=step_plan.get("includeProductImage", True),
            skipForRecentOrders=True,

            # Legacy fields for backward compatibility
            fullText=offer_text,
            minimumDiscount={"type": offer_type.replace("_discount", ""), "value": offer_value},
            minimumDiscountGlobal=False,
            scheduleReminder=True,
            allowSubscriptionUpsell=False,
            allowReminder=True,

            parameters=step_plan.get("parameters", {}),
            active=step_plan.get("active", True),
            events=events,
            purchaseOfferConfig={}
        )

    def _create_product_choice_step(self, step_plan: Dict[str, Any]) -> ProductChoiceStep:
        """
        Create product choice step with enhanced e-commerce integration.

        Args:
            step_plan: Step plan from planner

        Returns:
            ProductChoiceStep with proper FlowBuilder structure
        """
        events = self._parse_events(step_plan.get("events", []))

        # Extract product configuration
        product_selection = step_plan.get("productSelection", "manually")
        product_selection_prompt = step_plan.get("productSelectionPrompt",
            "Show me products you think I'll like based on my prior purchase, cart, browse behavior, profile properties, and recent messages. If you don't have enough information, show me popular products.")

        # Handle structured products input
        products = step_plan.get("products", [])
        if not products and self.request_context:
            structured_reqs = self.request_context.get('structured_requirements', {})

            # Create sample products based on merchant context or offer
            if structured_reqs.get('offer'):
                # Create products related to the offer
                offer = structured_reqs.get('offer', {})
                products = [
                    {
                        "id": f"offer-product-1",
                        "label": f"Special Offer - {offer.get('value', 'Discount')}% Off",
                        "showLabel": True,
                        "uniqueId": 1
                    },
                    {
                        "id": "offer-product-2",
                        "label": "Premium Collection Item",
                        "showLabel": True,
                        "uniqueId": 2
                    }
                ]
            else:
                # Default curated products
                products = [
                    {
                        "id": "prod_001",
                        "label": "Premium Product",
                        "showLabel": True,
                        "uniqueId": 1
                    },
                    {
                        "id": "prod_002",
                        "label": "Popular Item",
                        "showLabel": True,
                        "uniqueId": 2
                    },
                    {
                        "id": "prod_003",
                        "label": "Customer Favorite",
                        "showLabel": True,
                        "uniqueId": 3
                    }
                ]

        # Extract discount configuration from structured requirements
        discount = "None"
        discount_expiry = False
        discount_expiry_date = ""

        if self.request_context:
            structured_reqs = self.request_context.get('structured_requirements', {})
            structured_offer = structured_reqs.get('offer', {})

            if structured_offer:
                if structured_offer.get('type') == 'percentage_discount':
                    discount = f"{structured_offer.get('value', 10)}%"
                elif structured_offer.get('type') == 'fixed_amount':
                    discount = f"${structured_offer.get('value', 5)}"
                elif structured_offer.get('type') == 'code':
                    discount = structured_offer.get('code', 'SAVE20')

                if structured_offer.get('expiry'):
                    discount_expiry = True
                    discount_expiry_date = structured_offer.get('expiry')

        # Additional e-commerce options
        product_images = step_plan.get("productImages", True)
        custom_totals = step_plan.get("customTotals", False)
        custom_totals_amount = step_plan.get("customTotalsAmount", "Shipping")

        # Create compelling message text
        message_text = step_plan.get("messageText")
        if not message_text:
            if discount != "None":
                message_text = f"Reply to buy with {discount} discount:\n\nPremium Product Selection"
            else:
                message_text = "Reply to purchase from our curated collection:\n\nPremium Products"

        # Ensure proper events for product choice
        if not any(event.intent == "buy" for event in events):
            # Add buy event if missing
            buy_event = CampaignEvent(
                id=f"{step_plan['id']}-buy",
                type=EventType.REPLY,
                intent="buy",
                description="Customer wants to purchase a product",
                nextStepID=None,  # Will be set during flow building
                active=True,
                parameters={}
            )
            events.append(buy_event)

        # Add noreply event for follow-up
        if not any(event.type == EventType.NOREPLY for event in events):
            noreply_event = CampaignEvent(
                id=f"{step_plan['id']}-noreply",
                type=EventType.NOREPLY,
                after={"value": 2, "unit": "hours"},
                nextStepID=None,  # Will be set during flow building
                active=True,
                parameters={}
            )
            events.append(noreply_event)

        return ProductChoiceStep(
            id=step_plan["id"],
            type=StepType.PRODUCT_CHOICE,
            label=step_plan.get("label", "Choose Product"),
            messageType="standard",
            messageText=message_text,
            text=message_text,  # Backward compatibility
            prompt="Which product would you like to purchase?",
            productSelection=product_selection,
            productSelectionPrompt=product_selection_prompt,
            products=products,
            productImages=product_images,
            customTotals=custom_totals,
            customTotalsAmount=custom_totals_amount,
            discountExpiry=discount_expiry,
            discountExpiryDate=discount_expiry_date,
            discount=discount,
            productChoiceConfig=step_plan.get("productChoiceConfig", {}),
            parameters=step_plan.get("parameters", {}),
            active=step_plan.get("active", True),
            events=events
        )

    def _create_delay_step(self, step_plan: Dict[str, Any]) -> DelayStep:
        """Create delay step (no LLM needed) with proper FlowBuilder structure."""
        events = self._parse_events(step_plan.get("events", []))

        # Extract delay information from step plan
        duration = step_plan.get("duration", {"hours": 6})
        delay_value = None
        delay_unit = None

        # Parse duration to get value and unit
        if isinstance(duration, dict):
            for unit, value in duration.items():
                if unit in ['seconds', 'minutes', 'hours', 'days']:
                    delay_value = str(value)
                    delay_unit = unit.title()  # "Seconds", "Minutes", "Hours", "Days"
                    break

        # Default values if not found
        if not delay_value or not delay_unit:
            delay_value = "6"
            delay_unit = "Hours"

        # Create structured delay object
        delay_obj = {"value": delay_value, "unit": delay_unit}

        return DelayStep(
            id=step_plan["id"],
            type=StepType.DELAY,
            time=delay_value,
            period=delay_unit,
            delay=delay_obj,
            duration=duration,  # Keep for backward compatibility
            parameters=step_plan.get("parameters", {}),
            active=step_plan.get("active", True),
            events=events
        )

    def _create_condition_step(self, step_plan: Dict[str, Any]) -> ConditionStep:
        """Create condition step (no LLM needed)."""
        events = self._parse_events(step_plan.get("events", []))

        return ConditionStep(
            id=step_plan["id"],
            type=StepType.CONDITION,
            condition=step_plan.get("condition", {}),
            trueStepID=step_plan.get("trueStepID"),
            falseStepID=step_plan.get("falseStepID"),
            parameters=step_plan.get("parameters", {}),
            active=step_plan.get("active", True),
            events=events
        )

    def _create_experiment_step(self, step_plan: Dict[str, Any]) -> ExperimentStep:
        """Create A/B experiment step with proper FlowBuilder structure."""
        events = self._parse_events(step_plan.get("events", []))

        # Extract experiment configuration with robust fallbacks
        step_id = step_plan.get("id", "experiment_step")
        experiment_name = step_plan.get("experimentName") or step_plan.get("label") or f"Experiment {step_id}"
        version = step_plan.get("version", "1")

        # Build display content
        display_content = f"{experiment_name}(v{version})"

        # Build experiment configuration from variants or parameters
        experiment_config = step_plan.get("experimentConfig", {})

        # If using legacy variants/percentages, convert to experiment config
        if not experiment_config and step_plan.get("variants"):
            experiment_config = {
                "variants": step_plan.get("variants", []),
                "splitPercentages": step_plan.get("splitPercentages", [50, 50]),
                "experimentType": "ab_test"
            }

        # Ensure split events are properly structured for A/B testing
        enhanced_events = []
        for event in events:
            if event.type == "split":
                # Ensure proper split event structure for A/B branches
                enhanced_event = CampaignEvent(
                    id=event.id,
                    type=EventType.SPLIT,
                    label=event.label or f"Group {event.id[-1]}",  # Group A, Group B, etc.
                    nextStepID=event.nextStepID,
                    action=event.action or "include",
                    description=event.description or f"A/B test branch: {event.label}",
                    after=event.after,
                    parameters=event.parameters,
                    active=event.active
                )
                enhanced_events.append(enhanced_event)
            else:
                enhanced_events.append(event)

        # If no events provided, create default A/B split structure
        if not enhanced_events:
            enhanced_events = [
                CampaignEvent(
                    id=f"{step_id}-group-a",
                    type=EventType.SPLIT,
                    label="Group A",
                    nextStepID=None,  # Will be set during flow building
                    action="include",
                    description="A/B test Group A - Control variant",
                    parameters={},
                    active=True
                ),
                CampaignEvent(
                    id=f"{step_id}-group-b",
                    type=EventType.SPLIT,
                    label="Group B",
                    nextStepID=None,  # Will be set during flow building
                    action="include",
                    description="A/B test Group B - Test variant",
                    parameters={},
                    active=True
                )
            ]

        return ExperimentStep(
            id=step_id,
            type=StepType.EXPERIMENT,
            label=step_plan.get("label"),
            experimentName=experiment_name,
            version=version,
            content=display_content,
            experimentConfig=experiment_config,
            variants=step_plan.get("variants"),  # Legacy compatibility
            splitPercentages=step_plan.get("splitPercentages"),  # Legacy compatibility
            parameters=step_plan.get("parameters", {}),
            active=step_plan.get("active", True),
            events=enhanced_events
        )

    def _create_rate_limit_step(self, step_plan: Dict[str, Any]) -> RateLimitStep:
        """Create rate limit step with proper FlowBuilder compliance."""
        events = self._parse_events(step_plan.get("events", []))

        # Extract rate limiting parameters
        rate_config = step_plan.get("rateLimit", {})

        # Handle legacy formats and structured inputs
        if not rate_config:
            # Try to extract from legacy fields
            max_messages = step_plan.get("maxMessages")
            time_window = step_plan.get("timeWindow", {})

            if max_messages and time_window:
                # Convert legacy format
                value = str(max_messages)
                period_unit = time_window.get("unit", "Hours")
                timespan = str(time_window.get("value", 1))
            else:
                # Extract from direct parameters
                occurrences = step_plan.get("occurrences", "12")
                timespan = step_plan.get("timespan", "11")
                period = step_plan.get("period", "Minutes")
                value = str(occurrences)
                period_unit = period
        else:
            # Use structured rateLimit config
            value = str(rate_config.get("limit", "12"))
            period_unit = rate_config.get("period", "Minutes")
            timespan = step_plan.get("timespan", "1")

        # Build rate limit object
        rate_limit_obj = {"limit": value, "period": period_unit}

        # Build display content
        display_content = f"{value} times every {timespan} {period_unit.lower()}"

        # Ensure default event if none provided
        if not events:
            events = [
                CampaignEvent(
                    id=f"{step_plan['id']}-default",
                    type=EventType.DEFAULT,
                    nextStepID=None,  # Will be set during flow building
                    parameters={},
                    active=True
                )
            ]

        return RateLimitStep(
            id=step_plan["id"],
            type=StepType.RATE_LIMIT,
            occurrences=value,
            timespan=timespan,
            period=period_unit,
            rateLimit=rate_limit_obj,
            content=display_content,
            maxMessages=step_plan.get("maxMessages"),  # Legacy compatibility
            timeWindow=step_plan.get("timeWindow"),  # Legacy compatibility
            nextStepID=step_plan.get("nextStepID"),  # Legacy compatibility
            exceededStepID=step_plan.get("exceededStepID"),  # Legacy compatibility
            parameters=step_plan.get("parameters", {}),
            active=step_plan.get("active", True),
            events=events
        )

    def _create_limit_step(self, step_plan: Dict[str, Any]) -> LimitStep:
        """Create campaign execution limit step with proper FlowBuilder compliance."""
        events = self._parse_events(step_plan.get("events", []))

        # Extract limit parameters
        limit_config = step_plan.get("limit", {})

        # Handle structured inputs
        if limit_config:
            # Use structured limit config
            value = str(limit_config.get("value", "5"))
            period_unit = limit_config.get("period", "Hours")
            timespan = step_plan.get("timespan", "1")
        else:
            # Extract from direct parameters
            occurrences = step_plan.get("occurrences", "5")
            timespan = step_plan.get("timespan", "1")
            period = step_plan.get("period", "Hours")
            value = str(occurrences)
            period_unit = period

        # Build limit object
        limit_obj = {"value": value, "period": period_unit}

        # Build display content
        display_content = f"{value} times every {timespan} {period_unit.lower()}"

        # Ensure default event if none provided
        if not events:
            events = [
                CampaignEvent(
                    id=f"{step_plan['id']}-default",
                    type=EventType.DEFAULT,
                    nextStepID=None,  # Will be set during flow building
                    parameters={},
                    active=True
                )
            ]

        return LimitStep(
            id=step_plan["id"],
            type=StepType.LIMIT,
            occurrences=value,
            timespan=timespan,
            period=period_unit,
            limit=limit_obj,
            content=display_content,
            parameters=step_plan.get("parameters", {}),
            active=step_plan.get("active", True),
            events=events
        )

    def _create_purchase_step(self, step_plan: Dict[str, Any]) -> PurchaseStep:
        """Create purchase step with proper FlowBuilder compliance."""
        events = self._parse_events(step_plan.get("events", []))

        # Extract cart configuration
        cart_source = step_plan.get("cartSource", "manual")
        products = step_plan.get("products", [])

        # Handle structured products input
        if not products and self.request_context:
            structured_reqs = self.request_context.get('structured_requirements', {})
            offer = structured_reqs.get('offer', {})

            # Create product from structured offer if available
            if offer and offer.get('type') in ['percentage_discount', 'fixed_amount']:
                # Create a generic product for the offer
                products = [{
                    "productVariantId": f"offer-{offer.get('code', 'DEFAULT')}",
                    "quantity": "1",
                    "uniqueId": 1
                }]

        # Extract discount configuration
        discount = step_plan.get("discount", False)
        custom_totals = step_plan.get("customTotals", False)
        shipping_amount = step_plan.get("shippingAmount", "")

        # Handle structured offer integration
        if self.request_context and not discount:
            structured_reqs = self.request_context.get('structured_requirements', {})
            structured_offer = structured_reqs.get('offer', {})

            if structured_offer:
                discount = True
                if structured_offer.get('type') == 'percentage_discount':
                    shipping_amount = f"{structured_offer.get('value', 0)}% discount applied"
                elif structured_offer.get('type') == 'fixed_amount':
                    shipping_amount = f"${structured_offer.get('value', 0)} discount applied"

        # Additional purchase options
        send_reminder = step_plan.get("sendReminderForNonPurchasers", True)
        allow_automatic_payment = step_plan.get("allowAutomaticPayment", False)

        # Ensure default event if none provided
        if not events:
            events = [
                CampaignEvent(
                    id=f"{step_plan['id']}-default",
                    type=EventType.DEFAULT,
                    nextStepID=None,  # Will be set during flow building
                    parameters={},
                    active=True
                )
            ]

        return PurchaseStep(
            id=step_plan["id"],
            type=StepType.PURCHASE,
            cartSource=cart_source,
            products=products,
            discount=discount,
            customTotals=custom_totals,
            shippingAmount=shipping_amount,
            sendReminderForNonPurchasers=send_reminder,
            allowAutomaticPayment=allow_automatic_payment,
            purchaseConfig=step_plan.get("purchaseConfig", {}),
            parameters=step_plan.get("parameters", {}),
            active=step_plan.get("active", True),
            events=events
        )

    def _create_schedule_step(self, step_plan: Dict[str, Any]) -> ScheduleStep:
        """Create schedule step with proper FlowBuilder compliance."""
        events = self._parse_events(step_plan.get("events", []))

        # Extract schedule configuration
        schedule_config = step_plan.get("schedule", {})

        # Handle structured scheduling inputs from request
        if not schedule_config and self.request_context:
            # Extract from structured requirements
            structured_reqs = self.request_context.get('structured_requirements', {})
            scheduling = structured_reqs.get('scheduling')

            if scheduling:
                # Convert structured scheduling to schedule config
                schedule_config = {
                    "datetime": scheduling.get("datetime"),
                    "timezone": scheduling.get("timezone"),
                    "description": scheduling.get("description")
                }

        # Merge with any existing schedule config
        if step_plan.get("scheduleTime"):
            schedule_config["scheduleTime"] = step_plan.get("scheduleTime")

        # Build label and content
        label = step_plan.get("label")
        if not label:
            if schedule_config.get("description"):
                label = schedule_config["description"]
            elif schedule_config.get("datetime"):
                label = f"Scheduled for {schedule_config['datetime']}"
            else:
                label = "Schedule configuration"

        content = step_plan.get("content") or label

        # Ensure proper SCHEDULE events with split structure
        enhanced_events = []
        if not events:
            # Create default schedule events structure
            enhanced_events = [
                CampaignEvent(
                    id=f"{step_plan['id']}-default",
                    type=EventType.SPLIT,
                    label="All other time",
                    nextStepID=None,  # Will be set during flow building
                    action="include",
                    description="Default time branch",
                    parameters={},
                    active=True
                ),
                CampaignEvent(
                    id=f"{step_plan['id']}-scheduled",
                    type=EventType.SPLIT,
                    label=schedule_config.get("description", "Scheduled time"),
                    nextStepID=None,  # Will be set during flow building
                    action="include",
                    description="Scheduled time branch",
                    parameters={},
                    active=True
                )
            ]
        else:
            # Enhance existing events to ensure proper split structure
            for event in events:
                if event.type == "split":
                    enhanced_event = CampaignEvent(
                        id=event.id,
                        type=EventType.SPLIT,
                        label=event.label or "Scheduled time",
                        nextStepID=event.nextStepID,
                        action=event.action or "include",
                        description=event.description or "Time-based split",
                        parameters=event.parameters,
                        active=event.active
                    )
                    enhanced_events.append(enhanced_event)
                else:
                    enhanced_events.append(event)

        return ScheduleStep(
            id=step_plan["id"],
            type=StepType.SCHEDULE,
            label=label,
            content=content,
            schedule=schedule_config,
            scheduleTime=step_plan.get("scheduleTime"),  # Legacy compatibility
            nextStepID=step_plan.get("nextStepID"),  # Legacy compatibility
            parameters=step_plan.get("parameters", {}),
            active=step_plan.get("active", True),
            events=enhanced_events
        )

    def _create_split_step(self, step_plan: Dict[str, Any]) -> SplitStep:
        """Create split step with proper FlowBuilder compliance."""
        events = self._parse_events(step_plan.get("events", []))

        # Extract split configuration
        split_config = step_plan.get("splitConfig", {})

        # Build label and description
        label = step_plan.get("label", "split")
        description = step_plan.get("description", "Audience split")
        content = step_plan.get("content") or description

        # Default action for split
        action = step_plan.get("action", "include")

        # Ensure proper split events
        enhanced_events = []
        for event in events:
            if event.type == "split":
                # Ensure split events have required label and action fields
                enhanced_event = CampaignEvent(
                    type="split",
                    label=event.label if hasattr(event, 'label') else label,
                    action=event.action if hasattr(event, 'action') else action,
                    description=event.description or description,
                    nextStepID=event.nextStepID
                )
                enhanced_events.append(enhanced_event)
            else:
                enhanced_events.append(event)

        return SplitStep(
            id=step_plan["id"],
            type=StepType.SPLIT,
            label=label,
            action=action,
            description=description,
            content=content,
            enabled=step_plan.get("enabled", True),
            splitConfig=split_config,
            nextStepID=step_plan.get("nextStepID"),
            parameters=step_plan.get("parameters", {}),
            active=step_plan.get("active", True),
            events=enhanced_events
        )

    def _create_end_step(self, step_plan: Dict[str, Any]) -> EndStep:
        """Create end step (no LLM needed)."""
        return EndStep(
            id=step_plan["id"],
            type=StepType.END,
            reason=step_plan.get("reason", "Campaign completed"),
            parameters=step_plan.get("parameters", {}),
            active=step_plan.get("active", True),
            events=[]
        )

    def _validate_campaign_connections(self, campaign: Campaign) -> List[str]:
        """
        Validate campaign node connections for FlowBuilder compliance.

        Args:
            campaign: Generated campaign object

        Returns:
            List of validation warnings/errors
        """
        warnings = []
        errors = []

        # Create step lookup
        step_lookup = {step.id: step for step in campaign.steps}

        # Check each event's nextStepID
        for step in campaign.steps:
            if hasattr(step, 'events') and step.events:
                for event in step.events:
                    next_step_id = event.nextStepID
                    if next_step_id:
                        if next_step_id not in step_lookup:
                            errors.append(f"Event {event.id} in step {step.id} references non-existent step: {next_step_id}")
                        elif next_step_id == step.id:
                            warnings.append(f"Event {event.id} creates self-reference loop in step {step.id}")

        # Check if initialStepID exists
        if hasattr(campaign, 'initialStepID') and campaign.initialStepID:
            if campaign.initialStepID not in step_lookup:
                errors.append(f"Initial step ID not found: {campaign.initialStepID}")

        # Check for unreachable steps (no incoming events)
        if hasattr(campaign, 'initialStepID') and campaign.initialStepID:
            reachable_steps = {campaign.initialStepID}
            to_check = [campaign.initialStepID]

            while to_check:
                current_id = to_check.pop()
                current_step = step_lookup.get(current_id)
                if current_step and hasattr(current_step, 'events'):
                    for event in current_step.events:
                        if event.nextStepID and event.nextStepID not in reachable_steps:
                            reachable_steps.add(event.nextStepID)
                            to_check.append(event.nextStepID)

            # Find unreachable steps
            for step_id, step in step_lookup.items():
                if step_id not in reachable_steps:
                    warnings.append(f"Step {step_id} is unreachable from initial step")

        # Log validation results
        if errors:
            for error in errors:
                logger.error(f"Campaign connection error: {error}")
        if warnings:
            for warning in warnings:
                logger.warning(f"Campaign connection warning: {warning}")

        return errors + warnings

    def _create_base_step(self, step_plan: Dict[str, Any]):
        """Create a base step for unsupported types."""
        from ...models.campaign import BaseStep
        events = self._parse_events(step_plan.get("events", []))

        return BaseStep(
            id=step_plan["id"],
            type=step_plan.get("type", "message"),
            parameters=step_plan.get("parameters", {}),
            active=step_plan.get("active", True),
            events=events
        )

    def _parse_events(self, events_data: List[Dict[str, Any]]) -> List[CampaignEvent]:
        """
        Parse event dictionaries into CampaignEvent objects.

        Args:
            events_data: List of event dicts from plan

        Returns:
            List of CampaignEvent objects
        """
        events = []
        for event_data in events_data:
            try:
                # Convert string event type to EventType enum
                event_type_str = event_data.get("type", "reply")
                event_type = EventType(event_type_str) if event_type_str in EventType.__members__.values() else EventType.REPLY

                # Handle NO_REPLY events - fix after object structure
                after = event_data.get("after")
                if event_type == EventType.NOREPLY and after:
                    # Convert legacy formats to proper after object
                    if isinstance(after, dict):
                        # Check if already proper format
                        if "value" not in after or "unit" not in after:
                            # Try to extract from legacy formats
                            if "hours" in after:
                                after = {"value": after["hours"], "unit": "hours"}
                            elif "minutes" in after:
                                after = {"value": after["minutes"], "unit": "minutes"}
                            elif "seconds" in after:
                                after = {"value": after["seconds"], "unit": "seconds"}
                            elif "days" in after:
                                after = {"value": after["days"], "unit": "days"}
                            else:
                                # Default fallback
                                after = {"value": 6, "unit": "hours"}
                    elif isinstance(after, (int, float)):
                        # Convert numeric to proper structure
                        after = {"value": int(after), "unit": "hours"}
                    elif isinstance(after, str):
                        # Parse string like "24 hours" or "6h"
                        parts = after.lower().split()
                        if len(parts) == 2:
                            try:
                                value = int(parts[0])
                                unit = parts[1]
                                if unit.startswith('hour'):
                                    unit = 'hours'
                                elif unit.startswith('minute'):
                                    unit = 'minutes'
                                elif unit.startswith('second'):
                                    unit = 'seconds'
                                elif unit.startswith('day'):
                                    unit = 'days'
                                after = {"value": value, "unit": unit}
                            except ValueError:
                                after = {"value": 6, "unit": "hours"}
                        else:
                            after = {"value": 6, "unit": "hours"}

                # Handle SPLIT events - ensure proper structure
                if event_type_str == "split":
                    # Ensure split events have required label and action fields
                    label = event_data.get("label")
                    action = event_data.get("action")

                    # Set defaults for missing required fields
                    if not label:
                        label = "include"  # Default split label
                        event_data["label"] = label

                    if not action:
                        action = "include"  # Default split action
                        event_data["action"] = action

                    # Ensure description for better intent matching
                    description = event_data.get("description")
                    if not description:
                        if action == "include":
                            description = f"Include customers in {label} segment"
                        else:
                            description = f"Exclude customers from {label} segment"
                        event_data["description"] = description

                event = CampaignEvent(
                    id=event_data.get("id", f"event_{len(events)+1:03d}"),
                    type=event_type,
                    intent=event_data.get("intent"),
                    description=event_data.get("description"),
                    nextStepID=event_data.get("nextStepID"),
                    after=after,
                    action=event_data.get("action"),
                    parameters=event_data.get("parameters", {}),
                    active=event_data.get("active", True)
                )
                events.append(event)
            except Exception as e:
                logger.warning(f"Failed to parse event: {e}, skipping")
                continue

        return events

    def _track_usage(self, usage) -> None:
        """Track token usage and cost."""
        input_tokens = usage.prompt_tokens
        output_tokens = usage.completion_tokens

        # GPT-4o-mini pricing: $0.15 per 1M input, $0.60 per 1M output
        cost = (input_tokens / 1_000_000 * 0.15) + (output_tokens / 1_000_000 * 0.60)

        self.total_cost += cost
        self.total_tokens += input_tokens + output_tokens

    def get_generation_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about content generation.

        Returns:
            Dict with cost and token information
        """
        return {
            "model": self.content_model,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost, 6)
        }


# Factory function
def create_content_generator(openai_api_key: str) -> ContentGenerator:
    """
    Factory function to create ContentGenerator instance.

    Args:
        openai_api_key: OpenAI API key

    Returns:
        Configured ContentGenerator instance
    """
    client = AsyncOpenAI(api_key=openai_api_key)
    return ContentGenerator(client)