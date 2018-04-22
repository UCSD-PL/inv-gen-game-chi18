procedure main() {
  var i,j,k: int;
  i := 0;
  assume j > 0;
  assume k > 0;
  while (i < j*k)
  //invariant i <= j*k;
  {
    i := i + 1;
  }
  assert(i == j*k);
}
