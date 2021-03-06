#! /usr/bin/env python
import argparse
from levels import loadBoogieLvlSet
from vc_check import tryAndVerifyLvl
from lib.cpa_checker import runCPAChecker, convertCppFileForCPAChecker
from lib.boogie.z3_embed import to_smt2, z3_expr_to_boogie, Unknown
from lib.common.util import error
from shutil import move
#from signal import signal , SIGALRM,  alarm
from threading import Timer
from os.path import exists

def handler():
#def handler(signum):
#  assert (signum == SIGALRM)
  raise Exception("timeout")
#signal(SIGALRM, handler);

if (__name__ == "__main__"):
  p = argparse.ArgumentParser(description="run CPAChecker on a levelset")
  p.add_argument('--lvlset', type=str, \
          help='Path to lvlset file', required=True)
  p.add_argument('--csv-table', action="store_true", \
          default=True, help='Print results as a csv table')
  p.add_argument('--time-limit', type=int, default=300, \
          help='Time limit for CPAChecker')
  p.add_argument('--waitEnter', action="store_true", \
                 default=False, help='Wait for user to perss Enter before continuing (great for debug)')
  args = p.parse_args();
  if args.waitEnter:
    input("Press Enter to continue...")
  lvlSetName, lvls = loadBoogieLvlSet(args.lvlset)

  res = { }
  conf = { }

  for lvlName, lvl in lvls.iteritems():
    cppFile = lvl["path"][1]
    preprocessedFile = cppFile + ".cpachecker.preprocessed"
    error("Running ", lvlName)

    if (not exists(preprocessedFile)):
      convertCppFileForCPAChecker(cppFile, preprocessedFile);

    res[lvlName] = runCPAChecker(preprocessedFile, args.time_limit);

    move("output", "tmp_outputs/" + lvlName + "");

    solved, loopHeaderLbl, loopInvs, rawOutput = res[lvlName]
    conf_status = "N/A"

    if (solved):
      error("z3 invs: ", len(loopInvs), loopInvs)
      try:
        t = Timer(args.time_limit, handler)
        t.start()
        #alarm(args.time_limit)
        # On lvl d-14 for example the invariants explode exponentially due to
        # inlining of lets. So add timeout. Seems to be the only level with
        # this problem
        invs = map(z3_expr_to_boogie, loopInvs)
      except Exception,e:
        if (e.message == "timeout"):
          invs = None
          conf_status = "timeout"
        else:
          for i in loopInvs:
            error(to_smt2(i))
          raise
      finally:
        #alarm(0)
        t.cancel()
      if (invs != None):
        try:
          (overfitted, nonind, sound, violations) =\
            tryAndVerifyLvl(lvl, set(invs), set(), args.time_limit, addSPs=True)

          error ("Out of ", invs, "sound: ", sound)

          if (len(violations) > 0):
            error("Supposedly sound inv: ", invs)
            error("Level ", lvlName, "false claimed to be sound!")
            error("Raw output: ", rawOutput)
            conf_status = False
          else:
            conf_status = True
        except Exception, e:
            conf_status = "verification error: " + e.value
        conf[lvlName] = conf_status
    # if (args.csv_table):
    #   print lvlName, ",", res[lvlName][0], ",", conf_status
    # else:
    print "Level", lvlName, "solved: ", solved, "confirmed?: ", conf_status

if (args.csv_table):
  if (args.csv_table):
    print "Level,Solved,Confirmed"
  for lvlName in res:
    print lvlName, ",", res[lvlName][0], ",", conf[lvlName] if conf.has_key(lvlName) else "N/A"
