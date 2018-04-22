class Level {
  constructor(public id: string,
    public variables: string[],
    public data: dataT,
    public goal: any,
    public hint: any,
    public colSwap: any,
    public startingInvs: [string, invariantT][]) {
  }
  static load(lvlSet: string, id: string, cb: (lvl: Level) => void) {
    rpc_loadLvlBasic(lvlSet, id, function(data) {
      cb(new Level(id, data.variables, data.data, data.goal, data.hint, data.colSwap, data.startingInvs));
    });
  }

  isReplay(): boolean {
    return this.startingInvs.length > 0;
  }
}

class DynamicLevel extends Level{
  constructor(public id: string,
    public variables: string[],
    public data:  dataT,
    public goal:  any,
    public hint:  any,
    public colSwap: any,
    public startingInvs: [string, invariantT][],
    public exploration_state: any) {
    super(id, variables, data, goal, hint, colSwap, startingInvs);
  }

  static load(lvlSet: string, id: string, cb: (lvl: Level)=>void) {
    rpc_loadLvlDynamic(lvlSet, id, function(data) {
      cb(new DynamicLevel(id, data.variables, data.data, data.goal, data.hint, data.colSwap, data.startingInvs, data.exploration_state))
    })
  }

  static loadNext(cb: (res: [string, Level])=>void) {
    rpc_loadNextLvlDynamic(Args.get_worker_id(), function(data) {
      if (data === null)
        cb(null)
      else {
        let lvl = new DynamicLevel(data.id, data.variables, data.data, data.goal, data.hint, data.colSwap, data.startingInvs, data.exploration_state);
        cb([data.lvlSet, lvl]);
      }
    })
  }
}
