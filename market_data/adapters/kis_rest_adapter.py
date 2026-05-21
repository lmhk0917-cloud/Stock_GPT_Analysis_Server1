"""Korea Investment REST adapter skeleton.

This adapter is safe to import without credentials. It performs no network work
until a method is called with user credentials from BrokerCredentialStore.
Endpoint paths and TR IDs are centralized here so the rest of the server remains
provider-neutral.
"""

import json
import time
import urllib.parse
import urllib.request

from market_data.adapters.base import MarketDataAdapter


class KISRestAdapter(MarketDataAdapter):
    provider = "kis_rest"

    REAL_BASE_URL = "https://openapi.koreainvestment.com:9443"
    PAPER_BASE_URL = "https://openapivts.koreainvestment.com:29443"

    def __init__(self, environment="paper", timeout_sec=10):
        self.environment = environment
        self.timeout_sec = timeout_sec
        self.base_url = self.PAPER_BASE_URL if environment == "paper" else self.REAL_BASE_URL
        self._access_token = None
        self._token_expires_at = 0

    def list_symbols(self):
        return []

    def fetch_ohlcv(self, market, code, timeframe="1m", limit=80):
        raise NotImplementedError("KIS OHLCV endpoint mapping should be selected after the brokerage API is chosen")

    def get_quote(self, market, code, credentials):
        token = self.get_access_token(credentials)
        query = urllib.parse.urlencode({
            "fid_cond_mrkt_div_code": self._market_div_code(market),
            "fid_input_iscd": code,
        })
        headers = self._headers(
            credentials,
            token,
            tr_id="FHKST01010100",
        )
        return self._request_json(
            "GET",
            "/uapi/domestic-stock/v1/quotations/inquire-price?{}".format(query),
            headers=headers,
        )

    def place_order(self, order_request, credentials):
        raise RuntimeError("KIS order execution is intentionally disabled until order policy is finalized")

    def get_access_token(self, credentials):
        now = time.time()
        if self._access_token and now < self._token_expires_at:
            return self._access_token

        payload = {
            "grant_type": "client_credentials",
            "appkey": credentials["app_key"],
            "appsecret": credentials["app_secret"],
        }
        response = self._request_json("POST", "/oauth2/tokenP", payload=payload)
        token = response.get("access_token")
        if not token:
            raise RuntimeError("KIS token response did not include access_token")

        expires_in = int(response.get("expires_in", 3600))
        self._access_token = token
        self._token_expires_at = now + max(expires_in - 60, 60)
        return token

    def _headers(self, credentials, token, tr_id):
        return {
            "content-type": "application/json; charset=utf-8",
            "authorization": "Bearer {}".format(token),
            "appkey": credentials["app_key"],
            "appsecret": credentials["app_secret"],
            "tr_id": tr_id,
            "custtype": "P",
        }

    def _request_json(self, method, path, headers=None, payload=None):
        url = self.base_url + path
        raw_payload = None
        if payload is not None:
            raw_payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=raw_payload,
            headers=headers or {"content-type": "application/json; charset=utf-8"},
            method=method,
        )
        with urllib.request.urlopen(req, timeout=self.timeout_sec) as response:
            return json.loads(response.read().decode("utf-8"))

    def _market_div_code(self, market):
        return "J"
