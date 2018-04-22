-- To run: sqlite3 database.db <this-file.sql

DROP TRIGGER IF EXISTS lvldata_feed;

CREATE TRIGGER lvldata_feed
  AFTER INSERT
  ON events
FOR EACH ROW
WHEN
  (NEW.type = "StartLevel" OR NEW.type = "FinishLevel")
  AND NEW.src = json_extract(NEW.payload, "$.workerId")
  AND NEW.src <> ""
BEGIN
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
  VALUES (
    NEW.src,
    json_extract(NEW.payload, "$.hitId"),
    NEW.experiment,
    json_extract(NEW.payload, "$.lvlset"),
    json_extract(NEW.payload, "$.lvlid"),
    NEW.time,
    NEW.type = "StartLevel",
    NEW.type = "FinishLevel" AND json_extract(NEW.payload, "$.verified"),
    json_extract(NEW.payload, "$.all_found")
  );
END;
