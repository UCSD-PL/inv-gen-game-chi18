#! /usr/bin/env bash

MYDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )" 

pushd $MYDIR/src/static
make
popd
