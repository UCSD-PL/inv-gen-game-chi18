// Adaptation of sorin01
procedure main() {
  var i,j,k,l: int;
  j := 0;
  i := l;
  while (j < 1000)
  //invariant i == l + k*j;
  {
    i := i + k;
    j := j + 1;
  }
  assert(i == l + k*j);
}
