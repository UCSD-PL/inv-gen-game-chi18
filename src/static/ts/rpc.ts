/* This file defines the RPC interface between server and client */

interface loadLvlBasicRes {
  id: string;
  variables: string[];
  data: dataT;
  goal: any;
  hint: any;
  colSwap: any;
  startingInvs: [string, invariantT][];
}

interface loadLvlDynamicRes extends loadLvlBasicRes {
  exploration_state: any;
  support_pos_ex: any;
  support_neg_ex: any;
  support_ind_ex: any;
  multiround: any;
}

interface loadNextLvlDynamicRes extends loadLvlDynamicRes {
  id: string;
  lvlSet: string;
}

function mturkId(): [string, string, string] {
  return [Args.get_worker_id(), Args.get_hit_id(), Args.get_assignment_id()];
}

function rpc_loadLvlBasic(lvlSet: string, id: string, cb:(res: loadLvlBasicRes) => void) {
  rpc.call("App.loadLvl", [lvlSet, id, mturkId()], (data:any) => cb(<loadLvlBasicRes>data), log);
}

function rpc_loadLvlDynamic(lvlSet: string, id: string, cb:(res: loadLvlDynamicRes) => void) {
  rpc.call("App.loadLvl", [lvlSet, id, mturkId()], (data:any) => cb(<loadLvlDynamicRes>data), log);
}

function rpc_loadNextLvlDynamic(workerkId: string, cb:(res: loadNextLvlDynamicRes) => void) {
  rpc.call("App.loadNextLvl", [workerkId, mturkId(), Args.get_individual_mode()], (data:any) => cb(<loadNextLvlDynamicRes>data), log);
}

function rpc_genNextLvlDynamic(workerkId: string, lvlSet:string, lvlId: string, invs: invariantT[], cb:(res: loadNextLvlDynamicRes) => void) {
  rpc.call("App.genNextLvl", [workerkId, mturkId(), lvlSet, lvlId, invs, Args.get_individual_mode()], (data:any) => cb(<loadNextLvlDynamicRes>data), log);
}

function rpc_equivalentPairs(invL1: invariantT[], invL2: invariantT[],
                             cb: (arg:[ESTree.Node, ESTree.Node][])=>void): void {
  rpc.call("App.equivalentPairs", [ invL1, invL2, mturkId() ], cb, log)
}

function rpc_impliedPairs(invL1: invariantT[], invL2: invariantT[],
                             cb: (arg:[ESTree.Node, ESTree.Node][])=>void): void {
  rpc.call("App.impliedPairs", [ invL1, invL2, mturkId() ], cb, log)
}

function rpc_isTautology(inv: invariantT, cb:(res:boolean)=>void): void {
  rpc.call("App.isTautology", [ inv, mturkId() ], cb, log)
}

function rpc_simplify(inv:string, cb:(res:ESTree.Node)=>void): void {
  rpc.call("App.simplifyInv", [ esprima.parse(inv), mturkId() ], cb, log)
}

function rpc_tryAndVerify(lvlSet: string, lvlId: string, invs: invariantT[],
                              cb: (res: [ [ESTree.Node, any[]][], // Overfitted invs & counterexample
                                     [ESTree.Node, [any[], any[]]][], // Nonind. invs & counterexample
                                     ESTree.Node[], // Sound Invariants
                                     any[],// Post cond. counterexample to sound invariants
                                     any[]]) => void) {  // Post-cond counterexample to all invariants
  rpc.call("App.tryAndVerify", [ lvlSet, lvlId, invs, mturkId(), Args.get_individual_mode() ], cb, log)
}

function rpc_instantiate(templates: templateT[],
                     lvlVars: string[], // TODO: Should eventually not need this argument. Convert
                     data: [ any[] ],   //       data to a dictionary containing variable names.
                     cb: (invs: invariantT)=>void): void {
  let uniq_templates = unique(templates, (x)=> esprimaToStr(x[0]))
  console.log("Instantiating " + templates.length + " templates " +
              uniq_templates.length + " unique ones.");
  rpc.call("App.instantiate", [uniq_templates, lvlVars, data, mturkId()], cb, log);
}

function rpc_logEvent(workerId: string, name: string, data: any): any {
  return rpc.call("App.logEvent", [workerId, name, data, mturkId()], (res) => { }, log);
}
