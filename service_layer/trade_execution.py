import asyncio
from typing import Literal
from service_layer.data_fetcher import DataFetcher
from service_layer.analytics import AnalyticsEngine


# TODO - how to identify which asset to be trade today

class Execution:
    def __init__(self, asset: str):
        self.asset = asset
        self.data_fetcher = DataFetcher()
        self.analyzer = AnalyticsEngine()
        self._pre_market_analysis(asset)

    async def execute_trade(self, asset: str, trade_type: Literal["Equity", "Options"]):


        exec_data = asyncio.to_thread(self.data_fetcher.fetch_history_data, asset=asset, period="1mo", interval="30m")

        # Await them together - Both network calls hit the exchange simultaneously!
        # dir_data, exec_data = await asyncio.gather(dir_task, exec_task) #TODO change the calling of direction function

        # 2. ANALYZE DATA (Sequential math processing)
        exec_data_w_cators = self.analyzer.add_exec_indicators(exec_data)
        dir_data_w_cators = self.analyzer.add_dir_indicators(dir_data)

        # 3. GET DIRECTION & SIGNALS
        asset_dir = self.analyzer.get_asset_direction(dir_data_w_cators)
        exec_signals = self.analyzer.generate_signals(exec_data_w_cators)

        # 4. Extract the absolute latest signal and direction
        current_direction = asset_dir[-1]["DIRECTION"]
        current_signal = exec_signals[-1]["SIGNAL"]

        # TODO: Support/Resistance, Conviction check...

        # 5. FINAL CONVICTION LOGIC
        if current_signal == "BUY" and current_direction == "BULLISH":
            final_action = "BUY"
        elif current_signal == "SELL" and current_direction == "BEARISH":
            final_action = "SELL"
        else:
            final_action = "HOLD"

        print(f"[{asset}] 1D Trend: {current_direction} | 30m Signal: {current_signal} ---> ACTION: {final_action}")

        # 5. TRIGGER ACTUAL ORDER (Placeholder for next sprint)
        if final_action != "HOLD":
            print(f"🚀 Triggering {final_action} sequence for {asset}...")
            # Here we will call the Broker API (Kite/Groww)

        return final_action

    async def _pre_market_analysis(self, asset: str):
        '''

        :return:
        '''
        pass
        history_data_1d = self.data_fetcher.fetch_history_data(asset=asset, period="3mo")
