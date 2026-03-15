import asyncio
from datetime import datetime
import pandas as pd

class StateManager:
    def __init__(self):
        self.trade_history = []
        self.ui_update_callbacks = []
        self.live_df = pd.DataFrame() # NEW: Stores the live market data for the chart

    def add_trade(self, trade_info: dict):
        trade_info["timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.trade_history.append(trade_info)
        self._notify_ui()

    def update_live_data(self, df: pd.DataFrame):
        """Updates the live dataframe and refreshes the UI chart."""
        self.live_df = df
        self._notify_ui()

    def register_callback(self, callback):
        self.ui_update_callbacks.append(callback)

    def _notify_ui(self):
        for callback in self.ui_update_callbacks:
            if asyncio.iscoroutinefunction(callback):
                asyncio.create_task(callback())
            else:
                callback()

state = StateManager()