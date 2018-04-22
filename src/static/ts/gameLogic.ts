type voidCb = ()=>void
type boolCb = (res: boolean)=>void
type invSoundnessResT = { ctrex: [ any[], any[], any[] ]}
type invariantT = ESTree.Node;
type templateT = [ invariantT, string[], string[] ]

declare var curLvlSet: string; // TODO: Remove hack
declare var progW: any;
declare var progW2: any;
declare var traceW: any;
declare var traceW2: any;
declare var allowBonus: boolean;

class UserInvariant {
  public rawInv: invariantT;
  public archetype: templateT;
  public id: string;
  public archetypeId: string;

  constructor(public rawUserInp: string,
              public rawJS: string,
              public canonForm: invariantT) {
    this.rawInv = esprima.parse(rawJS);
    this.archetype = generalizeInv(canonForm);
    this.archetypeId = esprimaToStr(this.archetype[0]);
    this.id = esprimaToStr(this.canonForm);
  }
}

interface IGameLogic {
  clear(): void;
  loadLvl(lvl: Level): void;

  userInput(commit: boolean): void;
  goalSatisfied(cb: (sat: boolean, feedback: any) => void): void;

  onUserInput(cb: (inv:string)=>void): void;
  onLvlPassed(cb: ()=>void): void;
  onLvlLoaded(cb: ()=>void): void;
  onCommit(cb: ()=>void): void;
  skipToNextLvl() : void; 
}

interface IDynGameLogic extends IGameLogic {
  clear(): void;
  loadLvl(lvl: Level): void;
  addData(data: dataT): void;
  invSound(inv: UserInvariant, cb: (sound: boolean, res:invSoundnessResT)=>void): void;

  userInput(commit: boolean): void;
  goalSatisfied(cb: (sat: boolean, feedback: any) => void): void;

  onUserInput(cb: (inv:string)=>void): void;
  onLvlPassed(cb: ()=>void): void;
  onLvlLoaded(cb: ()=>void): void;
  onCommit(cb: ()=>void): void;
}

abstract class BaseGameLogic implements IGameLogic {
  curLvl: Level = null;
  lvlPassedCb: voidCb = null;
  lvlLoadedCb: voidCb = null;
  userInputCb: (inv:string)=> void = null;
  commitCb: voidCb = null;
  pwupSuggestion: IPowerupSuggestion = null;
  score: number = 0;

  constructor(public tracesW: ITracesWindow,
    public progressW: IProgressWindow,
    public scoreW: ScoreWindow,
    public stickyW: StickyWindow) {
    this.clear();
    let gl = this;
    this.tracesW.onChanged(function() {
      gl.userInput(false);
    });

    this.tracesW.onCommit(function() {
      gl.tracesW.msg("Trying out...");
      gl.tracesW.disable();
      gl.userInput(true);
      gl.tracesW.enable();
      if (gl.commitCb)
        gl.commitCb();
    });

    this.onUserInput(() => { });
    this.onLvlLoaded(() => { });
    this.onLvlPassed(() => { });
    this.onUserInput((x) => { });
  }

  clear(): void {
    this.tracesW.clearError();
    this.progressW.clear();
    this.stickyW.clear();
    // Leave score intact - don't clear score window
    this.curLvl = null;
  }

  loadLvl(lvl: Level): void {
    this.clear();
    this.curLvl = lvl;
    this.tracesW.setVariables(lvl);
    this.tracesW.addData(lvl.data);
    this.pwupSuggestion.clear(lvl);
    this.setPowerups(this.pwupSuggestion.getPwups());
    if (this.lvlLoadedCb)
      this.lvlLoadedCb();
  }

  protected computeScore(inv: invariantT, s: number): number {
    let pwups = this.pwupSuggestion.getPwups();
    let hold = pwups.filter((pwup) => pwup.holds(inv));
    let newScore = hold.reduce((score, pwup) => pwup.transform(score), s);
    hold.forEach((pwup) => pwup.highlight(() => 0));
    return newScore;
  }

  protected setPowerups(new_pwups: IPowerup[]): void {
    let pwups = {};
    for (let i in new_pwups) {
      pwups[new_pwups[i].id] = new_pwups[i];
    }

    this.stickyW.setPowerups(new_pwups);
  }

  abstract userInput(commit: boolean): void
  abstract goalSatisfied(cb:(sat: boolean, feedback: any)=>void):void;
  onUserInput(cb: (inv: string)=>void): void { this.userInputCb = cb; };
  onLvlPassed(cb: ()=>void): void { this.lvlPassedCb = cb; };
  onLvlLoaded(cb: ()=>void): void { this.lvlLoadedCb = cb; };
  onCommit(cb: ()=>void): void { this.commitCb = cb; };
  skipToNextLvl() : void { }
}

class StaticGameLogic extends BaseGameLogic implements IGameLogic {
  foundJSInv: UserInvariant[] = [];
  lvlPassedF: boolean = false;

  constructor(public tracesW: ITracesWindow,
              public progressW: IProgressWindow,
              public scoreW: ScoreWindow,
              public stickyW: StickyWindow,
              numBonuses: number = 5) {
    super(tracesW, progressW, scoreW, stickyW);
    this.pwupSuggestion = new PowerupSuggestionFullHistory(numBonuses, "lfu");
  }

  clear(): void {
    super.clear();
    this.foundJSInv = [];
    this.lvlPassedF = false;
  }

  goalSatisfied(cb: (sat: boolean, feedback?: any) => void): void {
    let goal = this.curLvl.goal;
    if (goal == null) {
      cb(true)
    } else  if (goal.equivalent) {
      assert(goal.equivalent.length > 0);
      let eq_exp:(string[]|ESTree.Node[]) = goal.equivalent
      if (typeof(eq_exp[0]) == "string") {
        eq_exp = (<string[]>eq_exp).map(esprima.parse);
      }
      equivalentPairs(<ESTree.Node[]>eq_exp, this.foundJSInv.map((x)=>x.canonForm), function(pairs) {
        var numFound = 0;
        var equiv = []
        for (var i=0; i < pairs.length; i++) {
          if (-1 == $.inArray(pairs[i][0], equiv))
            equiv.push(pairs[i][0])
        }

        cb(equiv.length == goal.equivalent.length,
           { "equivalent": { "found": equiv.length , "total": goal.equivalent.length } })
      })
    } else if (goal.hasOwnProperty('atleast')) {
      cb(this.foundJSInv.length >= goal.atleast)
    } else if (goal.hasOwnProperty("none")) {
      cb(false)
    } else {
      error("Unknown goal " + JSON.stringify(goal));
    }
  }

  userInput(commit: boolean): void {
    this.tracesW.disableSubmit();
    this.tracesW.clearError();
    this.progressW.clearMarks();

    let inv = invPP(this.tracesW.curExp().trim());
    this.userInputCb(inv);

    let desugaredInv = invToJS(inv)
    let parsedInv:invariantT = null

    try {
      parsedInv = esprima.parse(desugaredInv);
    } catch (err) {
      this.tracesW.delayedError(inv + " is not a valid expression.");
      return;
    }

    if (inv.length === 0) {
      this.tracesW.evalResult({ clear: true });
      return;
    }

    var jsInv = esprimaToStr(parsedInv);

    try {
      let pos_res = invEval(parsedInv, this.curLvl.variables, this.curLvl.data[0]);
      let neg_res = invEval(parsedInv, this.curLvl.variables, this.curLvl.data[2]);
      let res: [any[], [any, any][], any[]] = [pos_res, [], neg_res];
      this.tracesW.evalResult({ data: res });

      if (!evalResultBool(res))
        return;

      simplify(jsInv, (simplInv: ESTree.Node) => { 
        let ui: UserInvariant = new UserInvariant(inv, jsInv, simplInv)

        let redundant = this.progressW.contains(ui.id)
        if (redundant) {
          this.progressW.markInvariant(ui.id, "duplicate")
          this.tracesW.immediateError("Duplicate Expression!")
          return
        }

        let all = pos_res.length + neg_res.length
        let hold = pos_res.filter(function (x) { return x; }).length +
                   neg_res.filter(function (x) { return !x; }).length 

        if (hold < all)
          this.tracesW.error("Holds for " + hold + "/" + all + " cases.")
        else {
          this.tracesW.enableSubmit();
          if (!commit) {
            this.tracesW.msg("<span class='good'>Press Enter...</span>");
            return;
          }

          let gl = this;
          isTautology(ui.canonForm, function(res) {
            if (res) {
              gl.tracesW.error("This is always true...")
              return
            }

            impliedBy(gl.foundJSInv.map(x=>x.canonForm), ui.canonForm, function (x: ESTree.Node[]) {
              if (x.length > 0) {
                gl.progressW.markInvariant(esprimaToStr(x[0]), "implies")
                gl.tracesW.immediateError("This is weaker than a found expression!")
              } else {
                var addScore = gl.computeScore(parsedInv, 1)

                gl.pwupSuggestion.invariantTried(parsedInv);
                setTimeout(() => gl.setPowerups(gl.pwupSuggestion.getPwups()), 1000); // TODO: Remove hack

                gl.score += addScore;
                gl.scoreW.add(addScore);
                gl.foundJSInv.push(ui)
                gl.progressW.addInvariant(ui.id, ui.rawInv);
                gl.tracesW.setExp("");
                if (!gl.lvlPassedF) {
                  gl.goalSatisfied((sat, feedback) => {
                    var lvl = gl.curLvl
                    if (sat) {
                      gl.lvlPassedF = true;
                      gl.lvlPassedCb();
                    }
                  });
                }
              }
            })
          })
        }
      })
    } catch (err) {
      this.tracesW.delayedError(<string>interpretError(err));
    }
  }
}

class PatternGameLogic extends BaseGameLogic {
  foundJSInv: UserInvariant[] = [];
  invMap: { [ id: string ] : UserInvariant } = {};
  lvlPassedF: boolean = false;
  lvlSolvedF: boolean = false;
  nonindInvs: UserInvariant[] = [];
  overfittedInvs: UserInvariant[] = [];
  soundInvs: UserInvariant[] = [];

  allData: { [ lvlid: string ] : dataT } = { };
  allNonind: { [ lvlid: string ] : invariantT[] } =  { };

  constructor(public tracesW: ITracesWindow,
              public progressW: IProgressWindow,
              public scoreW: ScoreWindow,
              public stickyW: StickyWindow) {
    super(tracesW, progressW, scoreW, stickyW);
    //this.pwupSuggestion = new PowerupSuggestionFullHistoryVariableMultipliers(3, "lfu");
    this.pwupSuggestion = new PowerupSuggestionAll();
  }

  clear(): void {
    super.clear();
    this.foundJSInv = [];
    this.invMap = {};
    this.soundInvs = [];
    this.overfittedInvs = [];
    this.nonindInvs = [];
    this.lvlPassedF = false;
  }

  protected computeScore(inv: invariantT, s: number): number {
    let pwups = this.pwupSuggestion.getPwups();
    let hold: IPowerup[] = pwups.filter((pwup)=> pwup.holds(inv))
    let newScore = hold.reduce((score, pwup) => pwup.transform(score), s)
    let pwupsActivated : [string, number][] = [];
    for (var i in hold) {
      pwupsActivated.push([hold[i].id, (<MultiplierPowerup>(hold[i])).mult]);
      if (i == ""+(hold.length - 1)) {
        /* After the last powerup is done highlighting,
         * recompute the powerups
         */
        hold[i].highlight(()=>{
          this.pwupSuggestion.invariantTried(inv);
          this.setPowerups(this.pwupSuggestion.getPwups());
        });
      } else {
        hold[i].highlight(()=>0);
      }
    }

    logEvent("PowerupsActivated", [curLvlSet, this.curLvl.id, inv, pwupsActivated]);

    if (hold.length == 0) {
      this.pwupSuggestion.invariantTried(inv);
    }
    return newScore;
  }

  goalSatisfied(cb:(sat: boolean, feedback: any)=>void):void {
    if (this.foundJSInv.length > 0) {
      tryAndVerify(curLvlSet, this.curLvl.id, this.foundJSInv.map((x)=>x.canonForm),
        ([overfitted, nonind, sound, post_ctrex]) => {
          if (sound.length > 0) {
            cb(post_ctrex.length == 0, [overfitted, nonind, sound, post_ctrex]);
          } else {
            cb(false, null);
          }
        })
    } else {
      cb(false, [ [], [], [] ]);
    }
  }

  userInput(commit: boolean): void {
    this.tracesW.disableSubmit();
    this.tracesW.clearError();
    this.progressW.clearMarks();

    let gl = this;
    let inv = invPP(this.tracesW.curExp().trim());
    let desugaredInv = invToJS(inv)
    var parsedInv: ESTree.Node = null;

    this.userInputCb(inv);

    if (inv.length == 0) {
      this.tracesW.evalResult({ clear: true })
      return;
    }

    try {
      parsedInv = esprima.parse(desugaredInv);
    } catch (err) {
      //this.tracesW.delayedError(inv + " is not a valid expression.");
      return;
    }

    parsedInv = fixVariableCase(parsedInv, this.curLvl.variables);

    let undefined_ids = difference(identifiers(parsedInv), toStrset(this.curLvl.variables));
    if (!isEmpty(undefined_ids)) {
      this.tracesW.delayedError(any_mem(undefined_ids) + " is not defined.");
      return;
    }

    let jsInv = esprimaToStr(parsedInv)

    try {
      if (jsInv.search("\\^") >= 0) {
        throw new ImmediateErrorException("UnsupportedError", "^ not supported. Try * instead.");
      }

      let pos_res = invEval(parsedInv, this.curLvl.variables, this.curLvl.data[0])
      let res: [any[], [any, any][], any[]] = [pos_res, [], [] ]
      this.tracesW.evalResult({ data: res })

      if (!evalResultBool(res))
        return;

      simplify(jsInv, (simplInv: ESTree.Node) => { 
        let ui: UserInvariant = new UserInvariant(inv, jsInv, simplInv)
        logEvent("TriedInvariant",
                 [curLvlSet,
                  gl.curLvl.id,
                  ui.rawUserInp,
                  ui.canonForm,
                  gl.curLvl.colSwap,
                  gl.curLvl.isReplay()]);

        let redundant = this.progressW.contains(ui.id)
        if (redundant) {
          this.progressW.markInvariant(ui.id, "duplicate")
          this.tracesW.immediateError("Duplicate Expression!")
          return
        }

        let all = pos_res.length
        let hold = pos_res.filter(function (x) { return x; }).length

        if (hold < all)
          this.tracesW.error("Holds for " + hold + "/" + all + " cases.")
        else {
          this.tracesW.enableSubmit();
          if (!commit) {
            this.tracesW.msg("<span class='good'>Press Enter...</span>");
            return;
          }

          isTautology(ui.rawInv, function(res) {
            if (res) {
              gl.tracesW.error("This is always true...")
              return
            }

            let allCandidates = gl.foundJSInv.map((x)=>x.canonForm);

            impliedBy(allCandidates, ui.canonForm, function (x: ESTree.Node[]) {
              if (x.length > 0) {
                gl.progressW.markInvariant(esprimaToStr(x[0]), "implies")
                gl.tracesW.immediateError("This is weaker than a found expression!")
              } else {
                var addScore = gl.computeScore(ui.rawInv, 1)
                gl.score += addScore;
                gl.scoreW.add(addScore);
                gl.foundJSInv.push(ui)
                gl.invMap[ui.id] = ui;
                gl.progressW.addInvariant(ui.id, ui.rawInv);
                if (gl.curLvl.hint && gl.curLvl.hint.type == "post-assert") {
                  gl.tracesW.setExp(gl.curLvl.hint.assert);
                } else {
                  gl.tracesW.setExp("");
                }
                logEvent("FoundInvariant",
                         [curLvlSet,
                          gl.curLvl.id,
                          ui.rawUserInp,
                          ui.canonForm,
                          gl.curLvl.colSwap,
                          gl.curLvl.isReplay()]);
                if (!gl.lvlPassedF) {
                  if (gl.foundJSInv.length >= 6) {
                    var coin = Math.random() > .5;

                    if (coin) {
                      gl.lvlPassedF = true;
                      gl.lvlSolvedF = false;
                      gl.lvlPassedCb();
                      logEvent("FinishLevel",
                               [curLvlSet,
                                gl.curLvl.id,
                                false,
                                gl.foundJSInv.map((x)=>x.rawUserInp),
                                gl.foundJSInv.map((x)=>x.canonForm),
                                gl.curLvl.colSwap,
                                gl.curLvl.isReplay()]);
                    }
                  } else {
                    /*
                     * There is a potential race between an earlier call to
                     * goalSatisfied and a later game finish due to 8 levels,
                     * that could result in 2 or more FinishLevel events for
                     * the same level.
                     */
                    var preCallCurLvl = gl.curLvl.id;
                    gl.goalSatisfied((sat, feedback) => {
                      gl.lvlSolvedF = sat;
                      if (!sat)
                        return;

                      /*
                       * Lets try and make sure at least late "gameFinished" events from
                       * previous levels don't impact next level.
                       */
                      if (preCallCurLvl != gl.curLvl.id)
                        return;

                      logEvent("FinishLevel",
                               [curLvlSet,
                                gl.curLvl.id,
                                sat,
                                gl.foundJSInv.map((x)=>x.rawUserInp),
                                gl.foundJSInv.map((x)=>x.canonForm),
                                gl.curLvl.colSwap,
                                gl.curLvl.isReplay()]);
                      gl.lvlPassedF = true;
                      gl.lvlPassedCb();
                    });
                  }
                }
              }
            })
          })
        }
      })
    } catch (err) {
      if (err instanceof ImmediateErrorException) {
        this.tracesW.immediateError(<string>interpretError(err))
      } else {
        this.tracesW.delayedError(<string>interpretError(err))
      }
    }
  }

  loadLvl(lvl: DynamicLevel): void {
    let loadedCb = this.lvlLoadedCb;
    this.lvlLoadedCb = null;
    super.loadLvl(lvl);

    if (!this.allData.hasOwnProperty(lvl.id)) {
      this.allData[lvl.id] = [ [], [], [] ];
    }

    this.allData[lvl.id][0]  = this.allData[lvl.id][0].concat(lvl.data[0])
    this.allData[lvl.id][1]  = this.allData[lvl.id][1].concat(lvl.data[1])
    this.allData[lvl.id][2]  = this.allData[lvl.id][2].concat(lvl.data[2])

    for (let [rawInv, canonInv] of lvl.startingInvs) {
      let jsInv = esprimaToStr(esprima.parse(invToJS(rawInv)));
      let ui = new UserInvariant(rawInv, jsInv, canonInv);
      this.foundJSInv.push(ui);
      this.invMap[ui.id] = ui;
      this.progressW.addInvariant(ui.id, ui.rawInv);
    }

    this.lvlLoadedCb = loadedCb;
    if (this.lvlLoadedCb)
      this.lvlLoadedCb();
    logEvent("StartLevel",
             [curLvlSet,
              this.curLvl.id,
              this.curLvl.colSwap,
              this.curLvl.isReplay()]);
  }

  skipToNextLvl() : void {
    logEvent("SkipToNextLevel",
             [curLvlSet,
              this.curLvl.id,
              this.curLvl.colSwap,
              this.curLvl.isReplay()]);
    logEvent("FinishLevel",
             [curLvlSet,
              this.curLvl.id,
              false,
              this.foundJSInv.map((x)=>x.rawUserInp),
              this.foundJSInv.map((x)=>x.canonForm),
              this.curLvl.colSwap,
              this.curLvl.isReplay()]);
    this.lvlPassedF = true;
    this.lvlPassedCb();
  }
}

abstract class TwoPlayerBaseGameLogic implements IGameLogic {
  curLvl: Level = null;
  lvlPassedCb: voidCb = null;
  lvlLoadedCb: voidCb = null;
  userInputCb: (inv: string) => void = null;
  commitCb: voidCb = null;
  pwupSuggestion: IPowerupSuggestion = null;
  score: number = 0;
  player: number = null;

  constructor(public playerNum: number,
    public tracesW: ITracesWindow,
    public progressW: IProgressWindow,
    public scoreW: TwoPlayerScoreWindow,
    public stickyW: TwoPlayerStickyWindow) {
    this.clear();
    this.player = playerNum;
    let gl = this;
    this.tracesW.onChanged(function() {
      gl.userInput(false);
    });

    this.tracesW.onCommit(function() {
      gl.tracesW.msg("Trying out...");
      gl.tracesW.disable();
      gl.userInput(true);
      gl.tracesW.enable();
    });

    this.onUserInput(() => { });
    this.onLvlLoaded(() => { });
    this.onLvlPassed(() => { });
    this.onUserInput((x) => { });
  }

  clear(): void {
    this.tracesW.clearError();
    this.progressW.clear();
    this.stickyW.clear();
    // Leave score intact - don't clear score window
    this.curLvl = null;
  }

  loadLvl(lvl: Level): void {
    this.clear();
    this.curLvl = lvl;
    this.tracesW.setVariables(lvl);
    this.tracesW.addData(lvl.data);
    this.pwupSuggestion.clear(lvl);
    this.setPowerups(this.pwupSuggestion.getPwups());
    if (this.lvlLoadedCb)
      this.lvlLoadedCb();
  }

  protected computeScore(inv: invariantT, s: number): number {
    let pwups = this.pwupSuggestion.getPwups();
    let hold = pwups.filter((pwup) => pwup.holds(inv));
    let newScore = hold.reduce((score, pwup) => pwup.transform(score), s);
    hold.forEach((pwup) => pwup.highlight(() => 0));
    return newScore;
  }

  protected setPowerups(new_pwups: IPowerup[]): void {
    let pwups = {};
    for (let i in new_pwups) {
      pwups[new_pwups[i].id] = new_pwups[i];
    }

    this.stickyW.setPowerups(new_pwups);
  }

  abstract userInput(commit: boolean): void
  abstract goalSatisfied(cb: (sat: boolean, feedback: any) => void): void;
  onUserInput(cb: (inv: string) => void): void { this.userInputCb = cb; };
  onLvlPassed(cb: () => void): void { this.lvlPassedCb = cb; };
  onLvlLoaded(cb: () => void): void { this.lvlLoadedCb = cb; };
  onCommit(cb: () => void): void { this.commitCb = cb; };
  skipToNextLvl() : void { }
}

class TwoPlayerGameLogic extends TwoPlayerBaseGameLogic implements IGameLogic {
  foundJSInv: string[] = [];
  foundInv: string[] = [];
  lvlPassedF: boolean = false;

  constructor(public playerNum: number,
    public tracesW: ITracesWindow,
    public progressW: IProgressWindow,
    public scoreW: TwoPlayerScoreWindow,
    public stickyW: TwoPlayerStickyWindow) {
    super(playerNum, tracesW, progressW, scoreW, stickyW);
    this.pwupSuggestion = new TwoPlayerPowerupSuggestionFullHistory(playerNum, 5, "lfu");
    // this.tracesW = tracesW;
  }

  clear(): void {
    super.clear();
    this.foundJSInv = [];
    this.foundInv = [];
    this.lvlPassedF = false;
  }

  showNext(lvl): boolean {
    let goal = lvl.goal;
    if (goal == null) {
      return true;
    }
    else if (goal.manual) {
      return true;
    }
    return false;
  }

  goalSatisfied(cb: (sat: boolean, feedback?: any) => void): void {
    let goal = this.curLvl.goal;

    let player1Invs: string[] = getAllPlayer1Inv();
    let player2Invs: string[] = getAllPlayer2Inv();

    let allInvs = player1Invs.concat(player2Invs);

    if (goal == null) {
      cb(true);
    } else if (goal.manual) {
      cb(false);
    } else if (goal.find) {
      let numFound = 0;
      for (let i = 0; i < goal.find.length; i++) {
        let found = false;
        for (let j = 0; j < goal.find[i].length; j++) {
          // check for the union of both players' invariants
          // if ($.inArray(goal.find[i][j], this.foundJSInv) !== -1) {
          if ($.inArray(goal.find[i][j], allInvs) !== -1) {
            found = true;
            break;
          }
        }

        if (found)
          numFound++;

      }

      cb(numFound === goal.find.length,
        { "find": { "found": numFound, "total": goal.find.length } });
    } else if (goal.equivalent) {
      // check for the union of both players' invariants
      // equivalentPairs(goal.equivalent, this.foundJSInv, function(pairs) {
      equivalentPairs(goal.equivalent.map(esprima.parse), allInvs.map(esprima.parse), function(pairs) {
        let numFound = 0;
        let equiv = [];
        for (let i = 0; i < pairs.length; i++) {
          if (-1 === $.inArray(pairs[i][0], equiv))
            equiv.push(pairs[i][0]);
        }

        cb(equiv.length === goal.equivalent.length,
          { "equivalent": { "found": equiv.length, "total": goal.equivalent.length } });
      });
    } else if (goal.max_score) {
      cb(true, { "max_score": { "found": this.foundJSInv.length } });
    } else if (goal.none) {
      cb(false);
    } else if (goal.hasOwnProperty("atleast")) {
      // check for the union of both players' invariants
      // cb(this.foundJSInv.length >= goal.atleast);
      cb(allInvs.length >= goal.atleast);
    } else {
      error("Unknown goal " + JSON.stringify(goal));
    }
  }

  userInput(commit: boolean): void {
    this.tracesW.disableSubmit();
    this.tracesW.clearError();
    this.progressW.clearMarks();

    traceW.clearError();
    traceW2.clearError();

    progW.clearMarks();
    progW2.clearMarks();

    let inv = invPP(this.tracesW.curExp().trim());
    let desugaredInv = invToJS(inv);
    let parsedInv: ESTree.Node = null;

    this.userInputCb(inv);

    try {
      parsedInv = esprima.parse(desugaredInv);
    } catch (err) {
      this.tracesW.delayedError(inv + " is not a valid expression.");
      return;
    }

    if (inv.length === 0) {
      this.tracesW.evalResult({ clear: true });
      return;
    }

    let jsInv = esprimaToStr(parsedInv)

    try {
      let doProceed = true;
      let pos_res = invEval(parsedInv, this.curLvl.variables, this.curLvl.data[0]);
      let res: [any[], [any, any][], any[]] = [pos_res, [], []];
      this.tracesW.evalResult({ data: res });

      if (!evalResultBool(res))
        return;

      let redundant = this.progressW.contains(inv);
      if (redundant) {
        this.progressW.markInvariant(inv, "duplicate");
        this.tracesW.immediateError("Duplicate Invariant!");
        doProceed = false;
        return;
      }


      if (this.player === 1) {
        if (progW2.contains(inv)) {
          progW2.markInvariant(inv, "duplicate");
          traceW.immediateError("Duplicate Invariant!");
          doProceed = false;
          return;
        }

        let player2Invs: string[] = getAllPlayer2Inv();

        if (player2Invs.length !== 0) {
          equivalentPairs([esprima.parse(jsInv)], player2Invs.map(esprima.parse), function(x: any) {
            if (x != null && typeof player2Invs[x] !== "undefined") {
              // console.log(jsInv + " <=> " + player2Invs[x]);
              progW2.markInvariant(player2Invs[x], "duplicate");
              traceW.immediateError("Duplicate Invariant!");
              traceW.disableSubmit();
              doProceed = false;
              return;
            }
            else {
              impliedBy(player2Invs.map(esprima.parse), esprima.parse(jsInv), function(x: any) {
                if (x !== null) {
                  // console.log(player2Invs[x] + " ==> " + jsInv);
                  progW2.markInvariant(player2Invs[x], "implies");
                  traceW.immediateError("Implied by opponent's invariant!");
                  traceW.disableSubmit();
                  doProceed = false;
                  return;
                }
              });
            }

          });
        }
      }

      else if (this.player === 2) {
        if (progW.contains(inv)) {
          progW.markInvariant(inv, "duplicate");
          traceW2.immediateError("Duplicate Invariant!");
          doProceed = false;
          return;
        }

        let player1Invs: string[] = getAllPlayer1Inv();

        if (player1Invs.length !== 0) {

          equivalentPairs([esprima.parse(jsInv)], player1Invs.map(esprima.parse), function(x) {
            if (x != null && typeof player1Invs[x] !== "undefined") {
              // console.log(jsInv + " <=> " + player1Invs[x]);
              progW.markInvariant(player1Invs[x], "duplicate");
              traceW2.immediateError("Duplicate Invariant!");
              traceW2.disableSubmit();
              doProceed = false;
              return;
            }

            else {
              impliedBy(player1Invs.map(esprima.parse), esprima.parse(jsInv), function(x: invariantT[]) {
                if (x !== null && x.length > 0) {
                  // console.log(player1Invs[x] + " ==> " + jsInv);
                  progW.markInvariant(esprimaToStr(x[0]), "implies");
                  traceW2.immediateError("Implied by opponent's invariant!");
                  traceW2.disableSubmit();
                  doProceed = false;
                  return;
                }
              });
            }
          });
        }
      }


      let all = pos_res.length;
      let hold = pos_res.filter(function(x) { return x; }).length;

      if (hold < all) {
        this.tracesW.error("Holds for " + hold + "/" + all + " cases.");
        doProceed = false;
      }
      else {
        let gl = this;
        isTautology(esprima.parse(jsInv), function(res) {
          if (res) {
            gl.tracesW.error("This is always true...");
            gl.tracesW.disableSubmit();
            doProceed = false;
            return;
          }

          let jsInvEs = esprima.parse(jsInv);

          impliedBy(gl.foundJSInv.map(esprima.parse), jsInvEs, function(invs: invariantT[]) {
            if (invs !== null && invs.length > 0) {
              var x: number = gl.foundJSInv.indexOf(esprimaToStr(invs[0]));
              gl.progressW.markInvariant(gl.foundInv[x], "implies");
              gl.tracesW.immediateError("Implied by existing invariant!");
              // console.log(gl.foundInv[x] + " ==> " + jsInv);
              doProceed = false;
            }
            else {
              if (doProceed === true) {
                gl.tracesW.enableSubmit();
                if (!commit) {
                  gl.tracesW.msg("Press Enter...");
                  return;
                }

                let addScore = gl.computeScore(jsInvEs, 1);

                gl.pwupSuggestion.invariantTried(jsInvEs);
                setTimeout(() => gl.setPowerups(gl.pwupSuggestion.getPwups()), 1000); // TODO: Remove hack

                gl.score += addScore;
                gl.scoreW.add(addScore);
                gl.foundInv.push(inv);
                gl.foundJSInv.push(jsInv);
                gl.progressW.addInvariant(inv, jsInvEs);
                gl.tracesW.setExp("");

                if (allowBonus) {
                  getBonus(this.player, function(pt) {
                    gl.scoreW.add(pt);
                  });
                }
              }

              if (!gl.lvlPassedF) {
                gl.goalSatisfied((sat, feedback) => {
                  let lvl = gl.curLvl;
                  if (sat) {
                    gl.lvlPassedF = true;
                    gl.lvlPassedCb();
                  }
                });
              }
            }
          });
        });
      }

    } catch (err) {
      this.tracesW.delayedError(<string>interpretError(err));
    }
  }
}

