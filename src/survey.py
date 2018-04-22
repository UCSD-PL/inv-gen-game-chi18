#!/usr/bin/env python2.7

from argparse import ArgumentParser
from boto.mturk.connection import MTurkRequestError
from collections import OrderedDict
from datetime import datetime
from sqlalchemy import func
import json

from models import Event, SurveyData, open_sqlite_db, open_mysql_db
import mturk_util

def getSurveyData(session, mc, hit):
  """ Return survey information for the given HIT (with database caching)
  """
  data = session.query(SurveyData) \
    .filter(SurveyData.hit == hit) \
    .one_or_none()

  if not data:
    res = mc.get_assignments(hit)
    if len(res) > 0:
      assn = res[0]
      payload = OrderedDict()
      for ans in assn.answers[0]:
        payload[ans.qid] = ans.fields[0]

      submitTime = datetime.strptime(assn.SubmitTime, "%Y-%m-%dT%H:%M:%SZ")
      data = SurveyData(hit=hit, assignment=assn.AssignmentId,
        worker=assn.WorkerId, time=submitTime, payload=json.dumps(payload))

      session.add(data)
      session.commit()

  return data

if __name__ == "__main__":
  p = ArgumentParser(description="Pull survey data")
  p.add_argument("--credentials_file", default="credentials.csv",
    help="The path to a CSV file containing AWS credentials")
  p.add_argument("--db", required=True,
    help="The event/survey database to use")
  p.add_argument("--sandbox", action="store_true",
    help="Whether to use the production or sandbox MTurk endpoint")

  args = p.parse_args()

  if "mysql+mysqldb://" in args.db:
    sessionF = open_mysql_db(args.db)
  else:
    sessionF = open_sqlite_db(args.db)
  session = sessionF()

  mc = mturk_util.connect(args.credentials_file, args.sandbox)

  hitq = session.query(
      func.json_extract(Event.payload, "$.hitId").label("hit")
    ).subquery()
  q = session.query(hitq.c.hit) \
    .filter(hitq.c.hit.notin_(session.query(SurveyData.hit)))
  for hit, in q.distinct():
    print "Loading new HIT %s..." % hit,

    try:
      getSurveyData(session, mc, hit)
    except MTurkRequestError:
      print "error"
    else:
      print "done"
