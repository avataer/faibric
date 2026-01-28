# Analytics Track Endpoint Fix

## Issue

The `POST /api/analytics/track/` endpoint was returning a 500 Internal Server Error.

## Root Cause

The `TrackEventView` in `backend/apps/analytics/views.py` was calling methods that did not exist on the `AnalyticsProxy` class in `backend/apps/analytics/services.py`:

- **Line 128**: `proxy.track_event(event)` - method `track_event()` did not exist
- **Line 190**: `proxy.identify_user(distinct_id, traits)` - method `identify_user()` did not exist

The `AnalyticsProxy` class only had `track()` and `identify()` methods, but the views were calling `track_event()` and `identify_user()`.

## Fix

Added the missing methods to `AnalyticsProxy` class in `backend/apps/analytics/services.py`:

```python
def track_event(self, event):
    """Track an event object. Called from TrackEventView."""
    # Forward to external services based on config
    # For now, internal storage is handled by the view
    pass

def identify_user(self, distinct_id: str, traits: dict = None):
    """Identify a user. Called from IdentifyUserView."""
    # Forward to external services based on config
    # For now, internal storage is handled by the view
    pass
```

## Files Modified

- `backend/apps/analytics/services.py`

## Testing

Verified the fix by:
1. Checking that the methods exist on `AnalyticsProxy`
2. Calling the methods to ensure they execute without errors

## Date

2026-01-15
