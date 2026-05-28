from enum import StrEnum


USER_COLLECTION = "users"


class UserRole(StrEnum):
    """Supported user roles for customer and admin accounts."""

    CUSTOMER = "CUSTOMER"
    ADMIN = "ADMIN"


class UserPlan(StrEnum):
    """Supported subscription plans for PDF generation limits."""

    FREE = "FREE"
    PRO = "PRO"
    BUSINESS = "BUSINESS"


PLAN_LIMITS = {
    UserPlan.FREE.value: 5,
    UserPlan.PRO.value: 100,
    UserPlan.BUSINESS.value: 1000,
}
