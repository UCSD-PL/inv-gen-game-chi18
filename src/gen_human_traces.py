#!/usr/bin/env python

import argparse
#import lib.boogie.ast
import json
import levels
import math
import os
from random import randint
import tabulate
import pdb
import itertools
import re
from lib.boogie.interp import trace_n_from_start, finished
from lib.boogie.analysis import livevars
from lib.boogie.ast import parseExprAst
from lib.boogie.eval import evalPred
from lib.boogie.bb import bbEntry

p = argparse.ArgumentParser(description="improved trace dumper")
p.add_argument("--lvlset", type=str, default="lvlsets/sorin.lvlset",
  help="lvlset to use for benchmarks")
p.add_argument("--lvl", type=str, default="",
  help="lvl to use for generating traces")
p.add_argument("--write", action="store_true")
p.add_argument("--length", type=int, default=100, help="try find traces of length (defualt 10)")
p.add_argument("--limit", type=int, default=100, help="max numer of traces found (defualt 100)")

args = p.parse_args()

# Process arguments
lvlset_path = args.lvlset
curLevelSetName, lvls = levels.loadBoogieLvlSet(lvlset_path)

def write_trace_col_format(lvl, trace, marker = None):
  trace_str = trace_to_str(trace)
  marker_str = ("." + marker) if marker else ""
  trace_file = lvl["path"][0][:-4] + marker_str + ".auto.trace"
  print "Writing trace to file:", trace_file
  with open(trace_file, "w") as fh:
    fh.write(trace_str)

def trace_to_str(trace):
  if len(trace) == 0:
    return ""
  keys = trace[0].keys()
  keys.sort()
  return " ".join(keys) + "\n" + \
         "\n".join([" ".join([str(e[k]) for k in keys]) for e in trace]) + "\n"

def split_trace(trace, pred):
  if pred == None:
    return [trace]
  pos = []
  neg = []
  for e in trace:
    if evalPred(pred, e):
      pos.append(e)
    else:
      neg.append(e)
  return (neg,pos)

def gen(v,liveVars):
  if v in liveVars:
    yield 7
    yield 3
    vals = list(range(1,100,3))
    vals.remove(7)
    for i in vals:
      yield i
    while True:
      yield 99
  else:
    while True:
      yield 0

def find_split_pred(fname):
  lines = []
  with open(fname) as f:
    lines = f.readlines()
  r = re.compile(".*if.*\((.*)\).*")
  for l in lines:
    re_res = r.match(l)
    if re_res != None:
      return re_res.group(1)
  return None

def cat(fname):
  try:
    with open(fname, 'r') as f:
      print(f.read())
  except IOError:
    print("Could not read" + fname)

def print_comparison(lvl_name):
  lvl = lvls[lvl_name]
  print("== Comparison for " + lvl_name + " ==")
  cat(find_original_boogie_file(lvl))
  print("== Manual Trace ==")
  cat(lvl["path"][0][:-4] + ".trace")
  print("== Auto Trace ==")
  cat(lvl["path"][0][:-4] + ".auto.trace")

def find_original_boogie_file(lvl):
  for p in lvl["path"][1:]:
    if p.endswith(".bpl"):
      return p

def run_lvl(lvl_name):
  print("== " + lvl_name)
  
  lvl = lvls[lvl_name]
  spliter_pred = find_split_pred(find_original_boogie_file(lvl))
  print("Spliter pred: " + str(spliter_pred))

  if spliter_pred:
    print("Skiping programs with spliter preds.")
    return
  
  # vs = lvl["variables"]
  # vs.sort()

  bbs = lvl["program"]
  loop = lvl["loop"]
  entry = loop.header[0]
  liveVars = list(livevars(bbs)[entry])
  liveVars.sort()
  print("live vars: " + str(liveVars))
  loopHdr = loop.loop_paths[0][0]

  store_gen = levels.varproduct({v: gen(v,liveVars) for v in liveVars})
  # tracegen = levels.getEnsamble(loop=loop, bbs=bbs, exec_limit=args.limit,
  #                               tryFind=args.length, include_bbhit=True,
  #                               vargens={v: gen(v,liveVars) for v in liveVars})

  target_len = 7

  tried = set();
  filt_f = lambda bbs, states:  states
  rand_f = lambda state, Id:  randint(-1000, 1000)

  done = False
  while not done:
    try:
      starting_store = next(store_gen)
    except StopIteration:
      print("Exhausted candidate stores (not more in iteration)")
      break
    hashable = tuple(starting_store[v] for v in liveVars)
    if hashable in tried:
      print("Exhausted candidate stores (getting duplicate stores)")
      break
    tried.add(hashable)
    print("Evaluating in starting store: " + str(starting_store))
    (active, inactive) = trace_n_from_start(bbs, starting_store, args.limit, rand_f, filt_f)
    traces = active + [ t for t in inactive if finished(t[-1]) ]
    traces = [ [ st.store for st in tr if st.pc.bb == loopHdr ] for tr in traces]
    for trace in traces:
      print("Found trace of length " + str(len(trace)) + ": ")
      print((trace_to_str(trace)))
      if spliter_pred:
        (t0,t1) = split_trace(trace, spliter_pred)
        if len(t0) >= target_len and len(t1) >= target_len:
          print("Found split traces with lengths >= " + str(target_len) + ". Writing first " + str(target_len) + " elmts.")
          write_trace_col_format(lvl, trace[0:target_len])
          write_trace_col_format(lvl, t0[0:target_len], "0")
          write_trace_col_format(lvl, t1[0:target_len], "1")
          done = True
          break
      else:
        if len(trace) >= target_len:
          print("Found trace with length >= " + str(target_len) + ". Writing first " + str(target_len) + " elmts.")
          write_trace_col_format(lvl, trace[0:target_len])
          done = True
          break

  print_comparison(lvl_name)

    # try:
    #   trace, bbhit = tracegen.next()
    # except StopIteration:
    #   print("exception")
    #   break

    # print("Found trace of length " + str(len(trace)) + ": ")
    # print((trace_to_str(trace)))

    # if spliter_pred:
    #   (t0,t1) = split_trace(trace, spliter_pred)
    #   if len(t0) >= target_len and len(t1) >= target_len:
    #     print("Found split traces with lengths >= " + str(target_len) + ". Writing first " + str(target_len) + " elmts.")
    #     write_trace_col_format(lvl, trace[0:target_len])
    #     write_trace_col_format(lvl, t0[0:target_len], "0")
    #     write_trace_col_format(lvl, t1[0:target_len], "1")
    # else:
    #   if len(trace) >= target_len:
    #     print("Found trace with length >= " + str(target_len) + ". Writing first " + str(target_len) + " elmts.")
    #     write_trace_col_format(lvl, trace[0:target_len])
    #     break

    
# a = parseExprAst("x mod 5 == 5")
# print a
# print evalPred(a, {"x":6})
# pdb.set_trace()

if (args.lvl != ""):
  run_lvl(args.lvl)
else:
  for lvl_name in lvls.keys():
    run_lvl(lvl_name)

#pdb.set_trace()
