CREATE TABLE IF NOT EXISTS kiwoom_legacy_ticks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_event_id TEXT NOT NULL UNIQUE,
  market TEXT NOT NULL DEFAULT 'KRX',
  code TEXT NOT NULL,
  trade_time TEXT,
  price REAL,
  change_rate REAL,
  acc_volume REAL,
  tick_volume REAL,
  open_price REAL,
  high_price REAL,
  low_price REAL,
  strength REAL,
  received_at TEXT NOT NULL,
  imported_at TEXT NOT NULL,
  raw_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_kiwoom_legacy_ticks_code_received
  ON kiwoom_legacy_ticks(code, received_at DESC);
