import socket
import subprocess
import os
import json
from os.path import join, dirname, abspath, realpath, exists


BONUS_PER_LEVEL=0.75
BONUS_FOR_TUTORIAL=1.50
HIT_REWARD=1.50
REQUIRED_LEVELS_PER_HIT = 2

ROOT_DIR = dirname(dirname(abspath(realpath(__file__))))

def get_server_run_cmd():
    return join(ROOT_DIR, "src", "server.py")

def get_server_log_fname(experiment_name, srid):
    return join(ROOT_DIR, "logs", experiment_name, str(srid) + ".slog" )

def get_event_log_fname(experiment_name, srid):
    return join(ROOT_DIR, "logs", experiment_name, str(srid) + ".elog" )

def get_db_fname(experiment_name):
    return join(ROOT_DIR, "logs", experiment_name, "events.db" )

def get_lvlset_dir(lvlset):
    return join(ROOT_DIR, lvlset)


class ServerRun:
    def __init__(self, srid, hit_id, pid, port):
        self.srid = srid    # server run id, unique id for each run
        self.hit_id = hit_id
        self.pid = pid
        self.port = port;

class Experiment:
    def __init__(self, experiment_name, create_if_not_there = False):
        self.experiment_name = experiment_name
        eDirname = join(ROOT_DIR, 'logs', experiment_name)
        if not exists(eDirname):
            if create_if_not_there:
                os.makedirs(eDirname)
            else:
                raise IOError
        self.fname = join(ROOT_DIR, 'logs', experiment_name, 'server_runs')
        self.dirname = eDirname;
        self.server_runs = self.read_server_runs()
    def read_server_runs(self):
        self.server_runs = []
        try:
            with open(self.fname, "rb") as f:
                for line in f:
                    s = json.loads(line)
                    try:
                        port = s[3]
                    except IndexError:
                        port = 0
                    self.server_runs.append(ServerRun(s[0], s[1], s[2], port))
        except IOError:
            # file does not exist, create it
            self.store_server_runs()
        return self.server_runs
    def store_server_runs(self):
        with open(self.fname, 'wb') as f:
            for s in self.server_runs:
                json.dump([s.srid, s.hit_id, s.pid, s.port], f)
                f.write("\n")
    def create_unique_server_run_id(self):
        res = 0
        for s in self.server_runs:
            if s.srid > res:
                res = s.srid
        return res + 1
    def add_session(self, s):
        self.server_runs.append(s)
        self.store_server_runs()

def load_experiment_or_die(ename):
    try:
        return Experiment(ename)
    except IOError:
        print "Experiment", ename, "does not exist"
        exit(-1)

# def create_new_experiment():
#     experiment_id = 0
#     for file_name in os.listdir(get_log_dir()):
#         if file_name.endswith(".exp"):
#             i = int(os.path.splitext(file_name)[0])
#             if i > experiment_id:
#                 experiment_id = i
#     return Experiment(experiment_id+1)

def get_unused_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('localhost', 0))
    _, port = s.getsockname()
    s.close()
    return port

def start_server(port, experiment_name, srid, lvlset, adminToken, db,
                 email=None, maxlvls=None, colSwap=False, replay=False):
    server_log = get_server_log_fname(experiment_name, srid)
    event_log = get_event_log_fname(experiment_name, srid)

    if (db == None):
      db = get_db_fname(experiment_name)

    with open(server_log, 'w') as output:
        cmd = [ get_server_run_cmd(),
                "--port", str(port),\
                "--log", event_log,\
                "--ename", experiment_name,\
                "--lvlset", lvlset,\
                "--db", db,\
                "--adminToken", adminToken
              ]
        if email is not None:
          cmd.extend(["--email", email])
        if colSwap:
          cmd.append("--colSwap")
        if maxlvls is not None:
          cmd.extend(["--maxlvls", str(maxlvls)])
        if replay:
          cmd.append("--replay")
        p = subprocess.Popen(cmd, stdout=output, stderr=subprocess.STDOUT)
    return p

