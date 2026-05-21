"""Encrypted broker credential storage."""

from core.crypto import CredentialCrypto
from core.database import row_to_dict, utc_now


class BrokerCredentialStore:
    def __init__(self, conn, crypto=None):
        self.conn = conn
        self.crypto = crypto or CredentialCrypto()

    def upsert_credentials(
        self,
        user_id,
        provider,
        app_key,
        app_secret,
        account_no=None,
        environment="paper",
        can_read=True,
        can_order=False,
    ):
        now = utc_now()
        self.conn.execute(
            """
            INSERT INTO broker_credentials(
              user_id, provider, environment, app_key_encrypted, app_secret_encrypted,
              account_no_encrypted, can_read, can_order, is_active, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            ON CONFLICT(user_id, provider, environment)
            DO UPDATE SET app_key_encrypted = excluded.app_key_encrypted,
              app_secret_encrypted = excluded.app_secret_encrypted,
              account_no_encrypted = excluded.account_no_encrypted,
              can_read = excluded.can_read,
              can_order = excluded.can_order,
              is_active = 1,
              updated_at = excluded.updated_at
            """,
            (
                user_id,
                provider,
                environment,
                self.crypto.encrypt_text(app_key),
                self.crypto.encrypt_text(app_secret),
                self.crypto.encrypt_text(account_no),
                int(can_read),
                int(can_order),
                now,
                now,
            ),
        )
        self.conn.commit()

    def list_credentials_meta(self, user_id):
        rows = self.conn.execute(
            """
            SELECT id, user_id, provider, environment, can_read, can_order, is_active, created_at, updated_at
            FROM broker_credentials
            WHERE user_id = ?
            ORDER BY provider, environment
            """,
            (user_id,),
        )
        return [row_to_dict(row) for row in rows]

    def get_decrypted_credentials(self, user_id, provider, environment="paper"):
        row = self.conn.execute(
            """
            SELECT *
            FROM broker_credentials
            WHERE user_id = ? AND provider = ? AND environment = ? AND is_active = 1
            """,
            (user_id, provider, environment),
        ).fetchone()
        if not row:
            return None
        data = row_to_dict(row)
        return {
            "id": data["id"],
            "user_id": data["user_id"],
            "provider": data["provider"],
            "environment": data["environment"],
            "app_key": self.crypto.decrypt_text(data["app_key_encrypted"]),
            "app_secret": self.crypto.decrypt_text(data["app_secret_encrypted"]),
            "account_no": self.crypto.decrypt_text(data["account_no_encrypted"]),
            "can_read": bool(data["can_read"]),
            "can_order": bool(data["can_order"]),
            "is_active": bool(data["is_active"]),
        }
