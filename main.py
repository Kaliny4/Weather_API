import logging
import sys
from contextlib import asynccontextmanager
from typing import Annotated, List, Optional
from datetime import date

import uvicorn
from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc

from database import get_db_session, sessionmanager
from models.classes_alchemy import DMI, BME280, DS18B20, SCD41
from models.classes_schema import DMIBase, BME280Base, DS18B20Base, SCD41Base

from db_code.app.pipeline.etl import ETLProcess
from db_code.app.load.db.initialize import DatabaseInitializer
from db_code.app.config import docker
import os

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger(__name__)

DBSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up app...")
    initializer = DatabaseInitializer(docker=docker)
    initializer.create_db()
    initializer.initialize_db()
    logger.info("Database initialized.")
    yield
    if getattr(sessionmanager, "_engine", None) is not None:
        await sessionmanager.close()


app = FastAPI(
    lifespan=lifespan,
    title="Weather API",
    description="Read-only API for weather measurements from DMI and local sensors.",
    #version="1.0.0",
)


# Get list of dmi stations
@app.get(
    "/dmi/stations/",
    response_model=List[int],
    summary="List all DMI station IDs",
    tags=["DMI"],
)
async def get_dmi_stations(db: DBSessionDep):
    """Returns a list of all unique DMI station IDs in the database."""
    # SELECT DISTINCT station_id FROM "DMI"
    result = await db.execute(select(DMI.station_id).distinct())
    station_ids = result.scalars().all()
    if not station_ids:
        raise HTTPException(status_code=404, detail="No stations found.")
    return station_ids

# get latest measurment for dmi station
@app.get(
    "/dmi/latest/",
    response_model=List[DMIBase],
    summary="Latest measurement from each DMI station",
    tags=["DMI"],
)
async def get_latest_dmi_measurements(db: DBSessionDep):
    """Returns the single most recent measurement from each DMI station."""
    # SELECT "DMI".*
    # FROM "DMI"
    # JOIN (
    #     SELECT station_id, MAX(observed_at) AS max_observed_at
    #     FROM "DMI"
    #     GROUP BY station_id
    # ) AS subquery
    # ON "DMI".station_id = subquery.station_id
    # AND "DMI".observed_at = subquery.max_observed_at;
    subquery = (
        select(DMI.station_id, func.max(DMI.observed_at).label("max_observed_at"))
        .group_by(DMI.station_id)
        .subquery()
    )
    query = select(DMI).join(
        subquery,
        and_(
            DMI.station_id == subquery.c.station_id,
            DMI.observed_at == subquery.c.max_observed_at,
        ),
    )
    result = await db.execute(query)
    measurements = result.scalars().all()
    if not measurements:
        raise HTTPException(status_code=404, detail="No DMI measurements found.")
    return measurements

# Get meaurment for one station
@app.get(
    "/dmi/{station_id}/",
    response_model=List[DMIBase],
    summary="Get measurements for a specific DMI station",
    tags=["DMI"],
)
async def get_dmi_station_measurements(
    station_id: int,
    db: DBSessionDep,
    from_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    type: Optional[str] = Query(
        None,
        description="Measurement type: temp_dry, humidity, or pressure",
    ),
):
    """
    Returns all measurements for a single DMI station.
    
    """
# SELECT * FROM "DMI"
# WHERE station_id = 06180
#   AND observed_at >= '2024-01-01'
#   AND observed_at <= '2024-01-31'
#   AND parameter_id = 'temp_dry'
# ORDER BY observed_at DESC;
    # Validate type parameter if provided
    valid_types = {"temp_dry", "humidity", "pressure"}
    if type is not None and type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid type '{type}'. Must be one of: {', '.join(valid_types)}",
        )

    query = select(DMI).where(DMI.station_id == station_id)

    if from_date:
        query = query.where(DMI.observed_at >= from_date)
    if to_date:
        query = query.where(DMI.observed_at <= to_date)
    if type:
        query = query.where(DMI.parameter_id == type)

    query = query.order_by(desc(DMI.observed_at))

    result = await db.execute(query)
    measurements = result.scalars().all()

    if not measurements:
        raise HTTPException(
            status_code=404,
            detail=f"No measurements found for station {station_id} with the given filters.",
        )
    return measurements

# sensor readings (BME280, DS18B20, SCD41)

@app.get(
    "/sensors/latest/",
    summary="Latest reading from each local sensor",
    tags=["Sensors"],
)
async def get_latest_sensor_readings(db: DBSessionDep):
    """
    Returns the most recent reading from each sensor type and location.
    Covers BME280, DS18B20 (inside/outside), and SCD41.
    """
# SELECT "BME280".*
# FROM "BME280"
# JOIN (
#     SELECT location, MAX(observed_at) AS max_ts
#     FROM "BME280"
#     GROUP BY location
# ) AS sub
# ON "BME280".location = sub.location
# AND "BME280".observed_at = sub.max_ts;

#SELECT * FROM "SCD41"
#WHERE observed_at = (SELECT MAX(observed_at) FROM "SCD41");
    async def latest_for(model, has_location: bool):
        if has_location:
            sub = (
                select(model.location, func.max(model.observed_at).label("max_ts"))
                .group_by(model.location)
                .subquery()
            )
            q = select(model).join(
                sub,
                and_(model.location == sub.c.location, model.observed_at == sub.c.max_ts),
            )
        else:
            sub = select(func.max(model.observed_at).label("max_ts")).subquery()
            q = select(model).where(model.observed_at == sub.c.max_ts)

        res = await db.execute(q)
        return res.scalars().all()

    bme280  = await latest_for(BME280,  has_location=True)
    ds18b20 = await latest_for(DS18B20, has_location=True)
    scd41   = await latest_for(SCD41,   has_location=False)

    return {
        "BME280":  [BME280Base.model_validate(r)  for r in bme280],
        "DS18B20": [DS18B20Base.model_validate(r) for r in ds18b20],
        "SCD41":   [SCD41Base.model_validate(r)   for r in scd41],
    }


# get comapison of temperature

@app.get(
    "/compare/temperature/",
    summary="Compare temperature readings across all sources",
    tags=["Compare"],
)
async def compare_temperature(
    db: DBSessionDep,
    from_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    to_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
):
    """
    Returns temperature readings from DMI, BME280, DS18B20, and SCD41
    for the given date range. At least one date filter is required.
    """
# -- DMI (correct version, second query)
# SELECT dmi_id, observed_at, value AS temperature, station_id
# FROM "DMI"
# WHERE parameter_id = 'temp_dry'
#   AND observed_at >= '2024-01-01'
#   AND observed_at <= '2024-01-31'
# ORDER BY observed_at DESC;

# -- BME280
# SELECT reader_id, observed_at, temperature, location
# FROM "BME280"
# WHERE observed_at >= '2024-01-01'
#   AND observed_at <= '2024-01-31'
# ORDER BY observed_at DESC
# LIMIT 1000;

# -- DS18B20
# SELECT reader_id, observed_at, temperature, location
# FROM "DS18B20"
# WHERE observed_at >= '2024-01-01'
#   AND observed_at <= '2024-01-31'
# ORDER BY observed_at DESC
# LIMIT 1000;

# -- SCD41
# SELECT reader_id, observed_at, temperature
# FROM "SCD41"
# WHERE observed_at >= '2024-01-01'
#   AND observed_at <= '2024-01-31'
# ORDER BY observed_at DESC
# LIMIT 1000;
    
    if not (from_date or to_date):
        raise HTTPException(
            status_code=400,
            detail="At least one of from_date or to_date is required.",
        )
        # Shared helper for BME280, DS18B20, SCD41
    async def query_temp(model, temp_col, extra_cols: dict):
        q = select(model).where(model.observed_at != None)
        
        if from_date:
            q = q.where(model.observed_at >= from_date)
        if to_date:
            q = q.where(model.observed_at <= to_date)
        q = q.order_by(desc(model.observed_at)).limit(1000)
        res = await db.execute(q)
        rows = res.scalars().all()
        return [
            {
                "source": model.__tablename__,
                "observed_at": str(r.observed_at),
                "temperature": float(getattr(r, temp_col)),
                **{k: getattr(r, v) for k, v in extra_cols.items()},
            }
            for r in rows
        ]

    # DMI needs parameter_id filter so it gets its own query
    dmi_temp_q = (
        select(DMI)
        .where(DMI.parameter_id == "temp_dry")
    )
    if from_date:
        dmi_temp_q = dmi_temp_q.where(DMI.observed_at >= from_date)
    if to_date:
        dmi_temp_q = dmi_temp_q.where(DMI.observed_at <= to_date)
    dmi_temp_q = dmi_temp_q.order_by(desc(DMI.observed_at)).limit(1000)
    dmi_res = await db.execute(dmi_temp_q)
    dmi_rows = [
        {
            "source": "DMI",
            "observed_at": str(r.observed_at),
            "temperature": r.value,
            "station_id": r.station_id,
        }
        for r in dmi_res.scalars().all()
    ]
    bme_rows = await query_temp(BME280,  "temperature", {"location": "location"})
    ds_rows  = await query_temp(DS18B20, "temperature", {"location": "location"})
    scd_rows = await query_temp(SCD41,   "temperature", {})

    return {
        "DMI":     dmi_rows,
        "BME280":  bme_rows,
        "DS18B20": ds_rows,
        "SCD41":   scd_rows,
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0" if docker else "127.0.0.1", port=8000, reload=True)