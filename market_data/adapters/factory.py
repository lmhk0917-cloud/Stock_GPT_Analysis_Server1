"""Adapter factory for provider-neutral server code."""

from app.config import DEFAULT_PROVIDER
from broker.provider_registry import normalize_provider
from market_data.adapters.kis_rest_adapter import KISRestAdapter
from market_data.adapters.mock_adapter import MockMarketDataAdapter


def create_market_data_adapter(provider=None, environment="paper"):
    provider = normalize_provider(provider or DEFAULT_PROVIDER)
    if provider == "mock":
        return MockMarketDataAdapter()
    if provider == "kis_rest":
        return KISRestAdapter(environment=environment)
    if provider == "kiwoom_legacy":
        raise RuntimeError("Use legacy/kiwoom_worker.py for Kiwoom OpenAPI+")
    raise ValueError("Unknown market data provider: {}".format(provider))
