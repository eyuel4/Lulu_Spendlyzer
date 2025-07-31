from pydantic import BaseModel, ConfigDict

class GroceryCategoryBase(BaseModel):
    name: str
    keywords: str

class GroceryCategoryCreate(GroceryCategoryBase):
    pass

class GroceryCategoryUpdate(BaseModel):
    name: str | None = None
    keywords: str | None = None

class GroceryCategoryResponse(GroceryCategoryBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class GroceryCategoryRead(BaseModel):
    # ... fields ...
    model_config = ConfigDict(from_attributes=True) 