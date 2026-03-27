# Weather API Project

This project provides a **Weather API** with a PostgreSQL database backend and an **ETL process** that fetches data from external APIs (e.g., Specialisterne API).
---

## 🧱 Project Structure
Weather_API/
├── db_code/
│ └── app/
│ ├── extract/
│ ├── pipeline/
│ └── ...
├── etl_times.json
├── main.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
## 🔧 Setup

1. Clone the repository:

```bash
git clone <your-repo-url>
cd Weather_API

Ensure etl_times.json exists:

pip install -r requirements.txt

docker compose up --build

This will start:

postgres – PostgreSQL database
app – FastAPI / Weather API
etl – ETL process that fetches and updates data

docker compose ps

 requirements.txt

## 🗄️ Database Models & Schemas

This project uses **SQLAlchemy (ORM)** for database models and **Pydantic** for data validation and API serialization.

---

## 🔹 SQLAlchemy Models (`classes_alchemy.py`)

The file `classes_alchemy.py` defines the **database schema** using SQLAlchemy ORM.

### Base Class

```python
class Base(DeclarativeBase):
    pass

All database models inherit from Base
Used by SQLAlchemy to create tables and manage metadata

Fields:

dmi_id (UUID, primary key) – unique identifier
parameter_id (string) – type of measurement (e.g., temperature, wind)
value (float) – measured value
observed_at (datetime) – time of measurement
pulled_at (datetime) – time data was fetched
station_id (int) – weather station identifier
🌡️ BME280 Table

Stores data from the BME280 environmental sensor.

__table_args__ = (
    CheckConstraint("location IN ('inside', 'outside')"),
)

Fields:

reader_id (UUID, primary key)
location (inside/outside) – enforced by constraint
humidity (float)
pressure (float)
temperature (float)
observed_at, pulled_at (timestamps)
🌡️ DS18B20 Table

Stores temperature data from the DS18B20 sensor.

Fields:

reader_id (UUID, primary key)
location (inside/outside)
temperature (float)
observed_at, pulled_at
🌬️ SCD41 Table

Stores air quality data from the SCD41 sensor.

Fields:

reader_id (UUID, primary key)
co2 (int) – CO₂ concentration
humidity (float)
temperature (float)
observed_at, pulled_at
🔹 Pydantic Schemas (schema.py)

Pydantic models define how data is:

validated
serialized
returned via the API

Each schema corresponds to a database model.

Example: DMI Schema
class DMIBase(BaseModel):

Fields match the SQLAlchemy model:

dmi_id
parameter_id
value
observed_at
pulled_at
station_id
🔑 Important Configuration
model_config = ConfigDict(from_attributes=True)

This allows:

converting SQLAlchemy objects → Pydantic models
returning ORM objects directly from FastAPI endpoints
📍 Location Validation

For sensor data:

location: Literal["inside", "outside"]
Ensures only valid values are accepted
Matches database constraints
🔄 How Models and Schemas Work Together
ETL process
Fetches data from APIs/sensors
Stores it in PostgreSQL using SQLAlchemy models
FastAPI endpoints
Query database via SQLAlchemy
Return results using Pydantic schemas
Data flow
External API / Sensors
        ↓
   SQLAlchemy Models (DB)
        ↓
   Pydantic Schemas (API)
        ↓
     JSON Response
⚠️ Notes
Table names are case-sensitive ("DMI", "BME280", etc.)
UUIDs are used for unique identifiers across all tables
Constraints ensure data integrity (e.g., valid locations)

## 🔌 Database Configuration (`database.py`)

This module handles the **database connection and session management** using SQLAlchemy’s asynchronous engine.

---

### ⚙️ Settings

```python
class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:qwerty@localhost/weather"
    echo_sql: bool = True

database_url – connection string for PostgreSQL
echo_sql – enables SQL query logging

## 🗄️ Database Configuration (`database.py`)

This module handles **asynchronous database connections** using SQLAlchemy and provides a clean way to manage sessions in FastAPI.

---

### ⚙️ Settings

```python
class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:qwerty@localhost/weather"
    echo_sql: bool = True

Get All Stations
GET /dmi/stations/

Latest Measurements per Station
GET /dmi/latest/

Measurements for One Station
GET /dmi/{station_id}/

Latest Sensor Readings
GET /sensors/latest/

Compare Temperature Across Sources
GET /compare/temperature/
Uses SQLAlchemy async queries
Applies filters dynamically:
date range
measurement type
Uses:
select()
group_by()
join()
order_by(desc(...))



