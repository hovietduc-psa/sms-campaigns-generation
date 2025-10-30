# FlowBuilder Schema Compliance Implementation Plan

## Overview

This document outlines a comprehensive plan to make the SMS campaign generation system fully compliant with the schema defined in `format_json_flowbuilder.md`.

## Phase 1: Schema Analysis & Gap Identification

### Current State vs. Required Schema Analysis

#### Major Gaps Identified:

1. **Missing Step Types** in current `campaign.py`:
   - `REPLY` - Missing entirely (required for intent-based replies)
   - `NO_REPLY` - Missing entirely (required for timeout handling)
   - `SPLIT` - Present but incomplete structure
   - `SPLIT_GROUP` - Missing (required for experiment branches)
   - `SPLIT_RANGE` - Missing (required for schedule branches)
   - `PROPERTY` - Current `ADD_CUSTOMER_PROPERTY` has different structure

2. **Field Structure Mismatches**:
   - **MESSAGE**: Missing `content`, `label`, `addImage`, `imageUrl`, `sendContactCard`, discount fields
   - **SEGMENT**: Uses `segmentDefinition` instead of required `conditions` array
   - **DELAY**: Uses `duration` object instead of required `time`/`period` fields and `delay` object
   - **RATE_LIMIT**: Uses `maxMessages`/`timeWindow` instead of required `occurrences`/`timespan`/`period`
   - **EXPERIMENT**: Missing `experimentName`, `version`, `content` fields
   - **SCHEDULE**: Missing `label`, `content` fields
   - **END**: Missing `label` field

3. **Event Structure Issues**:
   - Missing `default` event type
   - Event field structure doesn't match required schema
   - Reply events missing `description` field

4. **Missing Structured Objects**:
   - Message: `discount` object with expiry, email restrictions
   - Delay: `delay` object with value/unit
   - RateLimit: `rateLimit` object with limit/period
   - NoReply: `after` object with value/unit
   - Products: Missing many required fields for text-to-buy steps

## Phase 2: Implementation Strategy

### Step 1: Update Data Models (campaign.py)

#### Priority 1: Core Field Updates
- Add missing fields to existing step models
- Update field types to match schema exactly
- Add backward compatibility layers
- Implement proper validators

#### Priority 2: Missing Step Types
- Add `ReplyStep`, `NoReplyStep`, `SplitStep`, `PropertyStep`
- Add `SplitGroupStep`, `SplitRangeStep` for automatic generation
- Update existing step models with complete field sets

#### Priority 3: Event System Overhaul
- Update `CampaignEvent` model to match schema
- Add support for `default` event type
- Add all required fields per event type

### Step 2: Create Transformation Layer

#### Schema Transformer Service:
```python
# src/services/campaign_transformation/schema_transformer.py
class SchemaTransformer:
    """Transforms current campaign models to FlowBuilder schema format"""

    def transform_campaign(self, campaign: Campaign) -> Dict[str, Any]:
        """Convert Campaign model to FlowBuilder JSON format"""

    def transform_step(self, step: CampaignStep) -> Dict[str, Any]:
        """Transform individual step to schema format"""

    def transform_events(self, events: List[CampaignEvent]) -> List[Dict[str, Any]]:
        """Transform events to match schema"""
```

### Step 3: Update Generation Pipeline

#### Planner Updates:
- Update planning prompts to include new schema requirements
- Generate campaigns using new field structures
- Ensure backward compatibility during transition

#### Generator Updates:
- Update content generation to populate new fields
- Generate proper event structures
- Create discount objects, structured time objects, etc.

### Step 4: Update Validation System

#### Schema Validator Enhancement:
- Add validation for new required fields
- Validate field types match schema exactly
- Ensure event structure compliance
- Add FlowBuilder-specific validation rules

## Phase 3: Detailed Implementation Tasks

### Task 1: Campaign Model Updates (2-3 days)

#### Updates needed in src/models/campaign.py:

```python
class MessageStep(BaseStep):
    # Add new fields
    content: Optional[str] = Field(None)  # Primary display field
    label: Optional[str] = Field(None)
    addImage: bool = Field(default=False)
    imageUrl: Optional[str] = Field(None)
    sendContactCard: bool = Field(default=False)

    # Discount fields
    discountType: str = Field(default="none")
    discountValue: Optional[str] = Field(None)
    discountCode: Optional[str] = Field(None)
    discountEmail: Optional[str] = Field(None)
    discountExpiry: Optional[str] = Field(None)

class SegmentStep(BaseStep):
    # Replace segmentDefinition with conditions array
    conditions: List[Dict[str, Any]] = Field(default_factory=list)
    label: Optional[str] = Field(None)

    # Keep for backward compatibility
    segmentDefinition: Optional[Dict[str, Any]] = Field(None)

class DelayStep(BaseStep):
    # New required fields
    time: str = Field(...)  # delay value as string
    period: str = Field(...)  # "Seconds" | "Minutes" | "Hours" | "Days"

    # Structured format
    delay: Dict[str, str] = Field(...)

    # Backward compatibility
    duration: Optional[Dict[str, int]] = Field(None)
```

### Task 2: New Step Types (2 days)

```python
class ReplyStep(BaseStep):
    type: Literal[StepType.REPLY] = StepType.REPLY
    enabled: bool = Field(default=True)
    intent: str = Field(...)
    description: Optional[str] = Field(None)
    label: str = Field(...)
    replyConfig: Dict[str, Any] = Field(default_factory=dict)

class NoReplyStep(BaseStep):
    type: Literal[StepType.NO_REPLY] = StepType.NO_REPLY
    enabled: bool = Field(default=True)
    value: int = Field(...)
    unit: str = Field(...)  # "seconds" | "minutes" | "hours" | "days"
    label: str = Field(default="No Reply")
    content: str = Field(...)

    # Structured format
    after: Dict[str, Union[int, str]] = Field(...)

    # Legacy format
    seconds: Optional[int] = Field(None)
    period: Optional[str] = Field(None)
```

### Task 3: Event Model Updates (1 day)

```python
class CampaignEvent(BaseModel):
    id: str
    type: str  # "reply" | "noreply" | "default" | "split"
    intent: Optional[str] = None
    description: Optional[str] = None
    nextStepID: Optional[str] = None
    after: Optional[Dict[str, Any]] = None
    label: Optional[str] = None
    action: Optional[str] = None
    active: bool = True
    parameters: Dict[str, Any] = Field(default_factory=dict)
```

### Task 4: Schema Transformation Service (2 days)

```python
class SchemaTransformer:
    def __init__(self):
        self.field_mappings = {
            'message': {
                'text': 'content',  # Map text to content
                # Add other mappings
            }
        }

    def transform_to_flowbuilder_format(self, campaign: Campaign) -> Dict[str, Any]:
        """Main transformation method"""
        transformed_steps = []

        for step in campaign.steps:
            transformed_step = self.transform_step(step)
            transformed_steps.append(transformed_step)

        return {
            "initialStepID": campaign.initialStepID,
            "steps": transformed_steps
        }
```

### Task 5: Update Generation Prompts (1-2 days)

#### Update planning prompts in `src/services/campaign_prompts/planner_prompts.py`:
- Include new field requirements
- Add schema structure examples
- Generate conditions arrays instead of segmentDefinition
- Include new step types in generation options

#### Update generation prompts in `src/services/campaign_prompts/generator_prompts.py`:
- Generate content for new fields (label, content, etc.)
- Create proper event structures
- Generate discount configurations
- Create structured time/limit objects

### Task 6: Validation Updates (1-2 days)

#### Update `src/services/campaign_validation/schema_validator.py`:
- Add FlowBuilder schema validation
- Validate required fields per step type
- Check event structure compliance
- Validate field types and formats

## Phase 4: Implementation Order & Timeline

### Week 1: Foundation
1. Update campaign models with new fields
2. Add missing step types
3. Update event model

### Week 2: Transformation Layer
4. Create SchemaTransformer service
5. Update generation prompts
6. Add transformation to output pipeline

### Week 3: Validation & Testing
7. Update validation system
8. Create comprehensive tests
9. Add integration tests

### Week 4: Deployment & Migration
10. Feature flag for new schema
11. Gradual rollout
12. Monitor for issues

## Phase 5: Risk Mitigation

### Backward Compatibility Strategy:
- Keep old fields alongside new ones during transition
- Use transformation layer for gradual migration
- Add feature flags to toggle between schemas
- Maintain both validation systems temporarily

### Testing Strategy:
- Create comprehensive test suite with schema examples
- Test all step types generate correctly
- Validate transformation accuracy
- Test edge cases and error handling

### Rollout Plan:
- Start with non-critical campaigns
- Monitor for schema compliance issues
- Gradually increase usage
- Full switch after validation

## Success Metrics

1. **Schema Compliance**: 100% of generated campaigns match FlowBuilder schema
2. **Backward Compatibility**: No breaking changes to existing campaigns
3. **Quality**: Maintain A-F quality grading system
4. **Performance**: Generation time remains under 10 seconds
5. **Accuracy**: All required fields populated correctly

## Deliverables

1. Updated campaign models with full schema compliance
2. Schema transformation service
3. Updated generation pipeline
4. Enhanced validation system
5. Comprehensive test suite
6. Documentation and migration guide

This plan provides a systematic approach to achieving full compliance with the FlowBuilder schema while maintaining system stability and backward compatibility.