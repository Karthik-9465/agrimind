import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from app.db.session import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), default="farmer")
    created_at = Column(DateTime, default=datetime.utcnow)

    farms = relationship("Farm", back_populates="owner", cascade="all, delete-orphan")
    disease_reports = relationship("DiseaseReport", back_populates="user", cascade="all, delete-orphan")

class Farm(Base):
    __tablename__ = "farms"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    owner_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    area_acres = Column(Float, default=1.0)
    soil_type = Column(String(100), default="Loam")
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="farms")
    crops = relationship("Crop", back_populates="farm", cascade="all, delete-orphan")
    disease_reports = relationship("DiseaseReport", back_populates="farm")

class Crop(Base):
    __tablename__ = "crops"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    farm_id = Column(String(36), ForeignKey("farms.id"), nullable=False)
    name = Column(String(100), nullable=False)
    variety = Column(String(100), nullable=True)
    planting_date = Column(String(50), nullable=True)
    status = Column(String(50), default="Healthy")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    farm = relationship("Farm", back_populates="crops")
    disease_reports = relationship("DiseaseReport", back_populates="crop")

class DiseaseReport(Base):
    __tablename__ = "disease_reports"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    farm_id = Column(String(36), ForeignKey("farms.id"), nullable=True)
    crop_id = Column(String(36), ForeignKey("crops.id"), nullable=True)
    image_reference = Column(String(500), nullable=True)
    possible_condition = Column(String(255), nullable=False)
    assessment_level = Column(String(50), default="Likely")
    observations = Column(Text, nullable=True) # JSON list
    symptoms = Column(Text, nullable=True)     # JSON list
    cause = Column(Text, nullable=True)
    treatment = Column(Text, nullable=True)    # JSON list
    prevention = Column(Text, nullable=True)   # JSON list
    disclaimer = Column(Text, nullable=False)
    is_mock = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="disease_reports")
    farm = relationship("Farm", back_populates="disease_reports")
    crop = relationship("Crop", back_populates="disease_reports")

class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String(50), default="weather_alert")  # weather_alert, irrigation_reminder, market_price, system
    channel = Column(String(50), default="console_stub")    # console_stub, email_stub
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")

