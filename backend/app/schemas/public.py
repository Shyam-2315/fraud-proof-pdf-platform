from pydantic import BaseModel


class PublicConfigResponse(BaseModel):
    """
    Schema describing the public config response payload.
    """
    product_name: str
    tagline: str
    free_limit: int
    login_required_message: str
