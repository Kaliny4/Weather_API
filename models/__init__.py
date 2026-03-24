from sqlalchemy.orm import declarative_base

Base = declarative_base() # model base class

from .classes_alchemy import Base, DMI, BME280, DS18B20, SCD41
from .classes_schema import DMIBase, BME280Base, DS18B20Base, SCD41Base

