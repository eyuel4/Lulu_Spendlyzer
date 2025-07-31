from pydantic import BaseModel, ConfigDict

class ShoppingCategoryBase(BaseModel):
    name: str
    keywords: str

class ShoppingCategoryCreate(ShoppingCategoryBase):
    pass

class ShoppingCategoryUpdate(BaseModel):
    name: str | None = None
    keywords: str | None = None

class ShoppingCategoryResponse(ShoppingCategoryBase):
    id: int

    model_config = ConfigDict(from_attributes=True)

class ShoppingCategoryRead(BaseModel):
    # ... fields ...
    model_config = ConfigDict(from_attributes=True) 