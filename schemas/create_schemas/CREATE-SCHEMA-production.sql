DROP SCHEMA IF EXISTS production CASCADE;
CREATE SCHEMA production;


-- predictions corresponding to each model.
CREATE TABLE production.predictions (
  model_id    INT REFERENCES results.models (model_id),
  as_of_date  TIMESTAMP,
  entity_id   BIGINT,
  score       NUMERIC,
  rank_abs    INT,
  rank_pct    REAL
);

CREATE INDEX ON production.predictions (as_of_date);
CREATE INDEX ON production.predictions (entity_id,as_of_date);

CREATE TABLE production.time_delta (
  model_id  INT REFERENCES results.models (model_id),
 entity_id   BIGINT,
 as_of_date TIMESTAMP,
 last_day  NUMERIC,
 last_week  NUMERIC,
 last_month NUMERIC,
 last_quarter NUMERIC,
 last_year  NUMERIC
);

CREATE INDEX ON production.time_delta (as_of_date,entity_id);

CREATE TABLE production.review_audit (
  model_id    INT REFERENCES results.models (model_id),
  entity_id   BIGINT,
  rank_abs    INT,
  rank_pct    REAL,
  review_status TEXT,		-- this needs to be updated later for the specific types 
  as_of_date  TIMESTAMP,
  date_reviewed TIMESTAMP, 
  date_created TIMESTAMP DEFAULT now()
);

CREATE INDEX ON production.review_audit(date_reviewed, model_id);

