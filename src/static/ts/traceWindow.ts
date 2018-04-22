import {das, assert} from "./util";
import {Level} from "./level";
import {invPP} from "./pp"
import {dataT, resDataT, resClearT, resT} from "./types"


export interface ITracesWindow {
  immediateError(msg: string): void;
  delayedError(msg: string): void;
  immediateMsg(msg: string): void;
  clearError(): void;

  error(msg: string): void;
  msg(msg: string): void;

  setVariables(lvl: Level): void;
  addData(data: dataT): void;

  curExp(): string;
  setExp(exp: string): void;

  onChanged(cb: () => void): void;
  onCommit(cb: () => void): void;
  evalResult(res: resT): void;

  enable(): void;
  disable(): void;
  enableSubmit(): void;
  disableSubmit():  void;
}

export abstract class BaseTracesWindow implements ITracesWindow {
  ppInv: string = "";
  okToSubmit: boolean = false;
  data: dataT = [ [], [], [] ];
  dataMap:  [ any[], any[], any[] ] = [ [], [], [] ];
  errorTimer: number;

  changedCb: () => void;
  commitCb: () => void;
  moreExCb: (typ: string) => void;

  constructor (public parent: HTMLElement) {
    $(this.parent).addClass("positioned");
    $(this.parent).addClass("box");
    $(this.parent).addClass("tracesWindow");
  }

  immediateError(msg: string): void {
    $("th #errormsg").html("<div class='error'> " + msg + "</div>");
    this.reflowCb();
  }

  delayedError(msg: string, errorDelay: number= 2000) {
    let traceW = this;
    this.errorTimer = setTimeout(() => traceW.immediateError(msg), errorDelay);
  }

  immediateMsg(msg: string): void {
    $("th #errormsg").html("<div class='msg'> " + msg + "</div>");
    this.reflowCb();
  }

  clearError() {
    if (this.errorTimer) {
      window.clearTimeout(this.errorTimer);
      this.errorTimer = null;
    }
    this.immediateError("&nbsp");
  }

  error(msg: string): void { this.immediateError(msg); }
  msg(msg: string): void { this.immediateMsg(msg); }

  setVariables(lvl: Level): void {
    let hstr = "<table id='lvl_table' class='table table-stripped'><thead><tr>";
    for (let i in lvl.variables) {
      hstr += "<th>" + lvl.variables[i] + "</th>";
    }
    hstr += '<th><input id="formula-entry" tabindex="-1" type="text"><span id="errormsg"><div>&nbsp;</div></span></th>';
    hstr += '</tr></thead><tbody></tbody></table>';
    $(this.parent).html(hstr)
    $('#formula-entry').focus();
    var tW = this;
    $('#formula-entry').keyup(function (keyEv) {
      let curInv = invPP(tW.curExp())
      if (keyEv.keyCode == 13 && tW.okToSubmit) {
        tW.commitCb();
      } else if (curInv !== tW.ppInv) {
        tW.ppInv = curInv;
        tW.changedCb();
      }
    });

    this.dataMap = [[], [], []];
    this.data = [[], [], []];
    das.reflowAll();
  }

  abstract addData(data: dataT): void;
  abstract evalResult(res: resT): void;

  curExp(): string {
   let v = $("#formula-entry").val();
   return (v === undefined ? "" : v);
  }

  setExp(exp: string) {
    $("#formula-entry").val(exp);
    this.changedCb();
  }

  onChanged(cb: () => void) { this.changedCb = cb; }

  onCommit (cb: () => void) { this.commitCb = cb; }

  onMoreExamples(cb: () => void) { this.moreExCb = cb; }

  enableSubmit(): void { this.okToSubmit = true; }

  disableSubmit(): void { this.okToSubmit = false; }

  disable(): void { $("#formula-entry").attr("disabled", "disabled"); }

  enable(): void { $("#formula-entry").removeAttr("disabled"); }

  highlightRect(x: number, y: number, w: number, h:number, border_style: string, backgroud_style: string) {
    for (let i = x; i < x+w; i++) {
      $("#" + y + "_" + i).css('border-top', border_style);
      $("#" + (y+h-1) + "_" + i).css('border-bottom', border_style);
    }
    for (let j = y; j < y+h; j++) {
      $("#" + j + "_" + x).css('border-left', border_style);
      $("#" + j + "_" + (x+w-1)).css('border-right', border_style);
    }
    for (let i = x; i < x+w; i++) {
      for (let j = y; j < y+h; j++) {
        $("#" + j + "_"+ i).css('background-color', backgroud_style);
      }
    }
  }

  clearRect(x: number, y: number, w: number, h:number) {
    this.highlightRect(x, y, w, h, "", "");
  }

  private reflowCb(): void { das.reflowAll(); }

  protected setResultCell(row: JQuery, datum: any): void {
    let cell = row.children('.temp_expr_eval')
    if (typeof(datum) != 'number' || (!isNaN(datum)) && datum !== Infinity && datum !== -Infinity) {
      cell.html(JSON.stringify(datum))
    } else {
      // TODO: Hack - assuming all NaNs come from division by 0
      cell.html("<span class='error'>Error! Did you divide by 0? Try * instead?</span>")
    }
    cell.removeClass('true false greyed')
    if (typeof(datum) == "boolean")
      cell.addClass(datum ? 'true' : 'false')
  }

  protected greyRow(row: JQuery): void {
    $(row).children("td")
      .html("&nbsp")
      .removeClass("true false")
      .addClass("greyed");
  }

  protected ungreyRow(row: JQuery, data: any, type: string): void {
    let dataCols = $(row).children("td").not(".temp_expr_eval");
    dataCols.each(function (i) {
      $(this).html(data[i]).removeClass("greyed true false").addClass(type);
    });

    $(row).children(".temp_expr_eval")
      .removeClass("greyed true false");
  }
}

export class PositiveTracesWindow extends BaseTracesWindow {
  addData(data: dataT): void {
    // For now support a single inductive counterexample
    assert (data[1].length === 0 && data[2].length === 0);
    let classes = [ "true", "false", "inductive" ];
    let id = $("table#lvl_table tr.traces-row").length;
    let lbls = [];

    for (let i in data[0]) {
      let data_id = this.data[0].length;
      let col_id = 0;
      let curRow = $(
          "<tr class='traces-row' id='" + id + "'>" +
            data[0][i].map(el =>
              "<td class='" + classes[0]  + "' id='" + id + "_" + col_id++ + "'>" + el + "</td>").join("") +
            "<td class='temp_expr_eval'>&nbsp</td>" +
          "</tr>");
      this.data[0].push(data[0][i]);
      $("table#lvl_table tbody").append(curRow);
      this.dataMap[0][data_id] = curRow;
      id ++;
    }
    das.reflowAll();
  }

  evalResult(res: resT): void {
    if (res.hasOwnProperty("data")) {
      let resD = <resDataT>res;

      for (let type in resD.data) {
        for (let i in resD.data[type]) {
          let datum = resD.data[type][i];
          let row = this.dataMap[type][i];
          this.setResultCell(row, datum);
        }
      }
    } else if (res.hasOwnProperty("clear")) {
      $(".temp_expr_eval").html("");
      $(".traces-row td.temp_expr_eval").removeClass("true");
      $(".traces-row td.temp_expr_eval").removeClass("false");
    }
    das.reflowAll();
  }
}

class TwoPlayerTracesWindow extends BaseTracesWindow {
  player: number;

  constructor (public playerNum: number, public parent: HTMLElement) {
    super(parent);
    this.player = playerNum;

    $(this.parent).removeClass("tracesWindow");

    if (this.player === 1) {
      $(this.parent).addClass("tracesWindow1");
    }
    else if (this.player === 2) {
      $(this.parent).addClass("tracesWindow2");
    }
  }

  getPlayer(): number {
    return this.player;
  }

  changed(cb) {
    this.changedCb = cb;
  }

  commit(cb) {
    this.commitCb = cb;
  }

  setVariables(lvl: Level): void {
    let hstr = "<table id='lvl_table" + this.player + "' class='table table-stripped'><thead><tr>";
    for (let i in lvl.variables) {
      hstr += "<th>" + lvl.variables[i] + "</th>";
    }
    if (this.player === 1) {
      hstr += "<th><input id='formula-entry' type='text'><span id='errormsg'>&nbsp</span></th>";
    }
    else if (this.player === 2) {
      hstr += "<th><input id='formula-entry2' type='text'><span id='errormsg'>&nbsp</span></th>";
    }

    hstr += "</tr></thead><tbody></tbody></table>";
    $(this.parent).html(hstr);

    if (this.player === 1) {
      $("#formula-entry").focus();
      let tW = this;
      $("#formula-entry").keyup(function (keyEv) {
        let curInv = invPP(tW.curExp());
        if (keyEv.keyCode === 13 && tW.okToSubmit) {
          tW.commitCb();
          $("#formula-entry").blur();
          setTimeout(function() {$("#btn-switch").click(); }, 2000);
          $("#formula-entry2").focus();
        } else if (curInv !== tW.ppInv) {
          tW.ppInv = curInv;
          tW.changedCb();
        }
      });
    }
    else if (this.player === 2) {
      $("#formula-entry2").focus();
      let tW = this;
      $("#formula-entry2").keyup(function (keyEv) {
        let curInv = invPP(tW.curExp());
        if (keyEv.keyCode === 13 && tW.okToSubmit) {
          tW.commitCb();
          $("#formula-entry2").blur();
          setTimeout(function() {$("#btn-switch2").click(); }, 2000);
          $("#formula-entry").focus();
        } else if (curInv !== tW.ppInv) {
          tW.ppInv = curInv;
          tW.changedCb();
        }
      });
    }

    this.dataMap = [[], [], []];
    this.data = [[], [], []];
    das.reflowAll();
  }

  addData(data: dataT) {
    assert (data[1].length === 0 && data[2].length === 0);
    let classes = [ "true", "false", "inductive" ];
    let id = $("table#lvl_table" + this.player + " tr.traces-row").length;
    let lbls = [];

    for (let i in data[0]) {
      let data_id = this.data[0].length;
      let curRow = $(
          "<tr class='traces-row' id='" + id + "'>" + // this.player + id???
            data[0][i].map(el =>
              "<td class='" + classes[0]  + "'>" + el + "</td>").join("") +
            "<td class='temp_expr_eval'>&nbsp</td>" +
          "</tr>");
      this.data[0].push(data[0][i]);
      $("table#lvl_table" + this.player + " tbody").append(curRow);
      this.dataMap[0][data_id] = curRow;
      id ++;
    }
    das.reflowAll();
  }

  evalResult(res: resT) {
    if (res.hasOwnProperty("data")) {
      let resD = <resDataT>res;

      for (let type in resD.data) {
        for (let i in resD.data[type]) {
          let datum = resD.data[type][i];
          let row = this.dataMap[type][i];
          this.setResultCell(row, datum);
        }
      }
    }
    else if (res.hasOwnProperty("clear")) {
      $(".temp_expr_eval").html("");
      $(".traces-row td.temp_expr_eval").removeClass("true");
      $(".traces-row td.temp_expr_eval").removeClass("false");
    }
    das.reflowAll();
  }

  curExp(): string {
    let v = null;
    if (this.player === 1) {
      v = $("#formula-entry").val();
    }
    else if (this.player === 2) {
      v = $("#formula-entry2").val();
    }
    return (v === undefined ? "" : v);
  }

  setExp(exp: string) {
    if (this.player === 1) {
      $("#formula-entry").val(exp);
    }
    else if (this.player === 2) {
      $("#formula-entry2").val(exp);
    }
    this.changedCb();
  }

  disable(): void {
    if (this.player === 1) {
      $("#formula-entry").attr("disabled", "disabled");
    }
    else if (this.player === 2) {
      $("#formula-entry2").attr("disabled", "disabled");
    }
  }

  enable(): void {
    if (this.player === 1) {
      $("#formula-entry").removeAttr("disabled");
    }
    else if (this.player === 2) {
      $("#formula-entry2").removeAttr("disabled");
    }
  }

}
