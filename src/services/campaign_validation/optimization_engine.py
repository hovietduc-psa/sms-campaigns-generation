"""
Optimization Suggestion Engine - Provides suggestions for improving campaigns.
"""
import logging
from typing import Dict, Any, List, Optional

from .schema_validator import ValidationIssue

logger = logging.getLogger(__name__)


class OptimizationSuggestion:
    """Represents an optimization suggestion."""

    def __init__(
        self,
        category: str,  # "cost", "performance", "engagement", "conversion"
        priority: str,  # "high", "medium", "low"
        title: str,
        description: str,
        impact: str,  # "high", "medium", "low"
        effort: str,  # "high", "medium", "low"
        estimated_savings: Optional[str] = None,
        step_id: Optional[str] = None
    ):
        self.category = category
        self.priority = priority
        self.title = title
        self.description = description
        self.impact = impact
        self.effort = effort
        self.estimated_savings = estimated_savings
        self.step_id = step_id

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "category": self.category,
            "priority": self.priority,
            "title": self.title,
            "description": self.description,
            "impact": self.impact,
            "effort": self.effort,
            "estimated_savings": self.estimated_savings,
            "step_id": self.step_id
        }

    def __repr__(self) -> str:
        return f"[{self.priority.upper()}] {self.title}"


class OptimizationEngine:
    """
    Analyzes campaigns and provides optimization suggestions.

    Focuses on:
    - Cost reduction (SMS segments, unnecessary steps)
    - Performance improvement (timing, flow optimization)
    - Engagement optimization (personalization, CTAs)
    - Conversion optimization (urgency, offers, A/B testing)
    """

    def __init__(self):
        self.suggestions: List[OptimizationSuggestion] = []

    def analyze(self, campaign_json: Dict[str, Any]) -> List[OptimizationSuggestion]:
        """
        Analyze campaign and generate optimization suggestions.

        Args:
            campaign_json: Campaign JSON dictionary

        Returns:
            List of optimization suggestions
        """
        self.suggestions = []

        if "steps" not in campaign_json or not isinstance(campaign_json["steps"], list):
            return self.suggestions

        self._analyze_cost_optimization(campaign_json)
        self._analyze_performance_optimization(campaign_json)
        self._analyze_engagement_optimization(campaign_json)
        self._analyze_conversion_optimization(campaign_json)
        self._analyze_phase4_analytics_optimization(campaign_json)
        self._analyze_phase5_ecommerce_optimization(campaign_json)

        # Sort by priority
        priority_order = {"high": 0, "medium": 1, "low": 2}
        self.suggestions.sort(key=lambda s: priority_order.get(s.priority, 3))

        return self.suggestions

    def _analyze_cost_optimization(self, campaign_json: Dict[str, Any]) -> None:
        """Analyze opportunities for cost reduction."""
        message_steps = [
            s for s in campaign_json["steps"]
            if isinstance(s, dict) and s.get("type") == "message"
        ]

        # Check for long messages that could be shortened
        long_messages = [
            (s.get("id"), s.get("text", ""))
            for s in message_steps
            if isinstance(s.get("text"), str) and len(s.get("text", "")) > 160
        ]

        if long_messages:
            total_chars = sum(len(text) for _, text in long_messages)
            avg_length = total_chars / len(long_messages)

            # Estimate savings: 2-segment vs 1-segment SMS cost
            # Assume $0.0079 per segment (Twilio pricing)
            extra_segments = sum((len(text) - 1) // 153 for _, text in long_messages if len(text) > 160)
            estimated_savings = f"${extra_segments * 0.0079:.2f} per send"

            self.suggestions.append(OptimizationSuggestion(
                category="cost",
                priority="medium",
                title="Shorten messages to reduce SMS costs",
                description=f"{len(long_messages)} message(s) exceed 160 chars (avg {avg_length:.0f} chars). "
                           f"Shortening to single SMS segments could save {estimated_savings}.",
                impact="medium",
                effort="low",
                estimated_savings=estimated_savings
            ))

        # Check for redundant delay steps
        delay_steps = [
            s for s in campaign_json["steps"]
            if isinstance(s, dict) and s.get("type") == "delay"
        ]

        if len(delay_steps) > 3:
            self.suggestions.append(OptimizationSuggestion(
                category="cost",
                priority="low",
                title="Consider consolidating delay steps",
                description=f"Campaign has {len(delay_steps)} delay steps. "
                           "Consolidating may simplify flow and reduce execution overhead.",
                impact="low",
                effort="medium"
            ))

        # Check for too many messages
        if len(message_steps) > 5:
            est_cost_per_1000 = len(message_steps) * 0.0079 * 1000
            self.suggestions.append(OptimizationSuggestion(
                category="cost",
                priority="medium",
                title="Reduce number of messages",
                description=f"Campaign sends {len(message_steps)} messages. "
                           f"Each additional message costs ~${est_cost_per_1000:.2f} per 1,000 recipients. "
                           "Consider combining or removing less effective messages.",
                impact="high",
                effort="medium",
                estimated_savings=f"${est_cost_per_1000 * 0.2:.2f}+ per 1,000 sends"
            ))

    def _analyze_phase5_ecommerce_optimization(self, campaign_json: Dict[str, Any]) -> None:
        """Analyze Phase 5 e-commerce integration opportunities."""
        steps = campaign_json.get("steps", [])

        # Analyze PRODUCT_CHOICE nodes for e-commerce optimization
        product_choice_steps = [s for s in steps if isinstance(s, dict) and s.get("type") == "product_choice"]

        for step in product_choice_steps:
            step_id = step.get("id")
            products = step.get("products", [])
            product_selection = step.get("productSelection", "manually")
            product_images = step.get("productImages", True)

            # Check for product selection optimization
            if product_selection == "manually" and len(products) < 3:
                self.suggestions.append(OptimizationSuggestion(
                    category="ecommerce",
                    priority="medium",
                    title="Add more product options",
                    description=f"Product choice step '{step_id}' has only {len(products)} products. "
                               "Consider adding 3-5 product options for better selection.",
                    impact="medium",
                    effort="low",
                    step_id=step_id
                ))

            # Check for product images
            if not product_images:
                self.suggestions.append(OptimizationSuggestion(
                    category="ecommerce",
                    priority="medium",
                    title="Enable product images",
                    description=f"Product choice step '{step_id}' has product images disabled. "
                               "Visual product selection typically increases conversion rates by 30%.",
                    impact="medium",
                    effort="low",
                    step_id=step_id
                ))

            # Check for automatic product selection
            if product_selection == "manually":
                self.suggestions.append(OptimizationSuggestion(
                    category="ecommerce",
                    priority="low",
                    title="Consider automatic product selection",
                    description=f"Product choice step '{step_id}' uses manual selection. "
                               "Consider 'popularity' or 'recently_viewed' for personalized recommendations.",
                    impact="medium",
                    effort="medium",
                    step_id=step_id
                ))

        # Analyze PURCHASE_OFFER nodes for offer optimization
        purchase_offer_steps = [s for s in steps if isinstance(s, dict) and s.get("type") == "purchase_offer"]

        for step in purchase_offer_steps:
            step_id = step.get("id")
            discount = step.get("discount", False)
            discount_type = step.get("discountType", "")
            skip_recent_orders = step.get("skipForRecentOrders", True)

            # Check for discount optimization
            if not discount:
                self.suggestions.append(OptimizationSuggestion(
                    category="ecommerce",
                    priority="high",
                    title="Add discount to purchase offer",
                    description=f"Purchase offer step '{step_id}' has no discount. "
                               "Purchase offers with discounts typically have 2-3x higher conversion rates.",
                    impact="high",
                    effort="low",
                    step_id=step_id
                ))

            # Check for recent order filtering
            if not skip_recent_orders:
                self.suggestions.append(OptimizationSuggestion(
                    category="ecommerce",
                    priority="medium",
                    title="Enable recent order filtering",
                    description=f"Purchase offer step '{step_id}' doesn't skip recent orders. "
                               "Avoid offering to customers who recently purchased to reduce annoyance.",
                    impact="medium",
                    effort="low",
                    step_id=step_id
                ))

        # Analyze PURCHASE nodes for checkout optimization
        purchase_steps = [s for s in steps if isinstance(s, dict) and s.get("type") == "purchase"]

        for step in purchase_steps:
            step_id = step.get("id")
            cart_source = step.get("cartSource", "manual")
            send_reminder = step.get("sendReminderForNonPurchasers", False)
            allow_automatic_payment = step.get("allowAutomaticPayment", False)

            # Check for reminder optimization
            if not send_reminder:
                self.suggestions.append(OptimizationSuggestion(
                    category="ecommerce",
                    priority="medium",
                    title="Enable purchase reminders",
                    description=f"Purchase step '{step_id}' doesn't send reminders for non-purchasers. "
                               "Purchase reminders can recover 15-20% of abandoned carts.",
                    impact="medium",
                    effort="low",
                    step_id=step_id
                ))

            # Check for automatic payment
            if not allow_automatic_payment:
                self.suggestions.append(OptimizationSuggestion(
                    category="ecommerce",
                    priority="low",
                    title="Consider automatic payment option",
                    description=f"Purchase step '{step_id}' doesn't allow automatic payment. "
                               "Automatic payment can increase completion rates for returning customers.",
                    impact="low",
                    effort="medium",
                    step_id=step_id
                ))

        # Cross-sell and upsell opportunities
        e_commerce_steps = product_choice_steps + purchase_offer_steps + purchase_steps

        if len(e_commerce_steps) >= 2:
            # Check for cross-sell opportunities
            has_product_choice = len(product_choice_steps) > 0
            has_purchase_offer = len(purchase_offer_steps) > 0

            if has_product_choice and not has_purchase_offer:
                self.suggestions.append(OptimizationSuggestion(
                    category="ecommerce",
                    priority="medium",
                    title="Add purchase offer after product choice",
                    description="Campaign has product selection but no purchase offer step. "
                               "Consider adding a purchase offer to convert product interest into sales.",
                    impact="high",
                    effort="medium"
                ))

        # Check for cart recovery flow completeness
        message_steps = [s for s in steps if isinstance(s, dict) and s.get("type") == "message"]

        if len(purchase_offer_steps) > 0 and len(message_steps) > 2:
            # Check if campaign has proper abandoned cart flow
            has_delay_steps = any(s.get("type") == "delay" for s in steps)

            if not has_delay_steps:
                self.suggestions.append(OptimizationSuggestion(
                    category="ecommerce",
                    priority="medium",
                    title="Add delays for cart recovery timing",
                    description="Cart recovery campaigns work best with strategic delays (2-4 hours, 24 hours). "
                               "Consider adding delay steps between messages.",
                    impact="medium",
                    effort="low"
                ))

        # Suggest advanced e-commerce features if missing
        all_step_types = [s.get("type") for s in steps]
        e_commerce_features = ["product_choice", "purchase_offer", "purchase"]
        has_any_ecommerce = any(feature in all_step_types for feature in e_commerce_features)

        if len(message_steps) > 3 and not has_any_ecommerce:
            self.suggestions.append(OptimizationSuggestion(
                category="ecommerce",
                priority="medium",
                title="Add e-commerce features to convert engagement",
                description="Campaign has multiple messages but no e-commerce features. "
                           "Consider adding product choice or purchase offers to monetize engagement.",
                impact="high",
                effort="medium"
            ))

    def _analyze_phase4_analytics_optimization(self, campaign_json: Dict[str, Any]) -> None:
        """Analyze Phase 4 analytics and optimization opportunities."""
        steps = campaign_json.get("steps", [])

        # Analyze EXPERIMENT nodes for A/B testing optimization
        experiment_steps = [s for s in steps if isinstance(s, dict) and s.get("type") == "experiment"]

        for step in experiment_steps:
            step_id = step.get("id")
            experiment_config = step.get("experimentConfig", {})
            variants = step.get("variants", [])
            split_percentages = step.get("splitPercentages", [])

            # Check for proper A/B test structure
            if len(variants) < 2:
                self.suggestions.append(OptimizationSuggestion(
                    category="analytics",
                    priority="high",
                    title="Add test variants for A/B experiment",
                    description=f"Experiment step '{step_id}' has fewer than 2 variants. "
                               "A/B testing requires at least 2 variants for meaningful comparison.",
                    impact="high",
                    effort="medium",
                    step_id=step_id
                ))

            # Check split percentage distribution
            if split_percentages and len(split_percentages) >= 2:
                # Check for balanced splits (50/50 is optimal for statistical significance)
                if abs(split_percentages[0] - split_percentages[1]) > 20:
                    self.suggestions.append(OptimizationSuggestion(
                        category="analytics",
                        priority="medium",
                        title="Balance A/B test split percentages",
                        description=f"Current split is {split_percentages[0]}%/{split_percentages[1]}%. "
                                   "More balanced splits (e.g., 50/50) achieve statistical significance faster.",
                        impact="medium",
                        effort="low",
                        step_id=step_id
                    ))

            # Suggest adding control group if missing
            if not any("control" in str(v).lower() for v in variants):
                self.suggestions.append(OptimizationSuggestion(
                    category="analytics",
                    priority="medium",
                    title="Add control group to A/B test",
                    description="Consider adding a control group (existing message) as baseline "
                               "for measuring experiment impact accurately.",
                    impact="medium",
                    effort="low",
                    step_id=step_id
                ))

        # Analyze RATE_LIMIT nodes for compliance optimization
        rate_limit_steps = [s for s in steps if isinstance(s, dict) and s.get("type") == "rate_limit"]

        for step in rate_limit_steps:
            step_id = step.get("id")
            occurrences = step.get("occurrences", "1")
            period = step.get("period", "Hours")

            # Check for overly restrictive limits
            if period == "Minutes" and int(occurrences) < 5:
                self.suggestions.append(OptimizationSuggestion(
                    category="compliance",
                    priority="low",
                    title="Review rate limit for customer experience",
                    description=f"Rate limit of {occurrences} per {period} may be too restrictive. "
                               "Consider if this level matches your actual compliance requirements.",
                    impact="low",
                    effort="low",
                    step_id=step_id
                ))

            # Check for overly lenient limits
            if period == "Hours" and int(occurrences) > 20:
                self.suggestions.append(OptimizationSuggestion(
                    category="compliance",
                    priority="medium",
                    title="Review rate limit for compliance",
                    description=f"Rate limit of {occurrences} per {period} may violate compliance rules. "
                               "Ensure this aligns with TCPA and local regulations.",
                    impact="high",
                    effort="low",
                    step_id=step_id
                ))

        # Analyze SCHEDULE nodes for timing optimization
        schedule_steps = [s for s in steps if isinstance(s, dict) and s.get("type") == "schedule"]

        for step in schedule_steps:
            step_id = step.get("id")
            schedule = step.get("schedule", {})
            schedule_time = schedule.get("datetime")

            if schedule_time:
                # Parse time to check for optimal send times
                try:
                    # Simple check for late night sends (assuming ISO format)
                    if "T" in schedule_time:
                        time_part = schedule_time.split("T")[1][:5]  # Get HH:MM
                        hour = int(time_part.split(":")[0])

                        if hour < 8 or hour > 21:
                            self.suggestions.append(OptimizationSuggestion(
                                category="performance",
                                priority="medium",
                                title="Optimize send time for engagement",
                                description=f"Scheduled send at {hour}:00 may be outside optimal hours (8AM-9PM). "
                                           "Consider adjusting for better response rates.",
                                impact="medium",
                                effort="low",
                                step_id=step_id
                            ))
                except (ValueError, IndexError):
                    pass  # Skip if time parsing fails

        # Analyze LIMIT nodes for campaign scope optimization
        limit_steps = [s for s in steps if isinstance(s, dict) and s.get("type") == "limit"]

        for step in limit_steps:
            step_id = step.get("id")
            occurrences = step.get("occurrences", "1")
            period = step.get("period", "Days")

            # Check if limits are too restrictive
            if period == "Days" and int(occurrences) < 2:
                self.suggestions.append(OptimizationSuggestion(
                    category="performance",
                    priority="low",
                    title="Review campaign frequency limit",
                    description=f"Limit of {occurrences} per {period} may be too restrictive. "
                               "Ensure this aligns with your campaign goals and customer expectations.",
                    impact="medium",
                    effort="low",
                    step_id=step_id
                ))

        # Suggest adding analytics tracking if missing
        has_analytics_steps = any(step.get("type") in ["experiment", "segment"] for step in steps)
        message_steps = [s for s in steps if isinstance(s, dict) and s.get("type") == "message"]

        if len(message_steps) > 2 and not has_analytics_steps:
            self.suggestions.append(OptimizationSuggestion(
                category="analytics",
                priority="medium",
                title="Add A/B testing for message optimization",
                description="Campaign has multiple messages but no A/B tests. "
                           "Consider adding experiments to optimize message content and timing.",
                impact="high",
                effort="medium"
            ))

        # Suggest advanced segmentation if missing
        segment_steps = [s for s in steps if isinstance(s, dict) and s.get("type") == "segment"]

        if len(message_steps) > 3 and len(segment_steps) == 0:
            self.suggestions.append(OptimizationSuggestion(
                category="personalization",
                priority="medium",
                title="Add customer segmentation for better targeting",
                description="Campaign has multiple messages but no segmentation. "
                           "Adding segments can improve relevance and conversion rates.",
                impact="high",
                effort="medium"
            ))

    def _analyze_performance_optimization(self, campaign_json: Dict[str, Any]) -> None:
        """Analyze opportunities for performance improvement."""
        steps = campaign_json.get("steps", [])

        # Check for optimal timing
        delay_steps = [s for s in steps if isinstance(s, dict) and s.get("type") == "delay"]

        for step in delay_steps:
            step_id = step.get("id")
            duration = step.get("duration", {})

            if not isinstance(duration, dict):
                continue

            total_hours = 0
            total_hours += duration.get("hours", 0)
            total_hours += duration.get("days", 0) * 24
            total_hours += duration.get("minutes", 0) / 60

            # Optimal follow-up timing: 6-24 hours
            if total_hours < 4:
                self.suggestions.append(OptimizationSuggestion(
                    category="performance",
                    priority="medium",
                    title="Increase delay for better timing",
                    description=f"Delay of {total_hours:.1f} hours may be too short. "
                               "Research shows 6-24 hour delays have better engagement.",
                    impact="medium",
                    effort="low",
                    step_id=step_id
                ))
            elif total_hours > 48:
                self.suggestions.append(OptimizationSuggestion(
                    category="performance",
                    priority="low",
                    title="Reduce delay to maintain engagement",
                    description=f"Delay of {total_hours / 24:.1f} days may cause users to forget context. "
                               "Consider 6-24 hour windows for better recall.",
                    impact="medium",
                    effort="low",
                    step_id=step_id
                ))

        # Check for experiment/A/B testing opportunities
        message_steps = [s for s in steps if isinstance(s, dict) and s.get("type") == "message"]
        has_experiment = any(s.get("type") == "experiment" for s in steps if isinstance(s, dict))

        if len(message_steps) >= 2 and not has_experiment:
            self.suggestions.append(OptimizationSuggestion(
                category="performance",
                priority="high",
                title="Add A/B testing to optimize performance",
                description="Campaign could benefit from testing message variations. "
                           "A/B testing typically improves conversion by 15-30%.",
                impact="high",
                effort="medium"
            ))

        # Check for segmentation opportunities
        has_segment = any(s.get("type") == "segment" for s in steps if isinstance(s, dict))

        if len(message_steps) > 1 and not has_segment:
            self.suggestions.append(OptimizationSuggestion(
                category="performance",
                priority="medium",
                title="Add customer segmentation",
                description="Segmenting customers can improve relevance and conversion. "
                           "Consider segmenting by purchase history or engagement level.",
                impact="high",
                effort="high"
            ))

    def _analyze_engagement_optimization(self, campaign_json: Dict[str, Any]) -> None:
        """Analyze opportunities for engagement improvement."""
        message_steps = [
            s for s in campaign_json["steps"]
            if isinstance(s, dict) and s.get("type") == "message"
        ]

        # Check personalization usage
        personalized_messages = sum(
            1 for s in message_steps
            if "{{" in s.get("text", "")
        )

        personalization_ratio = personalized_messages / len(message_steps) if message_steps else 0

        if personalization_ratio < 0.7:
            self.suggestions.append(OptimizationSuggestion(
                category="engagement",
                priority="high",
                title="Increase personalization",
                description=f"Only {personalization_ratio:.0%} of messages use personalization. "
                           "Personalized messages have 26% higher open rates and 14% higher CTR.",
                impact="high",
                effort="low"
            ))

        # Check for interactive elements
        has_quiz = any(s.get("type") == "quiz" for s in campaign_json["steps"] if isinstance(s, dict))
        has_product_choice = any(
            s.get("type") in ["product_choice", "reply_for_product_choice"]
            for s in campaign_json["steps"]
            if isinstance(s, dict)
        )

        if not has_quiz and not has_product_choice and len(message_steps) > 2:
            self.suggestions.append(OptimizationSuggestion(
                category="engagement",
                priority="medium",
                title="Add interactive elements",
                description="Interactive steps (quiz, product choice) can increase engagement by 40-60%. "
                           "Consider adding conversational elements.",
                impact="high",
                effort="high"
            ))

        # Check for reply handlers
        messages_with_reply = sum(
            1 for s in message_steps
            if any(
                e.get("type") in ["reply", "positive", "negative"]
                for e in s.get("events", [])
                if isinstance(e, dict)
            )
        )

        if messages_with_reply < len(message_steps) * 0.5:
            self.suggestions.append(OptimizationSuggestion(
                category="engagement",
                priority="medium",
                title="Add more reply handlers",
                description="Enable two-way conversation by handling replies. "
                           "Conversational campaigns have 3-5x higher engagement.",
                impact="high",
                effort="medium"
            ))

    def _analyze_conversion_optimization(self, campaign_json: Dict[str, Any]) -> None:
        """Analyze opportunities for conversion improvement."""
        message_steps = [
            s for s in campaign_json["steps"]
            if isinstance(s, dict) and s.get("type") == "message"
        ]

        # Check for urgency/scarcity
        urgency_keywords = ["limited", "expires", "today only", "last chance", "ending soon", "hurry"]
        messages_with_urgency = sum(
            1 for s in message_steps
            if any(keyword in s.get("text", "").lower() for keyword in urgency_keywords)
        )

        if messages_with_urgency == 0:
            self.suggestions.append(OptimizationSuggestion(
                category="conversion",
                priority="high",
                title="Add urgency to drive action",
                description="No messages create urgency. Adding time-sensitive elements "
                           "can increase conversion by 20-30%.",
                impact="high",
                effort="low"
            ))

        # Check for purchase offer steps
        has_purchase_offer = any(
            s.get("type") == "purchase_offer"
            for s in campaign_json["steps"]
            if isinstance(s, dict)
        )

        campaign_type = campaign_json.get("_metadata", {}).get("intent", {}).get("campaign_type")

        if campaign_type in ["promotional", "abandoned_cart"] and not has_purchase_offer:
            self.suggestions.append(OptimizationSuggestion(
                category="conversion",
                priority="high",
                title="Add purchase offer step",
                description=f"For {campaign_type} campaigns, purchase_offer steps "
                           "provide one-click buying, improving conversion by 40-60%.",
                impact="high",
                effort="medium"
            ))

        # Check for discount/offer clarity
        offer_keywords = ["discount", "off", "save", "deal", "offer", "promo", "code"]
        messages_with_offer = [
            s for s in message_steps
            if any(keyword in s.get("text", "").lower() for keyword in offer_keywords)
        ]

        if messages_with_offer:
            # Check if discount codes are clearly stated
            for step in messages_with_offer:
                text = step.get("text", "")
                has_code_var = "{{discount.code}}" in text or "{{code}}" in text

                if not has_code_var and "code" in text.lower():
                    self.suggestions.append(OptimizationSuggestion(
                        category="conversion",
                        priority="medium",
                        title="Use discount code variables",
                        description="Use {{discount.code}} variable for dynamic codes. "
                                   "Clear, personalized codes improve redemption rates.",
                        impact="medium",
                        effort="low",
                        step_id=step.get("id")
                    ))

        # Check for clear CTAs in first message
        if message_steps:
            first_message = message_steps[0]
            first_text = first_message.get("text", "").lower()

            cta_words = ["shop", "buy", "click", "visit", "get", "save", "join"]
            has_cta = any(word in first_text for word in cta_words)

            if not has_cta:
                self.suggestions.append(OptimizationSuggestion(
                    category="conversion",
                    priority="high",
                    title="Add clear CTA to first message",
                    description="First message should have a clear call-to-action. "
                               "CTAs in opening message increase conversion by 25%.",
                    impact="high",
                    effort="low",
                    step_id=first_message.get("id")
                ))

    def get_top_suggestions(self, limit: int = 5) -> List[OptimizationSuggestion]:
        """Get top N suggestions by priority and impact."""
        # Already sorted by priority in analyze()
        return self.suggestions[:limit]

    def get_by_category(self, category: str) -> List[OptimizationSuggestion]:
        """Get suggestions by category."""
        return [s for s in self.suggestions if s.category == category]

    def estimate_total_impact(self) -> Dict[str, Any]:
        """Estimate total potential impact of all suggestions."""
        categories = set(s.category for s in self.suggestions)

        impact_summary = {
            "total_suggestions": len(self.suggestions),
            "high_priority": len([s for s in self.suggestions if s.priority == "high"]),
            "medium_priority": len([s for s in self.suggestions if s.priority == "medium"]),
            "low_priority": len([s for s in self.suggestions if s.priority == "low"]),
            "by_category": {
                cat: len([s for s in self.suggestions if s.category == cat])
                for cat in categories
            },
            "potential_improvement": self._calculate_potential_improvement()
        }

        return impact_summary

    def _calculate_potential_improvement(self) -> str:
        """Calculate estimated potential improvement."""
        high_impact = len([s for s in self.suggestions if s.impact == "high"])
        medium_impact = len([s for s in self.suggestions if s.impact == "medium"])

        if high_impact >= 3:
            return "High (40-60% potential improvement)"
        elif high_impact >= 1 or medium_impact >= 3:
            return "Medium (20-40% potential improvement)"
        else:
            return "Low (5-20% potential improvement)"