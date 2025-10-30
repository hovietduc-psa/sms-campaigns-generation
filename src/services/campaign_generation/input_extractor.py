"""
Input Extractor Service for parsing specific values from campaign descriptions.
Extracts discounts, products, collections, and other actionable details.
"""

import re
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class SchedulingInfo:
    """Scheduling information extracted from campaign description."""
    datetime: Optional[str] = None
    timezone: Optional[str] = None
    date_expression: Optional[str] = None
    parsed_datetime: Optional[datetime] = None

@dataclass
class BehavioralCondition:
    """Individual behavioral condition for audience targeting."""
    action: str
    operator: str  # "has" or "has_not"
    timeframe: str  # "30 days", "90 days", etc.
    include: bool = True

@dataclass
class AudienceCriteria:
    """Audience targeting criteria extracted from description."""
    behavioral_criteria: List[BehavioralCondition]
    logical_operator: str  # "AND" or "OR"
    description: str

@dataclass
class ProductInfo:
    """Product information extracted from description."""
    products: List[Dict[str, str]]  # List of products with name, url, etc.
    specific_product: Optional[str] = None
    product_url: Optional[str] = None

@dataclass
class ExtractedDetails:
    """Extracted details from campaign description."""
    discount_percentage: Optional[float] = None
    discount_amount: Optional[float] = None
    discount_type: Optional[str] = None
    products: List[str] = None
    collections: List[str] = None
    urgency: Optional[str] = None
    duration: Optional[str] = None
    target_audience: Optional[str] = None
    special_offer: Optional[str] = None
    seasonal_themes: List[str] = None

    def __post_init__(self):
        if self.products is None:
            self.products = []
        if self.collections is None:
            self.collections = []
        if self.seasonal_themes is None:
            self.seasonal_themes = []

class InputExtractor:
    """Extracts specific, actionable details from campaign descriptions."""

    def __init__(self):
        self.discount_patterns = [
            r'(\d+)%\s*off',
            r'(\d+)\s*percent\s*off',
            r'\$(\d+(?:\.\d{2})?)\s*off',
            r'save\s+(\d+)%',
            r'discount\s+of\s+(\d+)%'
        ]

        self.product_patterns = [
            r'\b(books?|shoes?|clothes?|dresses?|shirts?|pants?|jeans?|jackets?|coats?|bags?|phones?|laptops?|tablets?|watches?|jewelry?|cosmetics?|makeup?|skincare?|hair|beauty|electronics?|appliances?|furniture?|toys?|games?|sports?|fitness?|food|groceries|restaurant|coffee|pizza|burger|sushi)\b'
        ]

        self.collection_patterns = [
            r'(summer|winter|spring|fall|autumn)\s+(collection|line|series)',
            r'(new|latest|recent)\s+(arrival|collection|line|series)',
            r'(seasonal|holiday|christmas|thanksgiving|black\s+friday|cyber\s+monday|valentine|easter)\s+(collection|sale|offer)',
            r'(clearance|outlet|final)\s+(sale|collection)'
        ]

        self.urgency_patterns = [
            r'(limited\s+time|today\s+only|now|hurry|quick|fast|urgent|don\'t\s+miss|last\s+chance)',
            r'(flash\s+sale|quick\s+sale|doorbuster|early\s+bird)'
        ]

        self.duration_patterns = [
            r'(\d+)\s+(hours?|hrs?|days?|weeks?)',
            r'(today|tonight|this\s+week|this\s+weekend)',
            r'(ends?\s+(today|tonight|tomorrow|soon|shortly))'
        ]

    def extract_details(self, description: str) -> ExtractedDetails:
        """Extract all actionable details from campaign description."""
        description_lower = description.lower()

        details = ExtractedDetails()

        # Extract discount information
        details.discount_percentage = self._extract_discount_percentage(description_lower)
        details.discount_amount = self._extract_discount_amount(description_lower)
        details.discount_type = self._determine_discount_type(details)

        # Extract products and collections
        details.products = self._extract_products(description_lower)
        details.collections = self._extract_collections(description_lower)

        # Extract urgency and duration
        details.urgency = self._extract_urgency(description_lower)
        details.duration = self._extract_duration(description_lower)

        # Extract other details
        details.special_offer = self._extract_special_offer(description_lower)
        details.seasonal_themes = self._extract_seasonal_themes(description_lower)
        details.target_audience = self._extract_target_audience(description_lower)

        logger.info(f"Extracted details from description: {details}")
        return details

    def _extract_discount_percentage(self, text: str) -> Optional[float]:
        """Extract discount percentage from text."""
        for pattern in self.discount_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return float(match.group(1))
                except (ValueError, IndexError):
                    continue
        return None

    def _extract_discount_amount(self, text: str) -> Optional[float]:
        """Extract discount amount from text."""
        for pattern in self.discount_patterns:
            match = re.search(pattern, text)
            if match and '$' in pattern:
                try:
                    return float(match.group(1))
                except (ValueError, IndexError):
                    continue
        return None

    def _determine_discount_type(self, details: ExtractedDetails) -> Optional[str]:
        """Determine discount type based on extracted details."""
        if details.discount_percentage:
            return "percentage"
        elif details.discount_amount:
            return "fixed"
        elif details.special_offer and any(word in details.special_offer.split() for word in "free gift free shipping buy one get one bogo".split()):
            return "special"
        return None

    def _extract_products(self, text: str) -> List[str]:
        """Extract product mentions from text."""
        products = []
        for pattern in self.product_patterns:
            matches = re.findall(pattern, text)
            products.extend(matches)
        return list(set([p.strip() for p in products if p.strip()]))

    def _extract_collections(self, text: str) -> List[str]:
        """Extract collection mentions from text."""
        collections = []
        for pattern in self.collection_patterns:
            match = re.search(pattern, text)
            if match:
                collections.append(match.group(0))
        return list(set([c.strip() for c in collections if c.strip()]))

    def _extract_urgency(self, text: str) -> Optional[str]:
        """Extract urgency indicators from text."""
        for pattern in self.urgency_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return None

    def _extract_duration(self, text: str) -> Optional[str]:
        """Extract duration information from text."""
        for pattern in self.duration_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return None

    def _extract_special_offer(self, text: str) -> Optional[str]:
        """Extract special offer types from text."""
        special_offers = [
            "free gift", "free shipping", "buy one get one", "bogo",
            "buy one get one free", "2 for 1", "buy 1 get 1",
            "free trial", "free sample", "bonus points", "double points",
            "cashback", "rebate", "price match", "price drop"
        ]

        for offer in special_offers:
            if offer in text:
                return offer
        return None

    def _extract_seasonal_themes(self, text: str) -> List[str]:
        """Extract seasonal themes from text."""
        seasons = ["summer", "winter", "spring", "fall", "autumn"]
        holidays = [
            "christmas", "thanksgiving", "black friday", "cyber monday",
            "valentine", "easter", "halloween", "new year", "july 4th",
            "mother's day", "father's day", "labor day", "memorial day"
        ]

        themes = []
        for theme in seasons + holidays:
            if theme in text:
                themes.append(theme)
        return themes

    def _extract_target_audience(self, text: str) -> Optional[str]:
        """Extract target audience from text."""
        audience_patterns = [
            r'\b(new|existing|loyal|vip|premium)\s+(customers?|members?|subscribers?)\b',
            r'\b(first.?time|returning|repeat)\s+(customers?|buyers?|shoppers?)\b',
            r'\b(students?|seniors?|teachers?|military|veterans?)\b',
            r'\b(kids?|children|men|women|teens?|adults?)\b'
        ]

        for pattern in audience_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        return None

    def create_template_variables(self, details: ExtractedDetails) -> Dict[str, str]:
        """Create template variables from extracted details."""
        variables = {}

        if details.discount_percentage:
            variables["{{discount.percent}}"] = f"{details.discount_percentage}%"
            variables["{{discount.display}}"] = f"{details.discount_percentage}% OFF"
            variables["{{discount.type}}"] = "percentage"

        if details.discount_amount:
            variables["{{discount.amount}}"] = f"${details.discount_amount:.2f}"
            variables["{{discount.display}}"] = f"${details.discount_amount:.2f} OFF"
            variables["{{discount.type}}"] = "fixed"

        if details.products:
            variables["{{product.focus}}"] = details.products[0]
            variables["{{product.list}}"] = ", ".join(details.products[:3])

        if details.collections:
            variables["{{collection.name}}"] = details.collections[0]
            variables["{{collection.display}}"] = details.collections[0].title()

        if details.urgency:
            variables["{{urgency.message}}"] = details.urgency.title()

        if details.duration:
            variables["{{promotion.duration}}"] = details.duration

        if details.special_offer:
            variables["{{special.offer}}"] = details.special_offer.title()

        if details.seasonal_themes:
            variables["{{seasonal.theme}}"] = details.seasonal_themes[0].title()

        if details.target_audience:
            variables["{{audience.target}}"] = details.target_audience

        return variables

    def create_campaign_context(self, details: ExtractedDetails) -> Dict[str, Any]:
        """Create rich campaign context for content generation."""
        context = {
            "has_discount": bool(details.discount_percentage or details.discount_amount),
            "discount_info": {
                "percentage": details.discount_percentage,
                "amount": details.discount_amount,
                "type": details.discount_type
            },
            "product_focus": details.products[:2] if details.products else [],
            "collection_focus": details.collections[:2] if details.collections else [],
            "urgency_level": "high" if details.urgency else "medium",
            "seasonal_relevance": bool(details.seasonal_themes),
            "seasonal_themes": details.seasonal_themes,
            "promotion_duration": details.duration,
            "special_offer_type": details.special_offer,
            "target_audience": details.target_audience
        }

        return context

    def extract_scheduling(self, description: str) -> SchedulingInfo:
        """Extract scheduling information from campaign description."""
        scheduling_info = SchedulingInfo()

        # Look for scheduling patterns
        scheduling_patterns = [
            r'Schedule\s+Date:\s*([^\n]+)',
            r'Scheduled?\s+for\s+([^\n]+)',
            r'Send\s+(?:on|at)\s+([^\n]+)',
            r'(?:tomorrow|today|tonight|next\s+week|this\s+week)\s+at\s+([^\n]+)',
        ]

        for pattern in scheduling_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                scheduling_info.date_expression = match.group(1).strip()
                break

        # Extract timezone information
        timezone_patterns = [
            r'(\b(?:PST|EST|CST|MST|UTC|GMT|PDT|EDT|CDT|MDT)\b)',
            r'([A-Z]{3,4})\s*time',
        ]

        for pattern in timezone_patterns:
            match = re.search(pattern, description)
            if match:
                scheduling_info.timezone = match.group(1)
                break

        # Parse specific time expressions
        if scheduling_info.date_expression:
            parsed_dt = self._parse_datetime_expression(
                scheduling_info.date_expression,
                scheduling_info.timezone
            )
            scheduling_info.parsed_datetime = parsed_dt
            scheduling_info.datetime = parsed_dt.isoformat() if parsed_dt else None

        logger.info(f"Extracted schedule: {scheduling_info}")
        return scheduling_info

    def extract_audience_criteria(self, description: str) -> AudienceCriteria:
        """Extract audience targeting criteria from campaign description."""
        conditions = []

        # Look for behavioral patterns
        behavioral_patterns = [
            # Time-based engagement patterns
            (r'(?:customers?|users?|people)\s+(?:who\s+)?(?:have\s+)?(?:engaged|interacted|clicked|responded)\s+(?:with|to)?\s+us\s+in\s+the\s+past\s+(\d+)\s+(days?|weeks?|months?)',
             'engaged', True),
            (r'(?:customers?|users?|people)\s+(?:who\s+)?(?:haven\'t|have\s+not)\s+(?:engaged|interacted|clicked|responded)\s+(?:with|to)?\s+us\s+in\s+the\s+past\s+(\d+)\s+(days?|weeks?|months?)',
             'engaged', False),

            # Purchase behavior patterns
            (r'(?:customers?|users?|people)\s+(?:who\s+)?(?:have\s+)?(?:made|placed)\s+(?:a\s+)?(?:purchase|order)\s+(?:in\s+the\s+past\s+)?(\d+)\s+(days?|weeks?|months?)',
             'placed_order', True),
            (r'(?:customers?|users?|people)\s+(?:who\s+)?(?:haven\'t|have\s+not)\s+(?:made|placed)\s+(?:a\s+)?(?:purchase|order)\s+(?:during|in\s+the\s+past\s+)?(\d+)\s+(days?|weeks?|months?)',
             'placed_order', False),

            # Cart behavior patterns
            (r'(?:customers?|users?|people)\s+(?:who\s+)?(?:have\s+)?(?:added|put)\s+(?:items?|products?)\s+(?:to\s+)?(?:cart|shopping\s+cart)\s+(?:in\s+the\s+last\s+)?(\d+)\s+(days?|weeks?|months?)',
             'added_product_to_cart', True),
            (r'(?:customers?|users?|people)\s+(?:who\s+)?(?:have\s+)?(?:started|begun)\s+(?:a\s+)?checkout\s+(?:in\s+the\s+last\s+)?(\d+)\s+(days?|weeks?|months?)',
             'started_checkout', True),
            (r'(?:customers?|users?|people)\s+(?:who\s+)?(?:haven\'t|have\s+not)\s+(?:added|put)\s+(?:items?|products?)\s+(?:to\s+)?(?:cart|shopping\s+cart)\s+(?:in\s+the\s+last\s+)?(\d+)\s+(days?|weeks?|months?)',
             'added_product_to_cart', False),
            (r'(?:customers?|users?|people)\s+(?:who\s+)?(?:haven\'t|have\s+not)\s+(?:started|begun)\s+(?:a\s+)?checkout\s+(?:in\s+the\s+last\s+)?(\d+)\s+(days?|weeks?|months?)',
             'started_checkout', False),
        ]

        for pattern, action, include in behavioral_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                condition = BehavioralCondition(
                    action=action,
                    operator="has" if include else "has_not",
                    timeframe=match.group(1) + " " + match.group(2).rstrip('s'),  # Remove plural 's'
                    include=include
                )
                conditions.append(condition)

        # Determine logical operator
        logical_operator = "AND"  # Default
        if " or " in description.lower():
            logical_operator = "OR"
        elif " and " in description.lower():
            logical_operator = "AND"

        # Create description
        if conditions:
            description_parts = [f"{'Has' if c.include else 'Has not'} {c.action} in past {c.timeframe}" for c in conditions]
            description_text = f"Target audience: {' AND '.join(description_parts) if logical_operator == 'AND' else ' OR '.join(description_parts)}"
        else:
            description_text = "All customers"

        audience_criteria = AudienceCriteria(
            behavioral_criteria=conditions,
            logical_operator=logical_operator,
            description=description_text
        )

        logger.info(f"Extracted audience criteria: {audience_criteria}")
        return audience_criteria

    def extract_product_details(self, description: str) -> ProductInfo:
        """Extract product-specific information from description."""
        product_info = ProductInfo(products=[])

        # Look for specific product patterns
        product_patterns = [
            r'(?:promote|feature|highlight)\s+(?:a\s+)?(?:specific\s+)?product:\s*([^\n]+)',
            r'(?:product|item):\s*([^\n]+)',
            r'(?:specific\s+)?product:\s*\[([^\]]+)\]',
        ]

        for pattern in product_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                product_name = match.group(1).strip()
                product_info.specific_product = product_name
                break

        # Look for product URL patterns
        url_patterns = [
            r'(?:product\s+)?(?:link|url):\s*\[([^\]]+)\]',
            r'(?:product\s+)?(?:link|url):\s*([^\n]+)',
            r'(?:browse|shop)\s+([^\s]+\.(?:com|org|net|io)[^\s]*)',
        ]

        for pattern in url_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                product_url = match.group(1).strip()
                # Clean up URL
                if not product_url.startswith(('http://', 'https://')):
                    product_url = 'https://' + product_url
                product_info.product_url = product_url
                break

        # Create product list if we have specific product
        if product_info.specific_product:
            product_dict = {
                "name": product_info.specific_product,
                "url": product_info.product_url or "",
                "type": "specific"
            }
            product_info.products.append(product_dict)

        logger.info(f"Extracted product details: {product_info}")
        return product_info

    def extract_template_variables(self, description: str) -> Dict[str, str]:
        """Extract custom template variables from description."""
        variables = {}

        # Find all {{variable}} patterns
        template_patterns = [
            r'\{\{([^}]+)\}\}',
            r'\{\{\#if\s+([^}]+)\}\}([^{\[]*)\{\{\/if\}\}',  # Conditional blocks
        ]

        for pattern in template_patterns:
            matches = re.findall(pattern, description)
            if matches:
                if pattern == template_patterns[0]:  # Simple variables
                    for var in matches:
                        # Create default mappings for common variables
                        if var == 'cart.list':
                            variables[f'{{{var}}}'] = "{{cart.latest_items}}"
                        elif var == 'checkout.link':
                            variables[f'{{{var}}}'] = "{{merchant.checkout_url}}"
                        elif var.startswith('discount.'):
                            var_name = var.split('.')[1]
                            variables[f'{{{var}}}'] = f"{{{{discount.{var_name}}}}}"
                        elif var.startswith('customer.'):
                            var_name = var.split('.')[1]
                            variables[f'{{{var}}}'] = f"{{{{customer.{var_name}}}}}"
                        elif var.startswith('merchant.'):
                            var_name = var.split('.')[1]
                            variables[f'{{{var}}}'] = f"{{{{merchant.{var_name}}}}}"
                        else:
                            variables[f'{{{var}}}'] = f"{{{{{var}}}}}"
                else:  # Conditional blocks
                    for condition, content in matches:
                        variables[f'{{#if {condition}}}'] = content

        logger.info(f"Extracted template variables: {len(variables)} variables found")
        return variables

    def _parse_datetime_expression(self, expression: str, timezone: Optional[str] = None) -> Optional[datetime]:
        """Parse datetime expressions like 'Tomorrow 10am PST'."""
        try:
            from datetime import datetime, timedelta
            import pytz

            today = datetime.now()
            expression_lower = expression.lower()

            # Handle relative dates
            if "tomorrow" in expression_lower:
                target_date = today + timedelta(days=1)
            elif "today" in expression_lower:
                target_date = today
            elif "next week" in expression_lower:
                target_date = today + timedelta(weeks=1)
            elif "next monday" in expression_lower:
                days_ahead = 0 - today.weekday() + 7
                target_date = today + timedelta(days=days_ahead)
            else:
                target_date = today  # Default fallback

            # Extract time
            time_patterns = [
                r'(\d{1,2}):(\d{2})\s*(am|pm)',
                r'(\d{1,2})\s*(am|pm)',
                r'(\d{1,2})\s*o\'clock',
            ]

            for time_pattern in time_patterns:
                match = re.search(time_pattern, expression_lower)
                if match:
                    if len(match.groups()) == 3:  # HH:MM AM/PM
                        hour = int(match.group(1))
                        minute = int(match.group(2))
                        period = match.group(3)
                    elif len(match.groups()) == 2:  # H AM/PM
                        hour = int(match.group(1))
                        minute = 0
                        period = match.group(2)
                    else:  # H o'clock
                        hour = int(match.group(1))
                        minute = 0
                        period = "am"  # Default

                    # Convert to 24-hour format
                    if period == 'pm' and hour != 12:
                        hour += 12
                    elif period == 'am' and hour == 12:
                        hour = 0

                    target_date = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    break

            # Apply timezone
            if timezone:
                try:
                    tz = pytz.timezone(timezone)
                    target_date = tz.localize(target_date)
                except:
                    target_date = pytz.UTC.localize(target_date)
            else:
                target_date = pytz.UTC.localize(target_date)

            return target_date

        except Exception as e:
            logger.warning(f"Failed to parse datetime expression '{expression}': {e}")
            return None

    # Phase 3: Advanced Features Extraction

    def extract_ab_test_criteria(self, description: str) -> Dict[str, Any]:
        """Extract A/B testing criteria from campaign description."""
        ab_test_info = {
            'enabled': False,
            'variants': [],
            'success_metrics': [],
            'duration_days': 7,
            'experiment_name': None,
            'experiment_description': None
        }

        # Look for A/B testing patterns
        ab_test_patterns = [
            r'(?:test|experiment|split.?test|a/b test|ab test)',
            r'(?:variant|variation)s?',
            r'(?:control|treatment)',
            r'(?:compare|comparison)',
            r'(?:optimize|optimization)'
        ]

        description_lower = description.lower()
        has_ab_test = any(re.search(pattern, description_lower) for pattern in ab_test_patterns)

        if has_ab_test:
            ab_test_info['enabled'] = True

            # Extract experiment name
            name_patterns = [
                r'(?:test|experiment):\s*([^\n]+)',
                r'(?:a/b|ab)\s+test\s*(?:of|for)?\s*([^\n]+)',
                r'(?:split|splitting)\s+(?:test|testing)?\s*([^\n]+)'
            ]

            for pattern in name_patterns:
                match = re.search(pattern, description_lower)
                if match:
                    ab_test_info['experiment_name'] = match.group(1).strip().title()
                    break

            # Extract variants
            variant_patterns = [
                r'(?:variant|variation)\s*([A-Z]):\s*([^\n]+)',
                r'([A-Z]):\s*([^\n]+)\s+(?:vs|versus)',
                r'(?:option|choice)\s*(\d+):\s*([^\n]+)'
            ]

            for pattern in variant_patterns:
                matches = re.findall(pattern, description_lower)
                for match in matches:
                    variant = {
                        'id': match[0].upper(),
                        'name': f'Variant {match[0].upper()}',
                        'description': match[1].strip(),
                        'next_step_id': f"message_variant_{match[0].lower()}"
                    }
                    ab_test_info['variants'].append(variant)

            # If no explicit variants, create default variants
            if not ab_test_info['variants']:
                ab_test_info['variants'] = [
                    {'id': 'A', 'name': 'Variant A', 'description': 'Control message', 'next_step_id': 'message_variant_a'},
                    {'id': 'B', 'name': 'Variant B', 'description': 'Test message', 'next_step_id': 'message_variant_b'}
                ]

            # Extract success metrics
            metric_patterns = [
                r'(?:measure|track|metric)s?:\s*([^\n]+)',
                r'(?:success|goal|objective)s?:\s*([^\n]+)',
                r'(?:optimize|optimization)\s+(?:for|to)?\s*([^\n]+)'
            ]

            for pattern in metric_patterns:
                match = re.search(pattern, description_lower)
                if match:
                    metrics_text = match.group(1)
                    # Split by common separators
                    metrics = re.split(r'[,;]|\s+and\s+|\s+or\s+', metrics_text)
                    ab_test_info['success_metrics'] = [m.strip() for m in metrics if m.strip()]
                    break

            # Default metrics if none found
            if not ab_test_info['success_metrics']:
                ab_test_info['success_metrics'] = ['conversion_rate', 'click_rate']

            # Extract duration
            duration_patterns = [
                r'(\d+)\s+days?',
                r'(\d+)\s+weeks?',
                r'run\s+(?:for|during)?\s*(\d+)\s+(days?|weeks?)'
            ]

            for pattern in duration_patterns:
                match = re.search(pattern, description_lower)
                if match:
                    duration = int(match.group(1))
                    if 'week' in match.group(2).lower():
                        duration *= 7
                    ab_test_info['duration_days'] = duration
                    break

        logger.info(f"Extracted A/B test criteria: enabled={ab_test_info['enabled']}, variants={len(ab_test_info['variants'])}")
        return ab_test_info

    def extract_rate_limiting_criteria(self, description: str) -> Dict[str, Any]:
        """Extract rate limiting criteria from campaign description."""
        rate_limit_info = {
            'enabled': False,
            'daily_limit': 10,
            'hourly_limit': 1,
            'cooldown_minutes': 60,
            'business_hours_only': False,
            'weekend_exclusion': False
        }

        description_lower = description.lower()

        # Look for rate limiting patterns
        rate_limit_patterns = [
            r'(?:rate\s*limit|limit\s*rate|frequency\s*cap)',
            r'(?:compliance|regulation|spam\s*prevent)',
            r'(?:don\'t|do not)\s+(?:spam|overwhelm|overload)',
            r'(?:maximum|max|limit)\s+(\d+)\s+(?:messages?|texts?|sms?)\s+(?:per|a)\s+(day|daily|hour|hourly)',
            r'(?:only|just)\s+(\d+)\s+(?:messages?|texts?|sms?)\s+(?:per|a)\s+(day|daily|hour|hourly)',
        ]

        has_rate_limit = any(re.search(pattern, description_lower) for pattern in rate_limit_patterns)

        if has_rate_limit:
            rate_limit_info['enabled'] = True

            # Extract daily limits
            daily_patterns = [
                r'(\d+)\s+(?:messages?|texts?|sms?)\s+(?:per|a)\s+(day|daily)',
                r'(?:daily|day)\s+(?:limit|cap|max)\s*(?:of)?\s*(\d+)',
                r'(?:maximum|max)\s+(\d+)\s+(?:per\s*)?(day|daily)'
            ]

            for pattern in daily_patterns:
                match = re.search(pattern, description_lower)
                if match:
                    rate_limit_info['daily_limit'] = int(match.group(1))
                    break

            # Extract hourly limits
            hourly_patterns = [
                r'(\d+)\s+(?:messages?|texts?|sms?)\s+(?:per|a)\s+(hour|hourly)',
                r'(?:hourly|hour)\s+(?:limit|cap|max)\s*(?:of)?\s*(\d+)',
                r'(?:maximum|max)\s+(\d+)\s+(?:per\s*)?(hour|hourly)'
            ]

            for pattern in hourly_patterns:
                match = re.search(pattern, description_lower)
                if match:
                    rate_limit_info['hourly_limit'] = int(match.group(1))
                    break

            # Extract cooldown periods
            cooldown_patterns = [
                r'(\d+)\s+(?:minutes?|mins?)\s+(?:between|wait|cooldown)',
                r'(?:wait|cooldown|gap)\s+(?:for)?\s*(\d+)\s+(?:minutes?|mins?)',
                r'(?:spacing|interval)\s*(?:of)?\s*(\d+)\s+(?:minutes?|mins?)'
            ]

            for pattern in cooldown_patterns:
                match = re.search(pattern, description_lower)
                if match:
                    rate_limit_info['cooldown_minutes'] = int(match.group(1))
                    break

            # Check for business hours restrictions
            business_hours_patterns = [
                r'business\s*hours?\s*(?:only)?',
                r'(?:during|while)\s+business\s*hours?',
                r'(?:no|avoid)\s+(?:messages|texts)\s+(?:outside|after)\s+business\s*hours?'
            ]

            rate_limit_info['business_hours_only'] = any(
                re.search(pattern, description_lower) for pattern in business_hours_patterns
            )

            # Check for weekend exclusion
            weekend_patterns = [
                r'(?:no|avoid|don\'t)\s+(?:messages|texts)\s+(?:on|during)\s+(?:weekends?|the\s+weekend)',
                r'weekends?\s*(?:excluded|only|only\s+weekdays)',
                r'(?:only|just)\s+weekdays?'
            ]

            rate_limit_info['weekend_exclusion'] = any(
                re.search(pattern, description_lower) for pattern in weekend_patterns
            )

        logger.info(f"Extracted rate limiting criteria: enabled={rate_limit_info['enabled']}, daily={rate_limit_info['daily_limit']}")
        return rate_limit_info

    def extract_audience_split_criteria(self, description: str) -> Dict[str, Any]:
        """Extract audience splitting criteria from campaign description."""
        split_info = {
            'enabled': False,
            'split_type': 'random',
            'split_percentages': {'group_a': 50, 'group_b': 50},
            'split_criteria': {},
            'group_names': {'group_a': 'Group A', 'group_b': 'Group B'},
            'next_steps': {'group_a': 'path_a', 'group_b': 'path_b'}
        }

        description_lower = description.lower()

        # Look for audience splitting patterns
        split_patterns = [
            r'(?:split|divide|separate)\s+(?:audience|customers?|users?|people)',
            r'(?:segment|group)\s+(?:audience|customers?|users?|people)',
            r'(?:half|50%|fifty\s*percent)\s+(?:of\s*)?(?:audience|customers?|users?|people)',
            r'(?:a\s*)?(?:vs|versus)\s+(?:b\s*)?',
            r'(?:control|treatment)\s+group',
        ]

        has_split = any(re.search(pattern, description_lower) for pattern in split_patterns)

        if has_split:
            split_info['enabled'] = True

            # Extract split percentages
            percentage_patterns = [
                r'(\d+)%\s+(?:and|vs|versus)\s+(\d+)%',
                r'(\d+)%\s+(?:for|to)\s+(?:group|segment)\s*([ab])',
                r'(?:split|divide)\s+(\d+)%[/-](\d+)%'
            ]

            for pattern in percentage_patterns:
                match = re.search(pattern, description_lower)
                if match:
                    split_info['split_percentages']['group_a'] = int(match.group(1))
                    split_info['split_percentages']['group_b'] = int(match.group(2))
                    break

            # Extract group names
            group_name_patterns = [
                r'group\s*([ab]):\s*([^\n,;]+)',
                r'([^\n,;]+)\s+(?:vs|versus)\s+([^\n,;]+)',
                r'(?:control|treatment):\s*([^\n,;]+)'
            ]

            for pattern in group_name_patterns:
                matches = re.findall(pattern, description_lower)
                for match in matches:
                    if len(match) == 2:
                        if match[0].lower() in ['a', 'b']:
                            group_key = f"group_{match[0].lower()}"
                            split_info['group_names'][group_key] = match[1].strip().title()
                        else:
                            split_info['group_names']['group_a'] = match[0].strip().title()
                            split_info['group_names']['group_b'] = match[1].strip().title()

            # Extract split type
            if 'random' in description_lower:
                split_info['split_type'] = 'random'
            elif 'behavioral' in description_lower:
                split_info['split_type'] = 'behavioral'
            elif 'demographic' in description_lower:
                split_info['split_type'] = 'demographic'
            elif 'purchase' in description_lower:
                split_info['split_type'] = 'purchase_history'

            # Extract specific criteria for each group
            criteria_patterns = [
                r'group\s*([ab]):\s*([^\n]+)',
                r'([^\n]+)\s+(?:goes|should)\s+to\s+group\s*([ab])'
            ]

            for pattern in criteria_patterns:
                matches = re.findall(pattern, description_lower)
                for match in matches:
                    group_key = f"group_{match[0].lower()}" if match[0].lower() in ['a', 'b'] else f"group_{match[1].lower()}"
                    criteria_text = match[1] if match[0].lower() in ['a', 'b'] else match[0]
                    split_info['split_criteria'][group_key] = criteria_text.strip()

        logger.info(f"Extracted audience split criteria: enabled={split_info['enabled']}, type={split_info['split_type']}")
        return split_info

    def extract_delay_timing(self, description: str) -> Dict[str, Any]:
        """Extract delay timing information from campaign description."""
        delay_info = {
            'enabled': False,
            'minutes': 0,
            'hours': 0,
            'days': 0,
            'business_hours_only': False,
            'max_wait_days': 7
        }

        description_lower = description.lower()

        # Look for delay patterns
        delay_patterns = [
            r'(?:wait|delay|pause)\s+(?:for)?\s*(\d+)\s+(minutes?|mins?|hours?|hrs?|days?)',
            r'(?:after|in)\s+(\d+)\s+(minutes?|mins?|hours?|hrs?|days?)',
            r'(?:send|deliver)\s+(?:after|in)\s+(\d+)\s+(minutes?|mins?|hours?|hrs?|days?)',
            r'(\d+)\s+(minutes?|mins?|hours?|hrs?|days?)\s+(?:later|after|wait)'
        ]

        has_delay = any(re.search(pattern, description_lower) for pattern in delay_patterns)

        if has_delay:
            delay_info['enabled'] = True

            # Extract specific time units
            for pattern in delay_patterns:
                match = re.search(pattern, description_lower)
                if match:
                    amount = int(match.group(1))
                    unit = match.group(2).lower()

                    if unit.startswith('min'):
                        delay_info['minutes'] = amount
                    elif unit.startswith('hr'):
                        delay_info['hours'] = amount
                    elif unit.startswith('day'):
                        delay_info['days'] = amount
                    break

            # Check for business hours restriction
            business_hours_patterns = [
                r'business\s*hours?\s*(?:only)?',
                r'(?:during|while)\s+business\s*hours?'
            ]

            delay_info['business_hours_only'] = any(
                re.search(pattern, description_lower) for pattern in business_hours_patterns
            )

            # Extract max wait days
            max_wait_patterns = [
                r'(?:maximum|max)\s+(?:wait|delay)\s*(?:of)?\s*(\d+)\s+days?',
                r'wait\s*(?:no\s*more\s*than|up\s*to)\s*(\d+)\s+days?'
            ]

            for pattern in max_wait_patterns:
                match = re.search(pattern, description_lower)
                if match:
                    delay_info['max_wait_days'] = int(match.group(1))
                    break

        logger.info(f"Extracted delay timing: enabled={delay_info['enabled']}, total_minutes={delay_info['minutes'] + delay_info['hours']*60 + delay_info['days']*24*60}")
        return delay_info

    