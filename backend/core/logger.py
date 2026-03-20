from datetime import datetime


def log(stage: str, message: str, level: str = "info", ctx=None):
    """
    Unified logger. Prints to stdout always.
    If ctx (RunContext) is provided, also pushes to that run's live buffer
    so the dashboard SSE stream picks it up.
    """
    time_str = datetime.now().strftime("%H:%M:%S")
    print(f"[{time_str}] [{stage}] {message}", flush=True)

    if ctx is not None:
        ctx.push({
            "time":    time_str,
            "stage":   stage,
            "message": message,
            "level":   level,
        })
