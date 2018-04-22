#! /usr/bin/env python
from json import loads, dumps
from js import esprimaToBoogie
from datetime import datetime
from models import open_sqlite_db, Source, Event, workers, done_tutorial,\
    finished_levels, found_invs, experiments
from experiments import Experiment, load_experiment_or_die, ServerRun
from argparse import ArgumentParser
from os.path import join, basename

p = ArgumentParser(description="Compute stats over an experiment");
p.add_argument('exp1', type=str, help='Name for first experiment to merge');
p.add_argument('exp2', type=str, help='Name for first experiment to merge');
p.add_argument('out', type=str, help='Name for merged experiment');

if __name__ == "__main__":
    args = p.parse_args();

    e1 = load_experiment_or_die(args.exp1)
    e1.read_server_runs();
    e2 = load_experiment_or_die(args.exp2)
    e2.read_server_runs();
    try:
      e3 = Experiment(args.out, False);
      print "Error: Experiment ", args.out, "already exists"
      exit(-1)
    except IOError:
      e3 = Experiment(args.out, True)

    s1 = open_sqlite_db("../logs/" + args.exp1 + "/events.db")()
    s2 = open_sqlite_db("../logs/" + args.exp2 + "/events.db")()
    s3 = open_sqlite_db("../logs/" + args.out + "/events.db")()


    # Merging consists of 3 steps:
    # 1) Copy over all ignore-*, tut-done-* and done-* files over in target
    #    directory
    from shutil import copyfile
    from glob import glob

    e1_files = glob(join(e1.dirname, "ignore-*")) +\
               glob(join(e1.dirname, "tut-done*")) +\
               glob(join(e1.dirname, "done-*"))

    e2_files = glob(join(e1.dirname, "ignore-*")) +\
               glob(join(e1.dirname, "tut-done*")) +\
               glob(join(e1.dirname, "done-*"))

    all_files = e1_files + e2_files

    for f in e1_files + e2_files:
      copyfile(f, join(e3.dirname, basename(f)));

    # 2) Merge server_runs and re-number exp2's server runs. Copy over (and
    # optionally re-number) the .elog and .slog files
    for e1run in e1.server_runs:
      e3.server_runs.append(ServerRun(e1run.srid, e1run.hit_id, e1run.pid,
        e1run.port));
      for f in glob(join(e1.dirname, str(e1run.srid) + ".*")):
        copyfile(f, join(e3.dirname, basename(f)))
    start = len(e1.server_runs);
    for e2run in e2.server_runs:
      e3.server_runs.append(ServerRun(e2run.srid + start, e2run.hit_id,
          e2run.pid, e2run.port));
      strSrid = str(e2run.srid)
      for f in glob(join(e2.dirname, strSrid + ".*")):
        copyfile(f, join(e3.dirname,
          str(e2run.srid + start) + basename(f)[len(strSrid):]))

    e3.store_server_runs();

    # 3) Merge the events.db files
    sources =  s1.query(Source).all() + s2.query(Source).all()
    events = s1.query(Event).all() + s2.query(Event).all()

    srcsSet = set()

    for src in sources:
      if src.name in srcsSet:
        continue
      srcsSet.add(src.name)
      s3.add(Source(name = src.name));

    s3.commit()

    for evt in events:
      s3.add(Event(type = evt.type,\
                   experiment = evt.experiment,\
                   src = evt.src,\
                   addr = evt.addr,\
                   time = evt.time,\
                   payload = evt.payload));

    s3.commit();
