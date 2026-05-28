from enum import StrEnum


BEHAVIOR_EVENTS_COLLECTION = "behavior_events"


class BehaviorEventType(StrEnum):
    """
    Model describing the behavior event type domain object.
    """
    PAGE_VIEW = "PAGE_VIEW"
    PDF_TITLE_TYPED = "PDF_TITLE_TYPED"
    PDF_CONTENT_PASTED = "PDF_CONTENT_PASTED"
    GENERATE_CLICKED = "GENERATE_CLICKED"
    PDF_GENERATED = "PDF_GENERATED"
    DOWNLOAD_CLICKED = "DOWNLOAD_CLICKED"
    LIMIT_REACHED = "LIMIT_REACHED"
    LOGIN_CLICKED = "LOGIN_CLICKED"
    SIGNUP_CLICKED = "SIGNUP_CLICKED"
