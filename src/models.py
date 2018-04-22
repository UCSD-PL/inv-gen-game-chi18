#pylint: disable=no-self-argument
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey, \
        create_engine, DateTime, Sequence
from sqlalchemy.orm import relationship, sessionmaker
import json
import re

Base = declarative_base();

local_sources = [ "server" ]
workerIDhashRE = re.compile("^[A-Z0-9]{5,}$")

class Source(Base):
  __tablename__ = "sources"
  name = Column(String(256), primary_key=True)
  events = relationship("Event", backref="source", lazy="dynamic")


class Event(Base):
  __tablename__ = "events"
  id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
  type = Column(String(128))
  experiment = Column(String(256))
  src = Column(String(256), ForeignKey("sources.name"))
  addr = Column(String(256)) # For mturk users this is the ip of the access
  time = Column(DateTime)
  payload = Column(String(16536))

  def payl(s):
    return json.loads(s.payload)


class LvlData(Base):
  __tablename__ = "lvldata"
  id = Column(Integer, primary_key=True, autoincrement=True)
  worker = Column(String(256), ForeignKey("sources.name"))
  hit = Column(String(64))
  experiment = Column(String(256))
  lvlset = Column(String(256))
  lvl = Column(String(256))
  time = Column(DateTime)
  startflag = Column(Integer, nullable=False)
  provedflag = Column(Integer, nullable=False)
  allinvs = Column(String(16536))


class VerifyData(Base):
  __tablename__ = "verifydata"
  id = Column(Integer, primary_key=True, autoincrement=True)
  config = Column(String(16536), nullable=False)
  lvlset = Column(String(256), nullable=False)
  lvl = Column(String(256), nullable=False)
  timeout = Column(Integer, nullable=False)
  time = Column(DateTime, nullable=False)
  provedflag = Column(Integer, nullable=False)
  payload = Column(String(16536), nullable=False)


class SurveyData(Base):
  __tablename__ = "surveydata"
  hit = Column(String(64), primary_key=True)
  assignment = Column(String(256), nullable=False)
  worker = Column(String(256), ForeignKey("sources.name"))
  time = Column(DateTime, nullable=False)
  payload = Column(String(16536), nullable=False)


def open_sqlite_db(path):
    engine = create_engine("sqlite:///" + path, echo=False,
      connect_args={'check_same_thread':False});
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine);
    return Session;

def open_mysql_db(url):
    engine = create_engine(url, echo=False);
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine);
    return Session;

def workers(s):
    return [x for x in s.query(Source).all() if workerIDhashRE.match(x.name)]

def _has_evt_type(src, evttype):
    return len([x for x in src.events if x.type == evttype]) > 0

def done_tutorial(src):
    return _has_evt_type(src, "TutorialDone")

def started_tutorial(src):
    return _has_evt_type(src, "TutorialStarted")

def finished_levels(src):
    return [ e.payl() for e in src.events if e.type == "FinishLevel"]

def started_levels(src):
    return [ e.payl() for e in src.events if e.type == "StartLevel"]

def found_invs(src):
    return [ e.payl() for e in src.events if e.type == "FoundInvariant"]

def experiments(src):
    return list(set([e.experiment for e in src.events]))
