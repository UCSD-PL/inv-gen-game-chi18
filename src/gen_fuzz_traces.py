#!/usr/bin/env python
import argparse
import lib.boogie.ast
import levels
import tabulate
from levels import getEnsamble
from random import randint
from json import dumps
from os import mkdir

p = argparse.ArgumentParser(description="trace dumper")
p.add_argument("--lvlset", type=str, default="single-loop-conditionals",
  help="lvlset to use for benchmarks")

args = p.parse_args()
curLevelSetName, lvls = levels.loadBoogieLvlSet(args.lvlset)

for lvl_name in lvls:
  print "Trying random values for ", lvl_name
  lvl = lvls[lvl_name]
  traces = getEnsamble(lvl["loop"], lvl["program"], 1000, 5,\
                       lambda:  randint(-100, 100))
  if (len(traces) == 0):
    print "Found ", len(traces), " traces."
    continue

  print "Found ", len(traces), " traces with ", sum(map(len, traces)), \
    " total rows ", " and ", sum(map(len, traces))*1.0/len(traces), \
    " average length."

  dirN = lvl["path"][0][:-4] + ".fuzz_traces"
  try:
    print "Making directory: ", dirN
    mkdir(dirN)
  except OSError:
    pass;

  for t in traces:
    str_t = dumps(t)
    fname = dirN + "/" + str(hash(str_t)) + ".trace"
    print "Saving trace to file: ", fname
    f = open(fname, "w")
    f.write(str_t)
    f.close()
