PRODUCT_NAME = "PDFCraft"
PRODUCT_TAGLINE = "Create clean, professional PDFs in seconds."
LOGIN_REQUIRED_MESSAGE = "Free limit reached. Please log in to continue."

CUSTOMER_COOKIE_NAME = "fraud_pdf_anon_id"
LEGACY_COOKIE_NAME = "anon_id"


def get_visitor_cookie(cookies: dict[str, str]) -> str | None:
    return cookies.get(CUSTOMER_COOKIE_NAME) or cookies.get(LEGACY_COOKIE_NAME)


def customer_cookie_options() -> dict[str, object]:
    from app.config import get_settings

    settings = get_settings()
    options: dict[str, object] = {
        "httponly": True,
        "samesite": settings.COOKIE_SAMESITE,
        "secure": settings.SECURE_COOKIES,
    }
    if settings.COOKIE_DOMAIN:
        options["domain"] = settings.COOKIE_DOMAIN
    return options
