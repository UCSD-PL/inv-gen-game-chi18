#!/usr/bin/env python
import json
import sys
import time
from atexit import register
from datetime import datetime, timedelta
from os.path import abspath, dirname, isfile, realpath

from flask import Flask
from flask_jsonrpc import JSONRPC as rpc
from sqlalchemy import case, func

import mturk_util
from experiments import Experiment
from levels import loadBoogieLvlSet
from lib.common.util import pp_exc, randomToken
from models import open_sqlite_db, open_mysql_db, Event, LvlData
from publish_hits import publish_hit
from server_common import openLog, log_d
from survey import getSurveyData

class Server(Flask):
  def get_send_file_max_age(self, name):
    if name in [
      "jquery-1.12.0.min.js",
      "jquery-migrate-1.2.1.min.js",
      "jquery.jsonrpcclient.js"
      ]:
      return 100000
    return 0

app = Server(__name__, static_folder="static/", static_url_path="")
api = rpc(app, "/api")

def isHitActive(hit):
  return hit.HITStatus in ("Assignable", "Unassignable")

def isHitPerHour(hit):
  creationTime = datetime.strptime(hit.CreationTime, "%Y-%m-%dT%H:%M:%SZ")
  return datetime.now() - creationTime <= timedelta(hours=1)

class ConfiguredExperiment:
  def __init__(self, expconf):
    self.name = expconf["ename"]
    self.args = expconf["args"]
    self.min_finished_per_lvl = expconf["minFinishedPerLvl"]
    self.lvls = expconf.get("lvls", None)

    self.exp = None
    self.load()

  def load(self):
    self.total_hits = 0
    self.active_hits = 0

    lvlset = self.args["lvlset"]
    _, lvls = loadBoogieLvlSet(lvlset)

    if self.lvls is None:
      self.lvls = lvls.keys()

    try:
      self.exp = Experiment(self.name)
    except IOError:
      print "Error loading experiment %s" % self.name
      # Ignore missing experiments
      return

    self.total_hits = len(self.exp.server_runs)
    self.active_hits = sum(sr.hit_id in hits and isHitActive(hits[sr.hit_id])
      for sr in self.exp.server_runs)

  def getName(self):
    return self.name

  def getArgs(self):
    return self.args

  def isSandbox(self):
    try:
      return self.args["sandbox"]
    except KeyError:
      return False

  def getTotalHits(self):
    return self.total_hits

  def getActiveHits(self):
    return self.active_hits

  def getRequiredFinishedPerLvl(self):
    return self.min_finished_per_lvl

  def getMinFinishedPerLvl(self):
    s = sessionF()

    rows = []
    for lvl in self.lvls:
      rows.extend(s.query(
          LvlData.lvl,
          func.count(case({0: 1}, value=LvlData.startflag))
        )
        .filter(
          LvlData.experiment == self.name
        )
        .filter(
          LvlData.lvl == lvl
        )
        .all())

    # We can probably compute this directly with the query
    return min(r[1] for r in rows) if rows else 0

  def getNeededHits(self):
    n = self.getRequiredFinishedPerLvl() - self.getMinFinishedPerLvl()
    return n if n > 0 else 0

class ExperimentsConfig:
  def __init__(self, path):
    self.path = path
    self.expconfs = None
    self.load()

  def load(self):
    with open(self.path) as expfile:
      jsonconf = json.load(expfile)

    self.load_time = time.time()
    self.max_active_hits = jsonconf["maxActiveHits"]
    self.max_hits_per_hour = jsonconf["maxHitsPerHour"]
    self.expconfs = map(ConfiguredExperiment, jsonconf["experiments"])

  def getLoadTime(self):
    return self.load_time

  def getMaxActiveHits(self):
    return self.max_active_hits

  def getMaxHitsPerHour(self):
    return self.max_hits_per_hour

  def getConfiguredExperiments(self):
    return self.expconfs

class PublishTask:
  def __init__(self, num_hits, exp):
    self.num_hits = num_hits
    self.exp = exp

  def __str__(self):
    return "Publish %d HIT%s of %s with args: %s" % (self.num_hits,
      "s" * (self.num_hits != 1), self.exp.getName(), self.formatArgs())

  def formatArgs(self):
    return ", ".join("%s=%s" % kv for kv in self.exp.getArgs().items())

  def execute(self, feedback):
    # Populate default arguments, then override with experiment arguments.
    # These default arguments must match the ones in publish_hits.
    kwargs = dict(adminToken=adminToken, db=args.db, mode="patterns",
      no_ifs=False, individual=False, with_new_var_powerup=False, mc=mc,
      email=args.email)
    eargs = self.exp.getArgs().copy()
    eargs.pop("sandbox", None) # Passed below
    eargs.pop("email", None) # Not overridden
    kwargs.update(eargs)

    publish_hit(None, args.sandbox, self.exp.getName(), self.num_hits,
      **kwargs)

    feedback.append("Published %d HITs for experiment %s" % (self.num_hits,
      self.exp.getName()))

balance = None
hits = None
expconf = None
def loadExperiments():
  global auto_feedback, balance, expconf, hits

  balance = mc.get_account_balance()[0]

  hits = {}
  hour_hits = 0
  for hit in mc.get_all_hits():
    hits[hit.HITId] = hit
    if isHitPerHour(hit):
      hour_hits += 1

  if expconf is None:
    expconf = ExperimentsConfig(args.experiments)
  else:
    expconf.load()

  exps = expconf.getConfiguredExperiments()
  total_active_hits = sum(e.getActiveHits() for e in exps)
  total_allowed_new_hits = min(expconf.getMaxActiveHits() - total_active_hits,
    expconf.getMaxHitsPerHour() - hour_hits)

  auto_feedback = []
  for e in exps:
    need_new_hits = e.getNeededHits() - e.getActiveHits()
    allowed_new_hits = min([need_new_hits, total_allowed_new_hits])
    if allowed_new_hits > 0:
      expsandbox = e.isSandbox()
      if expsandbox == args.sandbox:
        total_allowed_new_hits -= allowed_new_hits
        if allowed_new_hits > 0:
          auto_feedback.append(PublishTask(allowed_new_hits, e))
      else:
        auto_feedback.append("No action on experiment %s (%ssandbox)"
          % (e.name, "" if expsandbox else "not "))

  if not auto_feedback:
    auto_feedback.append("No action required")
  else:
    auto_feedback.append("Active HITs will become: %d" %
      (expconf.getMaxActiveHits() - total_allowed_new_hits))

@api.method("App.getDashboard")
@pp_exc
@log_d()
def getDashboard(inputToken):
  """ Return data for the dashboard view; only used by the dashboard.
  """
  if inputToken != adminToken:
    raise Exception(str(inputToken) + " not a valid token.")

  s = sessionF()
  rows = s.query(
      LvlData.experiment,
      LvlData.lvl,
      # count includes all non-null values, so we need case to exclude values
      # that do not match (the default case returns null)
      func.count(case({1: 1}, value=LvlData.startflag)),
      func.count(case({0: 1}, value=LvlData.startflag)),
      func.count(case({1: 1}, value=LvlData.provedflag))
    ) \
    .group_by(LvlData.experiment, LvlData.lvl)

  lvlstats = [ dict(zip([
      "experiment",
      "lvl",
      "nStarted",
      "nFinished",
      "nProved"
    ], r)) for r in rows ]
  lvlstats.sort(key=lambda x: (x["experiment"], x["lvl"]))

  expstats = [ {
    "name": e.name,
    "nTotalHits": e.getTotalHits(),
    "nActiveHits": e.getActiveHits(),
    "nNeededHits": e.getNeededHits(),
    "nRequiredFinishedPerLvl": e.getRequiredFinishedPerLvl(),
    "nMinFinishedPerLvl": e.getMinFinishedPerLvl()
    } for e in expconf.getConfiguredExperiments() ]

  return {
    "balance": str(balance),
    "experimentsFile": expconf.path,
    "nMaxActiveHits": expconf.getMaxActiveHits(),
    "nTotalActiveHits": sum(isHitActive(h) for h in hits.values()),
    "nMaxHitsPerHour": expconf.getMaxHitsPerHour(),
    "nTotalHitsPerHour": sum(isHitPerHour(h) for h in hits.values()),
    "lastHitCheck": time.time() - expconf.getLoadTime(),
    "autoFeedback": map(str, auto_feedback),
    "expstats": expstats,
    "lvlstats": lvlstats
    }

@api.method("App.getDashboardInvs")
@pp_exc
@log_d()
def getDashboardInvs(inputToken, experiment, lvl):
  """ Return invariants for the dashboard view; only used by the dashboard.
  """
  if inputToken != adminToken:
    raise Exception(str(inputToken) + " not a valid token.")

  s = sessionF()
  rows = s.query(
      LvlData.hit,
      LvlData.allinvs,
      LvlData.provedflag,
      LvlData.time
    ) \
    .filter(
      LvlData.experiment == experiment,
      LvlData.lvl == lvl,
      LvlData.startflag == 0
    )

  d = dict()
  for hit, allinvs, proved, timestamp in rows:
    d[hit] = {
      "invs": [i[0] for i in json.loads(allinvs)],
      "proved": True if proved else False,
      "timestamp": str(timestamp)
      }

  return d

@api.method("App.getSurvey")
@pp_exc
@log_d()
def getSurvey(inputToken, hit):
  """ Return survey responses for the given HIT; only used by the dashboard.
  """
  if inputToken != adminToken:
    raise Exception(str(inputToken) + " not a valid token.")

  s = sessionF()
  data = getSurveyData(s, mc, hit)

  if data is None:
    return { "complete": False }

  return {
    "complete": True,
    "worker": data.worker,
    "assignment": data.assignment,
    "submitTimestamp": str(data.time),
    "survey": json.loads(data.payload)
    }

@api.method("App.refreshExperiments")
@pp_exc
@log_d()
def refreshExperiments(inputToken):
  """ Reload experiments and update HIT information from Mechanical Turk; only
      used by the dashboard.
  """
  if inputToken != adminToken:
    raise Exception(str(inputToken) + " not a valid token.")

  loadExperiments()

@api.method("App.runAutomation")
@pp_exc
@log_d()
def runAutomation(inputToken):
  """ Manually run automated tasks (publish HITs); only used by the dashboard.
  """
  if inputToken != adminToken:
    raise Exception(str(inputToken) + " not a valid token.")

  global auto_feedback

  new_feedback = []
  for item in auto_feedback:
    if isinstance(item, PublishTask):
      item.execute(new_feedback)

  if not new_feedback:
    new_feedback.append("No action taken")

  auto_feedback = new_feedback
  return new_feedback

if __name__ == "__main__":
  p = mturk_util.mkParser("experiment monitor server")
  p.add_argument("--local", action="store_true",
    help="Run without SSL for local testing")
  p.add_argument("--port", type=int,
    help="An optional port number")
  p.add_argument("--db", type=str, required=True,
    help="Path to database")
  p.add_argument("--adminToken", type=str,
    help="Secret token for admin interface; randomly generated if omitted")
  p.add_argument("--experiments", type=str,
    help="Path to experiment configuration file")
  p.add_argument("--email", type=str,
    help="E-mail address to notify for problem reports")

  args = p.parse_args()

  if "mysql+mysqldb://" in args.db:
    sessionF = open_mysql_db(args.db)
  else:
    sessionF = open_sqlite_db(args.db)

  if args.adminToken:
    adminToken = args.adminToken
  else:
    adminToken = randomToken(5)

  mc = mturk_util.connect(args.credentials_file, args.sandbox)
  loadExperiments()

  MYDIR = dirname(abspath(realpath(__file__)))
  ROOT_DIR = dirname(MYDIR)

  if args.local:
    host = "127.0.0.1"
    sslContext = None
  else:
    host = "0.0.0.0"
    sslContext = MYDIR + "/cert.pem", MYDIR + "/privkey.pem"

  print "Admin Token:", adminToken
  print "Dashboard URL:", "dashboard.html?adminToken=" + adminToken
  app.run(host=host, port=args.port, ssl_context=sslContext, threaded=True)
