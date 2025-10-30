"""
Advanced Template Engine for complex variable mapping and custom template integration.
Handles sophisticated merchant requirements and dynamic variable substitution.
"""

import re
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TemplateMapping:
    """Template variable mapping configuration."""
    source_pattern: str
    target_variables: List[str]
    transformation_rule: Optional[str] = None
    default_value: Optional[str] = None

@dataclass
class CustomMessageStructure:
    """Custom message structure from merchant input."""
    step_type: str
    content_pattern: str
    required_variables: List[str]
    conditional_logic: Dict[str, Any]
    trigger_phrases: List[str]

class AdvancedTemplateEngine:
    """Advanced template processing engine for complex business requirements."""

    def __init__(self):
        # Advanced variable mapping patterns
        self.variable_mappings = [
            # Cart-related mappings
            TemplateMapping(
                source_pattern=r'(?:cart\.list|list of cart items|items in cart)',
                target_variables=['{{cart.list}}', '{{cart.items}}'],
                transformation_rule='generate_sample_items'
            ),
            TemplateMapping(
                source_pattern=r'(?:cart\.item_count|number of items|item count)',
                target_variables=['{{cart.item_count}}', '{{cart.count}}'],
                default_value='items'
            ),
            TemplateMapping(
                source_pattern=r'(?:checkout\.link|purchase link|order link)',
                target_variables=['{{checkout.link}}', '{{checkout.url}}'],
                default_value='{{merchant.url}}'
            ),
            TemplateMapping(
                source_pattern=r'(?:discount\.label|discount code|promo code)',
                target_variables=['{{discount.label}}', '{{discount.code}}'],
                transformation_rule='generate_promo_code'
            ),
            TemplateMapping(
                source_pattern=r'(?:payment\.method|billing method)',
                target_variables=['{{payment.method}}', '{{billing.type}}']
            ),
        ]

        # Message structure templates
        self.structure_templates = {
            'purchase_offer': {
                'pattern': r'Your favorites are going fast.*?Reply\s+(\w+).*?{{(checkout|discount)\.link}}',
                'required_vars': ['{{cart.list}}', '{{discount.label}}', '{{checkout.link}}'],
                'trigger_words': ['BUY', 'PURCHASE', 'ORDER', 'SHOP']
            },
            'cart_reminder': {
                'pattern': r'Your\s+(\w+)\s+are waiting',
                'required_vars': ['{{cart.items}}', '{{checkout.link}}'],
                'trigger_words': ['CHECKOUT', 'COMPLETE', 'FINISH']
            },
            'payment_request': {
                'pattern': r'To\s+finalize.*?Order\s+here:\s*{{checkout\.link}}',
                'required_vars': ['{{checkout.link}}', '{{payment.method}}'],
                'trigger_words': ['PAY', 'SEND', 'PROCEED']
            }
        }

    def extract_custom_structure(self, description: str) -> List[CustomMessageStructure]:
        """Extract custom message structures from merchant description."""
        structures = []

        # Look for message content patterns
        message_patterns = [
            r'(?:Message Content|Copy|Template):\s*"([^"]*?)"\s*Reply\s+(\w+)\s*',
            r'(?:initial step|first step)\s*should\s*be\s*a\s*(\w+)\s*offer\s*with\s*this\s*copy:\s*"([^"]*?)"',
            r'(?:step\s+\d+|message)\s*content:\s*"([^"]*?)"'
        ]

        for pattern in message_patterns:
            matches = re.finditer(pattern, description, re.IGNORECASE)
            for match in matches:
                if len(match.groups()) >= 2:
                    content_template = match.group(1)
                    trigger_word = match.group(2).upper()

                    # Determine step type
                    step_type = self._classify_message_type(content_template)

                    # Extract required variables
                    required_vars = re.findall(r'\{\{(\w+(?:\.\w+)*)\}\}', content_template)

                    # Extract conditional logic
                    conditional_logic = self._extract_conditional_logic(content_template)

                    structure = CustomMessageStructure(
                        step_type=step_type,
                        content_pattern=content_template,
                        required_variables=required_vars,
                        conditional_logic=conditional_logic,
                        trigger_phrases=[trigger_word]
                    )

                    structures.append(structure)
                    logger.info(f"Extracted custom structure: {step_type} with {len(required_vars)} variables")

        return structures

    def _classify_message_type(self, content: str) -> str:
        """Classify message type based on content patterns."""
        content_lower = content.lower()

        if any(phrase in content_lower for phrase in ['buy', 'purchase', 'order']):
            return 'purchase_offer'
        elif any(phrase in content_lower for phrase in ['waiting', 'still there', 'are waiting']):
            return 'cart_reminder'
        elif any(phrase in content_lower for phrase in ['finalize', 'complete', 'payment']):
            return 'payment_request'
        elif 'discount' in content_lower or 'off' in content_lower:
            return 'discount_offer'
        else:
            return 'custom'

    def _extract_conditional_logic(self, content: str) -> Dict[str, Any]:
        """Extract conditional logic patterns from template."""
        logic = {}

        # Extract {{#if condition}}...{{/if}} patterns
        if_patterns = re.findall(r'\{\{#if\s+(\w+)\}\}(.*?)\{\{/if\}\}', content)

        for pattern in if_patterns:
            condition_var = pattern[0]
            condition_content = pattern[1]
            logic[condition_var] = {
                'type': 'conditional',
                'content': condition_content
            }

        return logic

    def map_variables(self, description: str, campaign_context: Dict[str, Any]) -> Dict[str, str]:
        """Map description variables to system variables."""
        variable_map = {}

        # Apply mapping patterns
        for mapping in self.variable_mappings:
            matches = re.findall(mapping.source_pattern, description, re.IGNORECASE)
            if matches:
                for target_var in mapping.target_variables:
                    if mapping.transformation_rule:
                        value = self._apply_transformation(mapping.transformation_rule, campaign_context)
                    elif mapping.default_value:
                        value = mapping.default_value
                    else:
                        value = matches[0]

                    variable_map[target_var] = value
                    logger.info(f"Mapped variable: {target_var} = {value}")

        return variable_map

    def _apply_transformation(self, rule: str, context: Dict[str, Any]) -> str:
        """Apply transformation rule to generate value."""
        if rule == 'generate_sample_items':
            # Generate sample cart items
            sample_items = [
                "Summer Dress - Blue, Size M",
                "Leather Handbag - Tan",
                "Designer Sunglasses - Black",
                "Casual Sneakers - White, Size 8"
            ]
            return " | ".join(sample_items[:3])

        elif rule == 'generate_promo_code':
            # Generate promotional code based on context
            import random
            import string
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            return f"SAVE{code}"

        elif rule and context.get(rule):
            return str(context.get(rule, ""))

        return ""

    def process_custom_template(self, template_content: str, variable_map: Dict[str, str],
                           conditional_logic: Dict[str, Any]) -> str:
        """Process custom template with variable substitution and conditional logic."""
        processed_content = template_content

        # Apply variable mappings
        for var_key, var_value in variable_map.items():
            processed_content = processed_content.replace(var_key, var_value)

        # Process conditional logic
        for condition_var, condition_data in conditional_logic.items():
            if condition_data['type'] == 'conditional':
                # Check if condition should be applied
                condition_met = self._evaluate_condition(condition_var, condition_data, variable_map)

                if condition_met:
                    processed_content = processed_content.replace(
                        f"{{#if {condition_var}}}{condition_data['content']}{{/if}}",
                        condition_data['content']
                    )
                else:
                    processed_content = processed_content.replace(
                        f"{{#if {condition_var}}}{condition_data['content']}{{/if}}",
                        ""
                    )

        return processed_content

    def _evaluate_condition(self, condition_var: str, condition_data: Dict[str, Any],
                          variable_map: Dict[str, str]) -> bool:
        """Evaluate whether a condition should be applied."""
        # Check if the condition variable exists and has a value
        for var_key in variable_map:
            if condition_var in var_key or condition_var.replace('.', '_') in var_key:
                return True

        return False

    def generate_enhanced_step(self, base_step: Dict[str, Any], custom_structure: CustomMessageStructure,
                             variable_map: Dict[str, str]) -> Dict[str, Any]:
        """Generate enhanced step using custom structure and variable mapping."""
        enhanced_step = base_step.copy()

        # Process custom template
        if custom_structure.content_pattern:
            processed_content = self.process_custom_template(
                custom_structure.content_pattern,
                variable_map,
                custom_structure.conditional_logic
            )
            enhanced_step['content'] = processed_content
            enhanced_step['text'] = processed_content

        # Add step type classification
        enhanced_step['custom_step_type'] = custom_structure.step_type

        # Add trigger phrases
        if custom_structure.trigger_phrases:
            enhanced_step['trigger_phrases'] = custom_structure.trigger_phrases

        # Add required variables
        enhanced_step['required_variables'] = custom_structure.required_variables

        return enhanced_step

    def validate_variable_compliance(self, step: Dict[str, Any],
                                custom_structure: CustomMessageStructure) -> Dict[str, Any]:
        """Validate that required variables are present in the step content."""
        validation = {
            'is_compliant': True,
            'missing_variables': [],
            'present_variables': []
        }

        content = step.get('content', '')

        for required_var in custom_structure.required_variables:
            if required_var in content:
                validation['present_variables'].append(required_var)
            else:
                validation['is_compliant'] = False
                validation['missing_variables'].append(required_var)

        return validation