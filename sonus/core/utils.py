def fmt_time(seconds):
    try:
        total = max(0, int(float(seconds)))
    except Exception:
        total = 0
    minutes, sec = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02d}:{sec:02d}" if hours else f"{minutes:02d}:{sec:02d}"
