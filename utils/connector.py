from sqlalchemy import create_engine
import pandas as pd

class DataConnector():

    engine = None
    conn = None

    @classmethod
    def create_engine(cls, DB_URL):
        try:
            cls.engine = create_engine(str(DB_URL))
        
            return 1
        except Exception as ex:
            print(ex)
            return 0
        
    @classmethod
    def create_conn(cls):
        try:
            cls.conn = cls.engine.connect()
            
            return 1
        except Exception as ex:
            print(ex)
            return 0
        
    @classmethod
    def close_conn(cls):
        try:
            if cls.conn:
                cls.conn.close()
            return 1
        except Exception as ex:
            print(ex)
            return 0
        
    @classmethod
    def read_data(cls, query):
        try:
            df = pd.read_sql(query, con=cls.engine)
            
            return df
        except Exception as ex:
            print(ex)
            df = pd.DataFrame()
            return df
            
    @classmethod
    def run_query(cls, query):
        try:
            cls.engine.execute(query)
        except Exception as ex:
            print(ex)
            return None
    @classmethod
    def write_data(cls, df, schema, table, if_exists='append'):
        try:
            df.to_sql(name=table,schema=schema,if_exists=if_exists,con=cls.engine, index=False)
            return 1
        except Exception as ex:
            print(ex)
            return 0
    
        
