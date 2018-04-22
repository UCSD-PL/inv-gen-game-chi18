#! /usr/bin/env python
from traceback import *
import sys
from boto.mturk.connection import *
from argparse import *
from experiments import *
import smtplib
from email.mime.text import MIMEText
import os
import signal

def mkParser(desc, ename=False):
    p = ArgumentParser(description=desc)
    p.add_argument('--credentials_file', type=str,
                   default='credentials.csv',
                   help='path to a csv file containing the AWS credentials')
    p.add_argument('--sandbox', action='store_const', const=True,
                   default=False,
                   help='if specified execute on the sandbox servers')
  
    if ename:
        p.add_argument('--ename', type=str, 
                       default = 'default',
                       help='Name for experiment; if none provided, use "default"')
    return p

def parse_args(p):
    args = p.parse_args()
    if args.sandbox and hasattr(args, "ename"):
        args.ename = args.ename + ".sandbox"
    return args

def error(msg):
    sys.stderr.write(msg)
    sys.exit(-1)

def connect(credentials_file, sandbox, quiet = False):
    with open(credentials_file, 'r') as f:
        f.readline();
        user, a_key, s_key = f.read().split(',')

    HOST = None if (not sandbox) else "mechanicalturk.sandbox.amazonaws.com"

    if (not quiet):
        print "Connecting to", ("production" if HOST == None else "sandbox"),\
            " as ", user, " with access key ", a_key, "..."

    try:
        mc = MTurkConnection(a_key, s_key, host=HOST)
    except:
        error("Failed connecting")

    if (not quiet):
        print "Connected."
    return mc


# HITs can be retrieved by ID even after they have been
# deleted. So when we process our data structures containing HIT IDs,
# we need to check if the HIT was deleted. I could not find a better way
# to do it than calling get_all_hits, which does not return deleted
# HITs.
all_hits = None
def hit_disposed(mc, hit_id):
    global all_hits
    if all_hits == None:
        all_hits = set()
        r = mc.get_all_hits()
        for hit in r:
            all_hits.add(hit.HITId)
    return not (hit_id in all_hits)
    
def hit_status(mc, e, sandbox):
    print "HIT ID                         Assignment ID                  Worker ID"
    changed = False
    num_left = 0
    for sr in e.server_runs:
        try:
            r = mc.get_assignments(sr.hit_id)
        except:
            print sr.hit_id, "cannot get HIT; probably was in", ("production" if sandbox else "sandbox")
            continue
            
        assert(len(r) == 0 or len(r) == 1)
        if hit_disposed(mc, sr.hit_id):
            print sr.hit_id, "was disposed"
        elif len(r) == 0:
            print sr.hit_id, "not completed                  not completed"
            num_left = num_left + 1
            continue
        elif len(r) == 1:
            assn = r[0]
            print sr.hit_id, assn.AssignmentId, assn.WorkerId
        if (sr.pid != 0):
            try:
                os.kill(sr.pid, signal.SIGTERM)
            except:
                print "Could not kill process " + str(sr.pid) + ", probably already dead"
            sr.pid = 0
            changed = True

    if changed:
        e.store_server_runs()
    return num_left

def send_notification(to, subject, msg):
    msg = MIMEText(msg)
    from_email = "automated@zoidberg.ucsd.edu"
    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = to
    s = smtplib.SMTP('localhost')
    s.sendmail(from_email, [to], msg.as_string())
    s.quit()
