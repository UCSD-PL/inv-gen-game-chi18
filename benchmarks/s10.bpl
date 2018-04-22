// Adaptation of sorin01
procedure main() {
  var i,j,k: int;
  j := 0;
  i := 10;
  while (j < 1000)
  //invariant i == 10 + k*j;
  {
    i := i + k;
    j := j + 1;
  }
  assert(i == 10 + k*j);
}
