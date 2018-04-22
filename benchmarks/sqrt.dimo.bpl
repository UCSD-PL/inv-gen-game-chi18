procedure main()
{
  var n, a, su, t : int;

  a := 0;
  su := 1;
  t := 1;
  // Final assert doesn't make sense when n is negative
  assume(n>0);

  while (su <= n)
  // invariant su == (a+1)*(a+1)  && t == 2*a + 1 && su <= n + t;
  {
    a := a + 1;
    t := t + 2;
    su := su + t;
  }

  assert((a*a <= n) && ((a+1)*(a+1) > n));
}
