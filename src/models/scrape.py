from pydantic import BaseModel, Field


class ScrapeRequest(BaseModel):
    """
    Model for scrape data validation and serialization.
    Inherits from Pydantic's BaseModel for data validation.
    """

    facebook: str = Field("", description="Facebook URL")
    instagram: str = Field("", description="Instagram URL")
    tiktok: str = Field("", description="Tiktok URL")
    x: str = Field("", description="X URL")


# from pydantic import BaseModel, Field, field_validator
# from typing import Optional

# class ScrapeRequest(BaseModel):
#     """
#     Model for scrape data validation and serialization.
#     Inherits from Pydantic's BaseModel for data validation.
#     """

#     facebook: Optional[str] = Field(None, description="Facebook URL")
#     instagram: Optional[str] = Field(None, description="Instagram URL")
#     tiktok: Optional[str] = Field(None, description="Tiktok URL")
#     x: Optional[str] = Field(None, description="X URL")

#     @field_validator('facebook', 'instagram', 'tiktok', 'x')
#     def check_empty_string(cls, value):
#         if value == "":
#             raise ValueError("Field cannot be an empty string")
#         return value
