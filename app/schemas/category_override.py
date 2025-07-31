from pydantic import BaseModel, ConfigDict

class CategoryOverrideBase(BaseModel):
    plaid_category: str
    merchant_name: str | None = None
    custom_category: str

class CategoryOverrideCreate(CategoryOverrideBase):
    user_id: int

class CategoryOverrideUpdate(BaseModel):
    plaid_category: str | None = None
    merchant_name: str | None = None
    custom_category: str | None = None

class CategoryOverrideResponse(CategoryOverrideBase):
    id: int
    user_id: int

    model_config = ConfigDict(from_attributes=True)

class CategoryOverrideRead(BaseModel):
    # ... fields ...
    model_config = ConfigDict(from_attributes=True) 