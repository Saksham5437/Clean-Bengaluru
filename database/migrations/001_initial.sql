CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS reports (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  case_id TEXT NOT NULL UNIQUE,
  source TEXT NOT NULL CHECK (source IN ('citizen', 'bus_camera')),
  category TEXT NOT NULL,
  description TEXT,
  latitude NUMERIC(9,6),
  longitude NUMERIC(9,6),
  location_label TEXT NOT NULL,
  density_score SMALLINT CHECK (density_score BETWEEN 0 AND 100),
  severity TEXT CHECK (severity IN ('low', 'moderate', 'high', 'critical')),
  status TEXT NOT NULL DEFAULT 'submitted',
  evidence_url TEXT,
  ai_confidence NUMERIC(5,4),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS reports_status_idx ON reports(status);
CREATE INDEX IF NOT EXISTS reports_created_at_idx ON reports(created_at DESC);
CREATE INDEX IF NOT EXISTS reports_location_idx ON reports(latitude, longitude);

CREATE TABLE IF NOT EXISTS audit_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  report_id UUID REFERENCES reports(id) ON DELETE CASCADE,
  actor_id UUID,
  action TEXT NOT NULL,
  metadata JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
