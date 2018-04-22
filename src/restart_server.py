#! /usr/bin/env python
from argparse import ArgumentParser
from experiments import load_experiment_or_die, start_server, ServerRun
from lib.common.util import randomToken
import os
import signal

p = ArgumentParser(description='Restart a server')
p.add_argument('--ename', type=str, default = "default", \
        help='Name for experiment; if none provided, use "default"')
p.add_argument('--lvlset', type=str, \
        default = 'desugared-boogie-benchmarks', \
        help='Lvlset to use for serving benchmarks"')
p.add_argument('srid', type=int, \
        help='The server run ID that you want to restart')
p.add_argument("--adminToken", type=str,\
        help='Admin token to use(if omitted we generate a random one)')
p.add_argument('--db', type=str, default=None,
        help='If specified, an explicit database for the servers to use')
args = p.parse_args()
exp = load_experiment_or_die(args.ename)

if (args.adminToken):
    adminToken = args.adminToken
else:
    adminToken = randomToken(5);

for sr in exp.server_runs:
    if sr.srid == args.srid:
        print "Found srid", args.srid
        if sr.pid != 0:
            print "Trying to kill process", sr.pid
            try:
                os.kill(sr.pid, signal.SIGTERM)
                print "Success in killing process", sr.pid
            except Exception:
                print "Could not kill process " + str(sr.pid) + \
                      ", probably already dead, but please check"
            sr.pid = 0
        new_srid = exp.create_unique_server_run_id()
        port = sr.port
        p = start_server(port, args.ename, new_srid, args.lvlset, adminToken, args.db)
        print "Started server run", new_srid, "on port", port, "with pid", p.pid
        exp.add_session(ServerRun(new_srid, sr.hit_id, p.pid, port))
        exit(0)
print "Could not find srid", args.srid
