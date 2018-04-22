import {Args, disableBackspaceNav, Script, assert, queryAppend, label, removeLabel, log} from 'util';
import {StickyWindow} from 'stickyWindow';
import {CounterexGameLogic} from 'ctrexGameLogic';
import {RoundsGameLogic} from 'roundsGameLogic'
import {PatternGameLogic, curLvlSet, setCurLvlSet} from 'gameLogic'
import {invEval, evalResultBool} from 'eval'
import {BaseTracesWindow, PositiveTracesWindow} from "traceWindow";
import {ScoreWindow} from 'scoreWindow';
import {ProgressWindow} from 'progressWindow';
import {mturkId, rpc, logEvent} from 'rpc';
import {CounterexTracesWindow} from 'ctrexTracesWindow'
import {DynamicLevel} from 'level';

let traceW: BaseTracesWindow = null;
let stickyW: StickyWindow = null;
let scoreW: ScoreWindow = null;
let progW: ProgressWindow = null;

var mode = Args.get_mode();
var curLvl = null;
var curLvlId;
var curL = null;
var lvls = null;
var gameLogic = null;
var stepTimeout = 5000;
var curScript = null;
var numLvlPassed = 0;

disableBackspaceNav();

function loadTrace(res) {
if (res === null)
doneScreen(true)
else {
setCurLvlSet(res[0]);
let lvl = res[1];
curLvlId = lvl.id;
console.log("Just loaded " + curLvlSet() + "." + curLvlId);
gameLogic.loadLvl(lvl);
if (lvl.hint === null) {
  $("#hint-row").html("");
} else {
  if (lvl.hint.type == "plain") {
    $("#hint-row").html("<p class='lead'><b>" + lvl.hint + "</b></p>");
  } else if (lvl.hint.type == "post-assert") {
    var pos_res = invEval(lvl.hint.assert, lvl.variables, lvl.data[0])
    if (evalResultBool(pos_res)) {
      var holdsOnLast = pos_res[pos_res.length-1];
      var holdsOnAll = pos_res.reduce((acc,val)=> acc && val, true)

      if (holdsOnAll) {
	$("#hint-row").html("<p class='lead'><b>Hint: Check out: " +
	  lvl.hint.assert + 
	  "</b></p>");
	traceW.setExp(lvl.hint.assert);
      } else if (holdsOnLast) {
	$("#hint-row").html("<p class='lead'><b>Hint: " +
	  lvl.hint.assert + 
	  " holds for the last row. Can you change it to work for all rows?</b></p>");
	traceW.setExp(lvl.hint.assert);
      } else {
	// TODO
      }
    } else {
      // TODO
    }
  }
}
}
}

function loadNextTrace() {
if (mode == "rounds" && gameLogic.curLvl && !gameLogic.lvlSolvedF) {
gameLogic.curLvl.genNext(curLvlSet(),
    gameLogic.foundJSInv.map(function(x){ return x.canonForm}),
    loadTrace)
} else {
DynamicLevel.loadNext(loadTrace);
}
}

function nextLvl() {
  loadNextTrace()
}

function loadLvlSet(lvlset) {
  setCurLvlSet(lvlset);
  rpc.call('App.listData', [lvlset], function(res) {
    lvls = res;
    curLvl = -1;
    nextLvl();
  }, log)
}

function doneScreen(alldone) {
  let assignment_id = Args.get_assignment_id();
  if (assignment_id == "ASSIGNMENT_ID_NOT_AVAILABLE") {
    $("#done-screen").html("<h2 class='text-center'><b>You are previewing the HIT. To perform this HIT, please accept it.</b></h2>");
    $("#done-screen").fadeIn(1000);
    return;
  }
  if (assignment_id !== undefined) {
    let form_elem = document.getElementById("assignment-id-in-form");
    (form_elem as HTMLInputElement).value = assignment_id;
  }
  let turk_submit_to = Args.get_turk_submit_to();
  let form = document.getElementById("turk-form");
  if (turk_submit_to !== undefined) {
    (form as HTMLFormElement).action = turk_submit_to + "/mturk/externalSubmit";
  } else {
    (form as HTMLFormElement).action = "end.html";
  }
  
  function getSelected(category) {
    return $('#turk-form input[name=' + category + ']:checked')
  }
  
  $("#final-submit").click(function(evt) {
    $("label").removeClass("highlight")
    $('#turk-form-error').html("");
    var categories = ["fun", "challenging", "prog_experience", "math_experience"];
    var selected = $.map(categories, getSelected);
    var answered = $.map(selected, (s)=> s.length > 0);
    
    var missing = false;
    for (var i in answered) {
      if (!answered[i]) {
        $("label." + categories[i]).addClass("highlight")
        missing = true;
      }
    }
    
    if (missing) {
      $('#turk-form-error').html("Please answer the required questions (highlighted in red)");
      evt.preventDefault()
    }
  })
  let msg = "Good job! You finished " + numLvlPassed + " level(s)! Your score is: " + gameLogic.score  + "!";
  if (alldone) {
   msg = "There are no more levels to play at this moment.<br>" + msg
  }
  $("#done-screen").prepend("<h2 class='good text-center'>" + msg + "</h2>");
  logEvent("GameDone", [numLvlPassed]);
  
  $("#done-screen").fadeIn(1000);
  //$("#done-screen").click(function() {
  //  window.location.replace('survey.html' + window.location.search);
  //});
}

function labelRemover(lbl) {
return function () { removeLabel(lbl) }
}

var tutorialScript = [
{
setup: function (cs) {
	  curL = label($('#help_row').get()[0], "Help on operators or Replay Tutorials", "left")
	  $('body').focus();
	  cs.nextStepOnKeyClickOrTimeout(stepTimeout, labelRemover(curL), 32);
}
},
{
setup: function (cs) {
  curL = label($("#report_problem_row").get()[0],
    "If you notice a problem, click here to tell us", "up");
  $("body").focus();
  cs.nextStepOnKeyClickOrTimeout(stepTimeout, labelRemover(curL), 32);
}
},
{
setup: function (cs) {
  if (!$("#discovered-invariants-div .good-invariant").length)
    return;
  curL = label($("#discovered-invariants-div").get()[0],
    "You played this level before, so<br />" +
    "we included your expressions from<br />" +
    "last time. Try to find more!",
    "right");
  $("body").focus();
  cs.nextStepOnKeyClickOrTimeout(2 * stepTimeout, labelRemover(curL), 32);
}
},
{ setup: function (cs) {
	   $('#formula-entry').focus();
	   curScript = null;
       }
},
]

$(document).ready(function() {
console.log("About to start");
if (Args.get_assignment_id() == "ASSIGNMENT_ID_NOT_AVAILABLE") {
  let s = "This is just a preview of the HIT. The work you do here will have to be redone when you accept the HIT."
  $("#hit-preview-warning").html("<p class='lead'><b>" + s + "</b></p>");
}

let prog_div = $('#discovered-invariants-div').get()[0]
progW = new ProgressWindow(prog_div as HTMLDivElement);
scoreW = new ScoreWindow($('#score-div').get()[0]);
if (mode == "ctrex" || mode == "rounds") {
traceW = new CounterexTracesWindow($('#data-display').get()[0]);
} else {
traceW = new PositiveTracesWindow($('#data-display').get()[0]);
}
stickyW = new StickyWindow($('#sticky').get()[0])
if (mode == "ctrex") {
gameLogic = new CounterexGameLogic(traceW, progW, scoreW, stickyW);
} else if (mode == "rounds") {
gameLogic = new RoundsGameLogic(traceW, progW, scoreW, stickyW);
} else {
gameLogic = new PatternGameLogic(traceW, progW, scoreW, stickyW);
}

gameLogic.onLvlPassed(function() {
numLvlPassed = numLvlPassed + 1;
function plural(n,s) { return n == 1? s : s + "s" }
if (numLvlPassed >= 2) {
  let s = "You can continue or quit.<br>Each additional level you pass will give you a new $0.50 bonus!";
  $("#next-or-quit-additional-text").html("<h2>"+s+"</h2>");
  $("#quit-overlay").show();
} else {
  let left = 2 - numLvlPassed;
  let s = "Please try to finish at least " + left + plural(left," more level") + "!"
  $("#next-or-quit-additional-text").html("<h2>"+s+"</h2>")
  $("#quit-overlay").hide();
}
$("#next-or-quit-screen").fadeIn(1000);

});

$('#next-level-overlay').click(function() {
$("#next-or-quit-screen").fadeOut(1000);
nextLvl();
});

$('#help').click(function() {
$('#help-content').slideToggle(200);
})

var openEx = null;
function _openEx(idn) {
var el = $('#' + idn)[0]
if (openEx != null && openEx != el) {
  $(openEx).slideToggle(200, function () {
    $(el).slideToggle(200);
  })
  openEx = el;
} else if (openEx != null) {
  assert (openEx == el);
  $(openEx).slideToggle(200);
  openEx = null;
} else {
  assert (openEx == null);
  $(el).slideToggle(200);
  openEx = el;
}
}

var ops = [['#plus_op', 'plus_ex'],
	 ['#minus_op', 'minus_ex'],
	 ['#mul_op', 'mul_ex'],
	 ['#div_op', 'div_ex'],
	 ['#mod_op', 'mod_ex'],
	 ['#eq_op', 'eq_ex'],
	 ['#neq_op', 'neq_ex'],
	 ['#lt_op', 'lt_ex'],
	 ['#lte_op', 'lte_ex'],
	 ['#gt_op', 'gt_ex'],
	 ['#gte_op', 'gte_ex'],
	 ['#not_op', 'not_ex'],
	 ['#and_op', 'and_ex'],
	 ['#or_op', 'or_ex'],
	 //['#equiv_op', 'equiv_ex'],
]
if (!Args.get_noifs()) {
ops.push(['#impl_op', 'impl_ex'])
}
ops.push(['#tutorials', 'tutorials_info'])
for (var i in ops) {
$(ops[i][0]).click(function (lbl) {
  return function() {_openEx(lbl);}
}(ops[i][1]))
}

$('#see-conditional-tutorial-1, #see-conditional-tutorial-2').click(function() {
logEvent("SeeConditionalTutorial", []);
$('#tutorial-video').fadeIn(1000)
});
$('#tutorial-video-done').click(function() {
$('#tutorial-video').fadeOut(1000)
});
$('#replay-tutorial-all').click(function() {
logEvent("ReplayTutorialAll", []);
window.open('tutorial.html' + queryAppend(window.location.search, "tutorialAction=redo-all"),
	    '_blank').focus();
})
$('#replay-tutorial-cond-1, #replay-tutorial-cond-2').click(function() {
logEvent("ReplayTutorialConditional", []);
window.open('tutorial.html' + queryAppend(window.location.search, "tutorialAction=redo-cond"),
	    '_blank').focus();
})

if (Args.get_noifs()) {
$("#impl_op").hide();
$("#see-conditional-tutorial-1").hide();
$("#see-conditional-tutorial-2").hide();
$("#tutorial-video-done").hide();
$("#replay-tutorial-cond-1").hide();
$("#replay-tutorial-cond-2").hide();
$("#impl_ex").hide();
}

$('#quit').click(function () { doneScreen(false) });
$('#skip-to-next-lvl').click(function () {
$('#skip-to-next-lvl').prop("disable", true);
$('#skip-to-next-lvl').hide();
gameLogic.skipToNextLvl();
});
$('#quit-overlay').click(function() { doneScreen(false) });

$('#arrows').click(function() {
if (curScript == null) {
  curScript = new Script(tutorialScript);
}
})

$("#report_problem").click(function() {
$("#problem_form_error").hide();
$("#problem_input").val("");
$("#problem_screen").fadeIn(1000);
});

$("#problem_form").submit(function(e) {
e.preventDefault();
});

$("#problem_send").click(function() {
var errorMessage = $("#problem_form_error");
var desc = $("#problem_input").val();

if (desc === "") {
  errorMessage
    .text("Please enter a description of the problem.")
    .show();
  return;
}

rpc.call("App.reportProblem", [mturkId(), curLvlId, desc],
  function(res) {
    $("#problem_screen").fadeOut(1000);
  }, function() {
    errorMessage
      .text("An error occurred. Please try again.")
      .show();
  });
});

$("#problem_close").click(function() {
$("#problem_screen").fadeOut(1000);
$("#problem_input").val("");
});

nextLvl()

gameLogic.onLvlLoaded(function () {
curScript = new Script(tutorialScript)
//gameLogic.onLvlLoaded(function (){})
})

gameLogic.onUserInput(function () {
if (curScript) {
  curScript.cancel()
  curScript = null
}
if (gameLogic.foundJSInv.length >= 4) {
  $("#skip-to-next-lvl").show();
  $('#skip-to-next-lvl').prop("disable", false);
}
})
})

