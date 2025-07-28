"""
Utility module for handling schedule expressions and time conversions.
"""
from typing import Dict, Tuple, Union, Optional


def convert_to_hours(value: int, unit: str) -> int:
    """
    Convert a value in the specified unit to hours.
    
    Args:
        value: The numeric value
        unit: The unit (hour, day, week, month)
        
    Returns:
        Equivalent value in hours
        
    Raises:
        ValueError: If the unit is not supported
    """
    unit = unit.lower()
    if unit == "hour":
        return value
    elif unit == "day":
        return value * 24
    elif unit == "week":
        return value * 24 * 7
    elif unit == "month":
        # Approximate a month as 30 days
        return value * 24 * 30
    else:
        raise ValueError(f"Unsupported time unit: {unit}. Use hour, day, week, or month.")


def get_time_unit_from_hours(hours: int) -> Tuple[int, str]:
    """
    Convert hours to the most appropriate time unit for display.
    
    Args:
        hours: Number of hours
        
    Returns:
        Tuple of (value, unit) in the most appropriate unit
    """
    if hours % (24 * 30) == 0 and hours >= 24 * 30:
        return (hours // (24 * 30), "month")
    elif hours % (24 * 7) == 0 and hours >= 24 * 7:
        return (hours // (24 * 7), "week")
    elif hours % 24 == 0 and hours >= 24:
        return (hours // 24, "day")
    else:
        return (hours, "hour")


def generate_schedule_expression(hours: int) -> Tuple[str, str]:
    """
    Generate a schedule expression based on the given hours.
    Returns a tuple of (schedule_expression, description)
    
    Args:
        hours: Number of hours for the schedule (must be between 1 and 8760)
        
    Returns:
        Tuple containing:
        - schedule_expression: The cron or rate expression
        - description: Human-readable description of the schedule
        
    Raises:
        ValueError: If hours is not between 1 and 8760
    """
    # Validate hours range (1 to 8760, which is the number of hours in a year)
    if hours < 1 or hours > 8760:
        raise ValueError(f"Hours must be between 1 and 8760, got {hours}")
    # Convert to different time units for better readability
    if hours % 24 == 0 and hours >= 24:
        days = hours // 24
        if days == 1:
            # Daily at midnight UTC
            return "cron(0 0 * * ? *)", "daily"
        elif days == 7:
            # Weekly on Sunday at midnight UTC
            return "cron(0 0 ? * 1 *)", "weekly"
        elif days == 30 or days == 31:
            # Monthly on the 1st at midnight UTC
            return "cron(0 0 1 * ? *)", "monthly"
        else:
            # Every N days
            return f"rate({days} days)", f"every {days} days"
    
    # Handle common hourly patterns
    if hours == 24:
        # Daily at midnight UTC
        return "cron(0 0 * * ? *)", "daily"
    elif hours == 12:
        # Every 12 hours (midnight and noon UTC)
        return "cron(0 0,12 * * ? *)", "twice daily"
    elif hours == 8:
        # Every 8 hours (midnight, 8am, 4pm UTC)
        return "cron(0 0,8,16 * * ? *)", "every 8 hours"
    elif hours == 6:
        # Every 6 hours (midnight, 6am, noon, 6pm UTC)
        return "cron(0 0,6,12,18 * * ? *)", "every 6 hours"
    elif hours == 4:
        # Every 4 hours
        return "cron(0 0,4,8,12,16,20 * * ? *)", "every 4 hours"
    elif hours == 2:
        # Every 2 hours
        return "cron(0 0,2,4,6,8,10,12,14,16,18,20,22 * * ? *)", "every 2 hours"
    elif hours == 1:
        # Every hour
        return "cron(0 * * * ? *)", "hourly"
    else:
        # For other values, use rate expression
        return f"rate({hours} hours)", f"every {hours} hours"


def get_schedule_from_config(config: Dict[str, str], key: str = "batch_transform_schedule_in_hours", 
                            default: str = "24") -> Tuple[int, str, str]:
    """
    Get schedule information from config.
    
    Args:
        config: Configuration dictionary
        key: Configuration key to look for
        default: Default value if key is not found
        
    Returns:
        Tuple of (hours, schedule_expression, description)
        
    Raises:
        ValueError: If hours is not between 1 and 8760
    """
    # Get hours from config
    hours = int(config.get(key, default))
    
    # Validate hours range
    if hours < 1 or hours > 8760:
        raise ValueError(f"Hours in config must be between 1 and 8760, got {hours}")
    
    # Generate schedule expression
    schedule_expression, description = generate_schedule_expression(hours)
    return hours, schedule_expression, description


def get_human_readable_schedule(hours: int) -> str:
    """
    Get a human-readable description of a schedule in hours.
    
    Args:
        hours: Number of hours
        
    Returns:
        Human-readable description (e.g., "daily", "weekly", "every 2 days")
    """
    value, unit = get_time_unit_from_hours(hours)
    
    if value == 1:
        if unit == "day":
            return "daily"
        elif unit == "week":
            return "weekly"
        elif unit == "month":
            return "monthly"
        else:  # hour
            return "hourly"
    else:
        return f"every {value} {unit}{'s' if value > 1 else ''}"
