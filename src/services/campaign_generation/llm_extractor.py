"""
LLM-based information extraction service.
Replaces regex patterns with AI-powered extraction for better reliability.
"""
import json
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class SchedulingInfo(BaseModel):
    """Scheduling information extracted from campaign description."""
    datetime: Optional[str] = None
    timezone: Optional[str] = None
    date_expression: Optional[str] = None
    has_business_hours: bool = False
    weekend_exclusion: bool = False

class AudienceCriteria(BaseModel):
    """Audience criteria extracted from campaign description."""
    behavioral_criteria: list = []
    logical_operator: str = "AND"
    description: str = "All customers"
    customer_segment: Optional[str] = None
    purchase_history: Optional[Dict[str, Any]] = None
    engagement_period: Optional[str] = None

class ProductInfo(BaseModel):
    """Product information extracted from campaign description."""
    products: list = []
    specific_product: Optional[str] = None
    product_url: Optional[str] = None
    product_details: Dict[str, Any] = {}

class ExperimentConfig(BaseModel):
    """A/B testing configuration extracted from campaign description."""
    enabled: bool = False
    variants_count: int = 0
    variants: list = []
    success_metrics: list = []
    duration_days: int = 7
    experiment_name: Optional[str] = None

class RateLimitConfig(BaseModel):
    """Rate limiting configuration extracted from campaign description."""
    enabled: bool = False
    daily_limit: int = 10
    hourly_limit: int = 1
    cooldown_minutes: int = 60
    business_hours_only: bool = False
    weekend_exclusion: bool = False

class SplitConfig(BaseModel):
    """Audience splitting configuration extracted from campaign description."""
    enabled: bool = False
    split_type: str = "random"
    split_percentages: Dict[str, int] = {"group_a": 50, "group_b": 50}
    group_names: Dict[str, str] = {"group_a": "Group A", "group_b": "Group B"}
    next_steps: Dict[str, str] = {"group_a": "path_a", "group_b": "path_b"}

class DelayConfig(BaseModel):
    """Delay timing configuration extracted from campaign description."""
    enabled: bool = False
    minutes: int = 0
    hours: int = 0
    days: int = 0
    business_hours_only: bool = False
    max_wait_days: int = 7

class ProductChoiceInfo(BaseModel):
    """Product choice configuration extracted from campaign description."""
    enabled: bool = False
    products: list = []
    display_type: str = "list"
    next_step_id: Optional[str] = None

class PropertyInfo(BaseModel):
    """Property conditions configuration extracted from campaign description."""
    enabled: bool = False
    conditions: list = []
    match_all: bool = True
    next_step_id: Optional[str] = None

class ReplyInfo(BaseModel):
    """Reply configuration extracted from campaign description."""
    enabled: bool = False
    reply_type: str = "reply"  # reply, no_reply, default
    keywords: list = []
    response_template: Optional[str] = None
    next_step_id: Optional[str] = None

class PurchaseInfo(BaseModel):
    """Purchase configuration extracted from campaign description."""
    enabled: bool = False
    purchase_type: str = "purchase_offer"  # purchase_offer, purchase
    products: list = []
    discount_percentage: Optional[float] = None
    urgency: Optional[str] = None
    next_step_id: Optional[str] = None

class LimitInfo(BaseModel):
    """Limit configuration extracted from campaign description."""
    enabled: bool = False
    limit_type: str = "rate"  # rate, daily, total
    max_count: int = 100
    time_window: Optional[str] = None  # daily, weekly, monthly
    next_step_id: Optional[str] = None

class LLMExtractor:
    """LLM-based information extractor for campaign generation."""

    def __init__(self, client, model: str = "gpt-4o-mini"):
        """
        Initialize the LLM extractor.

        Args:
            client: OpenAI client
            model: Model to use for extraction
        """
        self.client = client
        self.model = model
        self.timeout = 30  # seconds

    async def extract_all_features(self, description: str) -> Dict[str, Any]:
        """
        Extract all campaign features using LLM in a single call.

        Args:
            description: Campaign description to analyze

        Returns:
            Dictionary containing all extracted features
        """
        try:
            logger.info("Extracting all campaign features using LLM...")

            # Create comprehensive extraction prompt
            prompt = self._create_extraction_prompt(description)

            # Call LLM
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                timeout=self.timeout
            )

            # Parse response
            result = response.choices[0].message.content
            extracted_data = json.loads(result)

            logger.info("LLM extraction completed successfully")
            return extracted_data

        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            # Return empty data structure
            return self._get_empty_extraction()

    def _get_system_prompt(self) -> str:
        """Get the system prompt for LLM extraction."""
        return """You are an expert at analyzing SMS campaign descriptions and extracting structured information.

Your task is to extract specific campaign features from the given description and return them as JSON.

Extract the following types of information if present:
1. Scheduling information (datetime, timezone, business hours restrictions)
2. Audience criteria (behavioral patterns, purchase history, segmentation)
3. Product details (specific products, URLs, details)
4. A/B testing configuration (variants, metrics, duration)
5. Rate limiting rules (daily/hourly limits, business hours, weekend rules)
6. Audience splitting (percentages, groups, paths)
7. Delay timing (minutes, hours, days, business hours)
8. Product choice configuration (products, display type)
9. Property conditions (field conditions, logic, next steps)
10. Reply configurations (reply types, keywords, response templates)
11. Purchase configurations (purchase offers, purchase links, urgency)
12. Limit configurations (rate limits, daily/monthly caps, time windows)

For each feature type, only include it if the description explicitly mentions it.
If a feature is not mentioned, return the default/empty values.

Respond with valid JSON only."""

    def _create_extraction_prompt(self, description: str) -> str:
        """Create the extraction prompt for the given description."""
        return f"""Extract campaign features from this description:

{description}

Return a JSON object with the following structure:

{{
    "scheduling": {{
        "datetime": "Extracted datetime or null",
        "timezone": "Extracted timezone or null",
        "date_expression": "Original date expression or null",
        "has_business_hours": true/false,
        "weekend_exclusion": true/false
    }},
    "audience_criteria": {{
        "behavioral_criteria": ["list", "of", "behavioral", "patterns"],
        "logical_operator": "AND or OR",
        "description": "Target audience description",
        "customer_segment": "segment name or null",
        "purchase_history": {{"criterion": "value"}} or null,
        "engagement_period": "time period or null"
    }},
    "product_info": {{
        "products": ["product1", "product2"],
        "specific_product": "main product or null",
        "product_url": "product URL or null",
        "product_details": {{"key": "value"}}
    }},
    "experiment_config": {{
        "enabled": true/false,
        "variants_count": 2,
        "variants": [
            {{"id": "A", "description": "Variant A"}},
            {{"id": "B", "description": "Variant B"}}
        ],
        "success_metrics": ["conversion_rate", "click_rate"],
        "duration_days": 7,
        "experiment_name": "Test name or null"
    }},
    "rate_limit_config": {{
        "enabled": true/false,
        "daily_limit": 10,
        "hourly_limit": 1,
        "cooldown_minutes": 60,
        "business_hours_only": true/false,
        "weekend_exclusion": true/false
    }},
    "split_config": {{
        "enabled": true/false,
        "split_type": "random/behavioral/demographic",
        "split_percentages": {{"group_a": 60, "group_b": 40}},
        "group_names": {{"group_a": "Group A", "group_b": "Group B"}},
        "next_steps": {{"group_a": "path_a", "group_b": "path_b"}}
    }},
    "delay_config": {{
        "enabled": true/false,
        "minutes": 0,
        "hours": 0,
        "days": 0,
        "business_hours_only": true/false,
        "max_wait_days": 7
    }},
    "product_choice_info": {{
        "enabled": true/false,
        "products": ["product1", "product2"],
        "display_type": "list/grid",
        "next_step_id": "next step ID or null"
    }},
    "property_info": {{
        "enabled": true/false,
        "conditions": [
            {{
                "field": "field_name",
                "operator": "equals/greater_than/contains",
                "value": "comparison_value",
                "logical_operator": "AND/OR"
            }}
        ],
        "match_all": true/false,
        "next_step_id": "next step ID or null"
    }},
    "reply_info": {{
        "enabled": true/false,
        "reply_type": "reply/no_reply/default",
        "keywords": ["keyword1", "keyword2"],
        "response_template": "Response template text or null",
        "next_step_id": "next step ID or null"
    }},
    "purchase_info": {{
        "enabled": true/false,
        "purchase_type": "purchase_offer/purchase",
        "products": ["product1", "product2"],
        "discount_percentage": 20.0,
        "urgency": "high/medium/low",
        "next_step_id": "next step ID or null"
    }},
    "limit_info": {{
        "enabled": true/false,
        "limit_type": "rate/daily/total",
        "max_count": 100,
        "time_window": "daily/weekly/monthly",
        "next_step_id": "next step ID or null"
    }}
}}

Only include features that are explicitly mentioned in the description.
If a feature is not mentioned, use default/empty values.
Respond with valid JSON only."""

    def _get_empty_extraction(self) -> Dict[str, Any]:
        """Get empty extraction data structure."""
        return {
            "scheduling": SchedulingInfo().dict(),
            "audience_criteria": AudienceCriteria().dict(),
            "product_info": ProductInfo().dict(),
            "experiment_config": ExperimentConfig().dict(),
            "rate_limit_config": RateLimitConfig().dict(),
            "split_config": SplitConfig().dict(),
            "delay_config": DelayConfig().dict(),
            "product_choice_info": ProductChoiceInfo().dict(),
            "property_info": PropertyInfo().dict(),
            "reply_info": ReplyInfo().dict(),
            "purchase_info": PurchaseInfo().dict(),
            "limit_info": LimitInfo().dict()
        }

    async def extract_scheduling_llm(self, description: str) -> Dict[str, Any]:
        """Extract scheduling information using LLM."""
        try:
            prompt = f"""Extract scheduling information from this campaign description:

{description}

Return JSON with:
- datetime: Extracted datetime or null
- timezone: Extracted timezone or null
- date_expression: Original date expression or null
- has_business_hours: true/false
- weekend_exclusion: true/false

Only include if scheduling is mentioned."""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Extract scheduling information. Return JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                timeout=self.timeout
            )

            result = response.choices[0].message.content
            return json.loads(result)

        except Exception as e:
            logger.error(f"LLM scheduling extraction failed: {e}")
            return SchedulingInfo().dict()

    async def extract_audience_criteria_llm(self, description: str) -> Dict[str, Any]:
        """Extract audience criteria using LLM."""
        try:
            prompt = f"""Extract audience targeting criteria from this campaign description:

{description}

Return JSON with:
- behavioral_criteria: List of behavioral patterns
- logical_operator: AND or OR
- description: Target audience description
- customer_segment: Segment name if specified
- purchase_history: Purchase criteria if specified
- engagement_period: Time period if specified

Only include if audience targeting is mentioned."""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Extract audience criteria. Return JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                timeout=self.timeout
            )

            result = response.choices[0].message.content
            return json.loads(result)

        except Exception as e:
            logger.error(f"LLM audience criteria extraction failed: {e}")
            return AudienceCriteria().dict()

    async def extract_ab_test_criteria_llm(self, description: str) -> Dict[str, Any]:
        """Extract A/B testing criteria using LLM."""
        try:
            prompt = f"""Extract A/B testing configuration from this campaign description:

{description}

Return JSON with:
- enabled: true/false
- variants_count: Number of variants (2-4)
- variants: Array of variants with id and description
- success_metrics: List of success metrics
- duration_days: Test duration in days
- experiment_name: Test name if specified

Only include if A/B testing is mentioned."""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Extract A/B testing configuration. Return JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                timeout=self.timeout
            )

            result = response.choices[0].message.content
            return json.loads(result)

        except Exception as e:
            logger.error(f"LLM A/B test extraction failed: {e}")
            return ExperimentConfig().dict()

    async def extract_rate_limiting_criteria_llm(self, description: str) -> Dict[str, Any]:
        """Extract rate limiting criteria using LLM."""
        try:
            prompt = f"""Extract rate limiting rules from this campaign description:

{description}

Return JSON with:
- enabled: true/false
- daily_limit: Maximum messages per day
- hourly_limit: Maximum messages per hour
- cooldown_minutes: Minutes between messages
- business_hours_only: true/false
- weekend_exclusion: true/false

Only include if rate limiting is mentioned."""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Extract rate limiting rules. Return JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                timeout=self.timeout
            )

            result = response.choices[0].message.content
            return json.loads(result)

        except Exception as e:
            logger.error(f"LLM rate limiting extraction failed: {e}")
            return RateLimitConfig().dict()

    async def extract_audience_split_criteria_llm(self, description: str) -> Dict[str, Any]:
        """Extract audience splitting criteria using LLM."""
        try:
            prompt = f"""Extract audience splitting configuration from this campaign description:

{description}

Return JSON with:
- enabled: true/false
- split_type: random/behavioral/demographic
- split_percentages: Percentages for each group
- group_names: Names for each group
- next_steps: Next step IDs for each group

Only include if audience splitting is mentioned."""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Extract audience splitting configuration. Return JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                timeout=self.timeout
            )

            result = response.choices[0].message.content
            return json.loads(result)

        except Exception as e:
            logger.error(f"LLM audience split extraction failed: {e}")
            return SplitConfig().dict()

    async def extract_delay_timing_llm(self, description: str) -> Dict[str, Any]:
        """Extract delay timing using LLM."""
        try:
            prompt = f"""Extract delay timing from this campaign description:

{description}

Return JSON with:
- enabled: true/false
- minutes: Minutes to wait
- hours: Hours to wait
- days: Days to wait
- business_hours_only: true/false
- max_wait_days: Maximum days to wait

Only include if delay timing is mentioned."""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Extract delay timing. Return JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                timeout=self.timeout
            )

            result = response.choices[0].message.content
            return json.loads(result)

        except Exception as e:
            logger.error(f"LLM delay timing extraction failed: {e}")
            return DelayConfig().dict()

    async def extract_product_choice_llm(self, description: str) -> Dict[str, Any]:
        """Extract product choice configuration using LLM."""
        try:
            prompt = f"""Extract product choice configuration from this campaign description:

{description}

Return JSON with:
- enabled: true/false
- products: List of products to show
- display_type: How to display products (list/grid)
- next_step_id: Next step after selection

Only include if product choice is mentioned."""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Extract product choice configuration. Return JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                timeout=self.timeout
            )

            result = response.choices[0].message.content
            return json.loads(result)

        except Exception as e:
            logger.error(f"LLM product choice extraction failed: {e}")
            return ProductChoiceInfo().dict()

    async def extract_property_conditions_llm(self, description: str) -> Dict[str, Any]:
        """Extract property conditions using LLM."""
        try:
            prompt = f"""Extract conditional property logic from this campaign description:

{description}

Return JSON with:
- enabled: true/false
- conditions: Array of conditions with field, operator, value, logical_operator
- match_all: true/false (all conditions must match)
- next_step_id: Next step when conditions are met

Only include if conditional logic is mentioned."""

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Extract property conditions. Return JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                timeout=self.timeout
            )

            result = response.choices[0].message.content
            return json.loads(result)

        except Exception as e:
            logger.error(f"LLM property conditions extraction failed: {e}")
            return PropertyInfo().dict()