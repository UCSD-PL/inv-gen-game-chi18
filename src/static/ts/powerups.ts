type holdsT = (inv: invariantT) => boolean
type transformT = (score: number) => number
type appliesT = (lvl: Level) => boolean

interface IPowerup {
  id: string;
  html: string;
  element: JQuery;
  holds(inv: invariantT): boolean;
  transform(score: number): number;
  applies(lvl: Level): boolean;
  highlight(cb: () => any): void;
}

interface IOneShotPowerup extends IPowerup {
  used: boolean;
}

function isOneShotPowerup(obj: IPowerup): obj is IOneShotPowerup {
  return 'used' in obj;
}

interface ILevelPowerup extends IPowerup {
  level_powerup_tag: boolean;
}

function isLevelPowerup(obj: IPowerup): obj is ILevelPowerup {
  return 'level_powerup_tag' in obj;
}

class BasePowerup implements IPowerup {
  element: JQuery;

  constructor(public id: string,
              public html: string,
              public holds: holdsT,
              public transform: transformT,
              public applies: appliesT,
              public tip: string) {
    this.element = $(html)
    this.element.attr("title", tip)
  }
  highlight(cb: () => any): void {
    this.element.effect("highlight", { color: "#008000" }, 500, cb);
  }
}

// NOTE: This probably makes more sense as a mixin/interface pair.
class MultiplierPowerup extends BasePowerup {
  constructor(public id: string,
              public html: string,
              public holds: holdsT,
              public mult: number,
              public applies: appliesT,
              tip: string) {
    super(id + "x",
          "<div class='pwup box'>" + html + "<div class='pwup-mul'>" + mult + "X</div></div>",
          holds,
          (x) => x * mult,
          applies,
          mult + "X if you " + tip)
  }

  highlight(cb: ()=>any): void {
    this.element.effect("highlight", { color: "#008000" }, 2000, ()=>0);
    let mulSpan = $("<span class='scoreText scoreFloat'>x" + this.mult + "</span>") 
    $(this.element).append(mulSpan);
    $(mulSpan).position({ "my": "right center", "at": "left-10 center", "of": this.element });
    mulSpan.hide({ effect: "puff", easing:"swing", duration:2000, complete: () => { mulSpan.remove(); cb(); }})
  }

  setMultiplier(newm: number): void {
    this.mult = newm;
    while (this.tip.charAt(0) >= "0" && this.tip.charAt(0) <= "9") { 
      this.tip = this.tip.slice(1);
    }
    this.tip = newm + this.tip;
    this.transform = (x)=>x*newm;
    this.element.find("div.pwup-mul").html(newm + "X");
    this.element.find("div.pwup-mul").effect({ effect: "highlight", color: "red" })
    this.element.attr("title", this.tip)
  }
}

class NewVarPowerup extends MultiplierPowerup implements ILevelPowerup, IOneShotPowerup {
  level_powerup_tag: boolean = true;
  used: boolean = false;

  constructor(varname: string, multiplier: number = 2) {
    super("NewVar=" + varname,
      varname + "<span style='position:absolute;left:4px;color:goldenrod'>" +
        "*</span>",
      (inv: invariantT) => isMember(identifiers(inv), varname),
      multiplier,
      (lvl) => true,
      "use '" + varname + "' in an expression")
  }
}

class VarOnlyPowerup extends MultiplierPowerup {
  constructor(multiplier: number = 2) {
    super("var only",
      "<span style='position: absolute; left:13px'>1</span>" +
      "<span style='position: absolute;color:red; left:10px'>&#10799;</span>",
      (inv: invariantT) => setlen(literals(inv)) === 0,
      multiplier,
      (lvl)=>true,
      "don't use constants")
  }
}

class UseXVarsPwup extends MultiplierPowerup {
  constructor(nvars: number, multiplier: number = 2) {
    super("NVars=" + nvars,
      nvars + "V",
      (inv: invariantT) => setlen(identifiers(inv)) === nvars,
      multiplier,
      (lvl)=> lvl.variables.length >= nvars && lvl.variables.length != 1,
      "you use " + nvars +  " variable(s)")
  }
}

class UseOpsPwup extends MultiplierPowerup {
  constructor(ops: [ string ], html: string, name: string, multiplier: number = 2) {
    super("Use ops: " + ops,
      html,
      (inv: invariantT) => {
        let inv_ops = operators(inv);
        for (let i in ops) {
          if (inv_ops.has(ops[i])) return true;
        }
        return false;
      },
      multiplier,
      (lvl)=> true,
      "use " + name)
  }
}

interface IPowerupSuggestion {
  clear(lvl: Level): void;
  invariantTried(inv: invariantT): void;
  getPwups(): IPowerup[];
}

class PowerupSuggestionAll implements IPowerupSuggestion {
  all_pwups: IPowerup[];
  age: { [ind: string]: number } = {};
  protected lbls : Label[] = [];
  protected timers : number[] = [];

  constructor() {
    this.all_pwups = [
      new VarOnlyPowerup(2),
      new UseOpsPwup(["<=", ">=", "<", ">", "!=="], "<>", "inequality"),
      new UseOpsPwup(["=="], "=", "equality"),
      new UseOpsPwup(["*", "/"], "*/", "multiplication or division"),
      new UseOpsPwup(["+", "-"], "&plusmn;", "addition or subtraction"),
      //new UseOpsPwup(["->"], "if", "if clause"),
      new UseOpsPwup(["%"], "%", "remainder after division by"),
    ]
  }

  clear(lvl: Level): void {
    this.all_pwups = this.all_pwups.filter(p => !isLevelPowerup(p));
    if (Args.get_use_new_var_powerup()) {
      for (let v of lvl.variables) {
        this.all_pwups.push(new NewVarPowerup(v));
      }
    }
    this.age = {};
    for (let p of this.all_pwups) {
      this.age[p.id] = 0;
      let mPwup = <MultiplierPowerup> p;
      mPwup.setMultiplier(2);
    }
    this.clearLabels();
  }

  clearLabels(): void {
    for (let t of this.timers) {
      clearTimeout(t);
    }
    for (let l of this.lbls) {
      removeLabel(l);
    }
    this.timers = [];
    this.lbls = [];
  }

  invariantTried(inv: invariantT): void {
    for (let p of this.all_pwups) {
      if (p.holds(inv)) {
        this.age[p.id] = 0;
        if (isOneShotPowerup(p)) {
          p.used = true;
        }
      } else {
        this.age[p.id] ++;
      }
      let newM : number = 2 * (this.age[p.id] + 1)
      let mPwup : MultiplierPowerup = <MultiplierPowerup> p;
      if (newM > mPwup.mult) {
        let fn = () => {
          let delay = 1000 + (1000 * newM / 2);
          let l = label({ "at": "left center", "of": mPwup.element },
            "Went up to " + newM + "X !", "right");
          let t = setTimeout(() => { removeLabel(l); }, delay);
          this.timers.push(t);
          this.lbls.push(l);
        }
        fn();
      }
      mPwup.setMultiplier(newM);
    }
  }

  getPwups(): IPowerup[] {
    return this.all_pwups.filter(p => !(isOneShotPowerup(p) && p.used));
  }
}

class PowerupSuggestionFullHistory implements IPowerupSuggestion {
  all_pwups: IPowerup[] = [];
  actual: IPowerup[] = [];
  age: { [ind: string]: number } = {};
  protected gen: number = 0;
  protected nUses: { [ind: string]: number } = { };
  protected lastUse: { [ind: string]: number } = { };
  protected sortFreq: [number, IPowerup][] = []; // TODO: Rename
  protected sortLast: [number, IPowerup][] = []; // TODO: Rename

  constructor(public nDisplay: number,
              public type: string) {
    this.all_pwups = [
      new VarOnlyPowerup(2),
      new UseOpsPwup(["<=", ">=", "<", ">", "!=="], "<>", "inequality"),
      new UseOpsPwup(["=="], "=", "equality"),
      new UseOpsPwup(["*", "/"], "*/", "multiplication or division"),
      new UseOpsPwup(["+", "-"], "&plusmn;", "addition or subtraction"),
    ]

    for (let i in this.all_pwups) {
      this.nUses[this.all_pwups[i].id] = 0;
      this.lastUse[this.all_pwups[i].id] = 0;
    }
  }

  protected computeOrders(): void {
    let sugg = this;
    if (this.gen > 0)
      this.sortFreq = this.actual.map(function (x, ind)  { return <[number, IPowerup]>[ sugg.nUses[x.id] / sugg.gen, x ]; });
    else
      this.sortFreq = this.actual.map(function (x, ind)  { return <[number, IPowerup]>[ 0, x ]; });

    this.sortLast = this.actual.map(function (x, ind)  { return <[number, IPowerup]>[ sugg.lastUse[x.id] , x ]; });

    this.sortFreq.sort(function (a, b) { return a[0] - b[0]; });
    this.sortLast.sort(function (a, b) { return a[0] - b[0]; });
  }

  clear(lvl: Level) {
    this.actual = [];
    this.age = {};

    for (let i in this.all_pwups) {
      if (this.all_pwups[i].applies(lvl)) {
        this.actual.push(this.all_pwups[i]);
      }
    }

    this.computeOrders();
  }

  invariantTried(inv: invariantT): void {
    this.gen ++;
    for (let i in this.actual) {
      if (this.actual[i].holds(inv)) {
        this.nUses[this.actual[i].id] ++;
        this.lastUse[this.actual[i].id] = this.gen;
      }
    }
    this.computeOrders();
  }

  getPwups(): IPowerup[] {
    if (this.type === "lru") {
      return this.sortLast.slice(0, this.nDisplay).map(([fst, snd]: [number, IPowerup]) => snd);
    } else {
      assert(this.type === "lfu");
      return this.sortFreq.slice(0, this.nDisplay).map(([fst, snd]: [number, IPowerup]) => snd);
    }
  }
}

class PowerupSuggestionFullHistoryVariableMultipliers extends PowerupSuggestionFullHistory {
  protected lbl : Label = null;
  protected shown : { [ k: string ] : boolean } = { }
  protected timer : number = 0;

  protected computeOrders(): void {
    super.computeOrders();
    let lst: [number, IPowerup][] = ( this.type == "lru" ? this.sortLast : this.sortFreq );
    this.shown = { };
    for (var i = 0; i < min(this.nDisplay, lst.length); i++) {
      this.shown[lst[i][1].id] = true;
    }

    if (this.lbl) {
      clearTimeout(this.timer);
      removeLabel(this.lbl);
      this.lbl = null;
    }
  }

  invariantTried(inv: invariantT): void {
    super.invariantTried(inv);
    let age : { [ k: string ] : number } = { }

    for (let pwup of this.actual) {
      let age : number = this.gen - this.lastUse[pwup.id];
      let newM : number = 2 * (Math.floor(age / 3) + 1)
      let mPwup : MultiplierPowerup = <MultiplierPowerup> pwup;
      if (newM != mPwup.mult)
        mPwup.setMultiplier(newM);

      if (this.shown[pwup.id] && age > 7 && this.lbl == null) {
        this.lbl = label({ "at": "left center", "of": pwup.element },
          "You haven't tried <br> this in a <br> while!", "right");
        this.timer = setTimeout(() => { removeLabel(this.lbl); }, 5000);
      }
    }
  }
}

// Two Player Stuff.
// TODO: Lots of code duplication. Resolve
class TwoPlayerBasePowerup implements IPowerup {
  element: JQuery;
  player: number;

  constructor(public playerNum: number,
              public id: string,
              public html: string,
              public holds: holdsT,
              public transform: transformT,
              public applies: appliesT,
              public tip: string) {
    this.player = playerNum;
    this.element = $(html);
    this.element.attr("title", tip);
    this.element.tooltip({ position: {
      within: $(".container"), // TODO: Ugly hack refers to external element
      my: "center top+15",
      at: "center bottom",
      collision: "none none",
    }});
  }

  highlight(cb: () => any): void {
    if (this.player === 1) {
      this.element.effect("highlight", { color: "#f00000" }, 500, cb);
    }
    else if (this.player === 2) {
      this.element.effect("highlight", { color: "#0000f0" }, 500, cb);
    }
  }
}

class TwoPlayerMultiplierPowerup extends TwoPlayerBasePowerup {
  constructor(playerNum: number,
              id: string,
              html: string,
              holds: holdsT,
              mult: number,
              applies: appliesT,
              tip: string) {
    super(playerNum, id + "x" + mult,
          (playerNum === 1) ?
            ("<div class='pwup1 box'>" + html + "<div class='pwup-mul'>" +
            mult + "X</div></div>")
            :
            ("<div class='pwup2 box'>" + html + "<div class='pwup-mul'>" +
            mult + "X</div></div>"),
          holds,
          (x) => x * mult,
          applies,
          tip);
  }
}

class TwoPlayerVarOnlyPowerup extends TwoPlayerMultiplierPowerup {
  constructor(playerNum: number, multiplier: number = 2) {
    super(playerNum, "var only",
      "<span style='position: absolute; left:13px'>1</span>" +
      "<span style='position: absolute;color:red; left:10px'>&#10799;</span>",
      (inv: invariantT) => setlen(literals(inv)) === 0,
      multiplier,
      (lvl) => true,
      multiplier + "X if you don't use constants");
  }
}

class TwoPlayerUseXVarsPwup extends TwoPlayerMultiplierPowerup {
  constructor(playerNum: number, nvars: number, multiplier: number = 2) {
    super(playerNum,
      "NVars=" + nvars,
      nvars + "V",
      (inv: invariantT) => setlen(identifiers(inv)) === nvars,
      multiplier,
      (lvl) => lvl.variables.length >= nvars && lvl.variables.length !== 1,
      multiplier + "X if you use " + nvars +  " variable(s)");
  }
}

class TwoPlayerUseOpsPwup extends TwoPlayerMultiplierPowerup {
  constructor(playerNum: number,
              ops: [ string ],
              html: string,
              name: string,
              multiplier: number = 2) {
    super(playerNum,
      "Use ops: " + ops,
      html,
      (inv: invariantT) => {
        let inv_ops = operators(inv);
        for (let op of ops) {
          if (isMember(inv_ops, op)) return true;
        }
        return false;
      },
      multiplier,
      (lvl) => true,
      multiplier + "X if you use " + name);
  }
}


class TwoPlayerPowerupSuggestionFullHistory implements IPowerupSuggestion {
  all_pwups: IPowerup[] = [];
  actual: IPowerup[] = [];
  age: { [ind: string]: number } = {};
  player: number;
  private gen: number = 0;
  private nUses: { [ind: string]: number } = { };
  private lastUse: { [ind: string]: number } = { };
  private sortFreq: [number, IPowerup][] = []; // TODO: Rename
  private sortLast: [number, IPowerup][] = []; // TODO: Rename

  constructor(public playerNum: number,
              public nDisplay: number,
              public type: string) {
    this.all_pwups = [
      new TwoPlayerVarOnlyPowerup(playerNum, 2),
      new TwoPlayerUseXVarsPwup(playerNum, 1, 2),
      new TwoPlayerUseXVarsPwup(playerNum, 2, 2),
      new TwoPlayerUseXVarsPwup(playerNum, 3, 2),
      new TwoPlayerUseXVarsPwup(playerNum, 4, 2),
      new TwoPlayerUseOpsPwup(playerNum, ["<=", ">=", "<", ">"], "<>", "inequality"),
      new TwoPlayerUseOpsPwup(playerNum, ["=="], "=", "equality"),
      new TwoPlayerUseOpsPwup(playerNum, ["*"], "*", "multiplication"),
      new TwoPlayerUseOpsPwup(playerNum, ["+"], "+", "addition"),
    ];

    for (let i in this.all_pwups) {
      this.nUses[this.all_pwups[i].id] = 0;
      this.lastUse[this.all_pwups[i].id] = -1;
    }
  }

  private computeOrders(): void {
    let sugg = this;
    if (this.gen > 0)
      this.sortFreq = this.actual.map(function (x, ind)  { return <[number, IPowerup]>[ sugg.nUses[x.id] / sugg.gen, x ]; });
    else
      this.sortFreq = this.actual.map(function (x, ind)  { return <[number, IPowerup]>[ 0, x ]; });

    this.sortLast = this.actual.map(function (x, ind)  { return <[number, IPowerup]>[ sugg.lastUse[x.id] , x ]; });

    this.sortFreq.sort(function (a, b) { return a[0] - b[0]; });
    this.sortLast.sort(function (a, b) { return a[0] - b[0]; });
  }

  clear(lvl: Level) {
    this.actual = [];
    this.age = {};

    for (let i in this.all_pwups) {
      if (this.all_pwups[i].applies(lvl)) {
        this.actual.push(this.all_pwups[i]);
      }
    }

    this.computeOrders();
  }

  invariantTried(inv: invariantT): void {
    for (let i in this.actual) {
      if (this.actual[i].holds(inv)) {
        this.nUses[this.actual[i].id] ++;
        this.lastUse[this.actual[i].id] = this.gen;
      }
    }
    this.gen ++;
    this.computeOrders();
  }

  getPwups(): IPowerup[] {
    if (this.type === "lru") {
      return this.sortLast.slice(0, this.nDisplay).map(([fst, snd]: [number, IPowerup]) => snd);
    } else {
      assert(this.type === "lfu");
      return this.sortFreq.slice(0, this.nDisplay).map(([fst, snd]: [number, IPowerup]) => snd);
    }
  }
}

