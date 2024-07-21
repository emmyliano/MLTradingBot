# Import necessary modules
from lumibot.brokers import Alpaca
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader
from datetime import datetime 
from alpaca_trade_api import REST 
from timedelta import Timedelta 
from finbert_utils import estimate_sentiment

# Import API keys from keys.py
from keys import API_KEY, API_SECRET, BASE_URL

# Dictionary to store Alpaca credentials
ALPACA_CREDS = {
    "API_KEY": API_KEY, 
    "API_SECRET": API_SECRET, 
    "PAPER": True
}

# Define the MLTrader strategy class
class MLTrader(Strategy): 
    def initialize(self, symbol: str = "SPY", cash_at_risk: float = .5): 
        # Initialize strategy parameters
        self.symbol = symbol
        self.sleeptime = "24H"  # How often to run the strategy
        self.last_trade = None  # Track the last trade action
        self.cash_at_risk = cash_at_risk  # Percentage of cash to risk per trade
        self.api = REST(base_url=BASE_URL, key_id=API_KEY, secret_key=API_SECRET)  # Alpaca API connection

    def position_sizing(self): 
        # Determine the position size for trading
        cash = self.get_cash()  # Get available cash
        last_price = self.get_last_price(self.symbol)  # Get the last price of the symbol
        quantity = round(cash * self.cash_at_risk / last_price, 0)  # Calculate the quantity to trade
        return cash, last_price, quantity  # Return cash, last price, and quantity

    def get_dates(self): 
        # Get the current date and three days prior
        today = self.get_datetime()  # Get today's date
        three_days_prior = today - Timedelta(days=3)  # Calculate three days prior
        return today.strftime('%Y-%m-%d'), three_days_prior.strftime('%Y-%m-%d')  # Return formatted dates

    def get_sentiment(self): 
        # Get sentiment analysis for the specified date range
        today, three_days_prior = self.get_dates()  # Get today and three days prior
        news = self.api.get_news(symbol=self.symbol, 
                                 start=three_days_prior, 
                                 end=today)  # Fetch news articles
        news = [ev.__dict__["_raw"]["headline"] for ev in news]  # Extract headlines
        probability, sentiment = estimate_sentiment(news)  # Estimate sentiment from headlines
        return probability, sentiment  # Return sentiment probability and label

    def on_trading_iteration(self):
        # Main trading logic executed on each iteration
        cash, last_price, quantity = self.position_sizing()  # Determine position size
        probability, sentiment = self.get_sentiment()  # Get sentiment analysis

        if cash > last_price:  # Ensure there is enough cash to trade
            if sentiment == "positive" and probability > .999:  # Check for strong positive sentiment
                if self.last_trade == "sell": 
                    self.sell_all()  # Sell all if last trade was a sell
                order = self.create_order(
                    self.symbol, 
                    quantity, 
                    "buy", 
                    type="bracket", 
                    take_profit_price=last_price * 1.20,  # Set take profit price
                    stop_loss_price=last_price * .95  # Set stop loss price
                )
                self.submit_order(order)  # Submit the buy order
                self.last_trade = "buy"  # Record the trade action
            elif sentiment == "negative" and probability > .999:  # Check for strong negative sentiment
                if self.last_trade == "buy": 
                    self.sell_all()  # Sell all if last trade was a buy
                order = self.create_order(
                    self.symbol, 
                    quantity, 
                    "sell", 
                    type="bracket", 
                    take_profit_price=last_price * .8,  # Set take profit price
                    stop_loss_price=last_price * 1.05  # Set stop loss price
                )
                self.submit_order(order)  # Submit the sell order
                self.last_trade = "sell"  # Record the trade action

# Define the backtesting period
start_date = datetime(2020, 1, 1)
end_date = datetime(2023, 12, 31) 

# Initialize the broker
broker = Alpaca(ALPACA_CREDS) 

# Initialize the strategy
strategy = MLTrader(name='mlstrat', broker=broker, 
                    parameters={"symbol": "SPY", 
                                "cash_at_risk": .5})

# Run backtesting
strategy.backtest(
    YahooDataBacktesting, 
    start_date, 
    end_date, 
    parameters={"symbol": "SPY", "cash_at_risk": .5}
)

# Uncomment to run the strategy live
# trader = Trader()
# trader.add_strategy(strategy)
# trader.run_all()
