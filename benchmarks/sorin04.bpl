// interesting way to compute cubes, but requires Gauss invariant, which
// we can't do yet. So I think we clearly won't be able to do this one, but
// useful to keep in mind
procedure main() {
  var i,a,c: int;
  i := 0;
  a := 0;
  c := 0;
  while (i < 10)
  //invariant i * (i+1) == 2*a && c == i*i*i;
  {
    c := c + (6*a) + 1;
    a := a + i + 1;
    i := i + 1;
  }
  assert(c ==  i*i*i);
}
