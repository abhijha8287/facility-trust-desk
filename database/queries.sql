-- Named queries for reference. Actual execution is in services/db.py.
--
-- PARAMETERIZATION: In Python, user-supplied values use ? placeholders
-- passed to cursor.execute(sql, [params]). Table names (catalog.schema)
-- use f-strings from env vars only — never from user input.
--
-- SOURCE TABLE (read-only, hardcoded):
--   databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities
--
-- WRITE TABLES (substituted at runtime from TARGET_CATALOG / TARGET_SCHEMA):
--   {catalog}.{schema}.facility_reviews
--   {catalog}.{schema}.facility_capability_scores

-- search_facilities
SELECT unique_id, name, address_city, address_stateOrRegion, numberDoctors, capacity
FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities
WHERE LOWER(name) LIKE ?            -- param: '%<name_query>%'
  AND address_city = ?              -- param: city_filter (omit condition if empty)
  AND address_stateOrRegion = ?     -- param: state_filter (omit condition if empty)
LIMIT 100;

-- get_facility_detail
SELECT *
FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities
WHERE unique_id = ?;                -- param: facility_id

-- get_distinct_cities
SELECT DISTINCT address_city
FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities
WHERE address_city IS NOT NULL
ORDER BY 1
LIMIT 200;

-- get_distinct_states
SELECT DISTINCT address_stateOrRegion
FROM databricks_virtue_foundation_dataset_dais_2026.virtue_foundation_dataset.facilities
WHERE address_stateOrRegion IS NOT NULL
ORDER BY 1;

-- get_cached_scores
SELECT *
FROM {catalog}.{schema}.facility_capability_scores
WHERE facility_id = ?;              -- param: facility_id

-- delete_cached_score (upsert step 1)
DELETE FROM {catalog}.{schema}.facility_capability_scores
WHERE facility_id = ?              -- param: facility_id
  AND capability = ?;              -- param: capability

-- insert_capability_score (upsert step 2)
INSERT INTO {catalog}.{schema}.facility_capability_scores
  (facility_id, facility_name, capability, trust_level, confidence_score,
   evidence_json, missing_evidence_json, reasoning, last_updated)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);

-- insert_review
INSERT INTO {catalog}.{schema}.facility_reviews
  (facility_id, capability, review_status, review_notes, reviewed_at, reviewed_by)
VALUES (?, ?, ?, ?, ?, ?);

-- get_reviews
SELECT *
FROM {catalog}.{schema}.facility_reviews
WHERE facility_id = ?              -- param: facility_id
ORDER BY reviewed_at DESC;
