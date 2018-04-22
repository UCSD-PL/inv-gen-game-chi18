#!/usr/bin/env python
import argparse
import levels
import lib.boogie.ast as bast
from lib.boogie.analysis import propagate_sp
from lib.common.util import error
from vc_check import tryAndVerifyLvl
from re import compile as reComp
from models import open_sqlite_db, Event
from datetime import datetime, timedelta

p = argparse.ArgumentParser(description=\
        "given an experiment ran over a split levelset see if " +\
        "the combined found invariants for each split solve the original level")
p.add_argument("--lvlset", type=str, help="lvlset to check", required=True)
p.add_argument("--ename", type=str, help="experiment name", required=True)
p.add_argument("--timeout", type=int, help="timeout on z3 queries")

args = p.parse_args()
lvlsetName, lvls = levels.loadBoogieLvlSet(args.lvlset)
s = open_sqlite_db("../logs/" + args.ename + "/events.db")()

endsWithNumP = reComp(".*\.[0-9]*$")
justEnd = reComp("\.[0-9]*$")

originalToSplitM = { }
splitToOriginal = { }

lvlStats = { lvlN: {
      "usersStarted": set(),\
      "nusersStarted": 0,\
      "usersFinished": set(),\
      "nusersFinished": 0,\
      "invs": set(),\
      "ninvs": 0,\
      "invariantsTried": set(),\
      "nInvariantsTried": 0,\
      "invariantsFound": set(),\
      "nInvariantsFound": 0,\
      "skipped": 0,\
      "totalTime": timedelta(),\
    } for lvlN in lvls }

for e in s.query(Event).all():
  typ, src, ename, time, p = e.type, e.src, e.experiment, e.time, e.payl()

  if ('lvlset' in p and p['lvlset'] != lvlsetName):
    error("Logs refer to levelset " + p['lvlset'] + " which is not loaded.")

  if ('lvlid' in p and p['lvlid'] not in lvls):
    error("Logs refer to level " + p['lvlid'] + \
          " which is not found in current lvlset.")

  if ('lvlid' in p):
    lvl = lvls[p['lvlid']]
    lvlS = lvlStats[p['lvlid']]
  else:
    lvl = None
    lvlS = None

  if (typ == "FoundInvariant"):
    lvlS["invariantsFound"].add((p['raw'], p['canonical']))


for lvl_name, lvl in lvls.items():
  if "splitterPreds" in lvl and not endsWithNumP.match(lvl_name):
    print "Print split traces level has name not ending in number: ", lvl_name

  if (endsWithNumP.match(lvl_name) and not "splitterPreds" in lvl):
    print "Print split lvl ", lvl_name, "is missing splitterPreds"

  if (endsWithNumP.match(lvl_name) and not "partialInv" in lvl):
    print "Print split lvl ", lvl_name, "is missing partialInv"

  if (endsWithNumP.match(lvl_name)):
    origName = justEnd.split(lvl_name)[0]
    originalToSplitM[origName] = \
            originalToSplitM.get(origName, []) + [ lvl_name ]
    splitToOriginal[lvl_name] = origName


print "Level, #Splits, Solved, #FoundInvariants, #Added Implications, " +\
      "#Added SPs, #Sound, #Overfit, #Nonind"
for origName in originalToSplitM:
  found = reduce(lambda x,y:  x.union(y),
    [lvlStats[z]["invariantsFound"] for z in originalToSplitM[origName]], set())
  implied = [ set([ bast.AstBinExpr(precc, "==>", bast.parseExprAst(inv[1]))
                    for inv in lvlStats[z]["invariantsFound"] \
                        for precc in lvls[z]["splitterPreds"] ])
              for z in originalToSplitM[origName] ]
  implied = reduce(lambda x,y:  x.union(y), implied, set())
  found = set([bast.parseExprAst(x[1]) for x in found])
  nraw = len(found)
  nimplied = len(implied)
  lvl = lvls[originalToSplitM[origName][0]]
  bbs = lvl["program"]
  loop = lvl["loop"]
  loop_header = loop.loop_paths[0][0]
  sps = propagate_sp(bbs)[loop_header]
  nsps = len(sps)
  invs = found.union(sps).union(implied)

  (overfitted, dummy1), (nonind, dummy2), sound, violations =\
      tryAndVerifyLvl(lvl, invs, set(), args.timeout, \
        useSplitters=False, addSPs=False, generalizeUserInvs=False)

  assert (len(dummy2) == 0 and len(dummy1) == 0);

  solved = len(violations) == 0
  print ",".join(map(str, [
    origName,\
    len(originalToSplitM[origName]),\
    solved,\
    nraw,\
    nimplied,\
    nsps,\
    len(sound),\
    len(overfitted),\
    len(nonind)\
  ]))
