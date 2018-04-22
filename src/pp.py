from js import esprimaToZ3

def pp_BoogieLvl(lvl):
  if (lvl != None):
    return "Boogie(" + str(lvl['data']) + ")"
  else:
    return str(lvl)

def pp_EsprimaInv(inv):
  return str(esprimaToZ3(inv, {}))

def pp_List(l, pp_el):
  return "[" + ",".join([pp_el(el) for el in l]) + "]"

def pp_Tuple(t, *pps):
  return "(" + ",".join([pp(el) for (pp,el) in zip(pps, t)]) + ")"

def pp_EsprimaInvs(invs):
  return pp_List(invs, pp_EsprimaInv)

def pp_EsprimaInvPairs(invPairs):
  return pp_List(invPairs, lambda p:  pp_Tuple(p, pp_EsprimaInv, pp_EsprimaInv))

def pp_Ctrex(ctrx):
  return pp_Tuple(ctrx, pp_EsprimaInv, str)

def pp_Ctrexs(ctrxs):
  return pp_List(ctrxs, pp_Ctrex);

def pp_CheckInvsRes(res):
  return pp_Tuple(res, pp_Ctrexs, pp_Ctrexs, pp_EsprimaInvs)

def pp_tryAndVerifyRes(res):
  return pp_Tuple(res, pp_Ctrexs, pp_Ctrexs, pp_EsprimaInvs, str, str)

def pp_mturkId(mId):
  return pp_Tuple(mId, str, str, str)
