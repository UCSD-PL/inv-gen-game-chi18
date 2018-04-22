requirejs.config({
  paths: {
    "esprima": './esprima',
    "bonus": "build/ts/bonus",
    "container": "build/ts/container",
    "ctrexGameLogic": "build/ts/ctrexGameLogic",
    "ctrexTracesWindow": "build/ts/ctrexTracesWindow",
    "curvedarrow": "build/ts/curvedarrow",
    "eval": "build/ts/eval",
    "gameLogic": "build/ts/gameLogic",
    "level": "build/ts/level",
    "logic": "build/ts/logic",
    "powerups": "build/ts/powerups",
    "pp": "build/ts/pp",
    "progressWindow": "build/ts/progressWindow",
    "roundsGameLogic": "build/ts/roundsGameLogic",
    "rpc": "build/ts/rpc",
    "scoreWindow": "build/ts/scoreWindow",
    "stickyWindow": "build/ts/stickyWindow",
    "traceWindow": "build/ts/traceWindow",
    "main": "build/ts/main",
    "util": "build/ts/util"
  },
  shim: {
  },
  waitSeconds: 10,
});

requirejs(
  [
    "esprima",
    "main"
  ],
  () => {
	console.log("Loaded...");
  }
);
