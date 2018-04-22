// Adaptation of S5
procedure main() {
  var i,j,k,l: int;
  j := 0;
  i := 0;
  assume(k >= 0);
  while (j < k)
  //invariant i == k*j*l;
  {
    i := i + l*k;
    j := j + 1;
  }
  assert(i == k*j*l);
}
