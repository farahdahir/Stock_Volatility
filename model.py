import os
from glob import glob

import joblib
import pandas as pd
from arch import arch_model
from config import settings
from data import AlphaVantageAPI, SQLRepository

class GarchModel:
    '''Class for training GARCH model and generating predictions.

    Attributes
    -----------
    ticker : str
        Ticker symbol of the equity whose volatility will be predicted.
    repo : SQLRepository
        The repository where the training data will be stored.
    use_new_data : bool
        Whether to download new data from AlphaVantage API to train the model OR
        to use existing data stored in the repository.
    model_directory: str
        Path for directory where trained models will be stored.

    Methods
    -----------
    wrangle_data
        Generate equity returns from data in database.
    fit
        Fit training data
    predict
        Generate volatility forecast from trained model.
    dump
        Save trained model to file.
    load
        Load trained model from file.
    '''

    def __init__(self, ticker, repo, use_new_data):
        self.ticker = ticker
        self.repo = repo
        self.use_new_data = use_new_data
        self.model_directory = settings.model_directory

    def wrangle_data(self, n_observations):

        '''Extract table data from database (or get from AlphaVantage API), transfrom
        it for training model & attach it to `self.data`.

        Parameters
        -----------
        n_observations : int
            Number of most recent records to retrieve

        Return
        -----------
        None
        '''
        # Add new data to database if required
        if self.use_new_data:
            # Instantiate an API class
            api = AlphaVantageAPI()
            # Get data
            new_data = api.get_daily(ticker=self.ticker)
            # Insert data to repo
            self.repo.insert_table(table_name=self.ticker, records=new_data, if_exists='replace')
        
        # Pull data from SQL database
        df = self.repo.read_table(table_name=self.ticker, limit=n_observations +1)

        # Clean data, attach to class as `data` attribute
        df.sort_index(ascending=True, inplace=True)
        df['return'] = df['close'].pct_change() *100

        self.data = df['return'].dropna()

    def fit(self, p, q):
        '''Create model, fit to `self.data` & attach to `self.model` attribute.

        Parameters
        -----------
        p : int
            Lag order of the symmetric innovation
        q : int
            Lag order of lagged volatility

        Return
        -----------
        None
        '''
        # Train model, attach to `self.model`
        self.model = arch_model(self.data, p=p, q=q, rescale=False).fit(disp=0)

    
    def __clean_prediction(self, prediction):
        '''Reformat model prediction to JSON.

        Parameters
        -----------
        prediction : pd.DataFrame
            Variance from a `ARCHModelForecast`

        Return
        -----------
        dict
            Forecast of volatility, Each key is date in ISO 8601 format.
            Each value is predicted volatiliy.
        '''

        # Create forecast start date
        start = prediction.index[0] + pd.DateOffset(days=1)

        # Create date range
        prediction_dates = pd.bdate_range(start=start, periods=prediction.shape[1])

        # Create prediction index label, ISO 8601 format
        prediction_index = [d.isoformat() for d in prediction_dates]

        # Extract prediction from DataFrame, get square root
        data = prediction.values.flatten()**0.5

        # Combine `data` and `prediction_index` into series
        prediction_formatted  = pd.Series(data, index=prediction_index)

        # Return Series as dictionary
        return prediction_formatted.to_dict()
    
    def predict_volatility(self, horizon=5):
        '''Predict volatility using `self.model`.

        Parameters
        -----------
        horizon : int
            Horizon of forecast, default 5.

        Return
        -----------
        dict
            Forecast of volatility, Each key is date in ISO 8601 format.
            Each value is predicted volatiliy.
        '''
        # Generate variance forecast from `self.model`
        prediction = self.model.forecast(horizon=horizon, reindex=False).variance

        # Format prediction with `self.__clean_prediction`
        prediction_formatted = self.__clean_prediction(prediction)

        # Return `prediction_formatted`
        return prediction_formatted
        
    def dump(self):
        '''Save model to `self.model_directory` with timestamp.

        Return
        -----------
        str
            filepath where model is saved.
        '''
        # Create NOW timestamp
        timestamp = pd.Timestamp.now().strftime("%Y-%m-%d_%H-%M-%S")

        # Create filepath, including `self.model_directory`
        filepath = os.path.join(self.model_directory, f'{timestamp}_{self.ticker}.pkl')

        # Save `self.nodel`
        joblib.dump(self.model, filepath)

        # Return filepath
        return filepath
    
    def load(self):
        '''Load latest model in `self.model_directory` for `self.ticker`,
        attach to `self.model` attribute.
        '''
        # Create pattern for glob search
        pattern = os.path.join(self.model_directory, f'*{self.ticker}.pkl')

        # Try to find path of latest model
        try:
            model_path = sorted(glob(pattern))[-1]
        # Handle possibel `IndexError`
        except IndexError:
            raise Exception (f'No model with {self.ticker}.')

        # Load model
        self.model = joblib.load(model_path)