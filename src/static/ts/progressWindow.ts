import {invariantT} from "./types";
import {invToHTML} from "./pp";

export interface IProgressWindow {
  addInvariant(key: string, invariant: invariantT): void;
  removeInvariant(key: string): void;
  markInvariant(key: string, state: string): void;
  clearMarks(): void;
  clear(): void;
  contains(key: string):  boolean;
}

export class ProgressWindow implements IProgressWindow {
  invMap: { [ inv: string]: HTMLElement } = { };
  container: HTMLElement;
  ctr: number = 0;

  constructor(public parent:  HTMLDivElement) {
    $(this.parent).html("<div class='progressWindow box good centered positioned'>" +
                      "Accepted expressions<br>" +
                      "<ul id='good-invariants'></ul>" +
                   "</div>");
    this.container = $(this.parent).children("div")[0];
  };

  addInvariant(key: string, invariant: invariantT) : void {
    let invUl = $(this.container).children("#good-invariants")[0]
    $(invUl).append("<li class='good-invariant' id='good_" +
      this.ctr + "'>" + invToHTML(invariant) + "</li>")
    this.invMap[key] = $('#good_' + this.ctr)[0]
    this.ctr ++;
  }

  removeInvariant(key: string): void {
    $(this.invMap[key]).remove();
    delete this.invMap[key]
  }

  
  markInvariant(key: string, state: string): void {
    let invDiv = $(this.invMap[key]);

    if (invDiv == undefined) {
      console.log("Unknown invariant " + key);
      return
    }

      if (state === "checking") {
      } else if (state === "duplicate") {
        invDiv.addClass("error");
      } else if (state === "tautology") {
      } else if (state === "implies") {
        invDiv.addClass("error");
      } else if (state === "counterexampled") {
        invDiv.addClass("error");
      } else if (state === "ok") {
        invDiv.removeClass("error");
      }
  }

  clearMarks(): void {
    for (let i in this.invMap) {
      $(this.invMap[i]).removeClass("error");
    }
  }

  clear(): void {
    let invUL: HTMLElement = $(this.container).children("#good-invariants")[0];
    $(invUL).html("");
    this.invMap = {};
    this.ctr = 0;
  }

  contains(key: string):  boolean {
    return this.invMap.hasOwnProperty(key);
  }
}

class IgnoredInvProgressWindow extends ProgressWindow {
  ignoredContainer: HTMLElement;
  constructor(public parent:  HTMLDivElement) {
    super(parent);
    $(this.parent).html("<div class='progressWindow box good centered positioned'>" +
                      "Accepted expressions<br>" +
                      "<ul id='good-invariants'></ul>"+
                   "</div>" +
                   "<div class='ignoreWindow box warn centered positioned'>" +
                      "Ignored expressions<br>" +
                      "<ul id='ignored-invariants'></ul>" +
                   "</div>");
    this.container = $(this.parent).children("div")[0]
    this.ignoredContainer = $(this.parent).children("div")[1]
  };

  addIgnoredInvariant(key: string, inv: invariantT) {
    let invUL: HTMLElement = $(this.ignoredContainer).children("ul")[0]
    $(invUL).append("<li class='ignored-invariant' id='ign_" +
      this.ctr + "'>" + invToHTML(inv) + "</li>")
    this.invMap[key] = $('#ign_' + this.ctr)[0]
    this.ctr++;
  }

  clear(): void {
    super.clear();
    let invUL: HTMLElement = $(this.ignoredContainer).children("ul")[0]
    $(invUL).html('')
  }
}


class TwoPlayerProgressWindow extends ProgressWindow {
  player: number;

  constructor(public playerNum: number, public parent:  HTMLDivElement) {
    super(parent);
    this.player = playerNum;
    $(this.parent).html("");

    $(this.parent).addClass("box");
    $(this.parent).addClass("progressWindow");

    if (this.player === 1) {
      $(this.parent).html("<strong>Invariants</strong><br>" +
        "<ul id='good-invariants' style='font-family: monospace; list-style-type: none; padding: 0px; text-align: center;'></ul>");
    }
    else if (this.player === 2) {
      $(this.parent).html("<strong>Invariants</strong><br>" +
        "<ul id='good-invariants2' style='font-family: monospace; list-style-type: none; padding: 0px; text-align: center;'></ul>");
    }

    this.container = $(this.parent).children("div")[0];
  }

  addInvariant(key: string, invariant: invariantT): void {
    let invUl = null;

    if (this.player === 1) {
      // invUl = $(this.container).children("#good-invariants")[0];
      invUl = $("#good-invariants");
    }
    else if (this.player === 2) {
      // invUl = $(this.container).children("#good-invariants2")[0];
      invUl = $("#good-invariants2");
    }

    $(invUl).append("<li class='good-invariant' id='good_" + this.player +
      this.ctr + "'>" + invToHTML(invariant) + "</li>");

    this.invMap[key] = $("#good_" + this.player + this.ctr)[0];
    this.ctr ++;
  }

  markInvariant(key: string, state: string): void {
    let invDiv = $(this.invMap[key]);
    // let invDiv = $(this.invMap[invariant]);

    if (invDiv === undefined) {
      console.log("Unknown invariant " + key);
      return;
    }

      if (state === "checking") {
      } else if (state === "duplicate") {
        invDiv.addClass("bold");
      } else if (state === "tautology") {
      } else if (state === "implies") {
        invDiv.addClass("bold");
      } else if (state === "counterexampled") {
        invDiv.addClass("bold");
      } else if (state === "ok") {
        invDiv.removeClass("bold");
      }
  }

  clearMarks(): void {
    for (let i in this.invMap) {
      $(this.invMap[i]).removeClass("bold");
    }
  }

  clear(): void {
    let invUL = null;
    if (this.player === 1) {
      invUL = $("#good-invariants");
    }
    else if (this.player === 2) {
      invUL = $("#good-invariants2");
    }
    $(invUL).html("");
    this.invMap = {};
    this.ctr = 0;
  }
}
