def track_length(milliseconds):
    length = ""
    seconds = milliseconds // 1000
    minutes = seconds // 60
    hours = minutes // 60
    if hours:
        length = f"{hours}:"
    return f"{length}{minutes%60}:{seconds%60}"
