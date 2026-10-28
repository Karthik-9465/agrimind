from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

# --- Crop Schemas ---
class CropBase(BaseModel):
    name: str
    variety: Optional[str] = None
    planting_date: Optional[str] = None
    status: Optional[str] = "Healthy"
    notes: Optional[str] = None

class CropCreate(CropBase):
    pass

class CropResponse(CropBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    farm_id: str
    created_at: datetime

# --- Farm Schemas ---
class FarmBase(BaseModel):
    name: str
    location: str
    area_acres: float = 1.0
    soil_type: str = "Loam"

class FarmCreate(FarmBase):
    pass

class FarmUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    area_acres: Optional[float] = None
    soil_type: Optional[str] = None

class FarmResponse(FarmBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    created_at: datetime
    crops: List[CropResponse] = []
