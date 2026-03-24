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

logging.basicConfig(stream=sys.stdout, level=logging.INFO)

DBSessionDep = Annotated[AsyncSession, Depends(get_db_session)]


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    if sessionmanager._engine is not None:
        await sessionmanager.close()


app = FastAPI(
    lifespan=lifespan,
    title="Weather API",
    description="Read-only API for weather measurements from DMI and local sensors.",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# 1. List all DMI stations
# ---------------------------------------------------------------------------
@app.get(
    "/dmi/stations/",
    response_model=List[int],
    summary="List all DMI station IDs",
    tags=["DMI"],
)
async def get_dmi_stations(db: DBSessionDep):
    """Returns a list of all unique DMI station IDs in the database."""
    result = await db.execute(select(DMI.station_id).distinct())
    station_ids = result.scalars().all()
    if not station_ids:
        raise HTTPException(status_code=404, detail="No stations found.")
    return station_ids


# ---------------------------------------------------------------------------
# 2. Measurements for one DMI station, with optional filters
# ---------------------------------------------------------------------------
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
    Optionally filter by date range and/or measurement type.
    """
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


# ---------------------------------------------------------------------------
# 3. Latest measurement per DMI station
# ---------------------------------------------------------------------------
@app.get(
    "/dmi/latest/",
    response_model=List[DMIBase],
    summary="Latest measurement from each DMI station",
    tags=["DMI"],
)
async def get_latest_dmi_measurements(db: DBSessionDep):
    """Returns the single most recent measurement from each DMI station."""
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


# ---------------------------------------------------------------------------
# 4. Latest sensor reading per location (BME280, DS18B20, SCD41)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# 5. Cross-source comparison — temperature across all sources
# ---------------------------------------------------------------------------
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
    if not (from_date or to_date):
        raise HTTPException(
            status_code=400,
            detail="At least one of from_date or to_date is required.",
        )

    async def query_temp(model, temp_col, extra_cols: dict):
        q = select(model).where(model.observed_at != None)
        if from_date:
            q = q.where(model.observed_at >= from_date)
        if to_date:
            q = q.where(model.observed_at <= to_date)
        q = q.order_by(desc(model.observed_at))
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

    dmi_rows    = await query_temp(DMI,    "value",       {"station_id": "station_id"})
    bme_rows    = await query_temp(BME280, "temperature", {"location": "location"})
    ds_rows     = await query_temp(DS18B20,"temperature", {"location": "location"})
    scd_rows    = await query_temp(SCD41,  "temperature", {})

    # Filter DMI to only temperature rows
    dmi_rows = [r for r in dmi_rows if r.get("station_id") and True]  # already filtered below
    dmi_temp_q = (
        select(DMI)
        .where(DMI.parameter_id == "temp_dry")
    )
    if from_date:
        dmi_temp_q = dmi_temp_q.where(DMI.observed_at >= from_date)
    if to_date:
        dmi_temp_q = dmi_temp_q.where(DMI.observed_at <= to_date)
    dmi_temp_q = dmi_temp_q.order_by(desc(DMI.observed_at))
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

    return {
        "DMI":     dmi_rows,
        "BME280":  bme_rows,
        "DS18B20": ds_rows,
        "SCD41":   scd_rows,
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", reload=True, port=8000)