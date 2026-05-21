"""Small credential encryption helper.

This uses a project master key from the environment and stores only encrypted
credential envelopes in SQLite. It is intentionally dependency-free so the MVP
can run in the existing Python 3.7 environment.
"""

import base64
import hashlib
import hmac
import json
import os

from app.config import CREDENTIAL_MASTER_KEY


_VERSION = "v1"
_SALT_BYTES = 16
_NONCE_BYTES = 16
_TAG_BYTES = 32
_ROUNDS = 200000


class CredentialCrypto:
    def __init__(self, master_key=None):
        self.master_key = master_key if master_key is not None else CREDENTIAL_MASTER_KEY
        if not self.master_key:
            raise ValueError("CREDENTIAL_MASTER_KEY is required for credential encryption")

    def encrypt_text(self, plaintext):
        if plaintext is None:
            return None
        salt = os.urandom(_SALT_BYTES)
        nonce = os.urandom(_NONCE_BYTES)
        key = self._derive_key(salt)
        raw = plaintext.encode("utf-8")
        ciphertext = self._xor_stream(raw, key, nonce)
        tag = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
        envelope = {
            "v": _VERSION,
            "salt": self._b64(salt),
            "nonce": self._b64(nonce),
            "ct": self._b64(ciphertext),
            "tag": self._b64(tag),
        }
        return base64.urlsafe_b64encode(json.dumps(envelope, separators=(",", ":")).encode("utf-8")).decode("ascii")

    def decrypt_text(self, encrypted):
        if encrypted is None:
            return None
        envelope = json.loads(base64.urlsafe_b64decode(encrypted.encode("ascii")).decode("utf-8"))
        if envelope.get("v") != _VERSION:
            raise ValueError("Unsupported credential envelope version")
        salt = self._unb64(envelope["salt"])
        nonce = self._unb64(envelope["nonce"])
        ciphertext = self._unb64(envelope["ct"])
        expected_tag = self._unb64(envelope["tag"])
        key = self._derive_key(salt)
        actual_tag = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(expected_tag, actual_tag):
            raise ValueError("Credential authentication failed")
        return self._xor_stream(ciphertext, key, nonce).decode("utf-8")

    def _derive_key(self, salt):
        return hashlib.pbkdf2_hmac("sha256", self.master_key.encode("utf-8"), salt, _ROUNDS, dklen=32)

    def _xor_stream(self, data, key, nonce):
        output = bytearray()
        counter = 0
        while len(output) < len(data):
            block = hmac.new(key, nonce + counter.to_bytes(8, "big"), hashlib.sha256).digest()
            output.extend(block)
            counter += 1
        return bytes(left ^ right for left, right in zip(data, output))

    def _b64(self, raw):
        return base64.urlsafe_b64encode(raw).decode("ascii")

    def _unb64(self, encoded):
        return base64.urlsafe_b64decode(encoded.encode("ascii"))
