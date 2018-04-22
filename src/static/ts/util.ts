type directionT = "up" | "down" | "left" | "right"

type strset = Set<string>

function emptyStrset(): strset {
  return new Set();
}

function toStrset(strs: string[]): strset {
  let res = emptyStrset();
  for (let x of strs) {
    res.add(x);
  }
  return res;
}

function isMember(s: strset, x: string): boolean {
  return s.has(x);
}

function isSubset(s1: strset, s2: strset): boolean {
  for (let k of s1) {
    if (!isMember(s2, k)) return false;
  }
  return true;
}

function difference(s1: strset, s2: strset): strset {
  let res  = emptyStrset();
  for (let k of s1) {
    if (isMember(s2, k)) continue;
    res.add(k);
  }
  return res;
}

function isEmpty(s: strset): boolean {
  return s.size === 0;
}

function any_mem(s: strset): string {
  for (let k of s) {
    return k;
  }
}

function log(arg: any): void { console.log(arg); }
function error(arg: any): void { log(arg); }
function assert(c: boolean, msg?: any): void {
  if (msg === undefined)
    msg = "Oh-oh";

  if (!c)
    throw msg || "Assertion failed.";
}
function logEvent(name: string, data: any): any {
  return rpc_logEvent(Args.get_worker_id(), name, data);
}

function fst<T1, T2>(x: [T1, T2]): T1 { return x[0]; }
function snd<T1, T2>(x: [T1, T2]): T2 { return x[1]; }

class Args {
  static parsed: boolean = false;
  static args: { [key:string] : string; } = {};
  static hit_id: string = null;
  static worker_id: string = null;
  static assignment_id: string = null;
  static turk_submit_to: string = null;
  static tutorial_action: string = null;
  static admin_token: string = null;
  static mode: string = null;
  static noifs: boolean = false;
  static use_new_var_powerup: boolean = false;
  static individual_mode: boolean = false;
  static consent: boolean = false;

  static parse_args() {
    if (Args.parsed)
      return;
    let query = window.location.search.substring(1).split("&");
    for (let i = 0; i < query.length; i++) {
      if (query[i] === "") // check for trailing & with no param
        continue;
      let param = query[i].split("=");
      Args.args[decodeURIComponent(param[0])] = decodeURIComponent(param[1] || "");
    }
    Args.hit_id = Args.args["hitId"];
    Args.worker_id = Args.args["workerId"] || "";
    Args.assignment_id = Args.args["assignmentId"];
    Args.turk_submit_to = Args.args["turkSubmitTo"];
    Args.tutorial_action = Args.args["tutorialAction"];
    Args.admin_token = Args.args["adminToken"];
    Args.mode = Args.args["mode"] || "patterns";
    Args.noifs = Args.args.hasOwnProperty("noifs");
    Args.use_new_var_powerup = !!+Args.args["nvpower"];
    Args.individual_mode = !!+Args.args["individual"];
    Args.consent = !!+Args.args["consent"];
    Args.parsed = true;
  }
  static get_hit_id(): string {
    Args.parse_args();
    return Args.hit_id;
  }
  static get_worker_id(): string {
    Args.parse_args();
    return Args.worker_id;
  }
  static get_assignment_id(): string {
    Args.parse_args();
    return Args.assignment_id;
  }
  static get_turk_submit_to(): string {
    Args.parse_args();
    return Args.turk_submit_to;
  }
  static get_tutorial_action(): string {
    Args.parse_args();
    return Args.tutorial_action;
  }
  static get_admin_token(): string {
    Args.parse_args();
    return Args.admin_token;
  }
  static get_mode(): string {
    Args.parse_args();
    return Args.mode;
  }
  static get_noifs(): boolean {
    Args.parse_args();
    return Args.noifs;
  }
  static get_use_new_var_powerup(): boolean {
    Args.parse_args();
    return Args.use_new_var_powerup;
  }
  static get_individual_mode(): boolean {
    Args.parse_args();
    return Args.individual_mode;
  }
  static get_consent(): boolean {
    Args.parse_args();
    return Args.consent;
  }
}

function shuffle<T>(arr: T[]): void {
  let j: number = null;
  for (let i: number = 0; i < arr.length; i++) {
    j = Math.floor(Math.random() * arr.length);
    let x = arr[i];
    arr[i] = arr[j];
    arr[j] = x;
  }
};

class Label {
  public pos: JQueryUI.JQueryPositionOptions;
  public elem: JQuery;
  public timer: any;

  constructor(pos_arg: (JQueryUI.JQueryPositionOptions | HTMLElement),
    public txt: string,
    public direction: directionT,
    public pulseWidth = 5,
    public pulse = 500) {

    if (pos_arg.hasOwnProperty("of")) {
      this.pos = <JQueryUI.JQueryPositionOptions>pos_arg;
    } else {
      this.pos = {
        of: <HTMLElement>pos_arg
      };
      if (direction === "up") {
        this.pos["at"] = "center bottom";
      } else if (direction === "down") {
        this.pos["at"] = "center top";
      } else if (direction === "left") {
        this.pos["at"] = "right center";
      } else if (direction === "right") {
        this.pos["at"] = "left center";
      }
    }

    type posArr = [ string, number ,string, number]
    function _strPos(s: posArr): string {
      return s[0] + (s[1] > 0 ? '+' : '') + (s[1] != 0 ? s[1] : "") + " " +
             s[2] + (s[3] > 0 ? '+' : '') + (s[3] != 0 ? s[3] : "");
    }

    let clazz: string = "", text_pos: string = "", arrow_pos: string = "";

    let vec: [number, number] = [0,0], arr_off: [number, number] = [0,0];


    if (direction == "up") {
      clazz = "arrow_up"
      text_pos = "top:  30px;"
      arrow_pos = "left:  20px; top:  20px;"
      arr_off = [ 0, 10 ]
      vec = [ 0, pulseWidth ]
    } else if (direction == "down") {
      clazz = "arrow_down"
      text_pos = "top:  0px;"
      arrow_pos = "left:  20px; top:  40px;"
      arr_off = [ 0, -10 ]
      vec = [ 0, -pulseWidth ]
    } else if (direction == "left") {
      clazz = "arrow_left"
      text_pos = "left:  30px; top: -10px;"
      arrow_pos = "left:  0px; top:  0px;"
      arr_off = [ 10, -5 ]
      vec = [ pulseWidth, 0 ]
    } else if (direction == "right") {
      clazz = "arrow_right"
      text_pos = "float:  left;"
      arrow_pos = "float: right;"
      arr_off = [ -15, -5 ]
      vec = [ -pulseWidth, 0 ]
    }

    let div = $("<div class='absolute'><div class=" + clazz +
      " style='" + arrow_pos + "'></div><div style='" + text_pos +
      "position: relative; text-align: center;'>" + txt + "</div></div>");

    $("body").append(div);

    this.pos.collision = "none none"

    let arrowDiv = $(div).children('div')[0]
    let aPos = $(arrowDiv).position()

    let aPosOff : posArr = [ "left", - aPos.left + arr_off[0], "top", - aPos.top + arr_off[1] ]
    this.pos.my = _strPos(aPosOff)
    $(div).position(this.pos)
    this.pos.using = (css, dummy) => $(div).animate(css, pulse / 2);

    let ctr = 0;
    let lbl = this;
    
    this.timer = setInterval(function () {
      let v: posArr = (ctr % 2 == 0 ? aPosOff : [ aPosOff[0], aPosOff[1] + vec[0], aPosOff[2], aPosOff[3] + vec[1]])
      lbl.pos.my = _strPos(v);
      $(div).position(lbl.pos)
      ctr ++;
    }, this.pulse / 2)
    this.elem = div;
  }

  remove(): void {
    this.elem.remove();
    clearInterval(this.timer);
  }
}

function removeLabel(l: Label) {
  l.remove();
}

function label(arg: (JQueryUI.JQueryPositionOptions | HTMLElement),
  txt: string,
  direction: directionT,
  pulseWidth = 5,
  pulse = 500) {
  return new Label(arg, txt, direction, pulseWidth, pulse);
}

interface IStep {
  setup(cs: any): any;
}

class Script {
  step: number = -1;
  cancelCb: () => void = null;
  timeoutId: any;

  constructor(public steps: IStep[]) { this.nextStep(); }
  nextStep(): void {
    this.step++;
    this.cancelCb = null;
    this.steps[this.step].setup(this);
  }

  nextStepOnKeyClickOrTimeout(timeout: number,
    destructor: () => any,
    keyCode: number = null) {
    let s = this;
    if (timeout > 0) {
      this.timeoutId = setTimeout(function() {
        $("body").off("keyup");
        $("body").off("keypress");
        $("body").off("click");
        destructor();
        s.nextStep();
      }, timeout);
    }

    this.cancelCb = function() {
      if (timeout > 0)
        clearTimeout(s.timeoutId);
      $("body").off("keyup");
      $("body").off("keypress");
      $("body").off("click");
      destructor();
    };

    $("body").keypress(function(ev) {
      if (keyCode === null || ev.which === keyCode) {
        ev.stopPropagation();
        return false;
      }
    });

    $("body").keyup(function(ev) {
      if (keyCode === null || ev.which === keyCode) {
        if (timeout > 0)
          clearTimeout(s.timeoutId);
        $("body").off("keyup");
        $("body").off("keypress");
        $("body").off("click");
        destructor();
        s.nextStep();
        ev.stopPropagation();
        return false;
      }
    });

    $("body").click(function(ev) { 
      if (timeout > 0)
        clearTimeout(s.timeoutId);
      $("body").off("keyup");
      $("body").off("keypress");
      $("body").off("click");
      destructor();
      s.nextStep();
    });
    $("body").focus();
  }
  cancel(): void {
    if (this.cancelCb)
      this.cancelCb();

    this.step = this.steps.length + 1;
  }
}

/* In-place union - modifies s1 */
function union(s1: strset, s2: strset): strset {
  for (let e of s2) {
    s1.add(e);
  }
  return s1;
}

function setlen(s: strset): number {
  return s.size;
}

function forAll(boolL: boolean[]): boolean {
  return boolL.map(x => x ? 1 : 0).reduce((x, y) => x + y, 0) === boolL.length;
}

function zip<T1, T2>(a1: T1[], a2: T2[]): [T1, T2][] {
  return a1.map((_, i: number) => <[T1, T2]>[a1[i], a2[i]]);
}

class KillSwitch {
  pos: number = 0;
  onFlipCb: (i: number) => any = (i) => 0;
  container: JQuery;

  constructor(public parent: HTMLElement) {
    this.container = $("<div class='kill-switch' style='position: absolute;'></div>");
    let pOff = $(this.parent).offset();
    let pW = $(this.parent).width();
    das.position(this.container[0], {
      my: "right center",
      of: this.parent,
      at: "right-40 bottom"
    });
    $("body").append(this.container);

    let ks = this;
    this.container.click(function() {
      if (ks.pos === 0) {
        ks.pos = 1;
      } else {
        ks.pos = 0;
      }
      ks.refresh();
      ks.onFlipCb(ks.pos);
    });
    this.refresh();
  }

  onFlip(cb: (i: number) => any): void {
    this.onFlipCb = cb;
  }

  refresh(): void {
    if (this.pos === 0) {
      this.container.html("<img src='knife-up.gif' style='width: 30; height: 60px;'/>");
    } else {
      this.container.html("<img src='knife-down.gif' style='width: 30; height: 60px;'/>");
    }
  }

  destroy(): void {
    this.container.remove();
    das.remove(this.container[0]);
  }

  flip(): void {
    this.container.click();
  }
}

class DynamicAttachments {
  objs: [HTMLElement, JQueryUI.JQueryPositionOptions][] = [];
  position(target: HTMLElement, spec: JQueryUI.JQueryPositionOptions) {
    for (let i in this.objs) {
      if (this.objs[i][0] === target) {
        this.objs[i][1] = spec;
        $(target).position(spec);
        return;
      }
    }
    this.objs.push([target, spec]);
    $(target).position(spec);
  }

  reflowAll(): void {
    for (let i in this.objs) {
      $(this.objs[i][0]).position(this.objs[i][1]);
    }
  }

  remove(elmt: HTMLElement): void {
    this.objs = this.objs.filter((item) => item[0] !== elmt);
  }
}

let das = new DynamicAttachments();

function disableBackspaceNav() {
  $(document).unbind("keydown").bind("keydown", function(event) {
    let doPrevent = false;
    if (event.keyCode === 8) {
      let d = event.srcElement || event.target;
      if (d.tagName.toUpperCase() === "INPUT") {
        let di = <HTMLInputElement>d;
        if (di.type.toUpperCase() === "TEXT" ||
          di.type.toUpperCase() === "PASSWORD" ||
          di.type.toUpperCase() === "FILE" ||
          di.type.toUpperCase() === "SEARCH" ||
          di.type.toUpperCase() === "EMAIL" ||
          di.type.toUpperCase() === "NUMBER" ||
          di.type.toUpperCase() === "DATE") {
          doPrevent = di.readOnly || di.disabled;
        } else {
          doPrevent = true;
        }
      } else if (d.tagName.toUpperCase() === "TEXTAREA") {
        let dta = <HTMLTextAreaElement>d;
        doPrevent = dta.readOnly || dta.disabled;
      } else {
        doPrevent = true;
      }

      if (doPrevent) {
        event.preventDefault();
      }
    }
  });
}

function shape_eq(o1: any, o2: any) {
  if (typeof(o1) != typeof(o2))
    return false;

  if (typeof(o1) == "number" || typeof(o1) == "boolean" || typeof(o1) == "string") {
    return o1 === o2
  }

  if (typeof(o1) == "object") {
    for (var i in o1) {
      if (!o1.hasOwnProperty(i))  continue;
      if (!o2.hasOwnProperty(i))  continue;
      if (!shape_eq(o1[i], o2[i]))  return false;
    }

    for (var i in o2) {
      if (o2.hasOwnProperty(i) && !o1.hasOwnProperty(i))  return false;
    }

    return true;
  }
  assert(false, "Unexpected objects being compared: " + o1 + " and " + o2);
}

function unique<T>(l:T[], id:(x:T)=>string): T[] {
  let dict: { [ key: string ] : T } = { }
  for (var x in l) {
    dict[id(l[x])] = l[x];
  }

  let res : T[] = [];

  for (var key in dict) {
    if (!dict.hasOwnProperty(key))  continue;
    res.push(dict[key])
  }

  return res;
}

function isin<T>(needle:T, hay:T[], id:(x:T)=>string): boolean {
  let key = id(needle)
  for (var i in hay) {
    if (id(hay[i]) == key)
      return true;
  }

  return false;
}

function min(...args: number[]): number {
  let min = args[0];
  for (var i in args)
    if (args[i] < min) {
      min = args[i];
    }
  return min
}

function queryAppend(qStr: string, append: string): string {
  if (qStr == "") {
    qStr += "?";
  } else {
    qStr += "&";
  }
  return qStr + append;
}
