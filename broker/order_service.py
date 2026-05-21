"""Order request gate.

Order integration is scaffolded but disabled by default. A future broker
adapter can execute approved requests after this service has accepted them.
"""

from app.config import ENABLE_ORDER_API, ORDER_CONFIRMATION_TEXT, REQUIRE_ORDER_CONFIRMATION
from core.database import dumps_json, row_to_dict, utc_now


class OrderService:
    def __init__(
        self,
        conn,
        order_api_enabled=None,
        require_confirmation=None,
        confirmation_text=None,
    ):
        self.conn = conn
        self.order_api_enabled = ENABLE_ORDER_API if order_api_enabled is None else bool(order_api_enabled)
        self.require_confirmation = (
            REQUIRE_ORDER_CONFIRMATION if require_confirmation is None else bool(require_confirmation)
        )
        self.confirmation_text = confirmation_text or ORDER_CONFIRMATION_TEXT

    def request_order(
        self,
        user_id,
        provider,
        market,
        code,
        side,
        quantity,
        order_type="market",
        limit_price=None,
        approval_text=None,
        extra=None,
    ):
        status = self._evaluate_status(approval_text)
        now = utc_now()
        request = {
            "user_id": user_id,
            "provider": provider,
            "market": market,
            "code": code,
            "side": side,
            "quantity": quantity,
            "order_type": order_type,
            "limit_price": limit_price,
            "extra": extra or {},
        }
        cur = self.conn.execute(
            """
            INSERT INTO order_requests(
              user_id, provider, market, code, side, quantity, order_type, limit_price,
              status, approval_required, approval_text, request_json, response_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                provider,
                market,
                code,
                side,
                float(quantity),
                order_type,
                limit_price,
                status,
                int(self.require_confirmation),
                approval_text,
                dumps_json(request),
                None,
                now,
                now,
            ),
        )
        self.conn.commit()
        return row_to_dict(self.conn.execute("SELECT * FROM order_requests WHERE id = ?", (cur.lastrowid,)).fetchone())

    def list_orders(self, user_id):
        rows = self.conn.execute(
            "SELECT * FROM order_requests WHERE user_id = ? ORDER BY id DESC",
            (user_id,),
        )
        return [row_to_dict(row) for row in rows]

    def _evaluate_status(self, approval_text):
        if not self.order_api_enabled:
            return "blocked_order_api_disabled"
        if self.require_confirmation and approval_text != self.confirmation_text:
            return "blocked_confirmation_required"
        return "accepted_pending_adapter"
