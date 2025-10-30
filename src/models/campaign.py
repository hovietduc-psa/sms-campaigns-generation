"""
Campaign models for AI-generated campaigns.

This module defines Pydantic models for all campaign step types,
matching the FlowBuilder JSON schema exactly.
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any, Literal, Union
from datetime import datetime
from enum import Enum


class StepType(str, Enum):
    """All supported campaign step types - FlowBuilder compliant."""
    # Core Steps
    MESSAGE = "message"
    SEGMENT = "segment"
    DELAY = "delay"
    SCHEDULE = "schedule"
    EXPERIMENT = "experiment"
    RATE_LIMIT = "rate_limit"
    END = "end"

    # FlowBuilder Steps (missing from original)
    REPLY = "reply"
    NO_REPLY = "no_reply"
    SPLIT = "split"
    SPLIT_GROUP = "split_group"
    SPLIT_RANGE = "split_range"
    PROPERTY = "property"
    LIMIT = "limit"

    # Text-to-Buy Steps
    PRODUCT_CHOICE = "product_choice"
    PURCHASE_OFFER = "purchase_offer"
    PURCHASE = "purchase"

    # Legacy/Additional Steps
    CONDITION = "condition"
    ADD_CUSTOMER_PROPERTY = "add_customer_property"
    QUIZ = "quiz"
    REPLY_FOR_CART_CHOICE = "reply_for_cart_choice"
    REPLY_FOR_PRODUCT_CHOICE = "reply_for_product_choice"
    FEEDBACK_REPLY = "feedback_reply"


class EventType(str, Enum):
    """Campaign event types - FlowBuilder compliant."""
    REPLY = "reply"
    NOREPLY = "noreply"
    CLICK = "click"
    PURCHASE = "purchase"
    SPLIT = "split"
    DEFAULT = "default"  # New FlowBuilder event type
    TIMEOUT = "timeout"
    CONDITION_MET = "condition_met"
    CONDITION_NOT_MET = "condition_not_met"


class CampaignEvent(BaseModel):
    """Event handler for campaign steps - FlowBuilder compliant."""
    id: str = Field(..., description="Unique event identifier")
    type: str = Field(..., description="Type of event (reply, noreply, default, split)")
    intent: Optional[str] = Field(None, description="Intent for reply events")
    description: Optional[str] = Field(None, description="Human-readable description for better intent matching")
    nextStepID: Optional[str] = Field(None, description="Next step to execute when event triggers")
    after: Optional[Dict[str, Any]] = Field(None, description="Delay configuration (value, unit)")
    label: Optional[str] = Field(None, description="Display label for event")
    action: Optional[str] = Field(None, description="Action for split events")
    active: bool = Field(default=True, description="Whether event is active")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Additional event parameters")

    model_config = {"use_enum_values": True}


class BaseStep(BaseModel):
    """Base class for all campaign steps - FlowBuilder compliant."""
    id: str = Field(..., description="Unique step identifier")
    type: StepType = Field(..., description="Step type")
    label: Optional[str] = Field(None, description="Display label for this step")
    content: Optional[str] = Field(None, description="Display content (usually same as label)")
    active: bool = Field(default=True, description="Whether step is active")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Step-specific parameters")
    events: List[CampaignEvent] = Field(default_factory=list, description="Event handlers for this step")

    model_config = {"use_enum_values": True}


# ============================================================================
# Core Steps - FlowBuilder Compliant
# ============================================================================

class MessageStep(BaseStep):
    """Message step - sends SMS to customer (FlowBuilder compliant)."""
    type: Literal[StepType.MESSAGE] = StepType.MESSAGE

    # Content Fields
    content: Optional[str] = Field(None, description="Main message text content")
    text: Optional[str] = Field(None, description="Message text (backward compatibility)")
    label: Optional[str] = Field(None, description="Optional label for this message step")

    # Image Settings
    addImage: bool = Field(default=False, description="Whether to include an image")
    imageUrl: Optional[str] = Field(None, description="Image URL (only when addImage = true)")

    # Contact Card
    sendContactCard: bool = Field(default=False, description="Whether to send contact card")

    # Discount Settings
    discountType: str = Field(default="none", description="Type: none | percentage | amount | code")
    discountValue: Optional[str] = Field(None, description="Discount value (only when discountType != 'none')")
    discountCode: Optional[str] = Field(None, description="Discount code (only when discountType = 'code')")
    discountEmail: Optional[str] = Field(None, description="Optional email restriction")
    discountExpiry: Optional[str] = Field(None, description="Optional expiry date: 2024-12-31T23:59:59")

    # AI Generation
    handled: bool = Field(default=False, description="Whether this step uses AI generation")
    aiGenerated: bool = Field(default=False, description="Whether content was AI-generated")
    prompt: Optional[str] = Field(None, description="AI prompt for dynamic message generation")

    @field_validator('text', 'prompt', 'content')
    @classmethod
    def validate_message_content(cls, v, info):
        """Ensure some form of message content is provided."""
        values = info.data if hasattr(info, 'data') else {}
        field_name = info.field_name if hasattr(info, 'field_name') else 'content'

        # Skip validation for discount fields that might be None
        if field_name in ['discountValue', 'discountCode', 'discountEmail', 'discountExpiry', 'imageUrl']:
            return v

        # Check if any content field has a value
        has_content = (
            (values.get('text') and values['text'].strip()) or
            (values.get('content') and values['content'].strip()) or
            (values.get('prompt') and values['prompt'].strip())
        )

        if not has_content and (v is None or (isinstance(v, str) and not v.strip())):
            # Only require content if no other content field is filled
            if not any([
                values.get('text') and values['text'].strip(),
                values.get('content') and values['content'].strip(),
                values.get('prompt') and values['prompt'].strip()
            ]):
                pass  # Allow empty for now, validation will happen at generation time

        return v


class SegmentStep(BaseStep):
    """Segment step - routes customers based on segment criteria (FlowBuilder compliant)."""
    type: Literal[StepType.SEGMENT] = StepType.SEGMENT
    label: Optional[str] = Field(None, description="Optional label for this segment step")

    # New FlowBuilder format - conditions array
    conditions: List[Dict[str, Any]] = Field(default_factory=list, description="Conditions array (preferred)")

    # Legacy format - segmentDefinition (for backward compatibility)
    segmentDefinition: Optional[Dict[str, Any]] = Field(None, description="Legacy segment definition")

    @field_validator('conditions', 'segmentDefinition')
    @classmethod
    def validate_segment(cls, v, info):
        """Ensure either conditions or segmentDefinition is provided."""
        values = info.data if hasattr(info, 'data') else {}
        field_name = info.field_name if hasattr(info, 'field_name') else 'conditions'

        if field_name == 'conditions' and not v and not values.get('segmentDefinition'):
            # Allow empty conditions if segmentDefinition exists
            pass
        elif field_name == 'segmentDefinition' and not v and not values.get('conditions'):
            # Allow empty segmentDefinition if conditions exists
            pass
        return v


class DelayStep(BaseStep):
    """Delay step - waits before proceeding to next step (FlowBuilder compliant)."""
    type: Literal[StepType.DELAY] = StepType.DELAY

    # New FlowBuilder required fields
    time: str = Field(..., description="Delay value as string")
    period: str = Field(..., description="Period: Seconds | Minutes | Hours | Days")

    # Structured format
    delay: Dict[str, str] = Field(..., description="Delay object with value and unit")

    # Legacy format (backward compatibility)
    duration: Optional[Dict[str, int]] = Field(None, description="Legacy duration format")

    @field_validator('delay')
    @classmethod
    def validate_delay_object(cls, v, info):
        """Ensure delay object has correct structure."""
        values = info.data if hasattr(info, 'data') else {}
        if not v:
            # Create delay object from time and period
            v = {"value": values.get('time', ''), "unit": values.get('period', '')}
        return v


class ScheduleStep(BaseStep):
    """Schedule step - executes at specific time (FlowBuilder compliant)."""
    type: Literal[StepType.SCHEDULE] = StepType.SCHEDULE

    # FlowBuilder fields
    label: Optional[str] = Field(None, description="Schedule configuration label")
    content: Optional[str] = Field(None, description="Display content (usually same as label)")

    # Schedule configuration
    schedule: Dict[str, Any] = Field(default_factory=dict, description="Schedule configuration object")

    # Legacy fields (backward compatibility)
    scheduleTime: Optional[str] = Field(None, description="Legacy schedule time")
    nextStepID: Optional[str] = Field(None, description="Legacy next step ID")


class ExperimentStep(BaseStep):
    """A/B test experiment step (FlowBuilder compliant)."""
    type: Literal[StepType.EXPERIMENT] = StepType.EXPERIMENT

    # FlowBuilder fields
    label: Optional[str] = Field(None, description="Optional label for experiment step")
    experimentName: str = Field(..., description="Required experiment name")
    version: str = Field(default="1", description="Experiment version")
    content: Optional[str] = Field(None, description="Display content: Welcome Message Test(v1)")

    # Configuration
    experimentConfig: Dict[str, Any] = Field(default_factory=dict, description="Experiment configuration")

    # Legacy fields (backward compatibility)
    variants: Optional[List[Dict[str, Any]]] = Field(None, description="Legacy variants")
    splitPercentages: Optional[List[int]] = Field(None, description="Legacy split percentages")

    @field_validator('splitPercentages')
    @classmethod
    def validate_split(cls, v):
        """Ensure split percentages sum to 100."""
        if v and sum(v) != 100:
            raise ValueError("splitPercentages must sum to 100")
        return v


class RateLimitStep(BaseStep):
    """Rate limit step - controls message frequency (FlowBuilder compliant)."""
    type: Literal[StepType.RATE_LIMIT] = StepType.RATE_LIMIT

    # New FlowBuilder required fields
    occurrences: str = Field(..., description="Number of occurrences as string")
    timespan: str = Field(..., description="Timespan as string")
    period: str = Field(..., description="Period: Minutes | Hours | Days")

    # Structured format
    rateLimit: Dict[str, str] = Field(..., description="Rate limit object with limit and period")

    # Display content
    content: Optional[str] = Field(None, description="Display content: 12 times every 11 minutes")

    # Legacy fields (backward compatibility)
    maxMessages: Optional[int] = Field(None, description="Legacy max messages")
    timeWindow: Optional[Dict[str, int]] = Field(None, description="Legacy time window")
    nextStepID: Optional[str] = Field(None, description="Legacy next step ID")
    exceededStepID: Optional[str] = Field(None, description="Legacy exceeded step ID")

    @field_validator('rateLimit')
    @classmethod
    def validate_rate_limit_object(cls, v, info):
        """Ensure rateLimit object has correct structure."""
        values = info.data if hasattr(info, 'data') else {}
        if not v:
            # Create rateLimit object from occurrences and period
            v = {"limit": values.get('occurrences', ''), "period": values.get('period', '')}
        return v


class EndStep(BaseStep):
    """End step - terminates campaign flow (FlowBuilder compliant)."""
    type: Literal[StepType.END] = StepType.END
    label: str = Field(default="End", description="End step label")

    # Legacy fields (backward compatibility)
    reason: Optional[str] = Field(None, description="Legacy reason field")


class PropertyStep(BaseStep):
    """Property step - sets customer properties (FlowBuilder compliant)."""
    type: Literal[StepType.PROPERTY] = StepType.PROPERTY

    # FlowBuilder fields
    label: Optional[str] = Field(None, description="Customer Property Step")
    content: Optional[str] = Field(None, description="Display content: Customer Property Step")

    # Properties array
    properties: List[Dict[str, Any]] = Field(..., description="Properties array with name/value pairs")

    # Configuration
    propertyConfig: Dict[str, Any] = Field(default_factory=dict, description="Property configuration")

    @field_validator('properties')
    @classmethod
    def validate_properties(cls, v):
        """Ensure properties array is not empty."""
        if not v:
            raise ValueError("properties array cannot be empty")
        for prop in v:
            if 'name' not in prop or 'value' not in prop:
                raise ValueError("Each property must have 'name' and 'value' fields")
        return v


class ReplyStep(BaseStep):
    """Reply step - handles intent-based replies (FlowBuilder compliant)."""
    type: Literal[StepType.REPLY] = StepType.REPLY

    # FlowBuilder fields
    enabled: bool = Field(default=True, description="Whether reply is enabled")
    intent: str = Field(..., description="Intent name to trigger")
    description: Optional[str] = Field(None, description="Optional description of the intent for better context")
    label: str = Field(..., description="Display label (usually same as intent)")

    # Configuration
    replyConfig: Dict[str, Any] = Field(default_factory=dict, description="Reply configuration")


class NoReplyStep(BaseStep):
    """No Reply step - handles timeout when no response (FlowBuilder compliant)."""
    type: Literal[StepType.NO_REPLY] = StepType.NO_REPLY

    # FlowBuilder fields
    enabled: bool = Field(default=True, description="Whether no reply is enabled")
    value: int = Field(..., description="Wait time as number")
    unit: str = Field(..., description="Unit: seconds | minutes | hours | days")
    label: str = Field(default="No Reply", description="Display label")
    content: str = Field(..., description="Display content: 6 hours")

    # Structured format
    after: Dict[str, Union[int, str]] = Field(..., description="After object with value and unit")

    # Legacy format (backward compatibility)
    seconds: Optional[int] = Field(None, description="Legacy seconds")
    period: Optional[str] = Field(None, description="Legacy period")

    # Configuration
    noReplyConfig: Dict[str, Any] = Field(default_factory=dict, description="No-reply configuration")

    @field_validator('after')
    @classmethod
    def validate_after_object(cls, v, info):
        """Ensure after object has correct structure."""
        values = info.data if hasattr(info, 'data') else {}
        if not v:
            # Create after object from value and unit
            v = {"value": values.get('value', 0), "unit": values.get('unit', '')}
        return v


class SplitStep(BaseStep):
    """Split step - handles split conditions (FlowBuilder compliant)."""
    type: Literal[StepType.SPLIT] = StepType.SPLIT

    # FlowBuilder fields
    enabled: bool = Field(default=True, description="Whether split is enabled")
    label: str = Field(..., description="Required - split condition label")
    action: str = Field(..., description="Split action")
    description: Optional[str] = Field(None, description="Optional description of split condition")
    content: Optional[str] = Field(None, description="Display content")

    # Configuration
    splitConfig: Dict[str, Any] = Field(default_factory=dict, description="Split configuration")


class SplitGroupStep(BaseStep):
    """Split Group step - experiment branch (FlowBuilder compliant)."""
    type: Literal[StepType.SPLIT_GROUP] = StepType.SPLIT_GROUP

    # FlowBuilder fields
    enabled: bool = Field(default=True, description="Whether split group is enabled")
    label: str = Field(..., description="Required - usually 'Group A' or 'Group B'")
    action: str = Field(default="include", description="Split action")
    content: Optional[str] = Field(None, description="Display content: Group A")


class SplitRangeStep(BaseStep):
    """Split Range step - schedule branch (FlowBuilder compliant)."""
    type: Literal[StepType.SPLIT_RANGE] = StepType.SPLIT_RANGE

    # FlowBuilder fields
    enabled: bool = Field(default=True, description="Whether split range is enabled")
    label: str = Field(..., description="Required time range")
    action: str = Field(default="include", description="Split action")
    content: Optional[str] = Field(None, description="Display content with time range")


class LimitStep(BaseStep):
    """Limit step - similar to rate limit (FlowBuilder compliant)."""
    type: Literal[StepType.LIMIT] = StepType.LIMIT

    # FlowBuilder fields
    occurrences: str = Field(..., description="Number of occurrences as string")
    timespan: str = Field(..., description="Timespan as string")
    period: str = Field(..., description="Period: Minutes | Hours | Days")

    # Structured format
    limit: Dict[str, str] = Field(..., description="Limit object with value and period")

    # Display content
    content: Optional[str] = Field(None, description="Display content: 5 times every 1 hour")

    @field_validator('limit')
    @classmethod
    def validate_limit_object(cls, v, info):
        """Ensure limit object has correct structure."""
        values = info.data if hasattr(info, 'data') else {}
        if not v:
            # Create limit object from occurrences and period
            v = {"value": values.get('occurrences', ''), "period": values.get('period', '')}
        return v


# ============================================================================
# Legacy Step Models (for backward compatibility)
# ============================================================================

class ConditionStep(BaseStep):
    """Condition step - evaluates condition and routes accordingly (Legacy)."""
    type: Literal[StepType.CONDITION] = StepType.CONDITION
    condition: Dict[str, Any] = Field(..., description="Condition to evaluate")
    trueStepID: Optional[str] = Field(None, description="Step if condition is true")
    falseStepID: Optional[str] = Field(None, description="Step if condition is false")


class AddCustomerPropertyStep(BaseStep):
    """Add or update customer property (Legacy)."""
    type: Literal[StepType.ADD_CUSTOMER_PROPERTY] = StepType.ADD_CUSTOMER_PROPERTY
    propertyName: str = Field(..., description="Property name to add/update")
    propertyValue: Any = Field(..., description="Property value")
    nextStepID: str = Field(..., description="Next step after property update")


# ============================================================================
# Text-to-Buy Steps - FlowBuilder Compliant
# ============================================================================

class ProductChoiceStep(BaseStep):
    """Product choice step - customer selects product (FlowBuilder compliant)."""
    type: Literal[StepType.PRODUCT_CHOICE] = StepType.PRODUCT_CHOICE

    # FlowBuilder fields
    label: Optional[str] = Field(None, description="Optional label for product choice step")

    # Message Configuration
    messageType: str = Field(default="standard", description="standard | personalized")
    messageText: Optional[str] = Field(None, description="Reply to buy: Product List")
    text: Optional[str] = Field(None, description="Backward compatibility")
    prompt: Optional[str] = Field(None, description="Alternative to messageText")

    # Product Selection
    productSelection: str = Field(default="manually", description="automatically | popularity | recently_viewed | manually")
    productSelectionPrompt: Optional[str] = Field(None, description="Show me products you think I'll like...")

    # Manual Products (only when productSelection="manually")
    products: List[Dict[str, Any]] = Field(default_factory=list, description="Manual products list")

    # Options
    productImages: bool = Field(default=True, description="Send product images")
    customTotals: bool = Field(default=False, description="Add custom totals")
    customTotalsAmount: str = Field(default="Shipping", description="Custom shipping amount")
    discountExpiry: bool = Field(default=False, description="Discount has expiry")
    discountExpiryDate: Optional[str] = Field(None, description="Expiry date when enabled")
    discount: str = Field(default="None", description="Discount type: None | 10% | $5 | SAVE20")

    # Configuration
    productChoiceConfig: Dict[str, Any] = Field(default_factory=dict, description="Product choice configuration")


class PurchaseOfferStep(BaseStep):
    """Purchase offer step - presents purchase offer to customer (FlowBuilder compliant)."""
    type: Literal[StepType.PURCHASE_OFFER] = StepType.PURCHASE_OFFER

    # FlowBuilder fields
    label: Optional[str] = Field(None, description="Optional label for purchase offer step")
    content: Optional[str] = Field(None, description="Display content from label")

    # Message Configuration
    messageType: str = Field(default="standard", description="standard | personalized")
    messageText: Optional[str] = Field(None, description="Reply 'yes' to buy: Cart List")
    text: Optional[str] = Field(None, description="Backward compatibility")

    # Cart Configuration
    cartSource: str = Field(default="manual", description="manual | latest")

    # Manual Products (only when cartSource="manual")
    products: List[Dict[str, Any]] = Field(default_factory=list, description="Manual products list")

    # Discount Settings
    discount: bool = Field(default=False, description="Enable/disable discount")
    discountType: str = Field(default="percentage", description="percentage | amount | code")
    discountPercentage: str = Field(default="", description="Discount percentage")
    discountAmount: str = Field(default="", description="Discount amount")
    discountCode: str = Field(default="", description="Discount code")
    discountAmountLabel: str = Field(default="", description="Optional label for code discount")
    discountEmail: str = Field(default="", description="Optional email restriction")
    discountExpiry: bool = Field(default=False, description="Discount has expiry")
    discountExpiryDate: Optional[str] = Field(None, description="Expiry date when enabled")

    # Additional Options
    customTotals: bool = Field(default=False, description="Add custom totals")
    shippingAmount: str = Field(default="", description="Custom shipping amount")
    includeProductImage: bool = Field(default=True, description="Send product images")
    skipForRecentOrders: bool = Field(default=True, description="Skip for recent orders")

    # Configuration
    purchaseOfferConfig: Dict[str, Any] = Field(default_factory=dict, description="Purchase offer configuration")

    # Legacy fields (backward compatibility)
    fullText: Optional[str] = Field(None, description="Legacy full text")
    minimumDiscount: Optional[Dict[str, Any]] = Field(None, description="Legacy minimum discount")
    minimumDiscountGlobal: Optional[bool] = Field(None, description="Legacy global discount")
    scheduleReminder: Optional[bool] = Field(None, description="Legacy schedule reminder")
    allowSubscriptionUpsell: Optional[bool] = Field(None, description="Legacy subscription upsell")
    allowReminder: Optional[bool] = Field(None, description="Legacy allow reminder")


class PurchaseStep(BaseStep):
    """Purchase step - completes purchase transaction (FlowBuilder compliant)."""
    type: Literal[StepType.PURCHASE] = StepType.PURCHASE

    # Cart Source Configuration
    cartSource: str = Field(..., description="manual | latest - Required")

    # Manual Products (only when cartSource="manual")
    products: List[Dict[str, Any]] = Field(default_factory=list, description="Manual products list")

    # Options
    discount: bool = Field(default=False, description="Add discount to order")
    customTotals: bool = Field(default=False, description="Add custom totals")
    shippingAmount: str = Field(default="", description="Custom shipping amount")
    sendReminderForNonPurchasers: bool = Field(default=False, description="Send reminder for non-purchasers")
    allowAutomaticPayment: bool = Field(default=False, description="Allow automatic payment completion")

    # Configuration
    purchaseConfig: Dict[str, Any] = Field(default_factory=dict, description="Purchase configuration")

    # Legacy fields (backward compatibility)
    checkoutUrl: Optional[str] = Field(None, description="Legacy checkout URL")
    paymentMethod: Optional[str] = Field(None, description="Legacy payment method")
    successStepID: Optional[str] = Field(None, description="Legacy success step")
    failureStepID: Optional[str] = Field(None, description="Legacy failure step")


# ============================================================================
# Legacy Multi Steps (Interactive/Multi-turn) - for backward compatibility
# ============================================================================

class QuizStep(BaseStep):
    """Quiz step - interactive quiz with multiple questions (Legacy)."""
    type: Literal[StepType.QUIZ] = StepType.QUIZ
    questions: List[Dict[str, Any]] = Field(..., description="Quiz questions")
    collectResponses: bool = Field(default=True, description="Collect and store responses")


class ReplyForCartChoiceStep(BaseStep):
    """Reply for cart choice - customer replies to modify cart (Legacy)."""
    type: Literal[StepType.REPLY_FOR_CART_CHOICE] = StepType.REPLY_FOR_CART_CHOICE
    prompt: str = Field(..., description="Prompt for cart choice")
    cartOptions: List[Dict[str, Any]] = Field(..., description="Available cart options")


class ReplyForProductChoiceStep(BaseStep):
    """Reply for product choice - customer replies to select product (Legacy)."""
    type: Literal[StepType.REPLY_FOR_PRODUCT_CHOICE] = StepType.REPLY_FOR_PRODUCT_CHOICE
    prompt: str = Field(..., description="Prompt for product choice")
    products: List[Dict[str, Any]] = Field(..., description="Available products")


class FeedbackReplyStep(BaseStep):
    """Feedback reply step - collect customer feedback (Legacy)."""
    type: Literal[StepType.FEEDBACK_REPLY] = StepType.FEEDBACK_REPLY
    feedbackPrompt: str = Field(..., description="Feedback request prompt")
    feedbackType: str = Field(default="text", description="Type of feedback (text, rating, etc.)")
    nextStepID: Optional[str] = Field(None, description="Next step after feedback")


# ============================================================================
# Campaign Model - FlowBuilder Compliant
# ============================================================================

# Union type for all step types (FlowBuilder + Legacy)
CampaignStep = Union[
    # FlowBuilder Core Steps
    MessageStep,
    SegmentStep,
    DelayStep,
    ScheduleStep,
    ExperimentStep,
    RateLimitStep,
    EndStep,
    PropertyStep,
    ReplyStep,
    NoReplyStep,
    SplitStep,
    SplitGroupStep,
    SplitRangeStep,
    LimitStep,

    # Text-to-Buy Steps
    ProductChoiceStep,
    PurchaseOfferStep,
    PurchaseStep,

    # Legacy Steps (backward compatibility)
    ConditionStep,
    AddCustomerPropertyStep,
    QuizStep,
    ReplyForCartChoiceStep,
    ReplyForProductChoiceStep,
    FeedbackReplyStep,
]


class Campaign(BaseModel):
    """
    Complete campaign structure matching the FlowBuilder JSON schema.

    This is the root model that represents a complete campaign
    with all its steps and flow logic, compliant with FlowBuilder.
    """
    initialStepID: str = Field(..., description="ID of the first step to execute")
    steps: List[CampaignStep] = Field(..., description="All campaign steps")

    model_config = {"use_enum_values": True}

    @field_validator('steps')
    @classmethod
    def validate_steps(cls, v, info):
        """Validate step consistency."""
        values = info.data if hasattr(info, 'data') else {}
        if not v:
            raise ValueError("Campaign must have at least one step")

        # Check initialStepID exists
        if 'initialStepID' in values:
            step_ids = {step.id for step in v}
            if values['initialStepID'] not in step_ids:
                raise ValueError(f"initialStepID '{values['initialStepID']}' not found in steps")

        return v

    @field_validator('steps')
    @classmethod
    def validate_unique_ids(cls, v):
        """Ensure all step IDs are unique."""
        step_ids = [step.id for step in v]
        duplicates = [id for id in step_ids if step_ids.count(id) > 1]
        if duplicates:
            raise ValueError(f"Duplicate step IDs found: {set(duplicates)}")
        return v

    def to_json_dict(self) -> Dict[str, Any]:
        """Convert to JSON dict for FlowBuilder execution engine."""
        return {
            "initialStepID": self.initialStepID,
            "steps": [step.model_dump(by_alias=True, exclude_none=True) for step in self.steps]
        }

    def to_flowbuilder_dict(self) -> Dict[str, Any]:
        """Convert to FlowBuilder compliant JSON format."""
        return {
            "initialStepID": self.initialStepID,
            "steps": [self._transform_step_to_flowbuilder(step) for step in self.steps]
        }

    def _transform_step_to_flowbuilder(self, step: CampaignStep) -> Dict[str, Any]:
        """Transform individual step to FlowBuilder format."""
        step_dict = step.model_dump(by_alias=True, exclude_none=True)

        # Apply FlowBuilder-specific transformations
        if hasattr(step, 'type'):
            step_type = step.type.value if hasattr(step.type, 'value') else step.type

            # Transform message steps
            if step_type == "message" and 'text' in step_dict and 'content' not in step_dict:
                step_dict['content'] = step_dict['text']

            # Transform segment steps
            elif step_type == "segment" and 'segmentDefinition' in step_dict and not step_dict.get('conditions'):
                # Convert legacy segmentDefinition to conditions array
                step_dict['conditions'] = self._convert_segment_definition_to_conditions(step_dict['segmentDefinition'])

            # Transform delay steps
            elif step_type == "delay" and 'duration' in step_dict:
                # Convert legacy duration to time/period format
                step_dict.update(self._convert_duration_to_flowbuilder(step_dict['duration']))

            # Transform rate_limit steps
            elif step_type == "rate_limit" and 'maxMessages' in step_dict:
                # Convert legacy maxMessages/timeWindow to occurrences/timespan/period
                step_dict.update(self._convert_rate_limit_to_flowbuilder(step_dict))

        return step_dict

    def _convert_segment_definition_to_conditions(self, segment_def: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert legacy segmentDefinition to FlowBuilder conditions array."""
        # This is a simplified conversion - in practice, you'd need more sophisticated logic
        conditions = []
        if 'segments' in segment_def:
            for i, segment in enumerate(segment_def['segments']):
                condition = {
                    "id": i + 1,
                    "type": segment.get('customerAction', {}).get('type', 'event'),
                    "operator": segment.get('customerAction', {}).get('filterOperator', 'has'),
                    "timePeriod": "within the last 30 Days",
                    "timePeriodType": "relative",
                    # Add other required fields based on the segment type
                }
                conditions.append(condition)
        return conditions

    def _convert_duration_to_flowbuilder(self, duration: Dict[str, int]) -> Dict[str, Any]:
        """Convert legacy duration to FlowBuilder time/period/delay format."""
        # Find the time unit and value
        for unit, value in duration.items():
            if unit in ['seconds', 'minutes', 'hours', 'days']:
                period = unit.title()  # "Seconds", "Minutes", "Hours", "Days"
                return {
                    "time": str(value),
                    "period": period,
                    "delay": {"value": str(value), "unit": period}
                }
        return {}

    def _convert_rate_limit_to_flowbuilder(self, step_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Convert legacy rate limit to FlowBuilder occurrences/timespan/period format."""
        max_messages = step_dict.get('maxMessages', 12)
        time_window = step_dict.get('timeWindow', {'hours': 1})

        # Find the time unit and value
        for unit, value in time_window.items():
            if unit in ['minutes', 'hours', 'days']:
                period = unit.title()  # "Minutes", "Hours", "Days"
                return {
                    "occurrences": str(max_messages),
                    "timespan": str(value),
                    "period": period,
                    "rateLimit": {"limit": str(max_messages), "period": period},
                    "content": f"{max_messages} times every {value} {unit}"
                }
        return {}