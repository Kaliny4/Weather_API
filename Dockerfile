FROM python:3.12-slim

WORKDIR /Weather_API

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]

# docker compose build
# docker compose up
# docker compose ps (in a second terminal)

# See logs for a specific service
# docker compose logs app
# docker compose logs postgres

# # Rebuild from scratch (no cache)
# docker compose build --no-cache

# # Stop and remove everything, then start fresh
# docker compose down
# docker compose up --build

# Common issues to look for in the logs:

# connection refused — app started before postgres was ready (healthcheck should prevent this)
# ModuleNotFoundError — a package is missing from requirements.txt
# password authentication failed — credentials in DATABASE_URL don't match POSTGRES_USER/POSTGRES_PASSWORD

