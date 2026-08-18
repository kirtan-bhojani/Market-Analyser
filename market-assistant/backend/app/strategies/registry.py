from app.strategies.base import Strategy

_REGISTRY: dict[str, Strategy] = {}


def register(strategy: Strategy) -> Strategy:
    _REGISTRY[strategy.name] = strategy
    return strategy


def get_strategy(name: str) -> Strategy:
    if name not in _REGISTRY:
        raise KeyError(f"Unknown strategy: {name}")
    return _REGISTRY[name]


def list_strategies() -> list[Strategy]:
    return list(_REGISTRY.values())
