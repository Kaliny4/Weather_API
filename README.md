# Weather API Project
## This project provides a Weather API with a PostgreSQL database backend and an ETL process that fetches data from external APIs (e.g., Specialisterne API).

1. git clone https://github.com/Kaliny4/Weather_API.git
   
2. cd Weather_API
   
3. create file .env:
   
    #Database for Docker container
   
    DB_HOST=
   
    DB_PORT=5432
   
    DB_USER=
   
    DB_PASSWORD=
   
    DB_NAME=weather 
    
    #Local database (for development outside Docker)
   
    LOCAL_HOST=
   
    LOCAL_USER=
   
    LOCAL_PASSWORD=
   
    LOCAL_DB= 
    
    #ETL mode. The ETL process can run once, or keep running in background at certain intervals
   
    ETL_MODE=interval
   
    #Can be set to 'interval' or 'once'
   
    ETL_INTERVAL=10
   
    #minutes between intervals

    #Old Specialisterne API token
   
    #your_api_token_here
   
    SPEC_TOKEN=
       
    #New Specialisterne API token
   
    #your_api_token_here
   
    NEW_SPEC_TOKEN=
       
5.  docker compose build     
    docker compose up
    
6. open in browser http://127.0.0.1:8000/docs

If container logs show "No more new records" from the New Specialisterne API means the API is reachable but returning empty data. The issue is the etl_times.json file. It stores the last pull timestamp, and if it was written with a timestamp that's ahead of actual sensor data, every subsequent pull returns empty because there's nothing newer than that timestamp.
- Check what's in etl_times.json file
- If the timestamp is in the future or too recent, reset it:
  
  docker compose exec etl sh -c 'echo "{\"DMI\": {\"temp_dry\": \"2026-03-09T00:00:00Z\", \"humidity\": \"2026-03-09T00:00:00Z\", \"pressure\": \"2026-03-09T00:00:00Z\"}, \"spec\": \"2026-03-09T00:00:00Z\"}" > /Weather_API/db_code/etl_times.json'
- Then restart the ETL to trigger a fresh pull:
  
    docker compose restart etl
  
    docker compose logs -f etl
- You should then see it pulling sensor records from March 9th onwards.

