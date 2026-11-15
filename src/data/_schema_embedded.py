"""Embedded copy of the KeKar schema.

PyInstaller does not ship .sql files that sit next to the source unless they
are declared as data in KeKar.spec. Missing the schema at runtime crashed the
bundled app on first launch, so the authoritative copy lives here as a Python
string and `schema.sql` is generated from it. `tests/test_bundle_safety.py`
asserts the two stay byte-identical.

Field names match spec §7.2 verbatim. Additions are marked `[+]`.
"""
from __future__ import annotations

SCHEMA_SQL = """\
-- KeKar schema v1. Field names match the specification verbatim.
CREATE TABLE IF NOT EXISTS schema_meta (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS properties (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  address        TEXT NOT NULL,
  city           TEXT,
  zip_code       TEXT,
  rent_price     REAL,
  deposit_amount REAL,
  available_date TEXT,
  bedrooms       INTEGER,
  bathrooms      REAL,
  sqft           INTEGER,
  pet_policy     TEXT,
  status         TEXT NOT NULL DEFAULT 'Vacant'
                 CHECK (status IN ('Vacant','Rented')),
  amenity_wd         INTEGER NOT NULL DEFAULT 0 CHECK (amenity_wd IN (0,1)),
  amenity_ac         INTEGER NOT NULL DEFAULT 0 CHECK (amenity_ac IN (0,1)),
  amenity_yard       INTEGER NOT NULL DEFAULT 0 CHECK (amenity_yard IN (0,1)),
  amenity_dishwasher INTEGER NOT NULL DEFAULT 0 CHECK (amenity_dishwasher IN (0,1)),
  amenity_parking    INTEGER NOT NULL DEFAULT 0 CHECK (amenity_parking IN (0,1)),
  notes          TEXT,
  created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS applicants (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  property_id    INTEGER REFERENCES properties(id) ON DELETE SET NULL,
  applicant_name TEXT NOT NULL,
  contact_info   TEXT,
  screening_stage TEXT NOT NULL DEFAULT 'Inquiry Received'
                 CHECK (screening_stage IN
                   ('Inquiry Received','Questionnaire Sent',
                    'Background Check','Approved','Rejected')),
  notes          TEXT,
  created_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at     TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS applicant_docs (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  applicant_id INTEGER NOT NULL REFERENCES applicants(id) ON DELETE CASCADE,
  rel_path     TEXT NOT NULL,
  kind         TEXT,
  created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS chat_messages (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  role       TEXT NOT NULL CHECK (role IN ('user','assistant','system','tool')),
  content    TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS listing_runs (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  channel     TEXT NOT NULL DEFAULT 'facebook_marketplace',
  status      TEXT NOT NULL DEFAULT 'draft'
              CHECK (status IN ('draft','autofilled','published','cancelled')),
  created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS leases (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  property_id INTEGER REFERENCES properties(id) ON DELETE SET NULL,
  tenant_name TEXT NOT NULL DEFAULT '',
  body        TEXT NOT NULL DEFAULT '',
  created_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE INDEX IF NOT EXISTS idx_applicants_property ON applicants(property_id);
CREATE INDEX IF NOT EXISTS idx_applicants_stage    ON applicants(screening_stage);
CREATE INDEX IF NOT EXISTS idx_chat_created        ON chat_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_leases_property    ON leases(property_id);
CREATE INDEX IF NOT EXISTS idx_listing_property    ON listing_runs(property_id);

-- Accounts. This is the plumbing for the client-facing feature: a user logs in
-- before the portal is opened. Nothing here is wired to a portal yet.
CREATE TABLE IF NOT EXISTS users (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  username      TEXT NOT NULL UNIQUE,
  display_name  TEXT NOT NULL DEFAULT '',
  password_hash TEXT NOT NULL,
  role          TEXT NOT NULL DEFAULT 'member'
                CHECK (role IN ('owner','member')),
  created_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

CREATE TABLE IF NOT EXISTS sessions (
  token      TEXT PRIMARY KEY,
  user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  expires_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON sessions(expires_at);
"""


def embedded_schema() -> str:
    """Return the schema DDL exactly as it appears in schema.sql."""
    return SCHEMA_SQL
