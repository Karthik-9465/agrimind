from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.models import Farm, Crop
from app.modules.farm.schemas import FarmCreate, FarmUpdate, CropCreate

# --- Farm CRUD ---
def create_farm(db: Session, owner_id: str, farm_in: FarmCreate) -> Farm:
    db_farm = Farm(
        owner_id=owner_id,
        name=farm_in.name,
        location=farm_in.location,
        area_acres=farm_in.area_acres,
        soil_type=farm_in.soil_type
    )
    db.add(db_farm)
    db.commit()
    db.refresh(db_farm)
    return db_farm

def get_farms_by_owner(db: Session, owner_id: str) -> List[Farm]:
    return db.query(Farm).filter(Farm.owner_id == owner_id).all()

def get_farm_by_id(db: Session, farm_id: str, owner_id: str) -> Optional[Farm]:
    return db.query(Farm).filter(Farm.id == farm_id, Farm.owner_id == owner_id).first()

def update_farm(db: Session, farm: Farm, farm_in: FarmUpdate) -> Farm:
    update_data = farm_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(farm, field, value)
    db.commit()
    db.refresh(farm)
    return farm

def delete_farm(db: Session, farm: Farm):
    db.delete(farm)
    db.commit()

# --- Crop CRUD ---
def create_crop(db: Session, farm_id: str, crop_in: CropCreate) -> Crop:
    db_crop = Crop(
        farm_id=farm_id,
        name=crop_in.name,
        variety=crop_in.variety,
        planting_date=crop_in.planting_date,
        status=crop_in.status or "Healthy",
        notes=crop_in.notes
    )
    db.add(db_crop)
    db.commit()
    db.refresh(db_crop)
    return db_crop

def get_crops_by_farm(db: Session, farm_id: str) -> List[Crop]:
    return db.query(Crop).filter(Crop.farm_id == farm_id).all()

def delete_crop(db: Session, crop_id: str, farm_id: str) -> bool:
    crop = db.query(Crop).filter(Crop.id == crop_id, Crop.farm_id == farm_id).first()
    if crop:
        db.delete(crop)
        db.commit()
        return True
    return False
