"""
Campaign Generation Orchestrator - Coordinates the complete generation pipeline.
"""
import logging
import time
from typing import Dict, Any, Optional, List
from uuid import uuid4

from openai import AsyncOpenAI
from qdrant_client import QdrantClient

from ...models.campaign import Campaign
from ...models.campaign_generation import (
    GenerationRequest,
    GenerationResponse,
    GenerationMetadata,
    ValidationResult,
)
from ..campaign_validation import CampaignValidator
from ...services.embeddings import EmbeddingService
from ...services.campaign_transformation import SchemaTransformer
from .planner import CampaignPlanner
from .generator import ContentGenerator
from .template_manager import TemplateManager
from .input_extractor import InputExtractor, ExtractedDetails
from .llm_extractor import LLMExtractor
from .behavioral_targeting import BehavioralTargeting, BusinessRequirements
from .advanced_template_engine import AdvancedTemplateEngine, CustomMessageStructure, TemplateMapping
from .scheduling_engine import SchedulingEngine, ScheduleConfig

logger = logging.getLogger(__name__)


class CampaignOrchestrator:
    """
    Orchestrates the complete campaign generation pipeline.

    This coordinates:
    1. Intent extraction and campaign planning (CampaignPlanner)
    2. Template search and recommendation (TemplateManager)
    3. Content generation for all steps (ContentGenerator)
    4. Validation and quality checks
    5. Error handling with retry/fallback logic

    The output is a complete Campaign JSON ready for the execution engine.
    """

    def __init__(
        self,
        openai_client: AsyncOpenAI,
        qdrant_client: Optional[QdrantClient] = None,
        cohere_api_key: Optional[str] = None,
        enable_templates: bool = True,
        use_groq: bool = False,
        use_openrouter: bool = False,
        model_primary: str = "gpt-4o",
        model_fallback: str = "gpt-4o-mini"
    ):
        """
        Initialize Campaign Orchestrator.

        Args:
            openai_client: Async OpenAI client for LLM calls
            qdrant_client: Optional Qdrant client for template search
            cohere_api_key: Optional Cohere API key for embeddings
            enable_templates: Whether to use template recommendations
            use_groq: Whether using GROQ instead of OpenAI
            use_openrouter: Whether using OpenRouter instead of OpenAI
            model_primary: Primary model to use for planning
            model_fallback: Fallback model to use for content generation
        """
        # Initialize template manager
        self.template_manager = None
        if enable_templates and qdrant_client:
            # Try Cohere embeddings first if API key provided, fallback to OpenAI
            if cohere_api_key:
                try:
                    embedding_service = EmbeddingService(provider="cohere", api_key=cohere_api_key)
                    self.template_manager = TemplateManager(qdrant_client, embedding_service)
                    logger.info("Template manager enabled with Cohere embeddings")
                except ValueError as e:
                    logger.warning(f"Cohere embeddings failed, falling back to OpenAI: {e}")
                    try:
                        embedding_service = EmbeddingService(provider="openai")
                        self.template_manager = TemplateManager(qdrant_client, embedding_service)
                        logger.info("Template manager enabled with OpenAI embeddings")
                    except ValueError as e2:
                        logger.warning(f"OpenAI API key also not available, disabling template manager: {e2}")
            else:
                logger.warning("Cohere API key not provided, trying OpenAI embeddings")
                try:
                    embedding_service = EmbeddingService(provider="openai")
                    self.template_manager = TemplateManager(qdrant_client, embedding_service)
                    logger.info("Template manager enabled with OpenAI embeddings")
                except ValueError as e2:
                    logger.warning(f"OpenAI API key also not available, disabling template manager: {e2}")
        else:
            logger.info("Template manager disabled")

        # Initialize planner and generator with model configuration
        self.planner = CampaignPlanner(openai_client, self.template_manager, use_groq=use_groq, planning_model=model_primary, intent_model=model_fallback)
        self.generator = ContentGenerator(openai_client, use_groq=use_groq, content_model=model_fallback)

        # Initialize comprehensive validator
        self.validator = CampaignValidator()

        # Initialize schema transformer for FlowBuilder compliance
        self.schema_transformer = SchemaTransformer()

        # Initialize advanced systems for enhanced content generation
        self.input_extractor = InputExtractor()
        self.llm_extractor = LLMExtractor(openai_client)
        self.behavioral_targeting = BehavioralTargeting()
        self.advanced_template_engine = AdvancedTemplateEngine()
        self.scheduling_engine = SchedulingEngine()

        self.openai_client = openai_client
        self.use_groq = use_groq
        self.use_openrouter = use_openrouter
        self.model_primary = model_primary
        self.model_fallback = model_fallback
        self.enable_flowbuilder_mode = True  # Enable FlowBuilder compliance by default

    async def generate_campaign(
        self,
        request: GenerationRequest,
        merchant_context: Optional[Dict[str, Any]] = None,
        max_retries: int = 2
    ) -> GenerationResponse:
        """
        Generate a complete campaign from natural language description.

        This is the main entry point for campaign generation.

        Args:
            request: Generation request with description and constraints
            merchant_context: Merchant information (name, industry, brand_voice, etc.)
            max_retries: Maximum number of retry attempts on failures

        Returns:
            GenerationResponse with complete campaign JSON

        Raises:
            Exception: If generation fails after all retries
        """
        start_time = time.time()
        campaign_id = str(uuid4())

        logger.info(f"Starting campaign generation: {campaign_id}")
        logger.info(f"Merchant: {request.merchant_id}, Description: {request.description[:100]}...")

        # Default merchant context if not provided
        if merchant_context is None:
            merchant_context = {
                "merchant_id": request.merchant_id,
                "name": "Store",
                "industry": "retail",
                "brand_voice": "friendly and professional",
                "url": "https://example.com"
            }

        # Advanced input processing for complex business requirements
        logger.info("Processing advanced business requirements...")

        # Extract basic details with existing system
        extracted_details = self.input_extractor.extract_details(request.description)
        basic_template_variables = self.input_extractor.create_template_variables(extracted_details)

        # Extract Phase 1 improvements using LLM-based extraction
        logger.info("Using LLM-based feature extraction...")
        try:
            # Use comprehensive LLM extraction for all features
            extracted_features = await self.llm_extractor.extract_all_features(request.description)

            # Map LLM-extracted features to existing data structures
            scheduling_info = extracted_features.get('scheduling', {})
            audience_criteria = extracted_features.get('audience_criteria', {})
            product_details = extracted_features.get('product_info', {})

            # Extract template variables using existing method for now
            template_variables = self.input_extractor.extract_template_variables(request.description)

            logger.info("LLM extraction completed successfully")
        except Exception as e:
            logger.warning(f"LLM extraction failed, falling back to regex: {e}")
            # Fallback to regex-based extraction
            scheduling_info = self.input_extractor.extract_scheduling(request.description)
            audience_criteria = self.input_extractor.extract_audience_criteria(request.description)
            product_details = self.input_extractor.extract_product_details(request.description)
            template_variables = self.input_extractor.extract_template_variables(request.description)

        # Extract behavioral targeting and custom structures
        business_requirements = self.behavioral_targeting.extract_business_requirements(request.description)
        custom_structures = self.advanced_template_engine.extract_custom_structure(request.description)

        # Map advanced variables
        advanced_variables = self.advanced_template_engine.map_variables(request.description, {
            "business_requirements": business_requirements,
            "extracted_details": extracted_details.__dict__
        })

        # Create enhanced merchant context with proper nested object conversion
        enhanced_context = {
            "extracted_details": extracted_details.__dict__,
            "basic_variables": basic_template_variables,
            "advanced_variables": advanced_variables,
            "business_requirements": {
                **business_requirements.__dict__,
                "schedule": business_requirements.schedule.__dict__ if hasattr(business_requirements.schedule, '__dict__') else business_requirements.schedule
            },
            "custom_structures": custom_structures,
            "campaign_context": self.behavioral_targeting.create_targeting_variables(business_requirements),
            # Phase 1 improvements
            "scheduling_info": scheduling_info.__dict__ if hasattr(scheduling_info, '__dict__') else scheduling_info,
            "audience_criteria": audience_criteria.__dict__ if hasattr(audience_criteria, '__dict__') else audience_criteria,
            "product_details": product_details.__dict__ if hasattr(product_details, '__dict__') else product_details,
            "template_variables": template_variables,
            # Phase 3: Add original description for advanced feature extraction
            "original_description": request.description,
            "campaign_description": request.description
        }

        # Process structured inputs from request
        structured_requirements = {}

        # Add scheduling configuration
        if request.scheduling:
            structured_requirements["scheduling"] = request.scheduling.dict()
            logger.info(f"Using structured scheduling: {request.scheduling.description}")

        # Add specific CTA and store link
        if request.specific_cta:
            structured_requirements["cta"] = request.specific_cta
            logger.info(f"Using specific CTA: {request.specific_cta[:50]}...")

        if request.store_link:
            structured_requirements["store_link"] = request.store_link
            logger.info(f"Using specific store link: {request.store_link}")

        # Add offer configuration
        if request.offer:
            structured_requirements["offer"] = request.offer.dict()
            logger.info(f"Using structured offer: {request.offer.type} - {request.offer.value}")

        # Add target audience criteria
        if request.target_audience:
            structured_requirements["target_audience"] = request.target_audience
            logger.info(f"Using target audience criteria: {len(request.target_audience)} fields")

        # Add structured requirements to enhanced context
        enhanced_context["structured_requirements"] = structured_requirements
        enhanced_context["content_requirements"] = structured_requirements  # For backward compatibility

        merchant_context.update(enhanced_context)

        logger.info(f"Extracted {len(basic_template_variables)} basic variables, {len(advanced_variables)} advanced variables")
        logger.info(f"Business requirements: {business_requirements.campaign_purpose} with {len(business_requirements.behavior_rules)} behavioral rules")
        logger.info(f"Custom structures found: {len(custom_structures)}")

        # Track attempts for retry logic
        attempt = 0
        last_error = None

        while attempt <= max_retries:
            try:
                attempt += 1
                logger.info(f"Generation attempt {attempt}/{max_retries + 1}")

                # Step 1: Plan campaign structure
                logger.info("Step 1/3: Planning campaign structure...")
                campaign_plan = await self._plan_with_fallback(
                    request,
                    merchant_context,
                    attempt
                )

                # Step 1.5: Add Phase 1 improvements (segments and scheduling)
                logger.info("Step 1.5/3: Adding segment and schedule nodes...")
                campaign_plan = await self._add_phase1_improvements(campaign_plan, enhanced_context)

                # Step 2: Generate content for all steps
                logger.info("Step 2/3: Generating campaign content...")
                campaign = await self._generate_with_fallback(
                    campaign_plan,
                    merchant_context,
                    attempt
                )

                # Step 2.5: Advanced enhancement with business requirements
                logger.info("Step 2.5/3: Applying advanced business requirements...")
                campaign = self._enhance_campaign_with_advanced_requirements(
                    campaign,
                    merchant_context
                )

                # Step 3: Validate campaign
                logger.info("Step 3/3: Validating campaign...")
                validation = self._validate_campaign(campaign)

                # Build metadata
                generation_metadata = self._build_metadata(
                    campaign_plan,
                    start_time,
                    attempt
                )

                # Transform to FlowBuilder format if enabled
                if self.enable_flowbuilder_mode:
                    logger.info("Transforming campaign to FlowBuilder format...")
                    campaign_json = self.schema_transformer.transform_to_flowbuilder_format(
                        campaign, strict_mode=False
                    )
                else:
                    campaign_json = campaign_json

                # Add campaign metadata from structured inputs
                campaign_metadata = {}
                structured_reqs = merchant_context.get('structured_requirements', {})

                if structured_reqs.get('scheduling'):
                    campaign_metadata['scheduling'] = structured_reqs['scheduling']
                    logger.info("Added scheduling metadata to campaign")

                if structured_reqs.get('target_audience'):
                    campaign_metadata['target_audience'] = structured_reqs['target_audience']
                    logger.info("Added target audience metadata to campaign")

                if structured_reqs.get('offer'):
                    campaign_metadata['offer'] = structured_reqs['offer']
                    logger.info("Added offer metadata to campaign")

                # Add Phase 3 improvements metadata from campaign plan
                if '_metadata' in campaign_json and 'phase3_improvements' in campaign_json['_metadata']:
                    phase3_metadata = campaign_json['_metadata']['phase3_improvements']
                    campaign_metadata['phase3_improvements'] = phase3_metadata
                    logger.info(f"Added Phase 3 metadata: {phase3_metadata.get('phase3_nodes_count', 0)} advanced nodes")

                # Add Phase 1 and Phase 2 improvements metadata
                if '_metadata' in campaign_json:
                    if 'phase1_improvements' in campaign_json['_metadata']:
                        campaign_metadata['phase1_improvements'] = campaign_json['_metadata']['phase1_improvements']
                        logger.info("Added Phase 1 metadata to campaign")

                    if 'phase2_improvements' in campaign_json['_metadata']:
                        campaign_metadata['phase2_improvements'] = campaign_json['_metadata']['phase2_improvements']
                        logger.info("Added Phase 2 metadata to campaign")

                    if 'phase3_improvements' in campaign_json['_metadata']:
                        campaign_metadata['phase3_improvements'] = campaign_json['_metadata']['phase3_improvements']
                        logger.info("Added Phase 3 metadata to campaign")

                    
                    if 'final_coverage' in campaign_json['_metadata']:
                        final_coverage = campaign_json['_metadata']['final_coverage']
                        campaign_metadata['node_coverage'] = final_coverage
                        coverage_percentage = final_coverage.get('coverage_percentage', 0)
                        logger.info(f"Final node coverage: {coverage_percentage}% ({final_coverage.get('implemented_nodes', 0)}/15 nodes)")

                        if coverage_percentage >= 100:
                            logger.info("🎉 ACHIEVED 100% FlowBuilder node coverage!")
                        elif coverage_percentage >= 90:
                            logger.info(f"✅ Excellent coverage: {coverage_percentage}%")
                        elif coverage_percentage >= 75:
                            logger.info(f"⚠️  Good coverage: {coverage_percentage}%")
                        else:
                            logger.info(f"❌ Limited coverage: {coverage_percentage}%")

                # Add metadata to campaign JSON
                if campaign_metadata:
                    campaign_json['metadata'] = campaign_metadata

                # Build response
                response = GenerationResponse(
                    campaign_id=campaign_id,
                    campaign_json=campaign_json,
                    generation_metadata=generation_metadata,
                    validation=validation,
                    status="ready" if validation.is_valid else "needs_review"
                )

                duration = time.time() - start_time
                logger.info(f"Campaign generation completed in {duration:.2f}s")
                logger.info(f"Total cost: ${generation_metadata.total_cost_usd:.4f}")
                logger.info(f"Validation: {'PASSED' if validation.is_valid else 'FAILED'}")

                return response

            except Exception as e:
                last_error = e
                logger.error(f"Generation attempt {attempt} failed: {e}")

                if attempt <= max_retries:
                    wait_time = 2 ** attempt  # Exponential backoff: 2s, 4s, 8s
                    logger.info(f"Retrying in {wait_time}s...")
                    await self._sleep(wait_time)
                else:
                    logger.error(f"All {max_retries + 1} attempts failed")
                    raise Exception(f"Campaign generation failed after {max_retries + 1} attempts: {last_error}")

        # Should never reach here, but just in case
        raise Exception(f"Campaign generation failed: {last_error}")

    async def _plan_with_fallback(
        self,
        request: GenerationRequest,
        merchant_context: Dict[str, Any],
        attempt: int
    ) -> Dict[str, Any]:
        """
        Plan campaign structure with fallback strategies.

        Attempt 1: GPT-4o with templates
        Attempt 2: GPT-4o without templates
        Attempt 3+: Simplified prompt

        Args:
            request: Generation request
            merchant_context: Merchant information
            attempt: Current attempt number

        Returns:
            Campaign plan dict

        Raises:
            Exception: If planning fails
        """
        try:
            # First attempt: use templates if enabled
            if attempt == 1:
                return await self.planner.plan_campaign_structure(request, merchant_context)

            # Second attempt: disable template search to simplify
            elif attempt == 2:
                logger.warning("Planning attempt 2: Disabling template search")
                original_use_template = request.use_template
                request.use_template = False
                try:
                    return await self.planner.plan_campaign_structure(request, merchant_context)
                finally:
                    request.use_template = original_use_template

            # Third+ attempt: Use even simpler approach
            else:
                logger.warning("Planning attempt 3+: Using minimal fallback")
                return await self._create_minimal_plan(request, merchant_context)

        except Exception as e:
            logger.error(f"Planning failed: {e}")
            raise

    async def _generate_with_fallback(
        self,
        campaign_plan: Dict[str, Any],
        merchant_context: Dict[str, Any],
        attempt: int
    ) -> Campaign:
        """
        Generate campaign content with fallback strategies.

        Attempt 1: Full generation with AI messages
        Attempt 2: Simplified generation with template messages
        Attempt 3+: Basic generation with minimal AI

        Args:
            campaign_plan: Campaign structure plan
            merchant_context: Merchant information
            attempt: Current attempt number

        Returns:
            Complete Campaign object

        Raises:
            Exception: If generation fails
        """
        try:
            # All attempts use the same generator for now
            # Future enhancement: could adjust temperature or model based on attempt
            return await self.generator.generate_campaign_content(
                campaign_plan,
                merchant_context
            )

        except Exception as e:
            logger.error(f"Content generation failed: {e}")
            raise

    def _enhance_campaign_with_extracted_details(
        self,
        campaign: Campaign,
        extracted_details: ExtractedDetails,
        template_variables: Dict[str, str]
    ) -> Campaign:
        """
        Enhance campaign content with specific details extracted from input description.

        This step addresses the input-output alignment gap by:
        1. Populating discount fields with extracted values
        2. Adding specific template variables to content
        3. Replacing generic content with extracted specifics

        Args:
            campaign: Generated campaign object
            extracted_details: Specific details extracted from description
            template_variables: Dynamic template variables created from extracted details

        Returns:
            Enhanced campaign with specific details integrated
        """
        logger.info(f"Enhancing campaign with {len(template_variables)} template variables")

        for step in campaign.steps:
            if step.type == "message" and hasattr(step, 'content'):
                # Replace template variables with extracted values
                enhanced_content = step.content

                # Apply template variable substitutions
                for var_key, var_value in template_variables.items():
                    enhanced_content = enhanced_content.replace(var_key, var_value)

                # Add extracted specifics to generic content
                if extracted_details.discount_percentage and "special offers" in enhanced_content:
                    enhanced_content = enhanced_content.replace(
                        "special offers",
                        f"{extracted_details.discount_percentage}% OFF special offers"
                    )

                if extracted_details.collections and "offers waiting for you" in enhanced_content:
                    collection_name = extracted_details.collections[0]
                    enhanced_content = enhanced_content.replace(
                        "offers waiting for you",
                        f"exciting {collection_name} offers waiting for you"
                    )

                if extracted_details.discount_percentage and "complete your purchase" in enhanced_content:
                    enhanced_content = enhanced_content.replace(
                        "complete your purchase today and enjoy our special offers!",
                        f"complete your purchase today and enjoy {extracted_details.discount_percentage}% OFF!"
                    )

                # Update the content
                step.content = enhanced_content
                if hasattr(step, 'text'):
                    step.text = enhanced_content

                # Populate discount fields if discounts were extracted
                if extracted_details.discount_percentage:
                    step.discountType = "percentage"
                    step.discountValue = str(extracted_details.discount_percentage)
                    # Generate a simple discount code
                    import random
                    import string
                    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                    step.discountCode = f"SAVE{extracted_details.discount_percentage}{code[:4]}"
                    logger.info(f"Added {extracted_details.discount_percentage}% discount with code: {step.discountCode}")

                elif extracted_details.discount_amount:
                    step.discountType = "fixed"
                    step.discountValue = str(extracted_details.discount_amount)
                    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                    step.discountCode = f"SAVE{int(extracted_details.discount_amount)}{code[:4]}"
                    logger.info(f"Added ${extracted_details.discount_amount} discount with code: {step.discountCode}")

        logger.info("Campaign enhancement completed - discount fields populated and content enriched")
        return campaign

    def _enhance_campaign_with_advanced_requirements(
        self,
        campaign: Campaign,
        merchant_context: Dict[str, Any]
    ) -> Campaign:
        """
        Enhance campaign with advanced business requirements including behavioral targeting,
        custom templates, scheduling, and variable mapping.
        """
        logger.info("Starting advanced campaign enhancement...")

        # Get business requirements from context
        business_requirements = merchant_context.get('business_requirements', {})
        custom_structures = merchant_context.get('custom_structures', [])
        advanced_variables = merchant_context.get('advanced_variables', {})

        # Convert campaign to dictionary for manipulation
        campaign_dict = campaign.model_dump() if hasattr(campaign, 'model_dump') else campaign.dict()

        # Process each step with advanced requirements
        enhanced_steps = []
        for i, step in enumerate(campaign_dict['steps'], 1):
            logger.info(f"Processing step {i}: {step.get('type', 'unknown')} for advanced enhancement")

            if step.get('type') == 'message':
                # Apply custom template processing if available
                if custom_structures:
                    custom_structure = self._find_matching_custom_structure(custom_structures, business_requirements)
                    if custom_structure:
                        step = self.advanced_template_engine.generate_enhanced_step(
                            step,
                            custom_structure,
                            advanced_variables
                        )

                        # Add trigger phrases for event handling
                        if custom_structure.trigger_phrases:
                            step = self._add_trigger_events(step, custom_structure.trigger_phrases)

                # Apply advanced variable mappings
                if advanced_variables:
                    step = self._apply_advanced_variables(step, advanced_variables, business_requirements)

                # Apply scheduling
                if business_requirements.get('schedule'):
                    step = self._apply_scheduling(step, business_requirements['schedule'])

                # Add business logic annotations
                step['business_logic'] = {
                    'targeting_criteria': business_requirements.get('behavior_rules', []),
                    'purpose': business_requirements.get('campaign_purpose', ''),
                    'urgency': business_requirements.get('urgency_level', 'medium')
                }

                enhanced_steps.append(step)
            else:
                enhanced_steps.append(step)  # Keep non-message steps unchanged

        # Update campaign dictionary
        campaign_dict['steps'] = enhanced_steps

        # Convert back to Campaign model (this will validate the structure)
        try:
            enhanced_campaign = Campaign(**campaign_dict)
        except Exception as e:
            logger.warning(f"Failed to convert enhanced campaign back to Campaign model: {e}")
            # Return the original campaign if enhancement fails validation
            return campaign

        logger.info(f"Advanced enhancement completed - processed {len(enhanced_steps)} steps")
        return enhanced_campaign

    def _find_matching_custom_structure(self, custom_structures: List[CustomMessageStructure],
                                    business_requirements: Dict[str, Any]) -> Optional[CustomMessageStructure]:
        """Find the best matching custom structure for current business requirements."""
        if not custom_structures:
            return None

        # For now, return the first matching structure
        # In a real implementation, this would use sophisticated matching algorithms
        for structure in custom_structures:
            if business_requirements.get('campaign_purpose') in ['cart_recovery', 'abandoned_cart']:
                if structure.step_type in ['purchase_offer', 'cart_reminder']:
                    return structure

        return custom_structures[0] if custom_structures else None

    def _apply_advanced_variables(self, step: Dict[str, Any], advanced_variables: Dict[str, Any],
                             business_requirements: Dict[str, Any]) -> Dict[str, Any]:
        """Apply advanced variable mappings to a campaign step."""
        # Apply basic extracted variables (discounts, collections, etc.)
        for var_key, var_value in advanced_variables.items():
            if '{{discount.percent}}' in step.get('content', ''):
                step['discountType'] = 'percentage'
                step['discountValue'] = var_value.replace('%', '')
                # Generate discount code
                import random
                import string
                code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                step['discountCode'] = f"SAVE{var_value.replace('%', '')}{code[:4]}"

            if 'content' in step:
                step['content'] = step['content'].replace(var_key, var_value)
            if 'text' in step and step['text']:
                step['text'] = step['text'].replace(var_key, var_value)

        return step

    def _apply_scheduling(self, step: Dict[str, Any], schedule_config) -> Dict[str, Any]:
        """Apply scheduling configuration to campaign step."""
        # step is already a dictionary, just make a copy
        enhanced_step = step.copy()

        # Handle both dict and ScheduleInfo dataclass
        if hasattr(schedule_config, 'start_time'):
            # ScheduleInfo dataclass object
            if schedule_config.start_time:
                time_config = self.scheduling_engine.create_delay_config(
                    self.scheduling_engine.parse_schedule_config(schedule_config.__dict__)
                )
                enhanced_step['after'] = time_config
        elif isinstance(schedule_config, dict):
            # Dictionary object
            if schedule_config.get('start_time'):
                time_config = self.scheduling_engine.create_delay_config(
                    self.scheduling_engine.parse_schedule_config(schedule_config)
                )
                enhanced_step['after'] = time_config

        return enhanced_step

    def _add_trigger_events(self, step: Dict[str, Any], trigger_phrases: List[str]) -> Dict[str, Any]:
        """Add trigger events based on expected reply phrases."""
        if 'events' not in step:
            step['events'] = []

        # Add reply events for each trigger phrase
        for phrase in trigger_phrases:
            trigger_event = {
                'id': f"evt_trigger_{phrase.lower()}",
                'type': 'reply',
                'intent': phrase.lower(),
                'nextStepID': step.get('id', getattr(step, 'id', 'step_end')),
                'active': True,
                'parameters': {}
            }
            step['events'].append(trigger_event)

        return step

    async def _create_minimal_plan(
        self,
        request: GenerationRequest,
        merchant_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create a minimal fallback campaign plan.

        This is used as a last resort when AI planning fails.

        Args:
            request: Generation request
            merchant_context: Merchant information

        Returns:
            Minimal campaign plan
        """
        logger.warning("Creating minimal fallback campaign plan")

        # Determine campaign type
        # Handle both string and enum types (Pydantic may convert)
        if request.campaign_type:
            # Use hasattr check instead of isinstance to handle Pydantic enum behavior
            campaign_type = request.campaign_type.value if hasattr(request.campaign_type, 'value') else str(request.campaign_type)
        else:
            campaign_type = "promotional"

        # Create simple 3-step campaign: message → delay → message → end
        minimal_plan = {
            "campaign_name": f"{campaign_type.title()} Campaign",
            "campaign_type": campaign_type,
            "initialStepID": "step_001",
            "steps": [
                {
                    "id": "step_001",
                    "type": "message",
                    "purpose": "Initial message",
                    "text_outline": "Send promotional message",
                    "position_in_flow": "initial",
                    "events": [
                        {
                            "id": "evt_001",
                            "type": "click",
                            "nextStepID": "step_end"
                        },
                        {
                            "id": "evt_002",
                            "type": "noreply",
                            "after": {"hours": 24},
                            "nextStepID": "step_002"
                        }
                    ]
                },
                {
                    "id": "step_002",
                    "type": "message",
                    "purpose": "Follow-up reminder",
                    "text_outline": "Send reminder message",
                    "position_in_flow": "closing",
                    "events": [
                        {
                            "id": "evt_003",
                            "type": "click",
                            "nextStepID": "step_end"
                        }
                    ]
                },
                {
                    "id": "step_end",
                    "type": "end",
                    "reason": "Campaign completed"
                }
            ],
            "_metadata": {
                "intent": {
                    "campaign_type": campaign_type,
                    "goals": ["engage", "convert"],
                    "target_audience": {"description": "all customers"},
                    "key_products": [],
                    "confidence": 0.5
                },
                "fallback": True,
                "model": "minimal_fallback",
                "cost_usd": 0.0
            }
        }

        return minimal_plan

    def _validate_campaign(self, campaign: Campaign) -> ValidationResult:
        """
        Validate generated campaign using comprehensive validation.

        Uses Phase 3 comprehensive validator with:
        - Schema validation
        - Flow validation
        - Best practices checking
        - Optimization suggestions

        Args:
            campaign: Generated campaign

        Returns:
            ValidationResult with issues and warnings
        """
        # Convert Campaign to JSON for validator
        campaign_json = campaign.dict(exclude_none=True)

        # Run comprehensive validation
        validation_result = self.validator.validate_and_log(
            campaign_json,
            include_optimizations=True
        )

        # Convert to legacy ValidationResult format
        issues = [issue.message for issue in validation_result.errors]
        warnings = [issue.message for issue in validation_result.warnings]

        # Log best practices score
        logger.info(f"Campaign quality: Grade {validation_result.best_practices_grade} "
                   f"({validation_result.best_practices_score:.0f}/100)")

        # Log top optimization suggestions
        if validation_result.optimizations:
            top_suggestions = validation_result.optimizations[:3]
            logger.info(f"Top optimization suggestions:")
            for suggestion in top_suggestions:
                logger.info(f"  - [{suggestion.priority.upper()}] {suggestion.title}")

        return ValidationResult(
            is_valid=validation_result.is_valid,
            issues=issues,
            warnings=warnings,
            checked_at=time.time()
        )

    def _build_metadata(
        self,
        campaign_plan: Dict[str, Any],
        start_time: float,
        attempts: int
    ) -> GenerationMetadata:
        """
        Build generation metadata from plan and execution info.

        Args:
            campaign_plan: Campaign plan with metadata
            start_time: Generation start timestamp
            attempts: Number of generation attempts

        Returns:
            GenerationMetadata object
        """
        plan_metadata = campaign_plan.get("_metadata", {})

        # Extract costs
        planning_cost = plan_metadata.get("cost_usd", 0.0)
        generation_metadata = self.generator.get_generation_metadata()
        generation_cost = generation_metadata.get("total_cost_usd", 0.0)

        # Calculate totals
        total_cost = planning_cost + generation_cost
        total_tokens = plan_metadata.get("tokens_used", 0) + generation_metadata.get("total_tokens", 0)
        duration = time.time() - start_time

        return GenerationMetadata(
            model_planning=plan_metadata.get("model", "gpt-4o"),
            model_content=generation_metadata.get("model", "gpt-4o-mini"),
            total_tokens=total_tokens,
            planning_tokens=plan_metadata.get("tokens_used", 0),
            generation_tokens=generation_metadata.get("total_tokens", 0),
            total_cost_usd=round(total_cost, 6),
            planning_cost_usd=round(planning_cost, 6),
            generation_cost_usd=round(generation_cost, 6),
            duration_seconds=round(duration, 2),
            template_used=plan_metadata.get("template_used"),
            template_similarity=plan_metadata.get("template_similarity"),
            attempts=attempts
        )

    async def _add_phase1_improvements(self, campaign_plan: Dict[str, Any], enhanced_context: Dict[str, Any]) -> Dict[str, Any]:
        """Add Phase 1, 2, 3, and 4 improvements (segments, scheduling, products, conditions, advanced features, and final integration) to campaign plan."""
        try:
            # Extract Phase 1 data from enhanced context
            scheduling_info = enhanced_context.get('scheduling_info', {})
            audience_criteria = enhanced_context.get('audience_criteria', {})
            product_details = enhanced_context.get('product_details', {})
            template_variables = enhanced_context.get('template_variables', {})

            # Extract Phase 3 data from input extractor
            campaign_description = enhanced_context.get('campaign_description', '')
            if not campaign_description and 'extracted_details' in enhanced_context:
                # Try to get description from request context
                campaign_description = enhanced_context.get('original_description', '')

            # Phase 3: Extract advanced features using LLM
            try:
                if campaign_description:
                    # Use LLM extraction for advanced features
                    llm_features = await self.llm_extractor.extract_all_features(campaign_description)

                    ab_test_criteria = llm_features.get('experiment_config', {})
                    rate_limit_criteria = llm_features.get('rate_limit_config', {})
                    split_criteria = llm_features.get('split_config', {})
                    delay_timing = llm_features.get('delay_config', {})
                    product_choice_info = llm_features.get('product_choice_info', {})
                    property_info = llm_features.get('property_info', {})
                    reply_info = llm_features.get('reply_info', {})
                    purchase_info = llm_features.get('purchase_info', {})
                    limit_info = llm_features.get('limit_info', {})

                    logger.info("LLM extraction for Phase 3 features completed successfully")
                else:
                    ab_test_criteria = {}
                    rate_limit_criteria = {}
                    split_criteria = {}
                    delay_timing = {}
                    product_choice_info = {}
                    property_info = {}
                    reply_info = {}
                    purchase_info = {}
                    limit_info = {}
            except Exception as e:
                logger.warning(f"LLM extraction for Phase 3 features failed, falling back to regex: {e}")
                # Fallback to regex-based extraction
                ab_test_criteria = self.input_extractor.extract_ab_test_criteria(campaign_description) if campaign_description else {}
                rate_limit_criteria = self.input_extractor.extract_rate_limiting_criteria(campaign_description) if campaign_description else {}
                split_criteria = self.input_extractor.extract_audience_split_criteria(campaign_description) if campaign_description else {}
                delay_timing = self.input_extractor.extract_delay_timing(campaign_description) if campaign_description else {}
                product_choice_info = {}
                property_info = {}

            
            # Get current steps
            steps = campaign_plan.get('steps', [])
            modified_steps = []

            # Initialize variables to track added nodes
            schedule_node = None
            segment_nodes = []
            product_choice_node = None
            property_nodes = []
            phase3_nodes = []

            # Phase 1: Add schedule node first if scheduling info exists
            schedule_node = self.planner.create_schedule_node(scheduling_info)
            if schedule_node:
                modified_steps.append(schedule_node)
                logger.info(f"Added SCHEDULE node: {schedule_node.get('datetime')}")

            # Phase 1: Add segment nodes if audience criteria exist
            segment_nodes = self.planner.create_audience_segments(audience_criteria)
            if segment_nodes:
                modified_steps.extend(segment_nodes)
                logger.info(f"Added {len(segment_nodes)} SEGMENT node(s)")

            # Phase 3: Add rate limit node if rate limiting criteria exist
            if rate_limit_criteria.get('enabled'):
                rate_limit_node = self.planner.create_rate_limit_node(
                    {
                        'daily': rate_limit_criteria.get('daily_limit', 10),
                        'hourly': rate_limit_criteria.get('hourly_limit', 1),
                        'cooldown': rate_limit_criteria.get('cooldown_minutes', 60),
                        'business_hours_only': rate_limit_criteria.get('business_hours_only', False),
                        'weekend_exclusion': rate_limit_criteria.get('weekend_exclusion', False)
                    },
                    enhanced_context
                )
                if rate_limit_node:
                    modified_steps.append(rate_limit_node)
                    phase3_nodes.append(('RATE_LIMIT', rate_limit_node))
                    logger.info(f"Added RATE_LIMIT node: {rate_limit_criteria.get('daily_limit')}/day")

            # Phase 3: Add split node if audience splitting criteria exist
            if split_criteria.get('enabled'):
                split_node = self.planner.create_split_node(
                    {
                        'description': split_criteria.get('group_names', {}).get('group_a', 'Group A') + ' vs ' + split_criteria.get('group_names', {}).get('group_b', 'Group B'),
                        'detailed_description': f"Audience split: {split_criteria.get('split_type', 'random')} distribution",
                        'split_a_percent': split_criteria.get('split_percentages', {}).get('group_a', 50),
                        'split_a_name': split_criteria.get('group_names', {}).get('group_a', 'Group A'),
                        'split_a_next': split_criteria.get('next_steps', {}).get('group_a', 'path_a'),
                        'split_a_criteria': split_criteria.get('split_criteria', {}).get('group_a', 'Random selection'),
                        'split_b_name': split_criteria.get('group_names', {}).get('group_b', 'Group B'),
                        'split_b_next': split_criteria.get('next_steps', {}).get('group_b', 'path_b'),
                        'split_b_criteria': split_criteria.get('split_criteria', {}).get('group_b', 'Random selection'),
                        'split_type': split_criteria.get('split_type', 'random')
                    },
                    enhanced_context
                )
                if split_node:
                    modified_steps.append(split_node)
                    phase3_nodes.append(('SPLIT', split_node))
                    logger.info(f"Added SPLIT node: {split_criteria.get('split_percentages', {}).get('group_a', 50)}%/{split_criteria.get('split_percentages', {}).get('group_b', 50)}%")

            # Phase 3: Add experiment node if A/B testing criteria exist
            if ab_test_criteria.get('enabled'):
                experiment_node = self.planner.create_experiment_node(
                    ab_test_criteria.get('variants', []),
                    {
                        'experiment_name': ab_test_criteria.get('experiment_name', 'A/B Test'),
                        'experiment_description': ab_test_criteria.get('experiment_description', 'Testing message variants'),
                        'success_metrics': ab_test_criteria.get('success_metrics', ['conversion_rate', 'click_rate']),
                        'duration_days': ab_test_criteria.get('duration_days', 7)
                    }
                )
                if experiment_node:
                    modified_steps.append(experiment_node)
                    phase3_nodes.append(('EXPERIMENT', experiment_node))
                    logger.info(f"Added EXPERIMENT node: {len(ab_test_criteria.get('variants', []))} variants")

            # Phase 3: Add delay node if delay timing exists
            if delay_timing.get('enabled'):
                delay_node = self.planner.create_delay_node(
                    {
                        'minutes': delay_timing.get('minutes', 0),
                        'hours': delay_timing.get('hours', 0),
                        'days': delay_timing.get('days', 0),
                        'label': 'Campaign Delay',
                        'description': f'Delay of {delay_timing.get("minutes", 0) + delay_timing.get("hours", 0)*60 + delay_timing.get("days", 0)*24*60} minutes',
                        'business_hours_only': delay_timing.get('business_hours_only', False),
                        'max_wait_days': delay_timing.get('max_wait_days', 7)
                    },
                    enhanced_context
                )
                if delay_node:
                    modified_steps.append(delay_node)
                    phase3_nodes.append(('DELAY', delay_node))
                    logger.info(f"Added DELAY node: {delay_timing.get('minutes', 0) + delay_timing.get('hours', 0)*60 + delay_timing.get('days', 0)*24*60} minutes")

            
            # Phase 2: Add product choice node if LLM-extracted product choice info exists
            if product_choice_info.get('enabled'):
                product_choice_node = self.planner.create_product_choice_node({
                    'products': product_choice_info.get('products', []),
                    'display_type': product_choice_info.get('display_type', 'list'),
                    'label': 'Product Selection',
                    'description': 'Choose from available products',
                    'next_step_id': product_choice_info.get('next_step_id', 'next_step')
                })
                if product_choice_node:
                    modified_steps.append(product_choice_node)
                    logger.info(f"Added PRODUCT_CHOICE node: {len(product_choice_info.get('products', []))} products")
            else:
                # Fallback to original product details extraction
                # Handle both dict and string product_details safely
                if isinstance(product_details, dict):
                    product_choice_node = self.planner.create_product_choice_node(product_details)
                else:
                    # Create simple product choice from string details
                    product_choice_node = self.planner.create_product_choice_node({'products': []})
                if product_choice_node:
                    modified_steps.append(product_choice_node)
                    logger.info(f"Added PRODUCT_CHOICE node: {product_choice_node.get('label')}")

            # Phase 2: Add property nodes if LLM-extracted property conditions exist
            if property_info.get('enabled'):
                for condition in property_info.get('conditions', []):
                    property_node = self.planner.create_property_node({
                        'field': condition.get('field', ''),
                        'operator': condition.get('operator', 'equals'),
                        'value': condition.get('value', ''),
                        'logical_operator': condition.get('logical_operator', 'AND'),
                        'label': f'Property: {condition.get("field", "")}',
                        'description': f'Check if {condition.get("field", "")} {condition.get("operator", "")} {condition.get("value", "")}',
                        'next_step_id': property_info.get('next_step_id', 'next_step')
                    }, enhanced_context)
                    if property_node:
                        property_nodes.append(property_node)
                logger.info(f"Added {len(property_nodes)} PROPERTY node(s) from LLM extraction")
            else:
                # Fallback to original property condition extraction
                if enhanced_context.get('basic_variables'):
                    # Check for conditions in the description or basic variables
                    property_conditions = self._extract_property_conditions(enhanced_context)
                    for condition in property_conditions:
                        property_node = self.planner.create_property_node(condition, enhanced_context)
                        if property_node:
                            property_nodes.append(property_node)

            if property_nodes:
                modified_steps.extend(property_nodes)
                logger.info(f"Added {len(property_nodes)} PROPERTY node(s)")

            # Phase 2: Add reply nodes if LLM-extracted reply conditions exist
            if reply_info.get('enabled'):
                reply_node = self._create_reply_node(reply_info, enhanced_context)
                if reply_node:
                    modified_steps.append(reply_node)
                    logger.info(f"Added REPLY node: {reply_info.get('reply_type')}")

            # Phase 2: Add purchase nodes if LLM-extracted purchase conditions exist
            if purchase_info.get('enabled'):
                purchase_node = self._create_purchase_node(purchase_info, enhanced_context)
                if purchase_node:
                    modified_steps.append(purchase_node)
                    logger.info(f"Added PURCHASE node: {purchase_info.get('purchase_type')}")

            # Phase 2: Add limit nodes if LLM-extracted limit conditions exist
            if limit_info.get('enabled'):
                limit_node = self._create_limit_node(limit_info, enhanced_context)
                if limit_node:
                    modified_steps.append(limit_node)
                    logger.info(f"Added LIMIT node: {limit_info.get('limit_type')}")

            # Add existing steps
            modified_steps.extend(steps)

            # Update campaign plan
            campaign_plan['steps'] = modified_steps

            # Update initial step ID if we added nodes
            if modified_steps:
                campaign_plan['initialStepID'] = modified_steps[0]['id']

            # Add product details and template variables to metadata
            if '_metadata' not in campaign_plan:
                campaign_plan['_metadata'] = {}

            campaign_plan['_metadata']['phase1_improvements'] = {
                'scheduling_added': bool(schedule_node),
                'segments_added': len(segment_nodes),
                'product_details': product_details,
                'template_variables': template_variables
            }

            # Add Phase 2 improvements metadata
            campaign_plan['_metadata']['phase2_improvements'] = {
                'product_choice_added': bool(product_choice_node),
                'property_nodes_added': len(property_nodes) if 'property_nodes' in locals() else 0,
                'reply_nodes_added': len([n for n in modified_steps if n.get('type') in ['reply', 'no_reply']]),
                'purchase_nodes_added': len([n for n in modified_steps if n.get('type') in ['purchase_offer', 'purchase']]),
                'limit_nodes_added': len([n for n in modified_steps if n.get('type') == 'limit']),
                'llm_product_choice_enabled': product_choice_info.get('enabled', False),
                'llm_property_conditions_enabled': property_info.get('enabled', False),
                'llm_reply_enabled': reply_info.get('enabled', False),
                'llm_purchase_enabled': purchase_info.get('enabled', False),
                'llm_limit_enabled': limit_info.get('enabled', False),
                'total_steps_added': len(modified_steps) - len(steps)
            }

            # Add Phase 3 improvements metadata
            campaign_plan['_metadata']['phase3_improvements'] = {
                'experiment_added': any(node_type == 'EXPERIMENT' for node_type, _ in phase3_nodes),
                'rate_limit_added': any(node_type == 'RATE_LIMIT' for node_type, _ in phase3_nodes),
                'split_added': any(node_type == 'SPLIT' for node_type, _ in phase3_nodes),
                'delay_added': any(node_type == 'DELAY' for node_type, _ in phase3_nodes),
                'llm_extraction_used': True,
                'llm_features_extracted': {
                    'experiment_config': ab_test_criteria.get('enabled', False),
                    'rate_limit_config': rate_limit_criteria.get('enabled', False),
                    'split_config': split_criteria.get('enabled', False),
                    'delay_config': delay_timing.get('enabled', False),
                    'product_choice_config': product_choice_info.get('enabled', False),
                    'property_config': property_info.get('enabled', False),
                    'reply_config': reply_info.get('enabled', False),
                    'purchase_config': purchase_info.get('enabled', False),
                    'limit_config': limit_info.get('enabled', False)
                },
                'phase3_nodes_count': len(phase3_nodes),
                'phase3_node_types': [node_type for node_type, _ in phase3_nodes],
                'ab_test_variants': len(ab_test_criteria.get('variants', [])) if ab_test_criteria.get('enabled') else 0,
                'split_percentages': split_criteria.get('split_percentages', {}) if split_criteria.get('enabled') else {},
                'rate_limits': {
                    'daily': rate_limit_criteria.get('daily_limit'),
                    'hourly': rate_limit_criteria.get('hourly_limit')
                } if rate_limit_criteria.get('enabled') else {}
            }

            
            # Calculate total phase improvements including all new node types
            reply_nodes_count = len([n for n in modified_steps if n.get('type') in ['reply', 'no_reply']])
            purchase_nodes_count = len([n for n in modified_steps if n.get('type') in ['purchase_offer', 'purchase']])
            limit_nodes_count = len([n for n in modified_steps if n.get('type') == 'limit'])

            total_phase_improvements = (
                len(segment_nodes) + len(property_nodes) + len(phase3_nodes) +
                reply_nodes_count + purchase_nodes_count + limit_nodes_count
            )

            if schedule_node:
                total_phase_improvements += 1
            if product_choice_node:
                total_phase_improvements += 1

            # Calculate node coverage
            implemented_node_types = set()
            if schedule_node:
                implemented_node_types.add('SCHEDULE')
            if segment_nodes:
                implemented_node_types.add('SEGMENT')
            if product_choice_node:
                implemented_node_types.add('PRODUCT_CHOICE')
            if property_nodes:
                implemented_node_types.add('PROPERTY')

            # Add Phase 2 and 3 node types
            reply_nodes = [n for n in modified_steps if n.get('type') in ['reply', 'no_reply']]
            purchase_nodes = [n for n in modified_steps if n.get('type') in ['purchase_offer', 'purchase']]
            limit_nodes = [n for n in modified_steps if n.get('type') == 'limit']

            if reply_nodes:
                implemented_node_types.add('REPLY')
                implemented_node_types.add('NO_REPLY')
            if purchase_nodes:
                implemented_node_types.add('PURCHASE_OFFER')
                implemented_node_types.add('PURCHASE')
            if limit_nodes:
                implemented_node_types.add('LIMIT')

            # Add Phase 3 node types
            for node_type, _ in phase3_nodes:
                implemented_node_types.add(node_type)

            # Always include basic nodes
            implemented_node_types.update(['MESSAGE', 'END'])

            node_coverage_percentage = len(implemented_node_types) / 15 * 100

            campaign_plan['_metadata']['final_coverage'] = {
                'implemented_nodes': len(implemented_node_types),
                'total_nodes': 15,
                'coverage_percentage': round(node_coverage_percentage, 1),
                'node_types': list(implemented_node_types),
                'phase_complete': node_coverage_percentage >= 100
            }

            logger.info(f"All Phase improvements applied: {total_phase_improvements} nodes added (Phase 1-3)")
            logger.info(f"Phase 3 nodes: {len(phase3_nodes)} ({', '.join([node_type for node_type, _ in phase3_nodes])})")
            logger.info(f"Final node coverage: {len(implemented_node_types)}/15 ({node_coverage_percentage:.1f}%)")

        except Exception as e:
            logger.error(f"Failed to apply Phase improvements: {e}", exc_info=True)
            # Continue with original plan if improvements fail

        return campaign_plan

    def _create_reply_node(self, reply_info: Dict[str, Any], context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create reply step node from LLM-extracted reply info."""
        if not reply_info.get('enabled'):
            return None

        return {
            'id': f"reply_{str(uuid4())[:8]}",
            'type': 'reply' if reply_info.get('reply_type') == 'reply' else 'no_reply',
            'label': f"Reply: {reply_info.get('reply_type')}",
            'description': f"Auto-reply for {', '.join(reply_info.get('keywords', []))}",
            'response_template': reply_info.get('response_template'),
            'next_step_id': reply_info.get('next_step_id'),
            'active': True,
            'events': []
        }

    def _create_purchase_node(self, purchase_info: Dict[str, Any], context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create purchase step node from LLM-extracted purchase info."""
        if not purchase_info.get('enabled'):
            return None

        purchase_type = purchase_info.get('purchase_type', 'purchase_offer')
        node_type = 'purchase_offer' if purchase_type == 'purchase_offer' else 'purchase'

        return {
            'id': f"{purchase_type}_{str(uuid4())[:8]}",
            'type': node_type,
            'label': f"Purchase: {purchase_type}",
            'description': f"Complete purchase with {purchase_info.get('discount_percentage', 0)}% discount" if purchase_info.get('discount_percentage') else "Complete purchase",
            'discount_percentage': purchase_info.get('discount_percentage'),
            'urgency': purchase_info.get('urgency'),
            'products': purchase_info.get('products', []),
            'next_step_id': purchase_info.get('next_step_id'),
            'active': True,
            'events': [
                {
                    "id": "evt_purchase_complete",
                    "type": "default",
                    "nextStepID": purchase_info.get('next_step_id', 'step_end'),
                    "active": True,
                    "parameters": {}
                }
            ]
        }

    def _create_limit_node(self, limit_info: Dict[str, Any], context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create limit step node from LLM-extracted limit info."""
        if not limit_info.get('enabled'):
            return None

        return {
            'id': f"limit_{str(uuid4())[:8]}",
            'type': 'limit',
            'label': f"Limit: {limit_info.get('limit_type')}",
            'description': f"Maximum {limit_info.get('max_count', 100)} per {limit_info.get('time_window', 'day')}",
            'max_count': limit_info.get('max_count', 100),
            'time_window': limit_info.get('time_window', 'daily'),
            'next_step_id': limit_info.get('next_step_id'),
            'active': True,
            'events': [
                {
                    "id": "evt_limit_complete",
                    "type": "default",
                    "nextStepID": limit_info.get('next_step_id', 'step_end'),
                    "active": True,
                    "parameters": {}
                }
            ]
        }

    def _extract_property_conditions(self, enhanced_context: Dict[str, Any]) -> List[str]:
        """Extract property conditions from enhanced context for conditional logic."""
        conditions = []

        # Extract from description
        description = enhanced_context.get('campaign_description', '').lower()

        # Check for common conditional patterns
        if any(word in description for word in ['if', 'when', 'only if', 'unless', 'except']):
            conditions.append(description)

        # Check for basic variables that suggest conditions
        basic_variables = enhanced_context.get('basic_variables', {})
        if basic_variables:
            conditions.append(f"Basic variables detected: {list(basic_variables.keys())}")

        # Check for customer attribute conditions
        if 'customer' in description.lower() or 'user' in description.lower():
            conditions.append(description)

        return conditions

    @staticmethod
    async def _sleep(seconds: float) -> None:
        """Sleep for given seconds (async)."""
        import asyncio
        await asyncio.sleep(seconds)


# Factory function
def create_campaign_orchestrator(
    openai_api_key: str,
    base_url: Optional[str] = None,
    model_primary: str = "gpt-4o",
    model_fallback: str = "gpt-4o-mini",
    qdrant_url: Optional[str] = None,
    qdrant_api_key: Optional[str] = None,
    cohere_api_key: Optional[str] = None,
    enable_templates: bool = True,
    use_groq: bool = False,
    use_openrouter: bool = False
) -> CampaignOrchestrator:
    """
    Factory function to create CampaignOrchestrator instance.

    Args:
        openai_api_key: OpenAI API key (or GROQ API key if use_groq=True)
        qdrant_url: Optional Qdrant server URL
        qdrant_api_key: Optional Qdrant API key
        enable_templates: Whether to enable template recommendations
        use_groq: Whether to use GROQ instead of OpenAI

    Returns:
        Configured CampaignOrchestrator instance
    """
    if use_groq:
        # Use GROQ with OpenAI-compatible client
        openai_client = AsyncOpenAI(
            api_key=openai_api_key,
            base_url="https://api.groq.com/openai/v1"
        )
        logger.info("Using GROQ for campaign generation")
    elif use_openrouter:
        # Use OpenRouter with OpenAI-compatible client
        openai_client = AsyncOpenAI(
            api_key=openai_api_key,
            base_url=base_url
        )
        logger.info(f"Using OpenRouter for campaign generation with base_url: {base_url}")
    else:
        # Use OpenAI (or default)
        client_config = {"api_key": openai_api_key}
        if base_url:
            client_config["base_url"] = base_url
        openai_client = AsyncOpenAI(**client_config)
        logger.info(f"Using OpenAI-compatible client for campaign generation")

    qdrant_client = None
    if enable_templates and qdrant_url:
        qdrant_client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)

    return CampaignOrchestrator(
        openai_client=openai_client,
        qdrant_client=qdrant_client,
        cohere_api_key=cohere_api_key,
        enable_templates=enable_templates,
        use_groq=use_groq,
        use_openrouter=use_openrouter,
        model_primary=model_primary,
        model_fallback=model_fallback
    )