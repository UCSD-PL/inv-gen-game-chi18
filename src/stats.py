#!/usr/bin/env python2.7
from argparse import ArgumentParser
from boto.mturk.connection import MTurkRequestError
from collections import OrderedDict
from datetime import datetime
from sqlalchemy import func
import json

from levels import loadBoogieFile, loadBoogieLvlSet
from models import Event, SurveyData, VerifyData
from db_util import open_db, filterEvents, filterSurveys
from lib.boogie.ast import parseExprAst
from vc_check import tryAndVerifyLvl
import mturk_util

def _add(m, k, v):
  a = m.get(k, [])
  a.append(v)
  m[k] = a

def _typs(events):
  return [x.type for x in events]

def events(session, **kwargs):
  query = session.query(
    Event,
    func.json_extract(Event.payload, "$.lvlid").label("lvlid"),
    func.json_extract(Event.payload, "$.lvlset").label("lvlset"),
    func.json_extract(Event.payload, "$.workerId").label("workerId"),
    func.json_extract(Event.payload, "$.assignmentId").label("assignmentId"))
  return filterEvents(query, **kwargs).all()


def splitEventsByAssignment(session, **kwargs):
  m = {}
  for e in events(session, **kwargs):
    _add(m, (e.workerId, e.assignmentId), e)

  for k in m:
    m[k].sort(key=lambda e:  e[0].time)
  return m

def split(lst, pred):
  res = []
  cur = []
  for x in lst:
    cur.append(x)

    if pred(x):
      res.append(cur)
      cur = []

  if (len(cur) > 0):
    res.append(cur)

  return res


def splitEventsByLvlPlay(session, **kwargs):
  """
  Split the events by their (assignment, worker, lvlid) tuples. Any event
  without lvlid is ignored
  """
  m = splitEventsByAssignment(session, **kwargs)
  plays = {}

  for k in m:

    ignore = ['Consent', 'TutorialStart', 'TutorialDone', 'ReplayTutorialAll', 'VerifyAttempt']

    for (ev, lvlid, lvlset, workerId, assignmentId) in m[k]:
      if (ev.type in ignore):
        continue

      if (lvlid is None):
        continue

      curLvl = (assignmentId, workerId, (lvlset, lvlid))
      _add(plays, curLvl, ev)

  split_plays = {}
  for ((assignmentId, workerId, (lvlset, lvlid)), play) in plays.items():
    play.sort(key=lambda x: x.time)
    play_lst = split(play, lambda evt:  evt.type == 'StartLevel')

    #if (len(play_lst) != 1):
    #  print play_lst

    for idx, split_play in enumerate(play_lst):
      split_plays[(assignmentId, workerId, (lvlset, lvlid), idx)] = split_play

  return split_plays
  

def pruneByNumPlays(plays, n):
  """
  Prune the plays such that for each level we keep only the first n
  plays in chronological order.
  """
  lvlPlays = {} # map from level to the plays for that level
  for (k, v) in plays.items():
    _add(lvlPlays, lvlid(v), (k, v))

  # Sort the plays by start time
  for lvlid in lvlPlays:
    lvlPlays[lvlid].sort(key=lambda x:  x[1][0].time)

  # Keep only the first n for each level.
  for lvlid in lvlPlays:
    lvlPlays[lvlid] = lvlPlays[lvlid][:n]

  return {k: play for lvlId in lvlPlays for (k, play) in lvlPlays[lvlId]}

def pruneByNumPlayers(plays, n):
  """
  Prune the plays such that for each level we keep only the 
  plays by the first n unique players in chronological order.
  """
  lvlPlays = {} # map from level to the plays for that level
  for (k, v) in plays.items():
    _add(lvlPlays, lvlid(v), (k, v))

  # Sort the plays by start time
  for lvlid in lvlPlays:
    lvlPlays[lvlid].sort(key=lambda x:  x[1][0].time)

  # For each level keep the plays for the first N unique players
  for lvlid in lvlPlays:
    unique_players = set()
    old_plays = lvlPlays[lvlid]
    new_plays = []
    while len(unique_players) < n and len(old_plays) > 0:
      play = old_plays.pop(0)
      unique_players.add(worker(play[1]))
      new_plays.append(play)

    lvlPlays[lvlid] = new_plays

  return {k: play for lvlId in lvlPlays for (k, play) in lvlPlays[lvlId]}

def interrupted(events):
  """ Given the events of one play, determine if it was interrupted - i.e. if it has a
      GameDone or a SkipLevel event, or none of these and no FinishLevel
  """
  ev_types = [e.type for e in events]
  return 'SkipLevel' in ev_types or 'GameDone' in ev_types or 'FinishLevel' not in ev_types

def finished(events):
  """ Given the events of one play, determine if it was finished - i.e. if its last event is a FinishLevel
  """
  ev_types = [e.type for e in events]
  return 'FinishLevel' in ev_types

def assignment(events):
  assert len(set(e.payl()['assignmentId'] for e in events)) == 1
  return events[0].payl()['assignmentId']

def worker(events):
  assert len(set(e.payl()['workerId'] for e in events)) == 1
  return events[0].payl()['workerId']

def lvlid(events):
  assert len(set(e.payl()['lvlid'] for e in events)) == 1,\
    (assignment(events), worker(events), [set(e.payl()['lvlid'] for e in events)], [(e.type, e.payl()['lvlid']) for e in events])
  return events[0].payl()['lvlid']

def verified_by_worker(lvl, worker, exp):
  s = session.query(VerifyData)\
    .filter(VerifyData.lvl == lvl)\
    .filter(func.json_extract(VerifyData.config, "$.mode") == "individual")\
    .filter(func.json_extract(VerifyData.config, "$.enames[0]") == exp)\
    .filter(func.json_extract(VerifyData.payload, "$.workers[0]") == worker)
  vs = s.all()
  if (len(vs) == 0):
    assert len(events(session, typ='InvariantFound', lvls=[lvl], workers=[worker])) == 0
    return False
  assert (len(vs) == 1), "Not 1 VerifyData entry for {}, {}, {}".format(lvl, worker, exp)
  return vs[0].provedflag

def verified_by_play(lvl, assignment, worker, exp):
  s = session.query(VerifyData)\
    .filter(VerifyData.lvl == lvl)\
    .filter(func.json_extract(VerifyData.config, "$.mode") == "individual-play")\
    .filter(func.json_extract(VerifyData.config, "$.enames[0]") == exp)\
    .filter(func.json_extract(VerifyData.payload, "$.workers[0]") == worker)\
    .filter(func.json_extract(VerifyData.payload, "$.assignments[0]") == assignment)
  vs = s.all()
  if (len(vs) == 0):
    assert len(events(session, typ='InvariantFound', lvls=[lvl], workers=[worker])) == 0
    return False
  assert (len(vs) == 1), "Not 1 VerifyData entry for {}, {}, {}, {} = {}".format(lvl, assignment, worker, exp, vs)
  return vs[0].provedflag

def really_verified_by_play(lvl, assignment, worker, exp, play, timeout):
  invs = set([parseExprAst(x.payl()['canonical']) for x in play if x.type == 'FoundInvariant'])
  (overfitted, _), (nonind, _), sound, violations = tryAndVerifyLvl(lvl, invs, set(), timeout)
  assert type(violations) == list
  return len(violations) == 0

if __name__ == "__main__":
  all_lvl_cols = ['nplays', 'nplay_solved', 'nfinish', 'ninterrupt', 'nplayers', 'nplayers_solved', 'avetime', 'ninv_found', 'ninv_tried']
  all_exp_cols = ['nplays', 'nplay_solved', 'nfinish', 'ninterrupt', 'nplayers', 'nplayers_solved', 'avetime', 'ninv_found', 'ninv_tried']
  p = ArgumentParser(description="Build graphs from database")
  p.add_argument("--db", required=True, help="Database path")
  p.add_argument("--experiments", nargs='+', help="Only consider plays from these experiments")
  p.add_argument("--lvlids", nargs='+', help="Only consider plays from these levels")
  p.add_argument("--nplays", type=int, help="Only consider the first N plays for each level")
  p.add_argument("--nplayers", type=int, help="Only consider the first N unique players for each level")
  p.add_argument("--stat",
    choices=[
      'fun_histo',
      'math_exp_histo',
      'prog_exp_histo',
      'challenging_histo',
      'lvl_stats',
      'math_exp_stats',
    ], help='Which stat to print', required=True)
  p.add_argument("--lvl-columns", nargs='+', choices = all_lvl_cols, help='Optionally pick which columns per benchmarks we want')
  p.add_argument("--exp-columns", nargs='+', choices = all_exp_cols, help='Optionally pick which columns per experience level we want')
  p.add_argument("--timeout", type=int, help="Z3 timeout")
  p.add_argument("--lvlset", required=True, help="Include lvlset invs; may specify multiple items (unset = any)")

  args = p.parse_args()
  filter_args = {}

  lvlset, lvls = loadBoogieLvlSet(args.lvlset)
  if args.experiments:
    filter_args['enames'] = args.experiments
  if args.lvlids:
    filter_args['lvls'] = args.lvlids
  if args.lvl_columns is not None:
    assert args.stat == 'lvl_stats'
    lvl_cols = args.lvl_columns
  else:
    lvl_cols = all_lvl_cols

  if args.nplayers is not None and args.nplays is not None:
    print "Error: Can't specify both --nplayers and --nplays"
    exit(-1)

  sessionF = open_db(args.db)
  session = sessionF()
  plays = splitEventsByLvlPlay(session, **filter_args)

  if (args.nplays is not None):
    plays = pruneByNumPlays(plays, args.nplays)

  if (args.nplayers is not None):
    plays = pruneByNumPlayers(plays, args.nplayers)

  assignments = set(assignment(play) for play in plays.values())
  lvlids = set(lvlid(play) for play in plays.values())

  if args.stat in ['fun_histo', 'challenging_histo']:
    field = {
      'fun_histo':  'fun',
      'challenging_histo':  'challenging',
    }[args.stat]

    histo = { }

    for s in filterSurveys(session.query(SurveyData), assignments=assignments).all():
      v = int(json.loads(s.payload)[field])
      histo[v] = histo.get(v, 0) + 1

    print "Score, # Replies"
    for k in sorted(histo.keys()):
      print k, ',', histo[k]

  elif args.stat in ['math_exp_histo', 'prog_exp_histo']:
    field = {
      'math_exp_histo':  'math_experience',
      'prog_exp_histo':  'prog_experience',
    }[args.stat]

    histo = { }
    workerM = {}

    # A worker may self-report different experiences in several hits.  Collect
    # all the self-reported experiences, average out and round to nearest
    # number.
    for s in filterSurveys(session.query(SurveyData), assignments=assignments).all():
      v = int(json.loads(s.payload)[field])
      _add(workerM, s.worker, v)

    for w in workerM:
      ave_score = int(round(sum(workerM[w]) * 1.0 / len(workerM[w])))
      histo[ave_score] = histo.get(ave_score, 0) + 1

    print "Score, # Workers"
    keys = range(1,6)

    for k in keys:
      print k, ',', histo.get(k, 0)
  elif args.stat == 'lvl_stats':
    players = {lvlid: [] for lvlid in lvlids}
    playsPerLvl = {lvlid: [] for lvlid in lvlids}
    interrupts = {lvlid: 0 for lvlid in lvlids}
    finishes = {lvlid: 0 for lvlid in lvlids}
    total_time = {lvlid: 0.0 for lvlid in lvlids}
    found_invs = {lvlid: [] for lvlid in lvlids}
    tried_invs = {lvlid: [] for lvlid in lvlids}

    for (assignmentId, workerId, (lvlset, lvlid), idx) in plays:
      play = plays[(assignmentId, workerId, (lvlset, lvlid), idx)]
      _add(players, lvlid, workerId)
      _add(playsPerLvl, lvlid, play)

      assert interrupted(play) or finished(play), _typs(play)
      if interrupted(play):
        interrupts[lvlid] = interrupts.get(lvlid, 0) + 1
      else:
        finishes[lvlid] = finishes.get(lvlid, 0) + 1

      time_spent = (play[-1].time - play[0].time).total_seconds()
      total_time[lvlid] = total_time.get(lvlid, 0.0) + time_spent
      for e in play:
        if e.type == 'FoundInvariant':
          _add(found_invs, lvlid, e.payl()['canonical'])
        if e.type == 'TriedInvariant':
          _add(tried_invs, lvlid, e.payl()['canonical'])

    col_header = {
      'nplays': '# Plays',
      'nplay_solved': '# Solving Plays',
      'nfinish': '# Finishes',
      'ninterrupt': '#Interrupts',
      'nplayers': '# Unique Players',
      'nplayers_solved': '# Players Solved Individually',
      'avetime': 'Average Time Spent(s)',
      'ninv_found': '# Invariants Found',
      'ninv_tried': '# Invariants Tried'
    }
    header_str = "Level"
    for col in lvl_cols:
      header_str += ', ' + col_header[col]
    print header_str

    for k in sorted(players.keys()):
      line_str = k
      for col in lvl_cols:
        line_str += ', '
        if col == 'nplays':
          num_plays = len(playsPerLvl[k])
          line_str += str(num_plays)
        elif col == 'nplay_solved':
          num_plays_solved = len(filter(None,
            [really_verified_by_play(lvls[k], assignment(play), worker(play), 'new-benchmarks', play, args.timeout) for play in playsPerLvl[k]]))
          line_str += str(num_plays_solved)
        elif col == 'nfinish':
          finished_plays = finishes.get(k, 0)
          line_str += str(finished_plays)
        elif col == 'ninterrupt':
          interrupted_plays = interrupts.get(k, 0)
          line_str += str(interrupted_plays)
        elif col == 'nplayers':
          unique_players = len(set(players[k]))
          line_str += str(unique_players)
        elif col == 'nplayers_solved':
          unique_players_solved = len(filter(None, [verified_by_worker(k, workerId, 'new-benchmarks')\
            for workerId in set(players[k])]))
          line_str += str(unique_players_solved)
        elif col == 'avetime':
          line_str += str(total_time[k] / num_plays)
        elif col == 'ninv_found':
          num_invs_found = len(set(found_invs[k]))
          line_str += str(num_invs_found)
        elif col == 'ninv_tried':
          num_invs_tried = len(set(tried_invs[k]))
          line_str += str(num_invs_tried)

      print line_str
