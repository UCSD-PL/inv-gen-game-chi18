# inv-gen-game-chi18


## Prerequisites

This has been tested on Ubuntu 16.04.

## Installation

After you check-out the repo in directory $REPO, please:

```bash
cd $REPO
./setup.sh env
```

This will:

1) Create a new directory $REPO/env
2) Install a python virtual environment in $REPO/env and download the neccessary python modules
3) Download and build Boogie and z3
4) Install typescript and any other npm packages needed


## Before you start working/running

Please run:

```bash
source $REPO/env/bin/activate
```

To activate the python virtual environment

## Running

To run the backend server with the benchmarks from the paper please run:

```bash
$REPO/src/server.py  --local --port 8080 --ename foo --lvlset ../lvlsets/unsolved.lvlset --db foo.db
```

For more information on arguments to the command run ``` $REPO/src/server.py -h```


## Directories
