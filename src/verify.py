#!/usr/bin/env python2.7

from argparse import ArgumentParser
from collections import OrderedDict
from datetime import datetime
from sqlalchemy import and_, func
import csv
import json
import multiprocessing
import multiprocessing.pool
import os.path
import time

from db_util import allInvs, filterEvents, open_db
from levels import loadBoogieFile, loadBoogieLvlSet
from lib.boogie.ast import parseExprAst
from lib.boogie.z3_embed import AllIntTypeEnv, Unknown, expr_to_z3, tautology
from models import Event, VerifyData
from vc_check import tryAndVerifyLvl

class NoDaemonProcess(multiprocessing.Process):
  def _get_daemon(self):
    return False
  def _set_daemon(self, value):
    pass
  daemon = property(_get_daemon, _set_daemon)

# This is needed because daemon processes can't have children (like Z3)
class NoDaemonPool(multiprocessing.pool.Pool):
  Process = NoDaemonProcess

def verify(lvl, invs, timeout=None, overfittedSet=None, nonindSet=None,
  soundSet=None):
  (overfitted, _), (nonind, _), sound, violations = tryAndVerifyLvl(lvl, invs,
    set(), timeout)

  print "OVERFITTED:", overfitted
  print "NONIND:", nonind
  print "SOUND:", sound
  print "VIOLATIONS:", violations
  print
  print "PROVED:", not violations
  print

  if overfittedSet is not None:
    overfittedSet.update(x[0] for x in overfitted)
  if nonindSet is not None:
    nonindSet.update(x[0] for x in nonind)
  if soundSet is not None:
    soundSet.update(sound)

  return not violations

def storeVerify(s, config, lvlset, lvlName, timeout, verifyTime, proved,
  payload):
  data = VerifyData(config=json.dumps(config), lvlset=lvlset, lvl=lvlName,
    timeout=timeout, time=verifyTime, provedflag=proved,
    payload=json.dumps(payload))
  s.add(data)
  s.commit()

def processLevel(args, lvl, lvls=None, lvlName=None, additionalInvs=[],
  storeArgs=None, worker=None, assignment=None):
  workers = args.workers if worker is None else [worker]
  assignments = None if assignment is None else [assignment]

  sessionF = open_db(args.db)
  s = sessionF()

  actualEnames = set()
  actualLvls = set()
  actualLvlsets = set()
  actualWorkers = set()
  actualAssignments = set()
  dbInvs = allInvs(s, enames=args.enames, lvls=lvls, lvlsets=args.lvlsets,
    workers=workers, assignments=assignments, enameSet=actualEnames,
    lvlSet=actualLvls, lvlsetSet=actualLvlsets, workerSet=actualWorkers,
    assignmentSet=actualAssignments)

  invs = set(parseExprAst(inv[1]) for inv in dbInvs)
  invs.update(additionalInvs)

  if lvlName is not None:
    print "_" * 40
    print "RESULTS FOR LEVEL", lvlName
    print
  print "ENAMES:", ", ".join(actualEnames)
  print "LVLS:", ", ".join(actualLvls)
  print "LVLSETS:", ", ".join(actualLvlsets)
  if len(actualWorkers) < 6:
    print "WORKERS:", ", ".join(actualWorkers)
  else:
    print "UNIQUE WORKERS:", len(actualWorkers)
  if len(actualAssignments) < 3:
    print "ASSIGNMENTS:", ", ".join(actualAssignments)
  else:
    print "UNIQUE ASSIGNMENTS:", len(actualAssignments)
  if len(additionalInvs) < 6:
    print "ADDITIONAL INVARIANTS:", ", ".join(str(x) for x in additionalInvs)
  else:
    print "ADDITIONAL INVARIANTS:", len(additionalInvs)
  if len(invs) < 6:
    print "UNIQUE INVARIANTS:", ", ".join(map(str, invs))
  else:
    print "UNIQUE INVARIANTS:", len(invs)
  print

  payload = {
    "enames": list(actualEnames),
    "lvls": list(actualLvls),
    "lvlsets": list(actualLvlsets),
    "workers": list(actualWorkers),
    "assignments": list(actualAssignments)
    }

  overfittedSet = set()
  nonindSet = set()
  soundSet = set()
  proved = verify(lvl, invs, timeout=args.timeout,
    overfittedSet=overfittedSet, nonindSet=nonindSet, soundSet=soundSet)
  payload["overfitted"] = list(str(s) for s in overfittedSet)
  payload["nonind"] = list(str(s) for s in nonindSet)
  payload["sound"] = list(str(s) for s in soundSet)

  if storeArgs is not None:
    config, lvlset, now = storeArgs
    storeVerify(s, config, lvlset, lvlName, args.timeout, now, proved,
      payload)

if __name__ == "__main__":
  p = ArgumentParser(description="Verify a level using selected invariants")
  p.add_argument("--additionalInvs",
    help="A .csv file with additional invariants")
  p.add_argument("--auto", action="store_true",
    help="Automatically run with new invariants as they arrive")
  p.add_argument("--bpl",
    help="A desugared .bpl file for the level to verify")
  p.add_argument("--db", required=True,
    help="The event database to use")
  p.add_argument("--enames", nargs="*",
    help="Include experiment invs; may specify multiple items (unset = any)")
  p.add_argument("--lvlName",
    help="A level name for a .bpl file or a level to select from a levelset")
  p.add_argument("--lvls", nargs="*",
    help="Include level invs; may specify multiple items (unset = any)")
  p.add_argument("--lvlset",
    help="A levelset file to load levels from")
  p.add_argument("--lvlsets", nargs="*",
    help="Include lvlset invs; may specify multiple items (unset = any)")
  p.add_argument("--modes", nargs="*", choices=["combined", "individual",
      "individual-play"],
    help="How to combine invariants for verification")
  p.add_argument("--parallel", action="store_true",
    help="Run multiple verification tasks in parallel")
  p.add_argument("--processes", type=int,
    help="Override the default number of processes for parallel execution")
  p.add_argument("--read", action="store_true",
    help="Read verification results from the database (and skip verified)")
  p.add_argument("--tag",
    help="A tag to differentiate results in the database")
  p.add_argument("--timeout", type=int, default=30,
    help="The maximum time (in seconds) to wait for Z3 queries")
  p.add_argument("--workers", nargs="*",
    help="Include worker invs; may specify multiple items (unset = any)")
  p.add_argument("--write", action="store_true",
    help="Write verification results to the database")

  args = p.parse_args()

  # Treat empty list as None for filter arguments
  if not args.enames:
    args.enames = None
  if not args.lvls:
    args.lvls = None
  if not args.lvlsets:
    args.lvlsets = None
  if not args.workers:
    args.workers = None

  if not args.modes:
    args.modes = ["combined"]

  sessionF = open_db(args.db)
  s = sessionF()

  if args.bpl:
    if args.auto or args.read or args.write:
      print "--auto, --modes, --read, --write are not supported with --bpl"
      exit(1)
    try:
      lvl = loadBoogieFile(args.bpl, False)
    except Exception as e:
      print "Couldn't load boogie file--is it desugared?"
      raise e
  elif args.lvlset:
    if args.auto and not args.read:
      print "--read must be specified with --auto"
      exit(1)
    lvlset, lvls = loadBoogieLvlSet(args.lvlset)
  else:
    print "Either --bpl or --lvlset must be specified"
    exit(1)

  additionalInvs = {}
  if args.additionalInvs:
    with open(args.additionalInvs) as f:
      r = csv.reader(f, delimiter=",")
      for row in r:
        if not row:
          continue
        invs = []
        for invstr in invlist.split(";"):
          if not len(invstr.strip()):
            continue
          try:
            inv = parseExprAst(invstr)
            if tautology(expr_to_z3(inv, AllIntTypeEnv())):
              print "Dropping additional invariant (tautology): ", inv
              continue
          except RuntimeError:
            # Some invariants are too large to parse
            print "Dropping additional invariant (parse): ", inv
            continue
          except Unknown:
            # Timeouts could be valid invariants
            pass
          invs.append(inv)
        additionalInvs[lvlName] = invs

  print "ADDITIONAL INVARIANTS LOADED FOR LVLS:", \
    ", ".join(additionalInvs.keys())
  print

  if args.bpl:
    # If a BPL file is specified we just look up invariants and try to prove
    # the level.  This is mostly for one-off testing.
    lvls = [args.lvlName] if args.lvls is None else args.lvls
    processLevel(args, lvl, lvls, args.lvlName,
      additionalInvs.get(args.lvlName, []))

  elif args.lvlset:
    # If a levelset is specified we try to prove each level.  Results can be
    # written to the database for further analysis.

    # For efficiency
    if args.lvls:
      args.lvls = set(args.lvls)

    while True:
      pool = None
      asyncres = []
      if args.parallel:
        pool = NoDaemonPool(processes=args.processes)

      now = datetime.now()

      for lvlName, lvl in lvls.items():
        # Allow processing of only some levels in a levelset
        if args.lvls:
          if lvlName not in args.lvls:
            continue

        additionalLvlInvs = additionalInvs.get(lvlName, [])

        for mode in args.modes:
          # This is stored to record the configuration in case runs need to be
          # repeated and to differentiate results from different runs.
          config = OrderedDict()
          if args.tag:
            config["tag"] = args.tag
          config["mode"] = mode
          config["enames"] = sorted(args.enames) if args.enames \
            is not None else None
          config["lvlsets"] = sorted(args.lvlsets) if args.lvlsets \
            is not None else None
          # lvls is not needed because we iterate over them individually

          if additionalInvs:
            config["additionalInvs"] = os.path.basename(args.additionalInvs)

          storeArgs = None
          if args.write:
            storeArgs = (config, lvlset, now)

          if mode == "combined":
            # Combined mode combines invariants from different workers
            config["workers"] = sorted(args.workers) if args.workers \
              is not None else None

            proved = False
            verifyTime = datetime.fromtimestamp(0)

            if args.read:
              q = s.query(
                  VerifyData.provedflag,
                  VerifyData.time
                ) \
                .filter(VerifyData.config == json.dumps(config)) \
                .filter(VerifyData.lvlset == lvlset) \
                .filter(VerifyData.lvl == lvlName) \
                .filter(VerifyData.timeout >= args.timeout) \
                .order_by(VerifyData.time.desc())

              res = q.first()
              if res:
                proved, verifyTime = res

            if proved:
              print "Skipping", lvlName, "(already proved)"
              continue

            q = s.query(Event.id).filter(Event.type == "FoundInvariant")
            q = filterEvents(q,
                enames=args.enames, lvls=[lvlName], lvlsets=args.lvlsets,
                workers=args.workers
              ) \
              .filter(Event.time.between(verifyTime, now))

            res = q.all()
            newInvs = len(res)

            print "Combined mode:",
            if newInvs:
              print newInvs, "new invariants for", lvlName, "since last run"
            else:
              print "Skipping", lvlName, "(no new invariants)"
              continue

            if pool is None:
              processLevel(args, lvl, [lvlName], lvlName, additionalLvlInvs,
                storeArgs=storeArgs)
            else:
              asyncres.append(pool.apply_async(processLevel, (args, lvl,
                [lvlName], lvlName, additionalLvlInvs),
                dict(storeArgs=storeArgs)))

          elif mode == "individual":
            # Individual mode uses each worker's invariants individually

            vq = s.query(
              VerifyData.provedflag,
              VerifyData.time,
              VerifyData.payload
              )
            if args.read:
              vq = vq \
                .filter(VerifyData.config == json.dumps(config)) \
                .filter(VerifyData.lvlset == lvlset) \
                .filter(VerifyData.lvl == lvlName) \
                .filter(VerifyData.timeout >= args.timeout)
            else:
              vq = vq.filter(False)

            vq = vq.subquery()
            q = s.query(
                Event.src,
                func.max(vq.c.provedflag),
                func.max(vq.c.time)
              ) \
              .filter(Event.type == "FoundInvariant") \
              .outerjoin(vq, Event.src ==
                func.json_extract(vq.c.payload, "$.workers[0]")) \
              .group_by(Event.src)
            q = filterEvents(q,
                enames=args.enames, lvls=[lvlName], lvlsets=args.lvlsets,
                workers=args.workers
              )

            for worker, proved, verifyTime in q.all():
              if proved is None:
                proved = False
              if verifyTime is None:
                verifyTime = datetime.fromtimestamp(0)

              if proved:
                print "Skipping worker", worker, "on", lvlName, \
                  "(already proved)"
                continue

              q = s.query(Event.id).filter(Event.type == "FoundInvariant")
              q = filterEvents(q,
                  enames=args.enames, lvls=[lvlName], lvlsets=args.lvlsets,
                  workers=[worker]
                ) \
                .filter(Event.time.between(verifyTime, now))

              res = q.all()
              newInvs = len(res)

              print "Individual mode:",
              if newInvs:
                print newInvs, "new invariants for worker", worker, "on", \
                  lvlName, "since last run"
              else:
                print "Skipping worker", worker, "on", lvlName, \
                  "(no new invariants)"
                continue

              if pool is None:
                processLevel(args, lvl, [lvlName], lvlName, additionalLvlInvs,
                  storeArgs=storeArgs, worker=worker)
              else:
                asyncres.append(pool.apply_async(processLevel, (args, lvl,
                  [lvlName], lvlName, additionalLvlInvs),
                  dict(storeArgs=storeArgs, worker=worker)))

          elif mode == "individual-play":
            # Individual-play mode uses each worker's invariants individually
            # without combining invariants from different playthroughs.

            vq = s.query(
              VerifyData.provedflag,
              VerifyData.time,
              VerifyData.payload
              )
            if args.read:
              vq = vq \
                .filter(VerifyData.config == json.dumps(config)) \
                .filter(VerifyData.lvlset == lvlset) \
                .filter(VerifyData.lvl == lvlName) \
                .filter(VerifyData.timeout >= args.timeout)
            else:
              vq = vq.filter(False)

            vq = vq.subquery()
            q = s.query(
                Event.src,
                func.json_extract(Event.payload, "$.assignmentId"),
                func.max(vq.c.provedflag),
                func.max(vq.c.time)
              ) \
              .filter(Event.type == "FoundInvariant") \
              .outerjoin(vq, and_(
                Event.src == func.json_extract(vq.c.payload, "$.workers[0]"),
                func.json_extract(Event.payload, "$.assignmentId") ==
                  func.json_extract(vq.c.payload, "$.assignments[0]"))) \
              .group_by(Event.src,
                func.json_extract(Event.payload, "$.assignmentId"))
            q = filterEvents(q,
                enames=args.enames, lvls=[lvlName], lvlsets=args.lvlsets,
                workers=args.workers
              )

            for worker, assignment, proved, verifyTime in q.all():
              if proved is None:
                proved = False
              if verifyTime is None:
                verifyTime = datetime.fromtimestamp(0)

              if proved:
                print "Skipping worker", worker, "assignment ", \
                  assignment, "on", lvlName, "(already proved)"
                continue

              q = s.query(Event.id).filter(Event.type == "FoundInvariant")
              q = filterEvents(q,
                  enames=args.enames, lvls=[lvlName], lvlsets=args.lvlsets,
                  workers=[worker], assignments=[assignment]
                ) \
                .filter(Event.time.between(verifyTime, now))

              res = q.all()
              newInvs = len(res)

              print "Individual-play mode:",
              if newInvs:
                print newInvs, "new invariants for worker", worker, \
                  "assignment", assignment, "on", lvlName, "since last run"
              else:
                print "Skipping worker", worker, "assignment", assignment, \
                  "on", lvlName, "(no new invariants)"
                continue

              if pool is None:
                processLevel(args, lvl, [lvlName], lvlName, additionalLvlInvs,
                  storeArgs=storeArgs, worker=worker, assignment=assignment)
              else:
                asyncres.append(pool.apply_async(processLevel, (args, lvl,
                  [lvlName], lvlName, additionalLvlInvs),
                  dict(storeArgs=storeArgs, worker=worker,
                    assignment=assignment)))

          else:
            print "UNSUPPORTED MODE:", args.mode
            exit(1)

      if pool is not None:
        pool.close()
        while asyncres:
          print len(asyncres), "workers remaining"
          asyncres = filter(lambda res: not res.ready(), asyncres)
          time.sleep(10)
        pool.terminate()
        pool.join()

      if not args.auto:
        break

      print "Finished pass; waiting 30 seconds"
      time.sleep(30)
