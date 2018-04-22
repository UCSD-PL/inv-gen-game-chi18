// Adaptation of Gauss benchmark, which we currently can't solve
// (well one person now solved it)
// I'm adding a new var j to see how this affects automated tools and humans
procedure main() {
  var n,s,i,j: int;
  assume(1 <= n && n <= 1000);
  s := 0;
  j := 0;
  i := 1;
  while (i <= n)
  //invariant 2 * s == i * j && j == i-1 && i <= n + 1;
  {
    s := s + i;
    j := i;
    i := i + 1;
  }
  assert(2*s == n*(n+1));
}
