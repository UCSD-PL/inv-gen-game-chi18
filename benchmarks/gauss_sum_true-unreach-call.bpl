// c/loop-new/gauss_sum_true-unreach-call.c

procedure main() {
  var n,sum,i,LARGE_INT: int;
  //n = __VERIFIER_nondet_int();
  assume(1 <= n && n <= 1000);
  sum := 0;
  i := 1;
  while (i <= n) 
  // invariant 2 * sum == i * (i - 1) && i <= n + 1;
  {
    sum := sum + i;
    i := i + 1;
  }
  assert(2*sum == n*(n+1));
}

