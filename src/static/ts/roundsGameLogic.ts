class RoundsGameLogic extends BaseGameLogic {
  foundJSInv: UserInvariant[] = [];
  invMap: { [ id: string ] : UserInvariant } = {};
  lvlPassedF: boolean = false;
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
    let contains = (v, arr) => {
      for (let i in arr)
        if (arr[i] == v) {
          return true;
        }
      return false;
    };
    if (this.foundJSInv.length > 0) {
      var invToTry = this.foundJSInv.filter((ui)=>!contains(ui.id, this.overfittedInvs));
      tryAndVerify(curLvlSet, this.curLvl.id, invToTry.map((x)=>x.canonForm),
        ([overfitted, nonind, sound, post_ctrex, direct_ctrex]) => {
          if (sound.length > 0) {
            cb(post_ctrex.length == 0, [overfitted, nonind, sound, post_ctrex, direct_ctrex]);
          } else {
            cb(false, [overfitted, nonind, sound, post_ctrex, direct_ctrex]);
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
      let neg_res = invEval(parsedInv, this.curLvl.variables, this.curLvl.data[2])
      let res: [any[], [any, any][], any[]]= [pos_res, [], neg_res ]
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

                /*
                 * Clear the current negative rows
                 */
                //gl.curLvl.data[2] = [];
                //(<CounterexTracesWindow>gl.tracesW).clearNegRows();

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
                      var overfittedInvs = feedback[0].map((p)=>esprimaToStr(p[0]));
                      gl.overfittedInvs = gl.overfittedInvs.concat(overfittedInvs);

                      if (!sat) {
                        // Add any counterexamples
                        /*
                        var overfitted = feedback[0].map((p)=>p[1]);
                        var postctrex = feedback[4];
                        console.log(overfitted, postctrex);
                        gl.tracesW.addData([overfitted, [], postctrex]);
                        gl.curLvl.data[0] = gl.curLvl.data[0].concat(overfitted);
                        gl.curLvl.data[2] = gl.curLvl.data[2].concat(postctrex);
                        */
                        return;
                      }

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

  invSatisfiesPos(inv: UserInvariant, data: dataT): boolean {
    let pos_res = invEval(inv.rawInv, this.curLvl.variables, data[0])
    let hold = pos_res.filter(function (x) { return x; }).length
    return hold == pos_res.length;
  }

  loadLvl(lvl: DynamicLevel): void {
    let gl = this;
    let goodInvs = this.foundJSInv.filter((inv:UserInvariant) => gl.invSatisfiesPos(inv, lvl.data));

    let loadedCb = this.lvlLoadedCb;
    this.lvlLoadedCb = null;
    super.loadLvl(lvl);

    if (!this.allData.hasOwnProperty(lvl.id)) {
      this.allData[lvl.id] = [ [], [], [] ];
    }

    this.allData[lvl.id][0]  = this.allData[lvl.id][0].concat(lvl.data[0])
    this.allData[lvl.id][1]  = this.allData[lvl.id][1].concat(lvl.data[1])
    this.allData[lvl.id][2]  = this.allData[lvl.id][2].concat(lvl.data[2])

    /*
    for (var inv of goodInvs) {
      this.foundJSInv.push(inv)
      this.invMap[inv.id] = inv;
      this.progressW.addInvariant(inv.id, inv.rawInv);
    }
    */

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
