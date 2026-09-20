class ScheduledJobDeferred(Exception):
    """Transient contention: retry later without consuming a failure attempt."""
