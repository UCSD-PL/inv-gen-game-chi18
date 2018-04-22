#! /usr/bin/env python
from datetime import timedelta
from models import open_sqlite_db, Event
from argparse import ArgumentParser
from levels import loadBoogieLvlSet
from lib.common.util import error, fatal
from lib.boogie.analysis import propagate_sp
from lib.boogie.ast import parseExprAst
from lib.boogie.z3_embed import Unknown, tautology, expr_to_z3, AllIntTypeEnv
from vc_check import tryAndVerifyLvl
import csv

p = ArgumentParser(description="Compute stats over an experiment");
p.add_argument('--ename', type=str, help='Name for experiment', required=True);
p.add_argument('--lvlStats', action="store_const", const=True, default=False,
               help='If set print lvl stats');
p.add_argument('--usrStats', action="store_const", const=True, default=False,
               help='If set print user stats');
p.add_argument('--lvlset', type=str,
               help='Path to levelset used in experiment', required=True);
p.add_argument('--timeout', type=int, default=10,
               help='Timeout in seconds for z3 queries.')
p.add_argument('--additionalInvs', type=str,
               help='Path to a .csv file with additional invariants.')

def isSrcUser(srcId):
    return srcId != 'verifier'

if __name__ == "__main__":
    args = p.parse_args();

    s = open_sqlite_db("../logs/" + args.ename + "/events.db")()
    lvlsetName, lvls = loadBoogieLvlSet(args.lvlset)

    otherInvs = { }
    if (args.additionalInvs):
      with open(args.additionalInvs) as f:
        r = csv.reader(f, delimiter=",");
        for row in r:
          (lvl, invs) = row
          bInvs = []
          for inv in [x for x in invs.split(";") if len(x.strip()) != 0]:
            try:
              bInv = parseExprAst(inv)
              if (tautology(expr_to_z3(bInv, AllIntTypeEnv()))):
                  continue
              bInvs.append(bInv)
            except RuntimeError:
              # Some invariants are just too large for parsing :(
              pass
            except Unknown:
              bInvs.append(bInv)

          otherInvs[lvl]=bInvs

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
    usrStats = { }
    startTimes = { }

    for e in s.query(Event).all():
      typ, src, ename, time, p = e.type, e.src, e.experiment, e.time, e.payl()

      if ('lvlset' in p and p['lvlset'] != lvlsetName):
        fatal("Logs refer to levelset " + p['lvlset'] + " which is not loaded.")

      if ('lvlid' not in p):
        lvlId = None
      else:
        lvlId = p['lvlid']
        while lvlId[-2:] == '.g':
          lvlId = lvlId[:-2]

      if (lvlId and lvlId not in lvls):
        fatal("Logs refer to level " + lvlId +\
              " which is not found in current lvlset.")

      if (lvlId):
        lvl = lvls[lvlId]
        lvlS = lvlStats[lvlId]
      else:
        lvl = None
        lvlS = None

      usrS = usrStats.get(src, {
        "gamesDone": 0,\
        "lvlsStarted": 0,\
        "levelsFinished": 0,\
        "tutorialStarted": 0, \
        "tutorialFinished": 0, \
        "invariantsTried": set(),\
        "nInvariantsTried": 0,\
        "invariantsFound": set(),\
        "nInvariantsFound": 0,\
        "totalNPowerups": 0,\
        "timesPowerupsActivated": 0,\
        "sumPowerupMultipliers": 0,\
        "skipped": 0,\
        "replayTutorial": 0,\
      })

      """
      # This assertion doesn't hold due to experiment merging
      if (ename != args.ename):
        fatal("Logs refer to experiment " + ename +
          " which is different from specified experiment " + args.ename)
      """

      if (typ == "StartLevel"):
        usrS["lvlsStarted"] += 1
        lvlS['nusersStarted'] += 1
        lvlS['usersStarted'].add(src);
        startTimes[src] = time
      elif (typ == "TutorialStart"):
        usrS["tutorialStarted"] += 1
      elif (typ == "TutorialDone"):
        usrS["tutorialFinished"] += 1
      elif (typ == "TriedInvariant"):
        usrS["nInvariantsTried"] += 1
        lvlS["nInvariantsTried"] += 1
        usrS["invariantsTried"].add((p['raw'], p['canonical']))
        lvlS["invariantsTried"].add((p['raw'], p['canonical']))
      elif (typ == "PowerupsActivated"):
        usrS['totalNPowerups'] += len(p['powerups'])
        usrS['timesPowerupsActivated'] += 1
        usrS['sumPowerupMultipliers'] += \
                reduce(lambda x,y: x*y, [z[1] for z in p['powerups']], 1)
      elif (typ == "FoundInvariant"):
        usrS["nInvariantsFound"] += 1
        lvlS["nInvariantsFound"] += 1
        usrS["invariantsFound"].add((p['raw'], p['canonical']))
        lvlS["invariantsFound"].add((p['raw'], p['canonical']))
      elif (typ == "VerifyAttempt"):
        pass
      elif (typ == "SkipToNextLevel"):
        usrS['skipped'] += 1
        lvlS['skipped'] += 1
      elif (typ == "FinishLevel"):
        usrS['levelsFinished'] += 1
        lvlS['nusersFinished'] += 1
        lvlS['usersFinished'].add(src);
        assert(src in startTimes)
        duration = e.time - startTimes[src]
        lvlS['totalTime'] += duration
      elif (typ == "GameDone"):
        usrS['gamesDone'] += 1
      elif (typ == "ReplayTutorialAll"):
        usrS['replayTutorial'] += 1
      else:
        fatal("Unknown type: " + typ)

    for lvlName in lvls:
      lvlS = lvlStats[lvlName]
      lvl = lvls[lvlName]
      invs = lvlS["invariantsTried"].union(lvlS["invariantsFound"])
      invM = { }
      for (raw,b) in invs:
        try:
          parsed = str(parseExprAst(b))
          invM[parsed]=raw
        except Exception, e:
          print "Failed parsing: ", raw,b

      userInvs = set();

      for x in invs:
        try:
          userInvs.add(parseExprAst(x[1]))
        except:
          print "Failed parsing: ", x[1]

      if (lvlName in otherInvs):
        oInvs = set(otherInvs[lvlName])
      else:
        oInvs = set([])

      ((overfitted, _), (nonind, _), sound, violations) =\
        tryAndVerifyLvl(lvl, userInvs, oInvs, args.timeout)

      lvlS["solved"] = (len(violations) == 0)
      lvlS["sound"] = [invM.get(str(x), str(x)) for x in sound];
      lvlS["overfitted"] = [invM.get(str(x[0]), str(x[0])) for x in overfitted]
      lvlS["nonind"] = [invM.get(str(x[0]),str(x[0])) for x in nonind]

    if (args.lvlStats):
      lvlStatColumns = ["Level", "Solved", "#Started", "Finished", \
                        "Total Time", "Ave Time/User", "#Invs Tried", \
                        "Ave #Invs Tried/Usr", "#Invs Found", "#Invs Found",\
                        "Ave #Invs Found/Usr", "#Sound", "Sound", \
                        "#Overfitted", "Overfitted", "#Nonind", "Nonind"]
      print ", ".join(lvlStatColumns)
      for (lvlName, lvlS) in lvlStats.items():
        print ", ".join([\
          lvlName,\
          str(lvlS["solved"]),\
          str(lvlS["nusersStarted"]),\
          str(lvlS["nusersFinished"]),\
          str(lvlS["totalTime"]),\
          str(lvlS["totalTime"] / lvlS["nusersFinished"]),\
          str(lvlS["nInvariantsTried"]),\
          str(lvlS["nInvariantsTried"]/(lvlS["nusersFinished"]*1.0)),\
          str(lvlS["nInvariantsFound"]),\
          str(lvlS["nInvariantsFound"]/(lvlS["nusersFinished"]*1.0)),\
          str(len(lvlS["sound"])),\
          ";".join(lvlS["sound"]),\
          str(len(lvlS["overfitted"])),\
          ";".join(lvlS["overfitted"]),\
          str(len(lvlS["nonind"])),\
          ";".join(lvlS["nonind"])]);

    if (args.userStats):
        raise Exception("NYI!");
