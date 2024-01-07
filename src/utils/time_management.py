import datetime

def seconds_to_hours(seconds):
    return round(seconds / 3600, 1)

def days_from_epoch(epoch_time):
    current_time = datetime.datetime.now()
    last_join_time = datetime.datetime.fromtimestamp(epoch_time)
    return (current_time - last_join_time).days