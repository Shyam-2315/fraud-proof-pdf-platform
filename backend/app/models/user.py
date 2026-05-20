from enum import StrEnum


USER_COLLECTION = "users"


class UserRole(StrEnum):
    CUSTOMER = "CUSTOMER"
    ADMIN = "ADMIN"


class UserPlan(StrEnum):
    FREE = "FREE"
    PRO = "PRO"
    BUSINESS = "BUSINESS"


PLAN_LIMITS = {
    UserPlan.FREE.value: 5,
    UserPlan.PRO.value: 100,
    UserPlan.BUSINESS.value: 1000,
}
