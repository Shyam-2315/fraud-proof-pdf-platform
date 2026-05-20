from pydantic import BaseModel


class PublicConfigResponse(BaseModel):
    product_name: str
    tagline: str
    free_limit: int
    login_required_message: str
