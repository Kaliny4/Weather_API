from db_code.app.load.db.connection import Connector
from db_code.app.config import local_database_schema, docker_database_schema
from sqlalchemy import create_engine
from models.classes_alchemy import Base
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


class DatabaseInitializer:
    def __init__(self, docker: bool = False):
        self.docker = docker
        if docker:
            self.db_name = docker_database_schema["database"]
            cfg = docker_database_schema
        else:
            self.db_name = local_database_schema["database"]
            cfg = local_database_schema

        self.db = Connector(cfg["database"], cfg["user"], cfg["password"], cfg["host"])
        self.cfg = cfg

    def create_db(self):
        """Create the database if it doesn't exist"""
        host = "postgres" if self.docker else "localhost"

        conn = psycopg2.connect(
            dbname="postgres",
            user=self.db.user,
            password=self.db.password,
            host=host,
            port=5432
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname='{self.db_name}';")
        if not cursor.fetchone():
            cursor.execute(f'CREATE DATABASE {self.db_name};')
            print(f"Database {self.db_name} created!")
        else:
            print(f"Database {self.db_name} already exists.")

        cursor.close()
        conn.close()

    def initialize_db(self):
        """Initialize tables using SQLAlchemy ORM"""
        self.db.connect()

        # Create SQLAlchemy engine
        from sqlalchemy import create_engine
        engine = create_engine(
            f"postgresql://{self.db.user}:{self.db.password}@{self.db.host}:5432/{self.db_name}"
        )

        # Create all ORM tables
        Base.metadata.create_all(bind=engine)
        print("All tables created successfully!")

        self.db.close()