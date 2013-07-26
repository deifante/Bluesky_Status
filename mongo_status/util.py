import datetime

def yesterday_dict():
    """
    Used for the 'yesterday' url for day summaries.
    """
    yesterday = datetime.date.today() + datetime.timedelta(-1)
    return {'year':yesterday.year, 'month':yesterday.month, 'day':yesterday.day}
