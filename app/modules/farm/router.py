from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.db.models import User
from app.modules.auth.router import get_current_user
from app.modules.farm import schemas, service

router = APIRouter(prefix="/api/v1/farms", tags=["Farms"])

@router.post("", response_model=schemas.FarmResponse, status_code=status.HTTP_201_CREATED)
def create_farm_profile(
    farm_in: schemas.FarmCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return service.create_farm(db, owner_id=current_user.id, farm_in=farm_in)

@router.get("", response_model=List[schemas.FarmResponse])
def list_farms(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    return service.get_farms_by_owner(db, owner_id=current_user.id)

@router.get("/{farm_id}", response_model=schemas.FarmResponse)
def get_farm(
    farm_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    farm = service.get_farm_by_id(db, farm_id=farm_id, owner_id=current_user.id)
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    return farm

@router.put("/{farm_id}", response_model=schemas.FarmResponse)
def update_farm_profile(
    farm_id: str,
    farm_in: schemas.FarmUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    farm = service.get_farm_by_id(db, farm_id=farm_id, owner_id=current_user.id)
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    return service.update_farm(db, farm=farm, farm_in=farm_in)

@router.delete("/{farm_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_farm_profile(
    farm_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    farm = service.get_farm_by_id(db, farm_id=farm_id, owner_id=current_user.id)
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    service.delete_farm(db, farm=farm)
    return None

# --- Crop Endpoints ---
@router.post("/{farm_id}/crops", response_model=schemas.CropResponse, status_code=status.HTTP_201_CREATED)
def add_crop_to_farm(
    farm_id: str,
    crop_in: schemas.CropCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    farm = service.get_farm_by_id(db, farm_id=farm_id, owner_id=current_user.id)
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    return service.create_crop(db, farm_id=farm_id, crop_in=crop_in)

@router.get("/{farm_id}/crops", response_model=List[schemas.CropResponse])
def list_farm_crops(
    farm_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    farm = service.get_farm_by_id(db, farm_id=farm_id, owner_id=current_user.id)
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    return service.get_crops_by_farm(db, farm_id=farm_id)

@router.delete("/{farm_id}/crops/{crop_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_crop_from_farm(
    farm_id: str,
    crop_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    farm = service.get_farm_by_id(db, farm_id=farm_id, owner_id=current_user.id)
    if not farm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Farm not found")
    deleted = service.delete_crop(db, crop_id=crop_id, farm_id=farm_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Crop not found")
    return None
