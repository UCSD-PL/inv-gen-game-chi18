#! /usr/bin/env bash

if [[ $# -ne 1 ]] ; then
  echo "Usage $0 <host>"
fi

wget $1:5000/api  --post-data='{"jsonrpc":"2.0","method":"App.setAdvance","params":[],"id":1}' -q -O - 
