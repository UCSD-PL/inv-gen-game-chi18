// http://www.lsi.upc.edu/~erodri/webpage/polynomial_invariants/cohencu.htm
procedure main() {
  var n,x,y,z: int;
  n := 0;
  x := 0;
  y := 1;
  z := 6;
  while (n < 100)
  //invariant z == 6*n + 6 && y == 3*n*(n+1) + 1 && x == n*n*n;
  {
    n := n + 1;
    x := x + y;
    y := y + z;
    z := z + 6;
  }
  assert(x == n*n*n);
}
