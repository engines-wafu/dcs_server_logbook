import datetime, re

def seconds_to_hours(seconds):
    return round(seconds / 3600, 1)

def days_from_epoch(epoch_time):
    current_time = datetime.datetime.now()
    last_join_time = datetime.datetime.fromtimestamp(epoch_time)
    return (current_time - last_join_time).days

def epoch_from_date(date_str):
    """
    Converts a date string to an epoch timestamp, attempting multiple date formats.

    Args:
        date_str (str): The date string in various acceptable formats.

    Returns:
        int: The number of seconds since the Unix epoch, or None if the format is unrecognized.
    """
    # Define multiple date formats to try
    date_formats = ["%Y%m%d", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"]

    for fmt in date_formats:
        try:
            date_obj = datetime.datetime.strptime(date_str, fmt)
            return int(date_obj.timestamp())
        except ValueError:
            continue  # Try the next format

    # If none of the formats matched
    print("Invalid date format. Please use one of the recognized formats.")
    return None