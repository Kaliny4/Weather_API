import psycopg2
from psycopg2.extras import execute_values
import pandas as pd
import os



class Connector:
    """This class handles the connection to the database northwind."""
    def __init__(self,database,user,password, host=None, port=None):
        #NOTE: As this is an exercise, the server password has been hardcoded in.
        self.user = user
        self.password = password
        self.host = os.getenv("DB_HOST") or host or "localhost"
        self.port = int(os.getenv("DB_PORT", port or 5432))
        self.database = database
        self.conn = None

    def connect(self):
        """This method handles opening the connection to the database"""
        if self.conn is None:
            try:
                print(f"🔌 Connecting to DB at {self.host}:{self.port} ({self.database})")

                self.conn = psycopg2.connect(
                    host=self.host,
                    port=self.port,
                    dbname=self.database,
                    user=self.user,
                    password=self.password,
                )

                print(f"✅ Connected to database {self.database}")

            except Exception as e:
                raise RuntimeError(f"❌ Connection failed: {e}")

    def close(self):
        """This method handles closing the connection to the database"""
        if self.conn:
            self.conn.close()
            self.conn = None
            print(f"Closed connection to database {self.database}")

    def query(self, query: str, parameters=None):
        if self.conn is None:
            raise RuntimeError("Call connect() before query()")

        with self.conn.cursor() as cur:
            cur.execute(query, parameters)
            return cur.fetchall()


    def query_as_df(self, query: str, parameters=None):
        if self.conn is None:
            raise RuntimeError("Call connect() before query()")

        with self.conn.cursor() as cur:
            cur.execute(query, parameters)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()

        df = pd.DataFrame(rows, columns=columns)

        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col])
            except Exception:
                pass

        return df

    def execute(self, statement, parameters=None, *, commit=False, close=True):
        if not self.conn:
            self.connect()

        try:
            with self.conn.cursor() as cur:
                cur.execute(statement, parameters)

            if commit:
                self.conn.commit()

        except Exception as e:
            self.conn.rollback()
            raise Exception(f"❌ Execute failed: {e}")

        finally:
            if close:
                self.close()

    def execute_mult(self, statement, parameters=None, *, commit=False, close=True):
        if not self.conn:
            self.connect()

        try:
            with self.conn.cursor() as cur:
                execute_values(cur, statement, parameters)

            if commit:
                self.conn.commit()

        except Exception as e:
            self.conn.rollback()
            raise Exception(f"❌ Bulk insert failed: {e}")

        finally:
            if close:
                self.close()

    def execute_sql_file(self, filepath, *, commit=False, close=True):
        with open(filepath, "r") as f:
            sql_query = f.read()

        self.execute(sql_query, commit=commit, close=close) 