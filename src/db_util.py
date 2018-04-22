from models import Source, Event, SurveyData, open_sqlite_db, open_mysql_db
from json import loads,dumps
from datetime import datetime
from js import esprimaToBoogie
from sqlalchemy import func

def playersWhoStartedLevel(lvlset, lvl, session):
  return set([ e.source.name for e in session.query(Event).all()
                             if (e.type == "StartLevel" and
                                 e.payl()["lvlset"] == lvlset and
                                 e.payl()["lvlid"] == lvl) ])

def filterSurveys(query, assignments=None):
  if assignments is not None:
    query = query.filter(SurveyData.assignment.in_(assignments))
  return query

def filterEvents(query, enames=None, lvls=None, lvlsets=None, workers=None,
  assignments=None, typ=None):
  if enames is not None:
    query = query.filter(Event.experiment.in_(enames))
  if lvls is not None:
    query = query.filter(func.json_extract(Event.payload, "$.lvlid")
      .in_(lvls))
  if lvlsets is not None:
    query = query.filter(func.json_extract(Event.payload, "$.lvlset")
      .in_(lvlsets))
  if workers is not None:
    query = query.filter(func.json_extract(Event.payload, "$.workerId")
      .in_(workers))
  if assignments is not None:
    query = query.filter(func.json_extract(Event.payload, "$.assignmentId")
      .in_(assignments))

  if typ is not None:
    query = query.filter(Event.type == typ)

  return query

def allInvs(session, enames=None, lvls=None, lvlsets=None, workers=None,
  assignments=None, enameSet=None, lvlSet=None, lvlsetSet=None,
  workerSet=None, assignmentSet=None, colSwaps=None):
  q = session.query(
      Event.experiment,
      func.json_extract(Event.payload, "$.lvlid"),
      func.json_extract(Event.payload, "$.lvlset"),
      func.json_extract(Event.payload, "$.workerId"),
      func.json_extract(Event.payload, "$.assignmentId"),
      func.json_extract(Event.payload, "$.raw"),
      func.json_extract(Event.payload, "$.canonical"),
      func.ifnull(func.json_extract(Event.payload, "$.colSwap"), 0)
    ) \
    .filter(Event.type == "FoundInvariant")

  q = filterEvents(q, enames, lvls, lvlsets, workers, assignments)

  def gen():
    for row in q.all():
      if enameSet is not None:
        enameSet.add(row[0])
      if lvlSet is not None:
        lvlSet.add(row[1])
      if lvlsetSet is not None:
        lvlsetSet.add(row[2])
      if workerSet is not None:
        workerSet.add(row[3])
      if assignmentSet is not None:
        assignmentSet.add(row[4])
      if colSwaps is not None:
        try:
          colSwaps[row[7]] += 1
        except KeyError:
          colSwaps[row[7]] = 1

      yield (row[5], row[6])

  return set(dict(gen()).iteritems())

def levelSkipCount(session, ename, lvlset, lvl, worker, assignment):
  q = session.query(Event.id).filter(Event.type == "SkipToNextLevel")
  q = filterEvents(q, enames=[ename], lvls=[lvl], lvlsets=[lvlset],
    workers=[worker], assignments=[assignment])
  return q.count()

def getOrAddSource(name, session):
  srcs = session.query(Source).filter(Source.name == name).all()
  if (len(srcs) != 0):
    assert len(srcs) == 1
    return srcs[0]

  s = Source(name = name)
  session.add(s)
  session.commit();
  return s


def addEvent(sourceName, typ, time, ename,  addr, data, session, mturkId):
  src = getOrAddSource(sourceName, session);

  payl = { "workerId": mturkId[0],
           "hitId": mturkId[1],
           "assignmentId": mturkId[2] }

  if typ == "Consent":
    pass
  elif (typ == "TutorialStart" or typ == "ReplayTutorialAll"):
    pass
  elif (typ == "TutorialDone"):
    pass
  elif (typ == "StartLevel" or
        typ == "FinishLevel" or
        typ == "SkipToNextLevel"):
    payl["lvlset"] = data[0]
    payl["lvlid"] = data[1]
    if typ == "FinishLevel":
      payl["verified"] = data[2]
      invs = zip(data[3], [ str(esprimaToBoogie(x, {})) for x in data[4] ])
      payl["all_found"] = invs;
    colSwap = data[-2]
    if colSwap is not None:
      payl["colSwap"] = colSwap
    replay = data[-1]
    if replay is not None:
      payl["replay"] = replay
  elif (typ == "FoundInvariant" or typ == "TriedInvariant"):
    payl["lvlset"] = data[0]
    payl["lvlid"] = data[1]
    payl["raw"] = data[2]
    payl["canonical"] = str(esprimaToBoogie(data[3], { }))
    payl["colSwap"] = data[4]
    payl["replay"] = data[5]
  elif (typ == "PowerupsActivated"):
    payl["lvlset"] = data[0]
    payl["lvlid"] = data[1]
    payl["raw"] = str(esprimaToBoogie(data[2], { }))
    payl["powerups"] = data[3]
  elif (typ == "GameDone"):
    payl["numLvlsPassed"] = data[0]
  elif (typ == "VerifyAttempt"):
    for k in data:
      payl[k] = data[k];
  elif (typ == "GenNext.Solved" or typ == "GenNext.NoNewRows"):
    payl = data
  else:
    print "Unknown event type: ", typ

  e = Event(type=typ,\
            source=src,\
            addr=addr,\
            experiment=ename,\
            time=datetime.fromtimestamp(time),\
            payload=dumps(payl))

  session.add(e)
  session.commit();

def levelSolved(session, lvlset, lvlid, workerId=None):
  verifys = session.query(Event).filter(Event.type == "VerifyAttempt").all()
  verifyPayls = [ x.payl() for x in verifys ]
  solved_events = [ x for x in verifyPayls
                      if (x["lvlset"] == lvlset and
                          x["lvlid"] == lvlid and
                          len(x["post_ctrex"]) == 0 and
                          (workerId is None or x["workerId"] == workerId)) ]
  # We can't just look for a successfull "FinishEvent", since sometimes the
  # solver takes a while, and finishes successfully only after the user has
  # gotten impatient and clicked next. So look for At least 1 successful
  # VerifyAttempt
  return len(solved_events) > 0

def levelFinishedBy(session, lvlset, lvlid, userId):
  finishLevels = session.query(Event)\
                    .filter(Event.type == "FinishLevel")\
                    .filter(Event.src == userId).all()
  finishLevelPayls = [ x.payl() for x in finishLevels ]
  finishLevelPayls = [ x for x in finishLevelPayls\
                         if x["lvlset"] == lvlset and x["lvlid"] == lvlid]
  return len(finishLevelPayls) > 0

def levelsPlayedInSession(session, assignmentId):
  q = session.query(Event.id).filter(Event.type == "FinishLevel")
  q = filterEvents(q, assignments=[assignmentId])
  return q.count()

def open_db(path):
  if "mysql+mysqldb://" in path:
    sessionF = open_mysql_db(path)
  else:
    sessionF = open_sqlite_db(path)
  return sessionF
