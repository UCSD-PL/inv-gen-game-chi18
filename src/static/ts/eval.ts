var notDefRe = /(.*) is not defined/;
type VarValMapT = { [varName: string] : any };

class InvException extends Error{
  constructor(public name: string, public message: string) { super(message); }
}

class ImmediateErrorException extends InvException {
  constructor(public name: string, public message: string) { super(name, message); }
}

function interpretError(err: Error): (string|Error) {
  if (err.name === "ReferenceError") {
    if (err.message.match(notDefRe))
      return err.message.match(notDefRe)[1] + " is not defined.";
    else
      return "Not a valid expression."
  } else if (err.name == 'SyntaxError') {
    return "Not a valid expression."
  } else if (err.name == 'NOT_BOOL') {
    return "Expression should evaluate to true or false, not " + err.message + " for example."
  } else if (err.name == "UnsupportedError"
          || err.name == "IMPLICATION_TYPES"
          || err.name == "OPERATOR_TYPES") {
    return (<InvException>err).message;
  }

  return err;
}

function invToJS(inv: string): string {
  return inv.replace(/[^<>]=[^>]/g, function(v) { return v[0] + "==" + v[2]; })
            .replace(/=>/g, "->")
            .replace(/(.+)if(.+)/g, "($2) -> ($1)")
            //.replace(/if(.+)then(.+)/g, "($1) -> ($2)")
}

function holds(inv:invariantT, variables: string[], data: any[][]): boolean {
  let res = invEval(inv, variables, data);
  return evalResultBool(res) &&
         res.filter((x)=>!(x === true)).length == 0;
}

function check_implication(arg1: any, arg2: any) {
  if (typeof(arg1) != "boolean" || typeof(arg2) != "boolean") {
    throw new InvException("IMPLICATION_TYPES", "Implication expects 2 booleans, not " + arg1 + " and " + arg2);
  }

  return (!(<boolean>arg1) || (<boolean>arg2));
}

function check_boolean(arg: any, op: string): boolean {
  if (typeof(arg) !== "boolean") {
    throw new InvException("OPERATOR_TYPES", op + " expects a boolean, not " +
      arg);
  }
  return true;
}

function check_number(arg: any, op: string): boolean {
  if (typeof(arg) !== "number") {
    throw new InvException("OPERATOR_TYPES", op + " expects a number, not " +
      arg);
  }
  return true;
}

function both_booleans(arg1: any, arg2: any, op: string): boolean {
  if (typeof(arg1) !== "boolean" || typeof(arg2) !== "boolean") {
    throw new InvException("OPERATOR_TYPES", op + " expects 2 booleans, not " +
      arg1 + " and " + arg2);
  }
  return true;
}

function both_numbers(arg1: any, arg2: any, op: string): boolean {
  if (typeof(arg1) !== "number" || typeof(arg2) !== "number") {
    throw new InvException("OPERATOR_TYPES", op + " expects 2 numbers, not " +
      arg1 + " and " + arg2);
  }
  return true;
}

function same_type(arg1: any, arg2: any, op: string): boolean {
  if (typeof(arg1) !== typeof(arg2)) {
    throw new InvException("OPERATOR_TYPES", op + " expects operands of the" +
      " same type, not " + arg1 + " and " + arg2);
  }
  return true;
}

function invEval(inv:invariantT, variables: string[], data: any[][]): any[] {
  // Sort variable names in order of decreasing length
  let vars: [string, number][] = variables.map(
    function(val, ind, _) { return <[string, number]>[val, ind]; });
  let holds_arr = [];

  // Do substitutions and eval
  for (var row in data) {
    let valMap = vars.reduce((m, el) => { m[el[0]] = data[row][el[1]]; return m; }, <VarValMapT>{})
    let instantiatedInv = instantiateVars(inv, valMap);
    holds_arr.push(eval(esprimaToEvalStr(instantiatedInv)));
  }
  return holds_arr;
}

function evalResultBool(evalResult: any[]): boolean {
  for (let i in evalResult) {
    if (evalResult[i] instanceof Array)
      return evalResultBool(evalResult[i]);
    if (typeof (evalResult[i]) !== "boolean")
      return false;
  }
  return true;
}

function estree_reduce<T>(t: ESTree.Node, cb: (n: ESTree.Node, args: T[]) => T): T {
  if (t.type === "Program") {
    let p = <ESTree.Program>t;
    let es = <ESTree.ExpressionStatement>p.body[0];
    return cb(t, [estree_reduce<T>(es.expression, cb)]);
  }

  if (t.type === "BinaryExpression") {
    let be = <ESTree.BinaryExpression>t;
    let lhs: T = estree_reduce(be.left, cb);
    let rhs: T = estree_reduce(be.right, cb);
    return cb(t, [lhs, rhs]);
  }

  if (t.type === "LogicalExpression") {
    let be = <ESTree.LogicalExpression>t;
    let lhs: T = estree_reduce(be.left, cb);
    let rhs: T = estree_reduce(be.right, cb);
    return cb(t, [lhs, rhs]);
  }

  if (t.type === "UnaryExpression") {
    let ue = <ESTree.UnaryExpression>t;
    let exp: T = estree_reduce(ue.argument, cb);
    return cb(t, [exp]);
  }

  if (t.type === "Literal") {
    return cb(t, []);
  }

  if (t.type === "Identifier") {
    return cb(t, []);
  }

  assert(false, "Shouldn't get here");
}

function identifiers(inv: (string|ESTree.Node)): strset {
  if (typeof (inv) === "string")
    return identifiers(esprima.parse(<string>inv));

  let t = <ESTree.Node> inv;

  return estree_reduce(t, (nd: ESTree.Node, args: strset[]) => {
    if (nd.type === "Program")
      return args[0];

    if (nd.type === "BinaryExpression" || nd.type === "LogicalExpression") {
      return union(args[0], args[1]);
    }

    if (nd.type === "UnaryExpression") {
      return args[0];
    }

    if (nd.type === "Identifier") {
      let r: strset = emptyStrset();
      r.add((<ESTree.Identifier>nd).name);
      return r;
    }

    return emptyStrset();
  });
}

function literals(inv: (string|ESTree.Node)): strset {
  if (typeof (inv) === "string")
    return literals(esprima.parse(<string>inv));

  return estree_reduce(<ESTree.Node>inv, (nd: ESTree.Node, args: strset[]) => {
    if (nd.type === "Program")
      return args[0];

    if (nd.type === "BinaryExpression" || nd.type === "LogicalExpression") {
      return union(args[0], args[1]);
    }

    if (nd.type === "UnaryExpression") {
      return args[0];
    }

    if (nd.type === "Literal") {
      let r: strset = emptyStrset();
      r.add(<string>(<ESTree.Literal>nd).value);
      return r;
    }

    return emptyStrset();
  });
}

function operators(inv: (string|ESTree.Node)): strset {
  if (typeof (inv) === "string")
    return operators(esprima.parse(<string>inv));

  return estree_reduce(<ESTree.Node>inv, (nd: ESTree.Node, args: strset[]) => {
    if (nd.type === "Program")
      return args[0];

    if (nd.type === "BinaryExpression" || nd.type === "LogicalExpression") {
      let be = <ESTree.BinaryExpression>nd;
      let p: strset = emptyStrset();
      p.add(be.operator);
      return union(union(p, args[0]), args[1]);
    }

    if (nd.type === "UnaryExpression") {
      let ue = <ESTree.UnaryExpression>nd;
      let p: strset = emptyStrset();
      p.add(ue.operator);
      return union(p, args[0]);
    }

    return emptyStrset();
  });
}

function replace(inv: (string|ESTree.Node), replF): ESTree.Node {
  if (typeof (inv) === "string")
    return replace(esprima.parse(<string>inv), replF);

  return estree_reduce(<ESTree.Node>inv, (nd: ESTree.Node, args: ESTree.Node[]): ESTree.Node => {
    if (nd.type === "Program") {
      let p = <ESTree.Program>nd;
      let es = <ESTree.ExpressionStatement>p.body[0];
      return <ESTree.Program>{
        "type": "Program",
        "body": [<ESTree.ExpressionStatement>{
          "type": "ExpressionStatement",
          "expression": replace(es.expression, replF)
        }],
        "sourceType": "dummy"
      };
    }

    if (nd.type === "BinaryExpression") {
      let be = <ESTree.BinaryExpression>nd;
      return replF(<ESTree.BinaryExpression>{ "type": "BinaryExpression",
                     "operator": be.operator,
                     "left": args[0],
                     "right": args[1],
                  })
    }

    if (nd.type === "LogicalExpression") {
      let le = <ESTree.LogicalExpression>nd;
      return replF(<ESTree.LogicalExpression>{
        "type": "LogicalExpression",
        "operator": le.operator,
        "left": args[0],
        "right": args[1],
      });
    }

    if (nd.type === "UnaryExpression") {
      let ue = <ESTree.UnaryExpression>nd;
      return replF(<ESTree.UnaryExpression>{
        "type": "UnaryExpression",
        "operator": ue.operator,
        "argument": args[0],
      });
    }

    if (nd.type === "Literal" || nd.type === "Identifier") {
      return replF(nd);
    }
  });
}

function instantiateVars(inv:invariantT, vals: VarValMapT): invariantT {
  return replace(inv, (node) => {
    if (node.type == "Identifier") {
      let val: number = vals[node.name];
      return { type: "Literal", raw: "" + val, value: val }
    }

    return node
  })
}

function generalizeConsts(inv:string|ESTree.Node): [ESTree.Node, string[], string[]] {
  let symConsts: string[] = [];
  let newInv: ESTree.Node = replace(inv, (node) => {
    if (node.type == "Literal") {
      var newId = "a" + symConsts.length
      symConsts.push(newId)
      return { "type": "Identifier", "name": newId }
    }
    return node
  })
  return [ newInv, symConsts, [] ]
}

function generalizeInv(inv:string|ESTree.Node): [ESTree.Node, string[], string[]] {
  let symConsts: string[] = [];
  let symVars: string[] = [];
  let newInv: ESTree.Node = replace(inv, (node) => {
    if (node.type == "Literal") {
      var newId = "a" + symConsts.length
      symConsts.push(newId)
      return { "type": "Identifier", "name": newId }
    }

    if (node.type == "Identifier") {
      var newId = "x" + symVars.length
      symVars.push(newId)
      return { "type": "Identifier", "name": newId }
    }

    return node
  })
  return [ newInv, symConsts, symVars ]
}

function fixVariableCase(inv: ESTree.Node, vars: string[]): ESTree.Node {
  var stringM : { [lowerCaseVar:string] : string } = {};

  for (let v of vars)
    stringM[v.toLowerCase()] = v;

  return replace(inv, (node) => {
    if (node.type == "Identifier" && node.name.toLowerCase() in stringM) {
      return { "type": "Identifier", "name": stringM[node.name.toLowerCase()] };
    } else {
      return node;
    }
  });
}

function esprimaToStr(nd: ESTree.Node): string {
  return estree_reduce<string>(nd,  (nd: ESTree.Node, args: string[]): string => {
    if (nd.type == "Program") {
      return args[0]
    }

    if (nd.type == "BinaryExpression") {
      let be = <ESTree.BinaryExpression>nd;
      return "(" + args[0] + be.operator + args[1] + ")"
    }

    if (nd.type == "LogicalExpression") {
      let le = <ESTree.LogicalExpression>nd;
      return "(" + args[0] + le.operator + args[1] + ")"
    }

    if (nd.type == "UnaryExpression") {
      let ue = <ESTree.UnaryExpression>nd;
      let s = args[0]
      if (ue.operator == '-' && s[0] == '-')
        s = '(' + s + ')'
      return "(" + ue.operator + s + ")"
    }

    if (nd.type == "Literal") {
      return "" + (<ESTree.Literal>nd).value
    }

    if (nd.type == "Identifier") {
      return (<ESTree.Identifier>nd).name
    }
  })
}

let NUM_BINOPS = new Set(["+", "-", "*", "/", "%", "<", ">", "<=", ">="]);

function esprimaToEvalStr(nd: ESTree.Node): string {
  return estree_reduce<string>(nd,  (nd: ESTree.Node, args: string[]): string => {
    if (nd.type == "Program") {
      return args[0]
    }

    if (nd.type == "BinaryExpression") {
      let be = <ESTree.BinaryExpression>nd;
      var checker: String;
      if (NUM_BINOPS.has(be.operator))
        checker = "both_numbers";
      else
        checker = "same_type";
      return "(" + checker + "(" + args[0] + "," + args[1] + ",\"" +
        be.operator + "\")&&(" + args[0] + be.operator + args[1] + "))";
    }

    if (nd.type == "LogicalExpression") {
      let le = <ESTree.LogicalExpression>nd;
      if (le.operator == "->")
        return "check_implication(" + args[0] + "," + args[1] + ")";
      else
        return "(both_booleans(" + args[0] + "," + args[1] + ",\"" +
          le.operator + "\")&&(" + args[0] + le.operator + args[1] + "))";
    }

    if (nd.type == "UnaryExpression") {
      let ue = <ESTree.UnaryExpression>nd;
      if (ue.operator == "!")
        checker = "check_boolean";
      else
        checker = "check_number";
      return "(" + checker + "(" + args[0] + ",\"" + ue.operator + "\")&&(" +
        ue.operator + "(" + args[0] + ")))";
    }

    if (nd.type == "Literal") {
      return "(" + (<ESTree.Literal>nd).value + ")"
    }

    if (nd.type == "Identifier") {
      return (<ESTree.Identifier>nd).name
    }
  })
}
