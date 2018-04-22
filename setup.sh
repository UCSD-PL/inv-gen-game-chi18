#! /usr/bin/env bash

if [[ $# -ne 1 ]] ; then
  echo "Usage $0 <target-directory>"
  exit -1
fi

if [ ! -d "$1" ] ; then
  echo "Directory $1 does not exist. Creating..."
  mkdir $1
fi

MYDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
DIR="$( cd $1 && pwd )"


virtualenv $DIR

source $DIR/bin/activate

pip install flask
pip install flask-jsonrpc
pip install slimit
pip install pyparsing
pip install boto
pip install pyOpenSSL
pip install colorama
pip install sqlalchemy
pip install tabulate
pip install Pyro4
pip install pydot
pip install frozendict
pip install infinite
pip install mysql-python

if [ ! -d $DIR/third_party ] ; then
  mkdir $DIR/third_party
fi

if [ ! -e $DIR/bin/z3 ]; then
  pushd $DIR/third_party
  git clone https://github.com/Z3Prover/z3.git z3
  cd z3
  python scripts/mk_make.py --prefix=$DIR --python
  cd build
  make -j 8
  make install
  popd
fi

if [ ! -e $DIR/third_party/daikon ]; then
  pushd $DIR/third_party
  mkdir daikon
  cd daikon
  wget https://plse.cs.washington.edu/daikon/download/daikon-5.5.6.tar.gz
  tar zxf daikon-5.5.6.tar.gz
  popd
fi

if [ ! -e $DIR/third_party/invgen ]; then
  pushd $DIR/third_party
  mkdir invgen
  cd invgen
  wget http://www.tcs.tifr.res.in/~agupta/invgen/invgen
  wget http://www.tcs.tifr.res.in/~agupta/invgen/frontend
  chmod a+x invgen
  chmod a+x frontend
  popd
fi

if [ ! -e $DIR/third_party/cpa_checker_1.4 ]; then
  pushd $DIR/third_party
  mkdir cpa_checker_1.4
  cd cpa_checker_1.4
  wget https://cpachecker.sosy-lab.org/CPAchecker-1.4-svcomp16c-unix.tar.bz2
  tar jxvf CPAchecker-1.4-svcomp16c-unix.tar.bz2
  popd
fi

if [ ! -e $DIR/third_party/boogie ]; then
  pushd $DIR/third_party
  git clone https://github.com/boogie-org/boogie.git
  cd boogie
  wget https://nuget.org/nuget.exe
  mono ./nuget.exe restore Source/Boogie.sln
  mozroots --import --sync
  xbuild Source/Boogie.sln
  ln -s $DIR/third_party/z3/build/z3 Binaries/z3.exe
  popd
fi

deactivate

which node;
if [[ $? -ne 0 ]]; then
  echo "node not found! Please make sure nodejs is installed"
  exit -1
fi

npm install

echo "export DAIKONDIR=$DIR/third_party/daikon/daikon-5.5.6" >> $DIR/bin/activate
echo "export JAVA_HOME=\${JAVA_HOME:-\$(dirname \$(dirname \$(dirname \$(readlink -f \$(/usr/bin/which java)))))}" >> $DIR/bin/activate
echo "source \$DAIKONDIR/scripts/daikon.bashrc" >> $DIR/bin/activate
echo "export PATH=\$PATH:$MYDIR/node_modules/.bin/" >> $DIR/bin/activate
echo "export PATH=\$PATH:$DIR/third_party/invgen/:$DIR/third_party/cpa_checker_1.4/CPAchecker-1.4-svcomp16c-unix/scripts/" >> $DIR/bin/activate

echo "To begin developing run source $DIR/bin/activate and then make"
