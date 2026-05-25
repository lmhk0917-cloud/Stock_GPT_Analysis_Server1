"""Broker provider registry shared by API, UI, and adapter factory."""


BROKER_PROVIDERS = {
    "mock": {
        "id": "mock",
        "label": "Mock",
        "environments": ["paper"],
        "credential_fields": ["app_key", "app_secret"],
        "supports_market_data": True,
        "supports_account": False,
        "supports_order": False,
        "order_default_enabled": False,
        "status": "ready_offline",
        "notes": "Offline deterministic adapter for development and smoke tests.",
    },
    "kis_rest": {
        "id": "kis_rest",
        "label": "Korea Investment REST",
        "environments": ["paper", "live"],
        "credential_fields": ["app_key", "app_secret", "account_no"],
        "supports_market_data": True,
        "supports_account": True,
        "supports_order": False,
        "order_default_enabled": False,
        "status": "credential_ready_adapter_partial",
        "notes": "Credential storage and quote-token skeleton exist. OHLCV/account/order execution still need final endpoint mapping.",
    },
    "kiwoom_legacy": {
        "id": "kiwoom_legacy",
        "label": "Kiwoom OpenAPI+ legacy",
        "environments": ["live"],
        "credential_fields": ["app_key", "app_secret", "account_no"],
        "supports_market_data": True,
        "supports_account": True,
        "supports_order": False,
        "order_default_enabled": False,
        "status": "legacy_worker_required",
        "notes": "Requires the isolated py37_32 legacy worker. It is not loaded by the 64-bit server process.",
    },
}

PROVIDER_ALIASES = {
    "kiwoom": "kiwoom_legacy",
}


def normalize_provider(provider):
    return PROVIDER_ALIASES.get(provider, provider)


def list_broker_providers():
    return [BROKER_PROVIDERS[key] for key in ("mock", "kis_rest", "kiwoom_legacy")]


def get_broker_provider(provider):
    normalized = normalize_provider(provider)
    return BROKER_PROVIDERS.get(normalized)


def validate_provider_environment(provider, environment):
    meta = get_broker_provider(provider)
    if not meta:
        raise ValueError("Unknown broker provider: {}".format(provider))
    if environment not in meta["environments"]:
        raise ValueError(
            "Provider {} does not support environment {}. Supported: {}".format(
                meta["id"],
                environment,
                ", ".join(meta["environments"]),
            )
        )
    return meta
