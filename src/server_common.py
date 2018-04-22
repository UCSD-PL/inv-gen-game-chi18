from json import dumps
from pp import pp_mturkId
from colorama import Fore,Back,Style, init as colorama_init
from time import time
from sys import exc_info, stdout
from flask import request
import traceback
# Profiling import
from cProfile import Profile
from StringIO import StringIO
from pstats import Stats

colorama_init();

# Logging stuff
logF = None;
def openLog(fname):
    global logF;
    logF = open(fname, 'w');

def log(action, *pps):
    action['time'] = time()
    action['ip'] = request.remote_addr;
    if (logF):
        logF.write(dumps(action) + '\n')
        logF.flush()
    else:
        if (len(pps) == 0):
          print dumps(action) + "\n";
        else:
          assert(len(action['kwargs']) == 0);
          assert(len(pps) >= len(action['args']));
          ppArgs = [pps[ind](arg) for (ind, arg) in enumerate(action["args"])]
          # See if one of the ppArgs is a mturkId
          hitId, assignmentId, workerId = (None, None, None)
          mturkArgInd = None
          for (i, _) in enumerate(ppArgs):
            if (pps[i] == pp_mturkId):
              workerId, hitId, assignmentId = action["args"][i]
              mturkArgInd = i

          if (mturkArgInd != None):
            ppArgs.pop(mturkArgInd)

          reset = Style.RESET_ALL
          red = Fore.RED
          green = Fore.GREEN

          prompt = "[" + green + str(action['ip']) + reset + \
              red + ":" + green + str(hitId) + reset + \
              red + ":" + green + str(assignmentId) + reset + \
              red + ":" + green + str(workerId) + reset + \
              '] ' + \
              Style.DIM + str(action['time']) + reset + ':'

          call = red + action['method'] + "(" + reset \
              + (red + "," + reset).join(map(str, ppArgs)) + \
               red + ")" + reset

          if (len(action['args']) + 1 == len(pps) and 'res' in action):
            call += "=" + pps[len(action['args'])](action['res']);

          print prompt + call;
        stdout.flush();

def log_d(*pps):
    def decorator(f):
        def decorated(*pargs, **kwargs):
            try:
                res = f(*pargs, **kwargs)
                log({ "method": f.__name__, "args": pargs, "kwargs": kwargs,
                      "res": res }, *pps)
                return res;
            except Exception:
                strTrace = ''.join(traceback.format_exception(*exc_info()))
                log({ "method": f.__name__, "args": pargs, "kwargs": kwargs,
                      "exception": strTrace})
                raise
        return decorated
    return decorator

# Profiling stuff
def prof_d(f):
    def decorated(*pargs, **kwargs):
        try:
            pr = Profile()
            pr.enable()
            res = f(*pargs, **kwargs)
            pr.disable()
            return res;
        except Exception:
            raise
        finally:
            # Print results
            s = StringIO()
            ps = Stats(pr, stream=s).sort_stats('cumulative')
            ps.print_stats()
            print s.getvalue()
    return decorated

