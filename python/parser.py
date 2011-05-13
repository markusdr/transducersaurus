#!/usr/bin/python
import re

class Parser():

    def __init__( self, command ):
        self._grammar = re.compile(
             r"""\s*(?:
                (push(?:_[lt])? | rmeps | det(?:_[lt])? | min(?:_(?:[ws]*[lt]?) | (?:[lt]?[ws]*))? | \* | \.) | #Operators and operations
                ([HCLGT]) | #WFST components
                ([\)\(]) |  #Order of operations parens
                ([\[\]]) |  #Optional argument brackets
                (log|tropical|standard|trop|el|ew|weights|labels|symbols),? | #Optional bracket arguments
                (.) ) #Left overs
              """, re.X
            )
        self.wfsts = set([])
        self.postfix = self._toPostfix( command )

    def _opGTE( self, top, op ):
        """
           Determine operator precedence for the WFST operations 
           allowed in self._grammar.
        """
        prec = { 
            re.compile(r'^det(_(l|t))?$'):10, 
            re.compile(r'^min((_(l|t))|(_s)|(_w))*$'):10, 
            'rmeps':10,
            re.compile(r'^push(_(l|t))?$'):10, 
            '*':5, 
            '.':5,
            re.compile(r"^(log|tropical|standard|trop|el|ew|weights|labels|symbols)$"):2,
            }
        
        if op in prec:
            if prec[op]<=prec[top]:
                return True
            else:
                return False
        else:
            for key in prec:
                if not type(key)==str and key.match(op):
                    if prec[key]<=prec[top]:
                        return True
                    else:
                        return False
        return

    def _map_oargs( self, oargs ):
        """
           Process any optional arguments.
        """
        arg_map = {
            'log':'l',
            'tropical':'t',
            'standard':'t',
            'trop':'t',
            'el':'s',
            'ew':'w',
            'weights':'w',
            'labels':'s',
            'symbols':'s',
            's':'s',
            'w':'w'
            }
        mapped_oargs = set([])
        for arg in oargs:
            mapped_oargs.add(arg_map[arg])
        if "l" in mapped_oargs and "t" in mapped_oargs:
            raise SyntaxError, "Both 'log' AND 'tropical' semirings were specified.  Please pick just one!"
        return mapped_oargs

    def _merge( self, tok, oargs ):
        oargs = self._map_oargs( oargs )
        parts = tok.split("_")
        if len(parts)==2:
            oargs.update(list(parts[1]))
        return parts[0], "".join(oargs)

    def _toPostfix( self, program ):
        """
           Tokenize and convert an infix expression to postfix notation
           based on the regex grammar specified in self._grammar
        """
        lparen = re.compile(r"\(")
        rparen = re.compile(r"\)")
        if not len(lparen.findall(program))==len(rparen.findall(program)):
            raise SyntaxError, "Unbalanced parentheses."
        tokens = []
        stack  = []
        oargs  = []
        for op, fst, paren, bracket, brarg, lo in  self._grammar.findall(program):
            if op:
                while len(stack)>0 and not stack[-1]=="(":
                    if self._opGTE( stack[-1], op ):
                        tokens.append(stack.pop())
                    else:
                        break
                stack.append(op)
            elif lo:
                raise SyntaxError, "Bad: %s"%lo
            elif fst:
                self.wfsts.add(fst)
                tokens.append(fst)
            elif brarg:
                stack.append(brarg)
            elif bracket:
                if bracket=="[":
                    stack.append(bracket)
                    oargs=[]
                elif bracket=="]":
                    tok = stack.pop()
                    while not tok=="[":
                        oargs.append(tok)
                        tok = stack.pop()
                    tok = stack.pop()
                    if tok=="rmeps" or tok=="*" or tok==".":
                        print "Ignoring bracket args:", ", ".join(oargs), "for operator:", tok
                    else:
                        tok, oargs = self._merge( tok, oargs )
                        tok = tok+"_"+oargs
                    stack.append(tok)
            elif paren:
                if paren=="(":
                    stack.append(paren)
                elif paren==")":
                    tok = stack.pop()
                    while not tok=="(":
                        tokens.append(tok)
                        tok = stack.pop()
        while len(stack)>0:
            tokens.append(stack.pop())
        return tokens

    def generateCascade( self ):
        """
           Parse a postfix expression and runs OpenFST composition 
           and optimization commands as needed.
           
           This could be combined with _toPostfix, but this seems clearer.
        """
        
        stack = []
        while len(self.postfix)>0:
            tok = self.postfix.pop(0)
            if tok=="*":
                r = stack.pop()
                l = stack.pop()
                stack.append(self._compose(l, r))
            elif tok==".":
                r = stack.pop()
                l = stack.pop()
                stack.append(self._composeOTF(l, r))
            elif tok.startswith("det"):
                l = stack.pop()
                stack.append(self._determinize(l,tok))
            elif tok.startswith("min"):
                l = stack.pop()
                stack.append(self._minimize(l,tok))
            elif tok.startswith("push"):
                l = stack.pop()
                stack.append(self._push(l,tok))
            elif tok=="rmeps":
                l = stack.pop()
                stack.append(self._rmepsilon(l,tok) )
            else:
                stack.append(tok)
        while len(stack)>0:
            print "\nDone:\t\t",stack.pop()
        return

    def _compose( self, l, r ):
        print "compose\t\t",l, r
        return "("+l+"c"+r+")"
    def _composeOTF( self, l, r ):
        print "otfcompose\t", l, r
        return "("+l+"o"+r+")"
    def _determinize( self, l, tok ):
        print "determinize\t",l
        return tok+"("+l+")"
    def _minimize( self, l, tok ):
        print "minimize\t",l
        return tok+"("+l+")"
    def _push( self, l, tok ):
        print "push\t\t",l, tok
        return tok+"("+l+")"
    def _rmepsilon( self, l, tok ):
        print "rmeps\t\t",l
        return tok+"("+l+")"

if __name__=="__main__":
    import sys, argparse
    from argparse import RawTextHelpFormatter
    info = """
This is an extended parser for the WFST compilation DSL for transducersaurus.
The DSL supports the following WFST operations:
  * rmeps:  Epsilon removal.
  * push:   Pushing.
  * det:    Determinize
  * min:    Minimize
  * '*':    Composition
  * '.':    Static lookahead composition

The default semiring can be overridden  for 'push', 'det', and 'min' in one of two ways:
  * shorthand:
     - det_l  (log semiring)
     - det_t  (tropical semiring)
  * brackets:
     - det[log]  (log semiring)
     - det[tropical|trop|standard]  (tropical semiring)

It is also possible to specify label and/or weight encoding for the 'min' operation:
  * shorthand:
     - min_w  (encode weights)
     - min_s  (encode labels)
     - min_ws/min_sw  (encode weights AND labels)
  * brackets:
     - min[weights|ew,labels|el]  (encode weights AND labels)

These can be combined as well:
  * min[weights,labels,log]

Redundant specifications will be ignored:
  * min_w[weights,labels] -> min_wl

Conflicts will raise an error:
  * push[log,trop] -> "Pick a semiring!"

Unbalanced parentheses will be caught:
  * (C*det(L).(G*T) -> "Unbalanced parentheses!"
"""
    parser  = argparse.ArgumentParser( description=info, formatter_class=RawTextHelpFormatter )
    parser.add_argument('--command',      "-c", help='The cascade compilation command.', required=True )
    args = parser.parse_args()

    compiler = Parser( args.command )
    compiler.generateCascade()
