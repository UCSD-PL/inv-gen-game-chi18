-- To run: sqlite3 database.db <this-file.sql

-- The lvldata table should be empty before running this since there are
-- currently no constraints to prevent duplicate rows.  Dropping the table
-- and restarting the server will recreate an empty table.

-- This statement should always match the lvldata_feed trigger.
BEGIN;
INSERT INTO lvldata (
  worker,
  hit,
  experiment,
  lvlset,
  lvl,
  time,
  startflag,
  provedflag,
  allinvs
)
SELECT
  src,
  json_extract(payload, "$.hitId"),
  experiment,
  json_extract(payload, "$.lvlset"),
  json_extract(payload, "$.lvlid"),
  time,
  type = "StartLevel",
  type = "FinishLevel" AND json_extract(payload, "$.verified"),
  json_extract(payload, "$.all_found")
FROM events
WHERE
  (type = "StartLevel" OR type = "FinishLevel")
  AND src = json_extract(payload, "$.workerId")
  AND src <> ""
;
COMMIT;
