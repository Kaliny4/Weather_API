import uuid
from pydantic import BaseModel, ConfigDict 
from datetime import datetime
from typing import Literal


class DMIBase(BaseModel):
    dmi_id: uuid.UUID
    parameter_id: str
    value: float
    observed_at: datetime
    pulled_at: datetime
    station_id: int
    
    model_config = ConfigDict(from_attributes=True)

    
class BME280Base(BaseModel):
    reader_id: uuid.UUID
    location: Literal["inside", "outside"]
    humidity: float
    pressure: float
    temperature: float
    observed_at: datetime
    pulled_at: datetime

    model_config = ConfigDict(from_attributes=True)
    
class DS18B20Base(BaseModel):
    reader_id: uuid.UUID
    location: Literal["inside", "outside"]
    temperature: float
    observed_at: datetime
    pulled_at: datetime
    
    model_config = ConfigDict(from_attributes=True)
    
class SCD41Base(BaseModel):
    reader_id: uuid.UUID
    co2: int
    humidity: float
    temperature: float
    observed_at: datetime
    pulled_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

