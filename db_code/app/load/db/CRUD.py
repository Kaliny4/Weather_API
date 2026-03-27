from db_code.app.load.db.connection import Connector
from db_code.app.load.error_handling.type_control import test_parameter, test_parameters
from db_code.app.load.schemas.table_schema import TABLES
from psycopg2 import sql
from db_code.app.config import local_database_schema, docker_database_schema
import os

class CRUD:
    def __init__(self, docker:bool = False):
        if docker:
            self.db = Connector(docker_database_schema["database"], docker_database_schema["user"],
                                   docker_database_schema["password"], docker_database_schema["host"])
        else:
            self.db = Connector(local_database_schema["database"], local_database_schema["user"],
                                   local_database_schema["password"], local_database_schema["host"])


    def create_mult_rows(self,table_name:str, rows: list[dict], commit:bool = True, close:bool = True):
        """This method handles creating multiple new rows in a designated table of the database.
        rows must be a list of dictionaries, with keys being column names and values being, well... values.
        The close argument decides whether to close the connection after running the method. By default, it is true
        The commit argument decides whether a change should be commited to the database immediately. By default, it is true."""
        columns = TABLES.get(table_name)
        if columns is None:
            raise ValueError(f"Unknown table: {table_name}")
        columns = list(columns.keys())

        #Check that all required columns are there
        for i, row in enumerate(rows):
            missing = [col for col in columns if col not in row]
            if missing:
                raise ValueError(f"Row {i} is missing columns for table '{table_name}': {missing}")

        column_names = [sql.Identifier(col_name) for col_name in columns]
        values = [[row[col] for col in columns] for row in rows]
        #Building the query
        query = sql.SQL("""INSERT INTO {} ({})
        VALUES %s
        ON CONFLICT DO NOTHING
        """).format(
            sql.Identifier(table_name),
            sql.SQL(", ").join(column_names)
        )
        self.db.execute_mult(query, values, commit=commit, close=close)

    def delete_all_rows(self, table_name:str,reset_id: bool = False):
        """This method deletes all rows of the given table.
        It is a nuclear option and should be handled with care."""
        query = sql.SQL("TRUNCATE TABLE {}").format(
        sql.Identifier(table_name)
        )
        if reset_id:
            query = sql.SQL("{} RESTART IDENTITY CASCADE").format(query)
        print(f"Deleting all rows from table {table_name}")
        self.db.execute(query, commit=True)

    def cleanse_db(self,reset_id: bool = False):
        """This method deletes every single row in every single table of the database.
        It is a nuclear option and should be handled with care.
        The optional variable reset_id tells the function whether to reset the ids in the tables."""
        for table in TABLES:
            self.delete_all_rows(table, reset_id)


    def reset_everything(self,reset_id: bool = False):
        self.cleanse_db(reset_id)
        file_path = "etl_times.json"

        # Check if the file exists first
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"{file_path} has been deleted.")
        else:
            print(f"{file_path} does not exist.")

