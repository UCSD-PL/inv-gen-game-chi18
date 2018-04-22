
import {Node as ESNode} from "estree"
export type voidCb = ()=>void
export type boolCb = (res: boolean)=>void
export type invSoundnessResT = { ctrex: [ any[], any[], any[] ]}
export type invariantT = ESNode;
export type templateT = [ invariantT, string[], string[] ]

export type dataT = [any[][], [ any[], any[] ][], any[][] ]
export type resDataT = { data: [ any[], [any, any][], any[] ]}
export type resClearT = { clear: any }
export type resT = resDataT | resClearT
