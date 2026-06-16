-- Authoritative schema for the two new Delta tables.
-- These are executed at app startup via services/db.py:init_tables().
-- Substitute {catalog} and {schema} from TARGET_CATALOG / TARGET_SCHEMA env vars.
-- review_status valid values: 'verified' | 'rejected' | 'noted'

CREATE TABLE IF NOT EXISTS {catalog}.{schema}.facility_reviews (
  facility_id    STRING NOT NULL,
  capability     STRING NOT NULL,
  review_status  STRING NOT NULL,
  review_notes   STRING,
  reviewed_at    TIMESTAMP NOT NULL,
  reviewed_by    STRING
) USING DELTA;

CREATE TABLE IF NOT EXISTS {catalog}.{schema}.facility_capability_scores (
  facility_id           STRING NOT NULL,
  facility_name         STRING,
  capability            STRING NOT NULL,
  trust_level           STRING NOT NULL,
  confidence_score      DOUBLE NOT NULL,
  evidence_json         STRING,
  missing_evidence_json STRING,
  reasoning             STRING,
  last_updated          TIMESTAMP NOT NULL
) USING DELTA;
