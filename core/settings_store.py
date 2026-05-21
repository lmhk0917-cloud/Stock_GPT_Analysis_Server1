"""User setting facade for the server MVP."""

from core.user_store import UserStore


class SettingsStore:
    def __init__(self, conn):
        self.users = UserStore(conn)

    def get_user_settings(self, user_id):
        return self.users.get_settings(user_id)

    def set_user_setting(self, user_id, key, value):
        self.users.set_setting(user_id, key, value)
