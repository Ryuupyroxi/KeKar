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
  kind           TEXT NOT NULL DEFAULT 'rental'
                 CHECK (kind IN ('rental','short_stay')),
  amenity_wd         INTEGER NOT NULL DEFAULT 0 CHECK (amenity_wd IN (0,1)),
  amenity_ac         INTEGER NOT NULL DEFAULT 0 CHECK (amenity_ac IN (0,1)),
  amenity_yard       INTEGER NOT NULL DEFAULT 0 CHECK (amenity_yard IN (0,1)),
  amenity_dishwasher INTEGER NOT NULL DEFAULT 0 CHECK (amenity_dishwasher IN (0,1)),
  amenity_parking    INTEGER NOT NULL DEFAULT 0 CHECK (amenity_parking IN (0,1)),
  notes          TEXT,
  -- Short-stay (Airbnb-style) terms. NULL for a long-term rental.
  nightly_price      REAL,
  cleaning_fee       REAL,
  extra_guest_fee    REAL,
  min_stay_nights    INTEGER,
  max_guests         INTEGER,
  check_in_time      TEXT,
  check_out_time     TEXT,
  instant_book       INTEGER NOT NULL DEFAULT 0 CHECK (instant_book IN (0,1)),
  cancellation_policy TEXT,
  house_rules        TEXT,
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

-- Reservations on a short-stay property. ``external_uid`` is the iCal UID the
-- portal assigned, so a sync updates rather than duplicates.
CREATE TABLE IF NOT EXISTS bookings (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  property_id  INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  portal       TEXT NOT NULL DEFAULT '',
  guest_name   TEXT NOT NULL DEFAULT '',
  guest_contact TEXT,
  check_in     TEXT NOT NULL DEFAULT '',
  check_out    TEXT NOT NULL DEFAULT '',
  nights       INTEGER,
  payout       REAL,
  status       TEXT NOT NULL DEFAULT 'confirmed'
               CHECK (status IN ('confirmed','cancelled','blocked','inquiry')),
  external_uid TEXT,
  source       TEXT NOT NULL DEFAULT 'manual'
               CHECK (source IN ('manual','ical')),
  notes        TEXT,
  created_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  updated_at   TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- Per-portal settings for a short-stay property: whether it is listed there,
-- a price/min-stay override, and the portal's own iCal URL.
CREATE TABLE IF NOT EXISTS property_portals (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  property_id         INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  portal              TEXT NOT NULL
                      CHECK (portal IN ('airbnb','vrbo','booking_com')),
  enabled             INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0,1)),
  price_override      REAL,
  min_stay_override   INTEGER,
  external_ical_url   TEXT,
  external_listing_url TEXT,
  last_sync_at        TEXT,
  UNIQUE(property_id, portal)
);

-- One row per sync attempt, newest last, so the UI can show what happened.
CREATE TABLE IF NOT EXISTS portal_sync_log (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  property_id INTEGER NOT NULL REFERENCES properties(id) ON DELETE CASCADE,
  portal      TEXT NOT NULL,
  started_at  TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  finished_at TEXT,
  result      TEXT NOT NULL DEFAULT 'ok'
              CHECK (result IN ('ok','failed','unchanged')),
  detail      TEXT
);

CREATE INDEX IF NOT EXISTS idx_applicants_property ON applicants(property_id);
CREATE INDEX IF NOT EXISTS idx_applicants_stage    ON applicants(screening_stage);
CREATE INDEX IF NOT EXISTS idx_chat_created        ON chat_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_leases_property    ON leases(property_id);
CREATE INDEX IF NOT EXISTS idx_listing_property    ON listing_runs(property_id);
CREATE INDEX IF NOT EXISTS idx_bookings_property  ON bookings(property_id);
CREATE INDEX IF NOT EXISTS idx_bookings_dates     ON bookings(property_id, check_in, check_out);
CREATE INDEX IF NOT EXISTS idx_portals_property   ON property_portals(property_id);

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
