#! /usr/bin/env python
from flask import Flask
from flask import request
from flask_jsonrpc import JSONRPC as rpc
from os.path import dirname, abspath, realpath, join, isfile
from js import esprimaToZ3, esprimaToBoogie, boogieToEsprima, \
        boogieToEsprimaExpr
from lib.boogie.ast import AstBinExpr, AstTrue, ast_and, AstId, AstNumber, \
        parseExprAst
from lib.common.util import pp_exc, powerset, split, nonempty, nodups, \
        randomToken
from lib.boogie.eval import instantiateAndEval, _to_dict
from lib.boogie.z3_embed import expr_to_z3, AllIntTypeEnv, z3_expr_to_boogie,\
        Unknown, simplify, implies, equivalent, tautology
from lib.boogie.analysis import propagate_sp
from vc_check import _from_dict, tryAndVerifyLvl, loopInvSafetyCtrex

from levels import _tryUnroll, findNegatingTrace, loadBoogieLvlSet

import argparse
import sys
from pp import pp_BoogieLvl, pp_EsprimaInv, pp_EsprimaInvs, pp_CheckInvsRes, \
        pp_tryAndVerifyRes, pp_mturkId, pp_EsprimaInvPairs
from copy import copy
from time import time
from datetime import datetime
from models import open_sqlite_db, open_mysql_db, Event
from db_util import addEvent, allInvs, levelSolved, levelFinishedBy,\
        levelSkipCount, levelsPlayedInSession
from mturk_util import send_notification
from atexit import register
from server_common import openLog, log, log_d

class Server(Flask):
    def get_send_file_max_age(self, name):
        if (name in [ 'jquery-1.12.0.min.js', \
                      'jquery-migrate-1.2.1.min.js', \
                      'jquery.jsonrpcclient.js']):
            return 100000

        return 0

app = Server(__name__, static_folder='static/', static_url_path='')
api = rpc(app, '/api')

## Utility functions #################################################
def getLastVerResult(lvlset, lvlid, session, workerId=None):
    events = session.query(Event)
    verifyAttempts = events.filter(Event.type == "VerifyAttempt").all();
    verifyAttempts = filter(
        lambda x: x.payl()["lvlset"] == lvlset and x.payl()["lvlid"] == lvlid
          and (workerId is None or x.payl()["workerId"] == workerId),
        verifyAttempts);
    if (len(verifyAttempts) > 0):
      return verifyAttempts[-1].payl();
    else:
      return None;

def divisionToMul(inv):
    if isinstance(inv, AstBinExpr) and \
       inv.op in ['==', '<', '>', '<=', '>=', '!==']:
        if (isinstance(inv.lhs, AstBinExpr) and inv.lhs.op == 'div' and\
                isinstance(inv.lhs.rhs, AstNumber)):
                    return AstBinExpr(inv.lhs.lhs, inv.op, \
                                      AstBinExpr(inv.rhs, '*', inv.lhs.rhs));

        if (isinstance(inv.rhs, AstBinExpr) and inv.rhs.op == 'div' and\
                isinstance(inv.rhs.rhs, AstNumber)):
                    return AstBinExpr(AstBinExpr(inv.lhs, "*", inv.rhs.rhs), \
                                      inv.op, inv.rhs.lhs);
    return inv

columnSwaps = {
  2: [[0, 1]],
  3: [[0, 1, 2],
      [0, 2, 1]],
  4: [[0, 1, 2, 3],
      [2, 0, 3, 1]],
  5: [[0, 1, 2, 3, 4],
      [1, 3, 0, 4, 2],
      [3, 1, 4, 2, 0]]
}

def swapColumns(row, nSwap):
  return [row[i] for i in columnSwaps[len(row)][nSwap]]

## API Entry Points ##################################################
@api.method("App.logEvent")
@pp_exc
@log_d(str,str,str,pp_mturkId, str)
def logEvent(workerId, name, data, mturkId):
    """ Log an event from either the frontend or backend. Event appears
        as JSON in both the textual log, as well as in the database """
    session = sessionF()
    addEvent(workerId, name, time(), args.ename, request.remote_addr, \
             data, session, mturkId);
    return None

@api.method("App.getTutorialDone")
@pp_exc
@log_d(str, str)
def getTutorialDone(workerId):
    """ Return whether a given user has done the tutorial. Called from
        mturk_landing.html """
    if workerId == "":
        return False
    return isfile(join(ROOT_DIR, 'logs', args.ename, "tut-done-" + workerId))

@api.method("App.setTutorialDone")
@pp_exc
@log_d(str)
def setTutorialDone(workerId):
    """ Specify that a given user has done the tutorial. Called form
        tutorial.html. TODO(Dimo): This should user the database instead
        of tut-done-ID marker files """
    if workerId != "":
        marker = join(ROOT_DIR, 'logs', args.ename, "tut-done-" + workerId)
        open(marker, "w").close()

@api.method("App.loadLvl")
@pp_exc
@log_d(str, str, pp_mturkId, bool, pp_BoogieLvl)
def loadLvl(levelSet, lvlId, mturkId, individualMode=False): #pylint: disable=unused-argument
    """ Load a given level. """
    if (levelSet not in traces):
        raise Exception("Unkonwn level set " + levelSet)

    if (lvlId not in traces[levelSet]):
        raise Exception("Unkonwn trace " + lvlId + " in levels " + levelSet)

    lvl = traces[levelSet][lvlId]
    if ('program' in lvl):
      # This is a boogie level - don't return the program/loop and other book
      # keeping
      lvl = {
             'lvlSet': levelSet,
             'id': lvlId,
             'variables': lvl['variables'],
             'data': lvl['data'],
             'exploration_state': lvl['exploration_state'],
             'hint': lvl['hint'],
             'goal' : lvl['goal'],
             'support_pos_ex' : lvl['support_pos_ex'],
             'support_neg_ex' : lvl['support_neg_ex'],
             'support_ind_ex' : lvl['support_ind_ex'],
             'multiround'     : lvl['multiround'],
      }

    if args.colSwap:
      nCols = len(lvl["variables"])
      if nCols not in columnSwaps:
        raise Exception("No column swap for %d columns" % nCols)

      nSwaps = (nCols + 1) // 2 # swaps are 0 to nSwaps - 1 inclusive

      session = sessionF()

      colSwaps = [0] * nSwaps
      allInvs(session, enames=[args.ename], lvlsets=[curLevelSetName],
        lvls=[lvlId], colSwaps=colSwaps)
      sortKeys = colSwaps
      if individualMode:
        workerId = mturkId[0]
        colSwaps = [0] * nSwaps
        allInvs(session, enames=[args.ename], lvlsets=[curLevelSetName],
          lvls=[lvlId], workers=[workerId], colSwaps=colSwaps)
        sortKeys = zip(colSwaps, sortKeys)

      nSwap = sorted(zip(sortKeys, range(nSwaps)), key=lambda x: x[0])[0][1]
      lvl["colSwap"] = nSwap

      lvl["variables"] = swapColumns(lvl["variables"], nSwap)
      lvl["data"] = [[swapColumns(row, nSwap) for row in rows]
        for rows in lvl["data"]]

    lvl["startingInvs"] = []
    if args.replay:
      # Only show players their own invariants, even if individual mode is off
      invs = allInvs(session, enames=[args.ename], lvlsets=[curLevelSetName],
        lvls=[lvlId], workers=[workerId])

      lvl["startingInvs"] = [(inv[0], boogieToEsprima(parseExprAst(inv[1])))
        for inv in invs]

    return lvl

@api.method("App.genNextLvl")
@pp_exc
@log_d(str, pp_mturkId, str, str, pp_EsprimaInvs, bool, pp_BoogieLvl)
def genNextLvl(workerId, mturkId, levelSet, levelId, invs, individualMode):
    """ Given a level (levelSet, levelId) and a set of invariants invs
        attempted by a user, generate and return a new level by appending the
        counterexamples to invs to the current level. The new level has the
        same id as levelId with ".g" appended at the end. This is a hack.
    """
    s = sessionF();
    if (levelSet not in traces):
        raise Exception("Unkonwn level set " + str(levelSet))

    if (levelId not in traces[levelSet]):
        raise Exception("Unkonwn trace " + str(levelId) + \
                        " in levels " + str(levelSet))

    if (len(invs) == 0):
        raise Exception("No invariants given")

    lvl = traces[levelSet][levelId]

    if ('program' not in lvl):
      # Not a boogie level - error
      raise Exception("Level " + str(levelId) + " " + \
                      str(levelSet) + " not a dynamic boogie level.")

    userInvs = set([ esprimaToBoogie(x, {}) for x in invs ])
    otherInvs = set([])
    lastSoundInvs = set([])
    lastNonindInvs = set([])
    lastVer = getLastVerResult(levelSet, levelId, s,
      workerId=(workerId if individualMode else None))

    if (lastVer):
      lastSoundInvs = set([parseExprAst(x) for x in lastVer["sound"]])
      lastNonindInvs = set([parseExprAst(x) for x in lastVer["nonind"]])


    otherInvs = lastSoundInvs.union(lastNonindInvs)
    ((overfitted, _), (_, _), sound, violations) =\
      tryAndVerifyLvl(lvl, userInvs, otherInvs, args.timeout)

    # See if the level is solved
    solved = len(violations) == 0;
    if (solved):
        payl = [levelSet, levelId, invs, [ boogieToEsprimaExpr(e) for e in sound ]]
        addEvent("verifier", "GenNext.Solved", time(), args.ename, \
                 "localhost", payl, s, mturkId)
        return loadNextLvl(workerId, mturkId, individualMode)

    fix = lambda env:   _from_dict(lvl['variables'], env, 0)
    greenRows = [ fix(v.endEnv()) for v in overfitted if type(v) != tuple]
    print "Invs: ", otherInvs.union(userInvs)
    print "GreenRows: ", greenRows
    bbs = lvl["program"]
    loop = lvl["loop"]
    ctrexInvs = lastSoundInvs.union(userInvs)
    safetyCtrex =\
        loopInvSafetyCtrex(loop, ctrexInvs, bbs, args.timeout)
    redRows = [ fix(x) for x in safetyCtrex if len(x) != 0 ]
    print "RedRows: ", redRows
    if (len(redRows) > 0 or len(greenRows) > 0):
        # Lets give them another level
        payl = [levelSet, levelId, invs, [ boogieToEsprimaExpr(e) for e in ctrexInvs ]]
        addEvent("verifier", "GenNext.NoNewRows", time(), args.ename, \
                 "localhost", payl, s, mturkId)
        newLvl = copy(lvl);
        newLvlId = levelId + ".g"
        newLvl["data"][0].extend(greenRows)
        newLvl["data"][2].extend(redRows)
        traces[levelSet][newLvlId] = newLvl;
        return loadLvl(levelSet, newLvlId, mturkId, individualMode)
    else:
        # Else give them the actual next level
        return loadNextLvl(workerId, mturkId, individualMode)

@api.method("App.loadNextLvl")
@pp_exc
@log_d(str, pp_mturkId, bool, pp_BoogieLvl)
def loadNextLvl(workerId, mturkId, individualMode):
    """ Return the unsolved level seen by the fewest users. """
    assignmentId = mturkId[2]
    session = sessionF();

    if args.maxlvls is not None:
      # It's inefficient to look through all the levels twice.  This can
      # probably be combined with the logic below with some effort.
      if levelsPlayedInSession(session, assignmentId) >= args.maxlvls:
        return

    level_names = traces[curLevelSetName].keys();
    sort_keys = [len(allInvs(session, enames=[args.ename],
      lvlsets=[curLevelSetName], lvls=[x])) for x in level_names]
    if individualMode:
      sort_keys = zip([len(allInvs(session, enames=[args.ename],
        lvlsets=[curLevelSetName], lvls=[x], workers=[workerId]))
        for x in level_names], sort_keys)
    sort_keys = zip([levelSkipCount(session, args.ename, curLevelSetName, x,
      workerId, assignmentId) for x in level_names], sort_keys)
    key_and_level = zip(sort_keys, level_names)
    # Stable sort on key only to preserve lvlset order
    key_and_level.sort(key=lambda x: x[0])

    for _, lvlId in key_and_level:
        if levelSolved(session, curLevelSetName, lvlId,
            workerId=(workerId if individualMode else None)) or \
           (not args.replay and workerId != "" and \
            levelFinishedBy(session, curLevelSetName, lvlId, workerId)):
            continue
        result = loadLvl(curLevelSetName, lvlId, mturkId, individualMode)
        return result

@api.method("App.instantiate")
@pp_exc
@log_d(pp_EsprimaInvs, str, str, pp_mturkId, pp_EsprimaInvs)
def instantiate(invs, traceVars, trace, mturkId): #pylint: disable=unused-argument
    """ 
        Given a set of invariant templates inv, a set of variables traceVars
        and concrete values for these variables trace, return a set of concrete
        instances of the invariant templates, that hold for the given traces. A
        concrete instatnce of a template is an invariant with the same shape, with 
        variables and constants substituted in the appropriate places.

        Not currently in use.
    """ 
    res = []
    z3Invs = []
    templates = [ (esprimaToBoogie(x[0], {}), x[1], x[2]) for x in invs]
    vals = map(lambda x:    _to_dict(traceVars, x), trace)

    for (bInv, symConsts, symVars) in templates:
        for instInv in instantiateAndEval(bInv, vals, symVars, symConsts):
            instZ3Inv = expr_to_z3(instInv, AllIntTypeEnv())
            implied = False
            z3Inv = None

            for z3Inv in z3Invs:
                if implies(z3Inv, instZ3Inv):
                    implied = True;
                    break

            if (implied):
                continue

            res.append(instInv)
            z3Invs.append(instZ3Inv)

    return map(boogieToEsprima, res)

@api.method("App.getPositiveExamples")
@pp_exc
@log_d()
def getPositiveExamples(levelSet, levelId, cur_expl_state, overfittedInvs, num):
    """ 
        Given a level (levelSet, levelId), and some overfitted invriants
        overfittedInvs, return a set of green rows that rebuke the overfitted
        invariants.

        Not currently in use.
    """ 
    if (levelSet not in traces):
        raise Exception("Unkonwn level set " + str(levelSet))

    if (levelId not in traces[levelSet]):
        raise Exception("Unkonwn trace " + str(levelId) + \
                        " in levels " + str(levelSet))

    lvl = traces[levelSet][levelId]

    if ('program' not in lvl):
      # Not a boogie level - error
      raise Exception("Level " + str(levelId) + " " + \
                      str(levelSet) + " not a dynamic boogie level.")

    bbs = lvl['program']
    loop = lvl["loop"]
    found = []
    need = num
    overfitBoogieInvs = [esprimaToBoogie(x, {}) for x in overfittedInvs]
    negatedVals, _= findNegatingTrace(loop, bbs, num, overfitBoogieInvs)

    if (negatedVals):
        newExpState = (_from_dict(lvl['variables'], negatedVals[0]), 0, False)
        cur_expl_state.insert(0, newExpState)

    for (ind, (loop_head, nunrolls, is_finished)) in enumerate(cur_expl_state):
        if is_finished:
            continue
        if need <= 0:
            break

        good_env = _to_dict(lvl['variables'], loop_head)
        # Lets first try to find terminating executions:
        new_vals, terminating = _tryUnroll(loop, bbs, nunrolls+1, \
                                           nunrolls+1+need, None, good_env)
        new_vals = new_vals[nunrolls+1:]
        cur_expl_state[ind] = (loop_head, nunrolls + len(new_vals), terminating)

        found.extend(new_vals)
        need -= len(new_vals)

    while need > 0:
        bad_envs = [ _to_dict(lvl['variables'], row)
                        for (row,_,_) in cur_expl_state ]
        new_vals, terminating = _tryUnroll(loop, bbs, 0, need, bad_envs, None)
        found.extend(new_vals)
        need -= len(new_vals)
        if (len(new_vals) == 0):
            break
        newExpState = (_from_dict(lvl['variables'], new_vals[0]), \
                       len(new_vals)-1, \
                       terminating)
        cur_expl_state.append(newExpState)

    # De-z3-ify the numbers
    js_found = [ _from_dict(lvl["variables"], env) for env in found]
    return (copy(cur_expl_state), js_found)

@api.method("App.equivalentPairs")
@pp_exc
@log_d(pp_EsprimaInvs, pp_EsprimaInvs, pp_mturkId, pp_EsprimaInvPairs)
def equivalentPairs(invL1, invL2, mturkId): #pylint: disable=unused-argument
    """ 
        Given lists of invariants invL1, invL2, return all pairs (I1, I2)
        where I1 <==> I2, I1 \in invL1, I2 \in invL2 

        Not currently in use.
    """ 
    z3InvL1 = [esprimaToZ3(x, {}) for x in invL1]
    z3InvL2 = [esprimaToZ3(x, {}) for x in invL2]

    res = []
    for x in z3InvL1:
      for y in z3InvL2:
        try:
          equiv = equivalent(x, y)
        except Unknown:
          equiv = False; # Conservative assumption

        if (equiv):
          res.append((x,y))

    res = [(boogieToEsprima(z3_expr_to_boogie(x)),
            boogieToEsprima(z3_expr_to_boogie(y))) for (x,y) in res]
    return res

@api.method("App.impliedPairs")
@pp_exc
@log_d(pp_EsprimaInvs, pp_EsprimaInvs, pp_mturkId, pp_EsprimaInvPairs)
def impliedPairs(invL1, invL2, mturkId): #pylint: disable=unused-argument
    """ 
        Given lists of invariants invL1, invL2, return all pairs (I1, I2)
        where I1 ==> I2, I1 \in invL1, I2 \in invL2 

        Used by game.html
    """ 
    z3InvL1 = [esprimaToZ3(x, {}) for x in invL1]
    z3InvL2 = [esprimaToZ3(x, {}) for x in invL2]

    res = []
    for x in z3InvL1:
      for y in z3InvL2:
        try:
          impl = implies(x, y)
        except Unknown:
          impl = False; # Conservative assumption

        if (impl):
          res.append((x,y))

    res = [(boogieToEsprima(z3_expr_to_boogie(x)),
            boogieToEsprima(z3_expr_to_boogie(y))) for (x,y) in res]
    return res

@api.method("App.isTautology")
@pp_exc
@log_d(pp_EsprimaInv, pp_mturkId, str)
def isTautology(inv, mturkId): #pylint: disable=unused-argument
    """ 
        Check whether the invariant inv is a tautology.
        Used by game.html
    """ 
    try:
      res = (tautology(esprimaToZ3(inv, {})))
      return res
    except Unknown:
      return False; # Conservative assumption

@api.method("App.tryAndVerify")
@pp_exc
@log_d(str, str, pp_EsprimaInvs, pp_mturkId, bool, pp_tryAndVerifyRes)
def tryAndVerify(levelSet, levelId, invs, mturkId, individualMode):
    """ 
        Given a level (levelSet, levelId) and a set of invaraints invs do:
        1) Find all invariants OldI that were not DEFINITELY false from the
           last time we tried to verify this level (getLastVerResult)

        2) Try and verify the level using S = OldI + invs. This is done by
           calling tryAndVerifyLvl. For more on that see comment in
           tryAndVerifyLvl

        3) Return object containing:
           overfitted - all invariants in invs not implied by precondition
           nonind - all invariants in invs that are not inductive
           sound - all invariants in invs that are sound
           post_ctrex - any safety counterexamples to the "sound" invariants.
              If this set is empty, then the level is verified.
           direct_ctrex - any safety counterexamples to ALL of the passed in
              invs (not just the sound ones). This is used by the 'rounds' game
              mode to generate red rows for the next level.
    """ 
    s = sessionF();
    if (levelSet not in traces):
        raise Exception("Unkonwn level set " + str(levelSet))

    if (levelId not in traces[levelSet]):
        raise Exception("Unkonwn trace " + str(levelId) + \
                        " in levels " + str(levelSet))

    if (len(invs) == 0):
        raise Exception("No invariants given")

    lvl = traces[levelSet][levelId]

    if ('program' not in lvl):
      # Not a boogie level - error
      raise Exception("Level " + str(levelId) + " " + \
                      str(levelSet) + " not a dynamic boogie level.")

    workerId, _, _ = mturkId
    print repr(set);
    userInvs = set([ esprimaToBoogie(x, {}) for x in invs ])
    otherInvs = set([])
    lastVer = getLastVerResult(levelSet, levelId, s,
      workerId=(workerId if individualMode else None))

    if (lastVer):
      otherInvs = otherInvs.union([parseExprAst(x) for x in lastVer["sound"]])
      otherInvs = otherInvs.union([parseExprAst(x) for x in lastVer["nonind"]])

    ((overfitted, _), (nonind, _), sound, violations) =\
      tryAndVerifyLvl(lvl, userInvs, otherInvs, args.timeout)

    # See if the level is solved
    solved = len(violations) == 0;
    fix = lambda x: _from_dict(lvl['variables'], x, 0)

    if (not solved):
        bbs = lvl["program"]
        loop = lvl["loop"]
        direct_ctrexs = loopInvSafetyCtrex(loop, otherInvs.union(userInvs),\
                                           bbs, args.timeout);
    else:
        direct_ctrexs = []

    # Convert all invariants from Boogie to esprima expressions, and
    # counterexamples to arrays
    # from dictionaries
    overfitted = [ (boogieToEsprima(inv), fix(v.endEnv()))
      for (inv, v) in overfitted ]
    nonind = [ (boogieToEsprima(inv), (fix(v.startEnv()), fix(v.endEnv())))
      for (inv, v) in nonind ]
    sound = [ boogieToEsprima(inv) for inv in sound ]
    safety_ctrexs = [ fix(v.startEnv()) for v in violations ]
    direct_ctrexs = [ fix(v) for v in direct_ctrexs ]


    res = (overfitted, nonind, sound, safety_ctrexs, direct_ctrexs)
    payl ={
      "lvlset": levelSet,
      "lvlid": levelId,
      "overfitted":nodups([str(esprimaToBoogie(x[0], {})) for x in overfitted]),
      "nonind":nodups([str(esprimaToBoogie(inv, {})) for (inv,_) in nonind]),
      "sound":nodups([str(esprimaToBoogie(inv, {})) for inv in sound]),
      "post_ctrex":safety_ctrexs,
      "direct_ctrex": direct_ctrexs
    }
    addEvent("verifier", "VerifyAttempt", time(), args.ename, \
             "localhost", payl, s, mturkId)

    return res

@api.method("App.simplifyInv")
@pp_exc
@log_d(pp_EsprimaInv, pp_mturkId, pp_EsprimaInv)
def simplifyInv(inv, mturkId): #pylint: disable=unused-argument
    """ Given an invariant inv return its 'simplified' version. We
        treat that as the canonical version of an invariant. Simplification
        is performed by z3 """
    boogieInv = esprimaToBoogie(inv, {});
    noDivBoogie = divisionToMul(boogieInv);
    z3_inv = expr_to_z3(noDivBoogie, AllIntTypeEnv())
    print z3_inv, boogieInv
    simpl_z3_inv = simplify(z3_inv, arith_lhs=True);
    simpl_boogie_inv = z3_expr_to_boogie(simpl_z3_inv);
    return boogieToEsprima(simpl_boogie_inv);

@api.method("App.getRandomCode")
@pp_exc
@log_d(str)
def getRandomCode():
    return randomToken(5)

kvStore = { }

@api.method("App.get")
@pp_exc
@log_d(str)
def getVal(key):
    """ Generic Key/Value store get() used by two-player gameplay for
        synchronizing shared state. 
    """
    if (type(key) != unicode):
      raise Exception("Key must be string");

    return kvStore[key];

@api.method("App.set")
@pp_exc
@log_d(str, str, str)
def setVal(key, val, expectedGen):
    """ Generic Key/Value store set() used by two-player gameplay for
        synchronizing shared state. 
    """
    if (type(key) != unicode):
      raise Exception("Key must be string");

    if (expectedGen != -1):
      (curGen, curVal) = kvStore[key]
    else:
      if (key in kvStore):
        raise Exception("Trying to add a new key with gen 0 " + \
                        "but key already there: " + key);

    if (expectedGen != -1 and curGen != expectedGen):
      return (curGen, curVal);
    else:
      kvStore[key] = (expectedGen + 1, val);
      return (expectedGen + 1, val)

    return kvStore[key];

# Admin Calls:
@api.method("App.getLogs")
@pp_exc
@log_d(str, str, str)
def getLogs(inputToken, afterTimestamp, afterId):
  """ Get the current logs (optionally only logs after a given afterTimestamp
      or afterId if specified). This is only used by admin interface.
  """
  if inputToken != adminToken:
    raise Exception(str(inputToken) + " not a valid token.");

  s = sessionF();
  if (afterTimestamp != None):
    afterT = datetime.strptime(afterTimestamp, "%a, %d %b %Y %H:%M:%S %Z")
    evts = s.query(Event).filter(Event.time > afterT).all();
  elif (afterId != None):
    evts = s.query(Event).filter(Event.id > afterId).all();
  else:
    evts = s.query(Event).all();

  return [ { "id": e.id,
             "type": e.type,
             "experiment": e.experiment,
             "src": e.src,
             "addr": e.addr,
             "time": str(e.time),
             "payload": e.payl() } for e in evts ]

@api.method("App.getSolutions")
@pp_exc
@log_d()
def getSolutions(): # Lvlset is assumed to be current by default
  """ Return all solutions for a levelset. Only used by admin interface.
  """
  res = { }
  for lvlId in lvls:
    solnFile = lvls[lvlId]["path"][0][:-len(".bpl")] + ".sol"
    soln = open(solnFile).read().strip();
    boogieSoln = parseExprAst(soln)
    res[curLevelSetName + "," + lvlId] = [boogieToEsprimaExpr(boogieSoln)]
  return res

@api.method("App.reportProblem")
@pp_exc
@log_d(pp_mturkId, str, str, str)
def reportProblem(mturkId, lvl, desc):
  """ Accept a problem report from a player and send it to the current
      notification e-mail address.
  """
  lines = []
  lines.append("A problem report has been submitted.")
  lines.append("")
  lines.append("Time: %s" %
    datetime.now().strftime("%a, %d %b %Y %H:%M:%S %Z"))
  lines.append("HIT: %s" % mturkId[1])
  lines.append("Worker: %s" % mturkId[0])
  lines.append("Experiment: %s" % args.ename)
  lines.append("Level: %s" % lvl)
  lines.append("Problem description:")
  lines.append("")
  lines.append(desc)

  send_notification(args.email, "Inv-Game Problem Report", "\n".join(lines))

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="invariant gen game server")
    p.add_argument('--local', action='store_true',
            help='Run without SSL for local testing')
    p.add_argument('--log', type=str,
            help='an optional log file to store all user actions. ' +
                 'Entries are stored in JSON format.')
    p.add_argument('--port', type=int, help='an optional port number')
    p.add_argument('--ename', type=str, default='default',
            help='Name for experiment; if none provided, use "default"')
    p.add_argument('--lvlset', type=str, \
            default='lvlsets/unsolved.lvlset',
            help='Lvlset to use for serving benchmarks"')
    p.add_argument('--db', type=str, help='Path to database', required=True)
    p.add_argument('--adminToken', type=str,
            help='Secret token for logging in to admin interface. ' +
            'If omitted will be randomly generated')
    p.add_argument('--timeout', type=int, default=60,
            help='Timeout in seconds for z3 queries.')
    p.add_argument('--email', type=str,
            help='E-mail address to notify for problem reports')
    p.add_argument('--colSwap', action='store_true',
            help='Enable column swapping')
    p.add_argument('--maxlvls', type=int,
            help='Maximum number of levels that can be played per HIT')
    p.add_argument('--replay', action='store_true',
            help='Enable replaying levels')

    args = p.parse_args();

    if ('mysql+mysqldb://' in args.db):
      sessionF = open_mysql_db(args.db)
    else:
      sessionF = open_sqlite_db(args.db)

    if (args.adminToken):
      adminToken = args.adminToken
    else:
      adminToken = randomToken(5);

    if args.log:
        openLog(args.log);

    MYDIR = dirname(abspath(realpath(__file__)))
    ROOT_DIR = dirname(MYDIR)

    if args.local:
      host = '127.0.0.1'
      sslContext = None
    else:
      host = '0.0.0.0'
      sslContext = MYDIR + '/cert.pem', MYDIR + '/privkey.pem'

    curLevelSetName, lvls = loadBoogieLvlSet(args.lvlset)
    traces = { curLevelSetName: lvls }

    print "Admin Token: ", adminToken
    print "Admin URL: ", "admin.html?adminToken=" + adminToken
    app.run(host=host, port=args.port, ssl_context=sslContext, threaded=True)
