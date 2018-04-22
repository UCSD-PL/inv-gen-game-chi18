import {rpc_loadLvlBasic, rpc_loadLvlDynamic, rpc_loadNextLvlDynamic, rpc_equivalentPairs, rpc_impliedPairs, rpc_isTautology, rpc_simplify, rpc_tryAndVerify, rpc_instantiate} from "./rpc";
import {dataT, invariantT, templateT} from "./types";
import {Node as ESNode} from "estree";

/* Requires Epsrima.js */
type cbT = (result: any) => void

export function equivalentPairs(invL1: invariantT[], invL2: invariantT[], cb: cbT): void {
  rpc_equivalentPairs(invL1, invL2, cb);
}

function equivalent(inv1:invariantT, inv2:invariantT, cb:(res:boolean)=>void): void {
  equivalentPairs([inv1], [inv2], function (res) { cb(res.length > 0) });
}

export function impliedPairs(invL1:invariantT[], invL2:invariantT[],
                      cb:(arg:[ESNode, ESNode][])=>void): void {
  rpc_impliedPairs(invL1, invL2, cb)
}

function implied(invL1:invariantT[], inv:invariantT , cb:(res:boolean)=>void): void {
  impliedPairs(invL1, [inv], function (res) { cb(res.length > 0) });
}

export function impliedBy(invL1:invariantT[], inv:invariantT, cb:(res:ESNode[])=>void): void {
  impliedPairs(invL1, [inv], function (res) {
    cb(res.map((([inv1,inv2])=>inv1)))
  });
}

export function isTautology(inv:invariantT, cb:(res:boolean)=>void): void {
  rpc_isTautology(inv, cb);
}

export function simplify(inv:string, cb:(res:ESNode)=>void): void {
  rpc_simplify(inv, cb);
}

/*
 *  Given a list of candidate invariants invs tryAndVerify will
 *  return:
 *    - the subset of inv that is overfitted (+ counterexample for each)
 *    - the subset of inv that is non-inductive (+ counterexample for each)
 *    - the subset of inv that is sound
 *    - any counterexamples if the sound subset doesn't imply the postcondition
 *
 */
export function tryAndVerify(lvlSet: string, lvlId: string, invs: invariantT[],
                         cb: (res: [ [ESNode, any[]][], // Overfitted invs & counterexample
                                     [ESNode, [any[], any[]]][], // Nonind. invs & counterexample
                                     ESNode[], // Sound Invariants
                                     any[],// Post cond. counterexample to sound invariants
                                     any[]]) => void) { // Post cond. counterex to all invariants
  rpc_tryAndVerify(lvlSet, lvlId, invs, cb);
}

function instantiate(templates: templateT[],
                     lvlVars: string[], // TODO: Should eventually not need this argument. Convert 
                     data: [ any[] ],   //       data to a dictionary containing variable names.
                     cb: (invs: invariantT)=>void): void {
  rpc_instantiate(templates, lvlVars, data, cb);
}
