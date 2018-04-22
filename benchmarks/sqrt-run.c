#include <stdio.h>
#include <time.h>
#include <stdlib.h>

void __VERIFIER_assert(int cond) {
  if (!(cond)) {
    ERROR: goto ERROR;
  }
  return;
}

int __VERIFIER_nondet_int(int n)
{
  srand(time(NULL));
  int r = rand() % n;
  return r;
}

int main(int argc, char* argv[])
{
  int n, a, su, t;
  n = __VERIFIER_nondet_int(20);

  // a = 0, su = 1, t = 1, n = 26
  // a = 1, su = 4, t = 3
  // a = 2, t = 5, su = 9, 
  // a = 3, t = 7, su = 16
  // a = 4, t = 9, su = 25,
  // a = 5, t = 11, su = 36, n = 26

  a = 0;
  su = 1;
  t = 1;

  // Finds "t*t + 2t - 4su = const", "2a*n - t*n + n = const", "2a*su - t*su + su = const"
  // Finds "a + a*t + t - 2su = const", "a*a + t - su = const", "2a*t + t - t*t = const"
  printf("n\ta\tt\tsu\n");
  while (su <= n)
  {
    printf("%d\t%d\t%d\t%d\n", n, a, t, su);
    a = a + 1;
    t = t + 2;
    su = su + t;
  }
  printf("%d\t%d\t%d\t%d\n", n, a, t, su);

  __VERIFIER_assert((a*a <= n) && ((a+1)*(a+1) > n));    
}

