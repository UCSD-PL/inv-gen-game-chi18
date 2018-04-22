#! /usr/bin/env python
import argparse
from datetime import datetime
from models import open_sqlite_db, Event
from server_common import log, log_d
from flask import Flask
from flask_jsonrpc import JSONRPC as rpc
from os.path import join, dirname, abspath, realpath
from js import boogieToEsprimaExpr
from lib.boogie.ast import parseExprAst
from lib.common.util import pp_exc, randomToken
from levels import loadBoogieLvlSet

class Server(Flask):
    def get_send_file_max_age(self, name):
        if (name in [ 'jquery-1.12.0.min.js',\
                      'jquery-migrate-1.2.1.min.js',\
                      'jquery.jsonrpcclient.js']):
            return 100000
        return 0

app = Server(__name__, static_folder='static/', static_url_path='')
api = rpc(app, '/api')

## Admin API Calls #######################################################
@api.method("App.getLogs")
@pp_exc
@log_d(str, str, str)
def getLogs(inputToken, afterTimestamp, afterId):
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

  return [ {
             "id": e.id,\
             "type": e.type,\
             "experiment": e.experiment,\
             "src": e.src,\
             "addr": e.addr,\
             "time": str(e.time),\
             "payload": e.payl()
           } for e in evts ]

@api.method("App.getSolutions")
@pp_exc
@log_d()
def getSolutions(): # Lvlset is assumed to be current by default
  res = { }
  for lvlId in lvls:
    solnFile = lvls[lvlId]["path"][0][:-len(".bpl")] + ".sol"
    soln = open(solnFile).read().strip();
    boogieSoln = parseExprAst(soln)
    res[curLevelSetName + "," + lvlId] = [boogieToEsprimaExpr(boogieSoln)]
  return res

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="invariant gen game server")
    p.add_argument('--port', type=int, help='a optional port number',
                   default=12345)
    p.add_argument('--ename', type=str, default='default',
                   help='Name for experiment; if none provided, use "default"')
    p.add_argument('--lvlset', type=str,
                   default='desugared-boogie-benchmarks',
                   help='Lvlset to use for serving benchmarks"')
    p.add_argument('--db', type=str, help='Path to database', default=None)
    p.add_argument('--adminToken', type=str,
                   help='Secret token for logging in to admin interface." +\
                        "If omitted will be randomly generated')
    p.add_argument('--timeout', type=int, default=60,
                   help='Timeout in seconds for z3 queries.')

    args = p.parse_args();

    if (not args.db):
      db = join("..", "logs", args.ename, "events.db")
    else:
      db = args.db

    sessionF = open_sqlite_db(db)

    if (args.adminToken):
      adminToken = args.adminToken
    else:
      adminToken = randomToken(5);

    MYDIR = dirname(abspath(realpath(__file__)))
    ROOT_DIR = dirname(MYDIR)

    curLevelSetName, lvls = loadBoogieLvlSet(args.lvlset)
    traces = { curLevelSetName: lvls }

    print "Admin Token: ", adminToken
    print "Admin URL: ", "admin.html?adminToken=" + adminToken
    app.run(host='0.0.0.0',\
            port=args.port,\
            ssl_context=(MYDIR + '/cert.pem', MYDIR + '/privkey.pem'),\
            threaded=True)
