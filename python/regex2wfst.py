#!/usr/bin/python
import re


class Parser():
    """
      A simple regular expression parser.
      Performs transformation of the infix-style regex grammar
       to postfix notation, and transforms the resulting postfix 
       expression into a WFST.
    """
    
    START  = "2738c9s0"
    CONCAT = "i12938sx"
    
    def __init__( self, grammar, prefix="test", semiring="log", eps="<eps>" ):
        self.language = re.compile(r"""\s*(?: 
                                ([\*\+\?\|]|%s) |  #Operators
                                ([\)\(])   |  #Parentheses
                                ([^\(\)\?\+\*\s]+) # Words/Tokens
                                )
                                    """%(Parser.CONCAT), re.X )
        self.grammar  = grammar.decode("utf8")
        self.prefix   = prefix
        self.semiring = semiring
        self.eps      = eps
        self.isyms    = set([])
        self.prec = {
            "*" : 5,
            "+" : 5,
            "?" : 5,
            Parser.CONCAT : 4,
            "|" : 3
            }
            
        self.postfix  = self._toPostfix( self.grammar )
        
        
    def _opGTE( self, top, op ):
        """
          Check the precedence of two operators
           based on a precedence table.
        """
        
        if not top in self.prec:
            return True
        if self.prec[op]<=self.prec[top]:
            return True
        else:
            return False
        return
    
    def _checkWeight( self, tok ):
        """
          Check that the token is a valid weight.
        """
        
        parts = tok.split("[")
        if len(parts)==1:
            return tok
        parts[1] = parts[1].replace("]","")
        try:
            weight = float(parts[1])
        except:
            raise ValueError, "Token: (%s) is not a valid weight!" % parts[1]
        return " ".join(parts)
        
    def _toPostfix( self, program ):
        """
          Tokenize an convert an infix regular expression grammar to 
          postfix notation.
        """
        
        lparen = re.compile(r"\(")
        rparen = re.compile(r"\)")
        if not len(lparen.findall(program))==len(rparen.findall(program)):
            raise SyntaxError, "Unbalanced parentheses"
        lbracket = re.compile(r"\[")
        rbracket = re.compile(r"\]")
        if not len(lbracket.findall(program))==len(rbracket.findall(program)):
            raise SyntaxError, "Unbalanced brackets"
            
        tokens = []
        stack  = []
        wordre = re.compile(r"^[^\(\)\?\+\*\|\s]+$")
        opre   = re.compile(r"^[\?\+\*\)]$")
        #Add concatenation nodes
        for op, paren, word in self.language.findall(program):
            if paren:
                if paren=="(":
                    if len(stack)>0 and len(wordre.findall(stack[-1]))>0:
                        stack.append(Parser.CONCAT)
                stack.append(paren)
            elif word:
                if len(stack)>0 and (len(wordre.findall(stack[-1]))>0 or len(opre.findall(stack[-1]))):
                    stack.append(Parser.CONCAT)
                stack.append(word)
            elif op:
                stack.append(op)
                
        program = " ".join(stack)
        stack = []
        #Convert to postfix notation
        for op, paren, word in self.language.findall(program):
            if op:
                while len(stack)>0 and not stack[-1]=="(":
                    if self._opGTE( stack[-1], op ):
                        tokens.append(stack.pop())
                    else:
                        break
                stack.append(op)
            elif word:
                stack.append(word)
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
        
    def postfix2WFST( self ):
        """
          Generate a WFST from a postfix-format regular expression.
          This follows the general Thompson algorithm.
        """
        
        stack = []
        states = {}
        nstate = 0
        while len(self.postfix)>0:
            tok = self.postfix.pop(0)
            if tok=="*":
                l = stack.pop()
                states[nstate]=state( nstate=nstate, c=self.eps, sout=l.startstate.nstate )
                l, states = patch( l, states[nstate], states )
                stack.append( frag( 
                    startstate=states[nstate], 
                    ptrlist=[(nstate,{'sout2':states[nstate].sout2})]
                ) )            
                nstate += 1
            elif tok=="+":
                l = stack.pop()
                states[nstate]=state( nstate=nstate, c=self.eps, sout=l.startstate.nstate, sout2=None )
                l, states = patch( l, states[nstate], states )
                patch( l, states[nstate], states )
                stack.append( frag(
                    startstate=l.startstate,
                    ptrlist=[(nstate,{'sout2':states[nstate].sout2})]
                ) )
                nstate += 1
            elif tok=="?":
                l = stack.pop()
                states[nstate]=state( nstate=nstate, c=self.eps, sout=l.startstate.nstate, sout2=None )
                stack.append( frag( 
                    startstate=states[nstate], 
                    ptrlist=append(l.ptrlist, [(nstate,{'sout2':states[nstate].sout2})]) 
                    ) )
                nstate += 1
            elif tok=="|":
                r = stack.pop()
                l = stack.pop()
                states[nstate]=state( nstate=nstate, c=self.eps, sout=l.startstate.nstate, sout2=r.startstate.nstate )
                stack.append( frag( startstate=states[nstate], ptrlist=append(l.ptrlist, r.ptrlist) ) )
                nstate += 1
            elif tok==Parser.CONCAT:
                r = stack.pop()
                l = stack.pop()
                l, states = patch( l, r.startstate, states )
                stack.append( frag( startstate=l.startstate, ptrlist=r.ptrlist ) )
            else:
                tok = self._checkWeight(tok)
                states[nstate]=state( nstate=nstate, c=tok, sout=None, sout2=None )
                stack.append( frag( startstate=states[nstate], ptrlist=[(nstate,{'sout':states[nstate].sout})] ) )
                nstate += 1
        s = stack.pop()
        states[nstate]=state( nstate=nstate, c=Parser.START, sout=-1, sout2=-1 )
        s, states = patch( s, states[nstate], states )
        
        return s, states

    def fsaprint( self, e, states ):
        """Print out the WFST."""
        
        ofp = open("PREFIX.g.fst.txt".replace("PREFIX",self.prefix),"w")
        for s in states:
            if states[s].sout==-1:
                ofp.write("%s\n" % states[s].nstate)
                continue
            parts = states[s].c.split(" ")
            weight = ""
            word   = ""
            if len(parts)==2:
                weight = parts[1]
            word = parts[0]
            self.isyms.add(word)
            ofp.write("%s\t%s\t%s\t%s\n" % (states[s].nstate, states[s].sout, word.encode("utf8"), weight.encode("utf8")))
            if not states[s].sout2==None:
                ofp.write("%s\t%s\t%s\t%s\n" % (states[s].nstate, states[s].sout2, word.encode("utf8"), weight.encode("utf8")))
        ofp.close()
        
        return
        
    def print_isyms( self ):
        """Print input symbols"""
        
        ofp = open("PREFIX.g.isyms".replace("PREFIX",self.prefix), "w")
        ofp.write("%s 0\n" % self.eps)
        
        for i, sym in enumerate(self.isyms):
            ofp.write("%s\t%d\n" % (sym.encode("utf8"),i+1))
        ofp.close()
        
        return
        

class state( ):
    """Toy state object."""
    
    def __init__(self, nstate=0, c=None, sout=None, sout2=None ):
        self.c = c
        self.sout  = sout
        self.sout2 = sout2
        self.nstate = nstate 

class frag( ):
    """Frament of an NFA."""
    
    def __init__( self, startstate=state(), ptrlist=[None] ):
        self.startstate = startstate 
        self.ptrlist    = ptrlist    

def patch( s, state, states ):
    """Patch two frags together."""
    
    for ptr in s.ptrlist:
        for out in ptr[1]:
            ptr[1][out] = state.nstate
            if   out == "sout"  and states[ptr[0]].sout ==None: 
                states[ptr[0]].sout  = state.nstate 
            elif out == "sout2" and states[ptr[0]].sout2==None: 
                states[ptr[0]].sout2 = state.nstate
            else: pass
    return s,states

def append(ptrlist1, ptrlist2):
    """Append a new pointer list to an existing one."""
    
    newptrlist = ptrlist1
    newptrlist.extend(ptrlist2)
    
    return newptrlist
    
        
if __name__=="__main__":
    import sys, argparse
    
    example = "%s --grammar gramm.txt --eps '<eps>' --prefix test" % sys.argv[0]
    parser  = argparse.ArgumentParser( description=example )
    parser.add_argument('--grammar',  "-g", help='JFSG format regex grammar.', required=True )
    parser.add_argument('--prefix',   "-p", help='Output files prefix.', default="test" )
    parser.add_argument('--eps',      "-e", help='The epsilson token.', default="<eps>" )
    parser.add_argument('--verbose',  "-v", help='Verbose mode.', default=False, action="store_true" )
    args = parser.parse_args()
    
    if args.verbose==True:
        print "Running regex2wfst with the following arguments:"
        for attr, value in args.__dict__.iteritems():
            print attr, "=", value
            
    gramm = Parser( args.grammar, prefix=args.prefix, eps=args.eps )
    s, states = gramm.postfix2WFST()
    gramm.fsaprint( s, states )
    gramm.print_isyms()
                    
                    
                    
                    
                    