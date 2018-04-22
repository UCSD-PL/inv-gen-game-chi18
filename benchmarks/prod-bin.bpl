// http://www.lsi.upc.edu/~erodri/webpage/polynomial_invariants/prodbin.htm
procedure main() {
  var a,b,x,y,z: int;
  assume(a >= 0 && b >= 0);
  x := a;
  y := b;
  z := 0;
  while (y != 0)
  //invariant z + x*y == a*b;
  {
    if (y mod 2 == 1) {
      z := z + x;
      y := y - 1;
    } else {
      x := 2*x;
      y := y div 2;
    }
  }
  assert(z == a*b);
}
