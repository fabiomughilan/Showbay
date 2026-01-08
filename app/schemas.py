from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID

class SummaryCreate(BaseModel):
    input_text: str = Field(min_length=20, max_length=10000)

class SummaryUpdate(BaseModel):
    summary_text: str = Field(min_length=10)

class SummaryOut(BaseModel):
    id: UUID
    input_text: str
    summary_text: str
    model: str

    model_config = ConfigDict(from_attributes=True)
