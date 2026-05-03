from abc import ABC, abstractmethod
import pandas as pd


class ITradingStrategy(ABC):
    """
        Interface for all Trading Setups.
        LSP (Liskov Substitution Principle): Any new strategy can replace the old one.
    """

    @property
    @abstractmethod
    def name(self):
        pass

    @abstractmethod
    def generate_signal(self, df:pd.DataFrame):
        '''
        Returns a boolean Pandas Series indicating if the setup triggered on that day.
        :param df:
        :return:
        '''
        pass
