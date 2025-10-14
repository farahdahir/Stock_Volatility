import sqlite3

import pandas as pd
import requests
from config import settings

class AlphaVantageAPI:
    def __init__(self, api_key=settings.alpha_api_key):
        self.__api_key = api_key
        
    def get_daily(self, ticker, output_size='full'):

        # Create URL
        url = ('https://www.alphavantage.co/query?'\
        'function=TIME_SERIES_DAILY&'\
        f'symbol={ticker}&'\
        f'outputsize={output_size}&'\
        'datatype=json&'\
        f'apikey={self.__api_key}')
        
        # Send request to API
        response = requests.get(url=url)

        # Extract JSON data from reponse
        response_data = response.json()

        if 'Time Series (Daily)' not in response_data.keys():
            raise Exception(f'Invalid API call. Check that ticker symbol: {ticker} is correct')

        # Read data into DataFrame
        stock_data = response_data['Time Series (Daily)']
        df = pd.DataFrame.from_dict(stock_data, orient='index', dtype=float)

        # Convert index to Datetime index & rename
        df.index = pd.to_datetime(df.index)
        df.index.name = 'date'

        # Rename columns
        df.columns = [c.split('. ')[-1] for c in df.columns]

        # Return DataFrame
        return df


class SQLRepository:
    def __init__(self, connection):
        self.connection = connection

    def insert_table(self, table_name, records, if_exists='replace'):

        '''Insert DataFrame into SQLite database as table

        Parameters
        -----------
        table_name : str
            Name of the table in SQLite database.
        records : pd.DataFrame
            Records to be inserted to database
        if_exists : str, optional
            How to behave if the table already exists.
            -`fail`: Raise ValueError.
            -`replace`: Drop the table before inserting new values.
            - `append`: Insert new values to existing table.

        Return
        -----------
        DataDframe
        Index is DatetimeIndex `date`. Columns are `open`, `high`, `low`, `close` and `volume`.
        '''

        # Insert DataFrame into SQLite database as table
        n_inserted = records.to_sql(name=table_name, con=self.connection, if_exists=if_exists)

        # Return number of records inserted & transaction_successful==True
        return {'transaction_successful': True, 'records_inserted': n_inserted}
    
    def read_table (self, table_name, limit=None):

        '''Read table from database.

        Parameters
        -----------
        table_name : str
            Name of the table in SQLite database.
        limit : int, None, optional
            Number of most recent records to retrieve

        Return
        -----------
        DataDframe
        Index is DatetimeIndex `date`. Columns are `open`, `high`, `low`, `close` and `volume`.
        '''

        # Create SQL query (with optional LIMIT)
        if limit:
            sql = f"SELECT * FROM '{table_name}' LIMIT {limit}"
        else:
            sql = f"SELECT * FROM '{table_name}'"

        # Retrieve data, read into DataFrame
        df = pd.read_sql(con=self.connection, sql=sql, parse_dates=['date'], index_col='date')

        # Return DataFrame
        return df
        