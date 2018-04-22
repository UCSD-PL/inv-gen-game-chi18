from slimit.parser import Parser
from slimit.visitors.nodevisitor import ASTVisitor
from slimit.visitors import nodevisitor
from slimit import ast as jsast
from lib.boogie.ast import AstUnExpr, AstBinExpr, AstId, AstTrue, \
        AstFalse, AstNumber, normalize
from lib.boogie.z3_embed import Int, And, Or, Not, Implies, BoolVal, IntVal

def addAllIntEnv(inv, env = None):
  if (env == None):
    env = {}
  p = Parser()
  t = p.parse(inv)

  for node in nodevisitor.visit(t):
    if isinstance(node, jsast.Identifier):
      env[node.value] = Int

  return env

def invJSToZ3(inv, typeEnv):
  p = Parser()
  t = p.parse(inv)

  assert(isinstance(t, jsast.Program))
  assert(len(t.children()) == 1)
  assert(isinstance(t.children()[0], jsast.ExprStatement))
  return jsToZ3Expr(t.children()[0].expr, typeEnv)

def jsNumToZ3(strN):
  try:
    intV = int(strN)
    return IntVal(intV)
  except Exception:
    raise Exception("Dont' currently support floats");

def jsToZ3Expr(astn, typeEnv):
  if (isinstance(astn, jsast.BinOp)):
    ln,rn = [jsToZ3Expr(x, typeEnv) for x in astn.children()]

    try:
      return {
        '&&': And,
        '||': Or,
        '==': lambda x,y: x == y,
        '!=': lambda x,y: x != y,
        '<': lambda x,y: x < y,
        '>': lambda x,y: x > y,
        '<=': lambda x,y: x <= y,
        '>=': lambda x,y: x >= y,
        '+': lambda x,y: x + y,
        '-': lambda x,y: x - y,
        '*': lambda x,y: x * y,
        '/': lambda x,y: x / y,
        '%': lambda x,y: x % y,
      }[astn.op](ln, rn)
    except KeyError:
      raise Exception("Don't know how to parse " + astn.to_ecma())
  elif (isinstance(astn, jsast.Identifier)):
    name = astn.value
    return typeEnv[name](name);
  if (isinstance(astn, jsast.Number)):
    return jsNumToZ3(astn.value)
  else:
    raise Exception("Don't know how to parse " + astn.to_ecma())

def esprimaToZ3Expr(astn, typeEnv):
  if (astn["type"] == "UnaryExpression"):
    arg = esprimaToZ3Expr(astn["argument"], typeEnv)
    try:
      if (astn["operator"] == "+"):
        return arg;
      return {
        '-': lambda x:  -x,
        '!': Not
      }[astn["operator"]](arg)
    except KeyError:
      raise Exception("Unknown unary expression " + str(astn))
  elif (astn["type"] == "BinaryExpression"):
    ln = esprimaToZ3Expr(astn["left"], typeEnv)
    rn = esprimaToZ3Expr(astn["right"], typeEnv)

    try:
      return {
        '==': lambda x,y: x == y,
        '!==': lambda x,y: x != y,
        '<': lambda x,y: x < y,
        '>': lambda x,y: x > y,
        '<=': lambda x,y: x <= y,
        '>=': lambda x,y: x >= y,
        '+': lambda x,y: x + y,
        '-': lambda x,y: x - y,
        '*': lambda x,y: x * y,
        '/': lambda x,y: x / y,
        '%': lambda x,y: x % y,
      }[astn["operator"]](ln, rn)
    except KeyError:
      raise Exception("Unkown binary expression " + str(astn))
  elif (astn["type"] == "LogicalExpression"):
    ln = esprimaToZ3Expr(astn["left"], typeEnv)
    rn = esprimaToZ3Expr(astn["right"], typeEnv)
    try:
      return {
        '&&': And,
        '||': Or,
        '->': Implies,
      }[astn["operator"]](ln, rn)
    except KeyError:
      raise Exception("Unkown logical expression " + str(astn))
  elif (astn["type"] == "Identifier"):
    return Int(astn["name"]);
  if (astn["type"] == "Literal"):
    if (astn["raw"] in ["true", "false"]):
      return BoolVal(True) if (astn["raw"] == "true") else BoolVal(False);
    else:
      return jsNumToZ3(astn["raw"])
  else:
    raise Exception("Don't know how to parse " + str(astn))

def _esprimaToBoogieExprAst(astn, typeEnv):
  if (astn["type"] == "UnaryExpression"):
    arg = _esprimaToBoogieExprAst(astn["argument"], typeEnv)
    try:
      if (astn["operator"] == "+"):
        return arg;

      return AstUnExpr({
        '-': '-',
        '!': '!'
      }[astn['operator']], arg)
    except KeyError:
      raise Exception("Unknown unary expression " + str(astn))
  elif (astn["type"] == "BinaryExpression"):
    ln = _esprimaToBoogieExprAst(astn["left"], typeEnv)
    rn = _esprimaToBoogieExprAst(astn["right"], typeEnv)

    try:
      op = {
        '==': '==',
        '!=': '!=',
        '!==': '!=',
        '<': '<',
        '>': '>',
        '<=': '<=',
        '>=': '>=',
        '+': '+',
        '-': '-',
        '*': '*',
        '/': 'div',
        '%': 'mod',
      }
      return AstBinExpr(ln, op[astn['operator']], rn)
    except KeyError:
      raise Exception("Unkown binary expression " + str(astn))
  elif (astn["type"] == "LogicalExpression"):
    ln,rn = _esprimaToBoogieExprAst(astn["left"], typeEnv), \
            _esprimaToBoogieExprAst(astn["right"], typeEnv)

    try:
      op = {
        '&&': '&&',
        '||': '||',
        '->': '==>',
      }
      return AstBinExpr(ln, op[astn['operator']], rn)
    except KeyError:
      raise Exception("Unkown logical expression " + str(astn))
  elif (astn["type"] == "Identifier"):
    return AstId(astn["name"]);
  if (astn["type"] == "Literal"):
    if (astn["raw"] in ["true", "false"]):
      return AstTrue() if astn["raw"] == "true" else AstFalse()
    else:
      return AstNumber(int(astn["raw"]))
  else:
    raise Exception("Don't know how to parse " + str(astn))

def esprimaToBoogieExprAst(n, typeEnv):
  return normalize(_esprimaToBoogieExprAst(n, typeEnv))

def esprimaToZ3(inv, typeEnv):
  if (inv["type"] != "Program" or "body" not in inv or \
    len(inv["body"]) != 1 or
    inv["body"][0]["type"] != "ExpressionStatement" or \
    "expression" not in inv["body"][0]):
    raise Exception("Bad struct")
  return esprimaToZ3Expr(inv["body"][0]["expression"], typeEnv)

def esprimaToBoogie(inv, typeEnv):
  if (inv["type"] != "Program" or "body" not in inv or \
    len(inv["body"]) != 1 or
    inv["body"][0]["type"] != "ExpressionStatement" or \
    "expression" not in inv["body"][0]):
    raise Exception("Bad struct")
  return esprimaToBoogieExprAst(inv["body"][0]["expression"], typeEnv)

def boogieToEsprimaExpr(expr):
    if isinstance(expr, AstNumber):
        return { "type": "Literal", "value": expr.num, "raw": str(expr.num) }
    elif isinstance(expr, AstId):
        return { "type": "Identifier", "name": expr.name }
    elif isinstance(expr, AstTrue):
        return { "type": "Literal", "value": True, "raw": "true" }
    elif isinstance(expr, AstFalse):
        return { "type": "Literal", "value": False, "raw": "false" }
    elif isinstance(expr, AstUnExpr):
        espr_op = {
            '-':    '-',
            '!':    '!',
        }[expr.op]
        return { "type": "UnaryExpression",
                 "operator": espr_op,
                 "argument": boogieToEsprimaExpr(expr.expr) }
    elif isinstance(expr, AstBinExpr):
        lhs = boogieToEsprimaExpr(expr.lhs)
        rhs = boogieToEsprimaExpr(expr.rhs)

        # Hack to desugar implication to disjunction for esprima.
        if (expr.op == "==>"):
          return {"type": "LogicalExpression",
                  "operator": "||",\
                  "left": { "type": "UnaryExpression",
                            "operator": "!",
                            "argument": lhs },
                  "right": rhs }

        espr_op, typ = {
            '+':    ('+', 'BinaryExpression'),
            '-':    ('-', 'BinaryExpression'),
            '*':    ('*', 'BinaryExpression'),
            'div':  ('/', 'BinaryExpression'),
            'mod':  ('%', 'BinaryExpression'),
            '<':    ('<', 'BinaryExpression'),
            '>':    ('>', 'BinaryExpression'),
            '<=':    ('<=', 'BinaryExpression'),
            '>=':    ('>=', 'BinaryExpression'),
            '==':    ('==', 'BinaryExpression'),
            '!=':    ('!==', 'BinaryExpression'),
            '&&':    ('&&', 'LogicalExpression'),
            '||':    ('||', 'LogicalExpression'),
        }[expr.op]
        return { "type": typ, "operator": espr_op, "left": lhs, "right": rhs }
    else:
        raise Exception("Unknown expression " + str(expr))

def boogieToEsprima(inv):
  return { "type":"Program",
           "sourceType": "script",
           "body": [ { "type": "ExpressionStatement",
                       "expression": boogieToEsprimaExpr(inv) } ] }

if __name__ == "__main__":
  tmpP = Parser()
  tmpT = tmpP.parse("  i == 4 && b == 44")
  print invJSToZ3("i == 4", { "i" : Int })
  print invJSToZ3("  i == 4 && b == 44", { "i" : Int, "b" : Int })
