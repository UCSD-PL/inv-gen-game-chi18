procedure main() {
  var i,j,k,l: int;
  i := 0;
  assume i*j <= k;
  while (j < 1000)
  //invariant i*j <= k;
  {
    i := i + 1;
    k := k + j;
  }
  assert(i*j <= k);
}
