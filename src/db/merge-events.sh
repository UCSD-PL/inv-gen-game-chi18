#!/usr/bin/env bash
# Merge one sqlite event database into another
sqlite3 "$1" <<EOF
ATTACH '$2' AS srcdb;
BEGIN;
INSERT INTO main.sources
SELECT *
FROM srcdb.sources
WHERE
  name NOT IN main.sources;
INSERT INTO main.events
  (type, experiment, src, addr, time, payload)
SELECT
  type, experiment, src, addr, time, payload
FROM srcdb.events;
COMMIT;
DETACH srcdb;
EOF
