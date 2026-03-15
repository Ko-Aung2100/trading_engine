from .golden_cross import GoldenCrossStrategy
from .smc_strategy import SMCStrategy

class StrategyFactory:
    _strategies = {
        "golden_cross": GoldenCrossStrategy(),
        "smc": SMCStrategy()
    }

    @classmethod
    def get_strategy(cls, strategy_id: str):
        strategy = cls._strategies.get(strategy_id.lower())
        if not strategy:
            raise ValueError(f"Strategy '{strategy_id}' is not registered in the Factory.")
        return strategy