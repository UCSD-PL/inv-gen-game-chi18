#!/usr/bin/env python

import argparse
import boogie.ast
import levels
import tabulate

p = argparse.ArgumentParser(description="trace dumper")
p.add_argument("--lvlset", type=str, default="single-loop-conditionals",
  help="lvlset to use for benchmarks")
p.add_argument("--lvl", type=str, default="18",
  help="lvl to use for generating traces")
p.add_argument("--nunrolls", type=int, default=20,
  help="number of times to unroll loops")

args = p.parse_args()

# Process arguments
LVLSET_PATH = "lvlsets/%s.lvlset" % args.lvlset

curLevelSetName, lvls = levels.loadBoogieLvlSet(LVLSET_PATH)

lvl = lvls[args.lvl]
print
print "=== LEVEL ==="
print lvl

trace = levels.getInitialData(lvl["loop"], lvl["program"], args.nunrolls,
  [boogie.ast.parseExprAst(inv)[0] for inv in []]) # Invariant placeholder
print
print "=== RAW TRACE ==="
print trace

vars_ = lvl["variables"]
vars_.sort()
data = trace[0]

print
print "=== TRACE ==="
print tabulate.tabulate([[d[v] for v in vars_] for d in data],
  headers=vars_)
