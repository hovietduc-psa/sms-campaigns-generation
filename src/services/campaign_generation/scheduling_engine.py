"""
Advanced Scheduling Engine for campaign timing and timezone handling.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from dataclasses import dataclass

@dataclass
class ScheduleConfig:
    """Scheduling configuration."""
    start_time: Optional[str] = None
    timezone: Optional[str] = None
    date_expression: Optional[str] = None
    trigger_conditions: Dict[str, Any] = None

class SchedulingEngine:
    """Advanced scheduling and timing engine."""

    def __init__(self):
        self.timezone_mapping = {
            "PST": "America/Los_Angeles",
            "EST": "America/New_York",
            "CST": "America/Chicago",
            "MST": "America/Denver",
            "GMT": "UTC",
            "UTC": "UTC"
        }

    def parse_schedule_config(self, schedule_info: Dict[str, Any]) -> ScheduleConfig:
        """Parse scheduling information from business requirements."""
        config = ScheduleConfig()

        if 'start_time' in schedule_info:
            config.start_time = schedule_info['start_time']

        if 'timezone' in schedule_info:
            config.timezone = self._normalize_timezone(schedule_info['timezone'])

        if 'date_expression' in schedule_info:
            config.date_expression = schedule_info['date_expression']

        if 'trigger_conditions' in schedule_info:
            config.trigger_conditions = schedule_info['trigger_conditions']

        return config

    def _normalize_timezone(self, tz_str: str) -> str:
        """Normalize timezone string."""
        return self.timezone_mapping.get(tz_str.upper(), tz_str)

    def calculate_next_run_time(self, config: ScheduleConfig) -> Optional[datetime]:
        """Calculate the next run time based on schedule config."""
        if not config.date_expression:
            return None

        now = datetime.now()

        if config.date_expression.lower() == "tomorrow":
            return now + timedelta(days=1)
        elif config.date_expression.lower() == "today":
            return now
        elif config.date_expression.startswith("next "):
            day_name = config.date_expression[5:].lower()
            return self._get_next_weekday(day_name)

        return None

    def _get_next_weekday(self, day_name: str) -> datetime:
        """Get the next occurrence of a specific weekday."""
        today = datetime.now()
        current_weekday = today.weekday()  # 0 = Monday, 6 = Sunday

        weekday_map = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }

        target_weekday = weekday_map.get(day_name.lower())
        if target_weekday is None:
            return today + timedelta(days=7)  # Default to next week

        days_until_target = (target_weekday - current_weekday + 7) % 7
        return today + timedelta(days=days_until_target)

    def parse_time_string(self, time_str: str) -> Optional[Dict[str, int]]:
        """Parse time string like '10am', '2:30pm'."""
        if not time_str:
            return None

        # Handle formats like "10am", "10:30am", "2:30pm", "2pm"
        time_match = re.match(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', time_str.lower())
        if not time_match:
            return None

        hour = int(time_match.group(1))
        minute = int(time_match.group(2)) if time_match.group(2) else 0
        am_pm = time_match.group(3)

        # Convert to 24-hour format
        if am_pm == 'pm' and hour < 12:
            hour += 12
        elif am_pm == 'am' and hour == 12:
            hour = 0

        return {'hour': hour, 'minute': minute}

    def create_delay_config(self, config: ScheduleConfig) -> Dict[str, Any]:
        """Create delay configuration for campaign steps."""
        delay_config = {}

        if config.start_time:
            time_info = self.parse_time_string(config.start_time)
            if time_info:
                # Calculate delay from now to target time
                now = datetime.now()
                target_time = datetime.now().replace(hour=time_info['hour'], minute=time_info['minute'], second=0)

                if target_time <= now:
                    target_time += timedelta(days=1)  # If time has passed, schedule for tomorrow

                delay_seconds = (target_time - now).total_seconds()
                delay_hours = max(1, int(delay_seconds / 3600))  # Minimum 1 hour delay

                delay_config['initial_delay'] = {
                    'value': delay_hours,
                    'unit': 'hours',
                    'scheduled_time': target_time.strftime('%Y-%m-%d %H:%M')
                }

        if config.date_expression == "tomorrow":
            tomorrow = datetime.now() + timedelta(days=1)
            delay_config['initial_delay'] = {
                'value': 24,
                'unit': 'hours',
                'scheduled_time': tomorrow.strftime('%Y-%m-%d %H:%M')
            }

        return delay_config