"""
FlowBuilder schema models for SMS campaign generation.

This module contains comprehensive Pydantic models for all FlowBuilder node types
based on the format_json_flowbuilder.md specification.
"""

from typing import Any, Dict, List, Literal, Optional, Union
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class NodeType(str, Enum):
    """Node type enumeration for FlowBuilder compatibility."""
    MESSAGE = "message"
    SEGMENT = "segment"
    DELAY = "delay"
    SCHEDULE = "schedule"
    EXPERIMENT = "experiment"
    RATE_LIMIT = "rate_limit"
    REPLY = "reply"
    NO_REPLY = "no_reply"
    SPLIT = "split"
    SPLIT_GROUP = "split_group"
    SPLIT_RANGE = "split_range"
    PROPERTY = "property"
    PRODUCT_CHOICE = "product_choice"
    PURCHASE_OFFER = "purchase_offer"
    PURCHASE = "purchase"
    LIMIT = "limit"
    END = "end"


class DiscountType(str, Enum):
    """Discount type enumeration."""
    NONE = "none"
    PERCENTAGE = "percentage"
    AMOUNT = "amount"
    CODE = "code"


class TimePeriod(str, Enum):
    """Time period enumeration."""
    SECONDS = "Seconds"
    MINUTES = "Minutes"
    HOURS = "Hours"
    DAYS = "Days"


class MessageType(str, Enum):
    """Message type enumeration."""
    STANDARD = "standard"
    PERSONALIZED = "personalized"


class ProductSelectionType(str, Enum):
    """Product selection type enumeration."""
    AUTOMATICALLY = "automatically"
    POPULARITY = "popularity"
    RECENTLY_VIEWED = "recently_viewed"
    MANUALLY = "manually"


class CartSourceType(str, Enum):
    """Cart source type enumeration."""
    MANUAL = "manual"
    LATEST = "latest"


class ConditionType(str, Enum):
    """Condition type enumeration."""
    EVENT = "event"
    PROPERTY = "property"
    REFILL = "refill"


class ConditionOperator(str, Enum):
    """Condition operator enumeration."""
    HAS = "has"
    HAS_NOT = "has_not"


class EventAction(str, Enum):
    """Event action enumeration."""
    PLACED_ORDER = "placed_order"
    CLICKED_LINK = "clicked_link"
    VIEWED_PRODUCT = "viewed_product"
    ADDED_PRODUCT_TO_CART = "added_product_to_cart"
    STARTED_CHECKOUT = "started_checkout"


class PropertyOperator(str, Enum):
    """Property operator enumeration."""
    EXISTS = "that exists"
    DOES_NOT_EXIST = "does not exist"
    WITH_VALUE = "with a value of"
    WITH_VALUE_NOT_EQUAL = "with a value not equal to"
    WITH_VALUE_CONTAINING = "with a value containing"
    WITH_VALUE_NOT_CONTAINING = "with a value not containing"


# Event Models
class BaseEvent(BaseModel):
    """Base event model for all node types."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: Literal["reply", "noreply", "no_reply", "default", "split"]
    nextStepID: Optional[str] = None

    # Reply event fields
    intent: Optional[str] = None
    description: Optional[str] = None

    # NoReply event fields
    after: Optional[Dict[str, Any]] = None

    # Split event fields
    label: Optional[str] = None
    action: Optional[str] = None

    active: bool = True
    parameters: Dict[str, Any] = Field(default_factory=dict)


# Node Models
class BaseNode(BaseModel):
    """Base node model for all FlowBuilder node types."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: str
    active: bool = True
    parameters: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        """Pydantic configuration."""
        extra = "allow"  # Allow extra fields for different node types


# Condition Models
class TimeSettings(BaseModel):
    """Time settings for conditions."""
    timePeriod: str = "within the last 30 Days"
    timePeriodType: str = "relative"
    customTimeValue: Optional[str] = None
    customTimeUnit: Optional[TimePeriod] = None
    showTimePeriodOptions: bool = False


class SegmentCondition(BaseModel):
    """Segment condition model."""
    id: int
    type: ConditionType
    operator: ConditionOperator

    # Event condition fields
    action: Optional[EventAction] = None
    filter: Optional[str] = None

    # Property condition fields
    propertyName: Optional[str] = None
    propertyValue: Optional[str] = None
    propertyOperator: Optional[PropertyOperator] = None
    showPropertyValueInput: bool = False
    showPropertyOperatorOptions: bool = False

    # Time settings
    timeSettings: Optional[TimeSettings] = None

    # Display settings
    filterTab: Optional[str] = None
    cartFilterTab: Optional[str] = None
    optInFilterTab: Optional[str] = None
    showFilterOptions: bool = False
    showLinkFilterOptions: bool = False
    showCartFilterOptions: bool = False
    showOptInFilterOptions: bool = False
    filterData: Optional[Any] = None


# FlowBuilder Node Models
class MessageNode(BaseNode):
    """MESSAGE node - for sending messages."""
    type: Literal["message"] = "message"

    # Content fields
    content: str
    text: Optional[str] = None  # Backward compatibility
    label: Optional[str] = None

    # Image settings
    addImage: bool = False
    imageUrl: Optional[str] = None

    # Contact card
    sendContactCard: bool = False

    # Discount settings
    discountType: DiscountType = DiscountType.NONE
    discountValue: str = ""
    discountCode: str = ""
    discountEmail: str = ""
    discountExpiry: Optional[str] = None

    # Status fields
    handled: bool = False
    aiGenerated: bool = False

    # Events
    events: List[BaseEvent] = Field(default_factory=list)


class SegmentNode(BaseNode):
    """SEGMENT node - for customer segmentation."""
    type: Literal["segment"] = "segment"

    # Basic fields
    label: Optional[str] = None

    # Conditions
    conditions: List[SegmentCondition] = Field(default_factory=list)

    # Legacy format
    segmentDefinition: Optional[Dict[str, Any]] = None

    # Events
    events: List[BaseEvent] = Field(default_factory=list)


class DelayNode(BaseNode):
    """DELAY node - for time delays."""
    type: Literal["delay"] = "delay"

    # Basic fields
    time: str
    period: TimePeriod

    # Structured format
    delay: Optional[Dict[str, str]] = None

    # Events
    events: List[BaseEvent] = Field(default_factory=list)


class ScheduleNode(BaseNode):
    """SCHEDULE node - for scheduled actions."""
    type: Literal["schedule"] = "schedule"

    # Basic fields
    label: Optional[str] = None
    content: Optional[str] = None

    # Configuration
    schedule: Optional[Dict[str, Any]] = None

    # Events
    events: List[BaseEvent] = Field(default_factory=list)


class ExperimentNode(BaseNode):
    """EXPERIMENT node - for A/B testing."""
    type: Literal["experiment"] = "experiment"

    # Basic fields
    label: Optional[str] = None
    experimentName: str
    version: str = "1"
    content: Optional[str] = None

    # Configuration
    experimentConfig: Optional[Dict[str, Any]] = None

    # Events
    events: List[BaseEvent] = Field(default_factory=list)


class RateLimitNode(BaseNode):
    """RATE_LIMIT node - for rate limiting."""
    type: Literal["rate_limit"] = "rate_limit"

    # Basic fields
    occurrences: str
    timespan: str
    period: TimePeriod

    # Structured format
    rateLimit: Optional[Dict[str, str]] = None

    content: Optional[str] = None

    # Events
    events: List[BaseEvent] = Field(default_factory=list)


class ReplyNode(BaseNode):
    """REPLY node - for reply handling."""
    type: Literal["reply"] = "reply"

    # Basic fields
    enabled: bool = True
    intent: str
    description: Optional[str] = None
    label: str

    # Configuration
    replyConfig: Optional[Dict[str, Any]] = None

    # Events
    events: List[BaseEvent] = Field(default_factory=list)


class NoReplyNode(BaseNode):
    """NO_REPLY node - for handling no reply."""
    type: Literal["no_reply"] = "no_reply"

    # Basic fields
    enabled: bool = True
    value: int
    unit: str  # "seconds", "minutes", "hours", "days"
    label: str = "No Reply"
    content: Optional[str] = None

    # Structured format
    after: Optional[Dict[str, Any]] = None

    # Legacy format
    seconds: Optional[int] = None
    period: Optional[str] = None

    # Configuration
    noReplyConfig: Optional[Dict[str, Any]] = None

    # Events
    events: List[BaseEvent] = Field(default_factory=list)


class SplitNode(BaseNode):
    """SPLIT node - for split conditions."""
    type: Literal["split"] = "split"

    # Basic fields
    enabled: bool = True
    label: str
    action: str
    description: Optional[str] = None
    content: Optional[str] = None

    # Configuration
    splitConfig: Optional[Dict[str, Any]] = None

    # Events
    events: List[BaseEvent] = Field(default_factory=list)


class SplitGroupNode(BaseNode):
    """SPLIT_GROUP node - experiment branch."""
    type: Literal["split_group"] = "split_group"

    # Basic fields
    enabled: bool = True
    label: str
    action: str = "include"
    content: Optional[str] = None

    # Events
    events: List[BaseEvent] = Field(default_factory=list)


class SplitRangeNode(BaseNode):
    """SPLIT_RANGE node - schedule branch."""
    type: Literal["split_range"] = "split_range"

    # Basic fields
    enabled: bool = True
    label: str
    action: str = "include"
    content: Optional[str] = None

    # Events
    events: List[BaseEvent] = Field(default_factory=list)


class PropertyNode(BaseNode):
    """PROPERTY node - for customer properties."""
    type: Literal["property"] = "property"

    # Basic fields
    label: str
    content: Optional[str] = None

    # Properties array
    properties: List[Dict[str, Any]] = Field(default_factory=list)

    # Configuration
    propertyConfig: Optional[Dict[str, Any]] = None

    # Events
    events: List[BaseEvent] = Field(default_factory=list)


class ProductChoiceNode(BaseNode):
    """PRODUCT_CHOICE node - for product selection."""
    type: Literal["product_choice"] = "product_choice"

    # Basic fields
    label: Optional[str] = None

    # Message configuration
    messageType: MessageType = MessageType.STANDARD
    messageText: str
    text: Optional[str] = None  # Backward compatibility
    prompt: Optional[str] = None

    # Product selection
    productSelection: ProductSelectionType = ProductSelectionType.MANUALLY
    productSelectionPrompt: Optional[str] = None

    # Manual products
    products: List[Dict[str, Any]] = Field(default_factory=list)

    # Options
    productImages: bool = True
    customTotals: bool = False
    customTotalsAmount: str = "Shipping"
    discountExpiry: bool = False
    discountExpiryDate: Optional[str] = None
    discount: str = "None"

    # Configuration
    productChoiceConfig: Optional[Dict[str, Any]] = None

    # Events
    events: List[BaseEvent] = Field(default_factory=list)


class PurchaseOfferNode(BaseNode):
    """PURCHASE_OFFER node - for purchase offers."""
    type: Literal["purchase_offer"] = "purchase_offer"

    # Basic fields
    label: Optional[str] = None
    content: Optional[str] = None

    # Message configuration
    messageType: MessageType = MessageType.STANDARD
    messageText: str
    text: Optional[str] = None  # Backward compatibility

    # Cart configuration
    cartSource: CartSourceType = CartSourceType.MANUAL

    # Manual products
    products: List[Dict[str, Any]] = Field(default_factory=list)

    # Discount settings
    discount: bool = False
    discountType: DiscountType = DiscountType.NONE
    discountPercentage: str = ""
    discountAmount: str = ""
    discountCode: str = ""
    discountAmountLabel: str = ""
    discountEmail: str = ""
    discountExpiry: bool = False
    discountExpiryDate: Optional[str] = None

    # Additional options
    customTotals: bool = False
    shippingAmount: str = ""
    includeProductImage: bool = True
    skipForRecentOrders: bool = False

    # Configuration
    purchaseOfferConfig: Optional[Dict[str, Any]] = None

    # Events
    events: List[BaseEvent] = Field(default_factory=list)


class PurchaseNode(BaseNode):
    """PURCHASE node - for direct purchases."""
    type: Literal["purchase"] = "purchase"

    # Cart source configuration
    cartSource: CartSourceType = CartSourceType.MANUAL

    # Manual products
    products: List[Dict[str, Any]] = Field(default_factory=list)

    # Options
    discount: bool = False
    customTotals: bool = False
    shippingAmount: str = ""
    sendReminderForNonPurchasers: bool = False
    allowAutomaticPayment: bool = False

    # Configuration
    purchaseConfig: Optional[Dict[str, Any]] = None

    # Events
    events: List[BaseEvent] = Field(default_factory=list)


class LimitNode(BaseNode):
    """LIMIT node - for usage limits."""
    type: Literal["limit"] = "limit"

    # Basic fields
    occurrences: str
    timespan: str
    period: TimePeriod

    # Structured format
    limit: Optional[Dict[str, str]] = None

    content: Optional[str] = None

    # Events
    events: List[BaseEvent] = Field(default_factory=list)


class EndNode(BaseNode):
    """END node - workflow termination."""
    type: Literal["end"] = "end"

    # Basic fields
    label: str = "End"

    # Events - end node has no events
    events: List[BaseEvent] = Field(default_factory=list)


# Generic step for fallback
class GenericNode(BaseNode):
    """Generic node for unknown types."""
    type: str
    events: List[BaseEvent] = Field(default_factory=list)


# Main Campaign Flow Model
class CampaignFlow(BaseModel):
    """Main campaign flow model matching FlowBuilder format."""
    initialStepID: str
    steps: List[Union[
        MessageNode,
        SegmentNode,
        DelayNode,
        ScheduleNode,
        ExperimentNode,
        RateLimitNode,
        ReplyNode,
        NoReplyNode,
        SplitNode,
        SplitGroupNode,
        SplitRangeNode,
        PropertyNode,
        ProductChoiceNode,
        PurchaseOfferNode,
        PurchaseNode,
        LimitNode,
        EndNode,
        GenericNode  # Fallback for unknown step types
    ]]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    version: str = "1.0"
    active: bool = True

    @model_validator(mode='before')
    @classmethod
    def validate_initial_step_exists(cls, data):
        """Validate that the initial step exists in the steps list."""
        if isinstance(data, dict):
            initial_step_id = data.get('initialStepID')
            steps = data.get('steps', [])

            if not initial_step_id:
                raise ValueError("initialStepID is required")

            step_ids = [step.get('id') for step in steps if isinstance(step, dict)]
            if initial_step_id not in step_ids:
                raise ValueError(f"Initial step '{initial_step_id}' not found in steps")

        return data

    @model_validator(mode='before')
    @classmethod
    def validate_unique_step_ids(cls, data):
        """Validate that all step IDs are unique."""
        if isinstance(data, dict):
            steps = data.get('steps', [])
            step_ids = []

            for step in steps:
                if isinstance(step, dict):
                    step_id = step.get('id')
                    if step_id in step_ids:
                        raise ValueError(f"Duplicate step ID: {step_id}")
                    step_ids.append(step_id)

        return data

    def get_step_by_id(self, step_id: str) -> Optional[Union[MessageNode, SegmentNode, DelayNode, ScheduleNode, ExperimentNode, RateLimitNode, ReplyNode, NoReplyNode, SplitNode, SplitGroupNode, SplitRangeNode, PropertyNode, ProductChoiceNode, PurchaseOfferNode, PurchaseNode, LimitNode, EndNode, GenericNode]]:
        """Get a step by its ID."""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def get_next_step(self, current_step_id: str) -> Optional[Union[MessageNode, SegmentNode, DelayNode, ScheduleNode, ExperimentNode, RateLimitNode, ReplyNode, NoReplyNode, SplitNode, SplitGroupNode, SplitRangeNode, PropertyNode, ProductChoiceNode, PurchaseOfferNode, PurchaseNode, LimitNode, EndNode, GenericNode]]:
        """Get the next step in the flow."""
        current_step = self.get_step_by_id(current_step_id)
        if current_step:
            # Look through events to find the next step
            for event in current_step.events:
                if event.nextStepID:
                    return self.get_step_by_id(event.nextStepID)
        return None

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Serialize the campaign flow to a dictionary."""
        return super().model_dump(**kwargs)

