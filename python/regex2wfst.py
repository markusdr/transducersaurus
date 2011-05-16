#!/usr/bin/python
import re
from wfst import WFST

class Parser():
    """
      A simple regular expression parser.
      Performs transformation of the infix-style regex grammar
       to postfix notation, and transforms the resulting postfix 
       expression into a WFST.
    """
    
    START  = "2738c9s0h"
    CONCAT = "i12938sx7"
    PLUS   = "as767sk3w"
    STAR   = "s79w043jk"
    HATENA = "vytw723i2"
    ALT    = "asiytg10c"

    def __init__( self, grammar, prefix="test", semiring="log", eps="<eps>", algorithm="new" ):
        self.language = re.compile(r"""\s*(?: 
                                ([\*\+\?\|]|%s) |  #Operators
                                ([\)\(])   |  #Parentheses
                                ([^\(\)\?\+\*\s]+) # Words/Tokens
                                )
                                    """%(Parser.CONCAT), re.X )
        self.grammar  = self._load_grammar(grammar)
        self.prefix   = prefix
        self.semiring = semiring
        self.eps      = eps
        self.isyms    = set([])
        self.max      = 0
        self.prec = {
            "*" : 5,
            "+" : 5,
            "?" : 5,
            Parser.CONCAT : 3,
            "|" : 4
            }
        self.algorithm = algorithm
        self.postfix  = self._toPostfix( self.grammar )
        
    def regex2wfst( self ):
        if self.algorithm=="new":
            self.postfix2WFSTnew( )
        elif self.algorithm=="classic":
            self.postfix2WFSTclassic( )
        return
            
        
    def _load_grammar( self, grammar_file ):
        """Load the grammar file."""
        
        grammar = ""
        ifp = open(grammar_file,"r")
        for line in ifp:
            grammar += line.decode("utf8")
        ifp.close()
        return grammar
        
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
        
    def _toPostfix( self, tokens ):
        """
          Convert the regex to postfix format.
          The implementation is described here:
          http://swtch.com/~rsc/regexp/regexp1.html
        """

        p = [paren() for i in xrange(100)]
        dst = []
        nalt  = 0
        natom = 0
        g = 0
        regex = tokens.split(" ")
        for i in xrange(len(regex)):
            if regex[i]=='(':
                if natom > 1:
                    natom -= 1
                    dst.append(Parser.CONCAT)
                p[g].nalt = nalt
                p[g].natom = natom
                g += 1
                nalt  = 0
                natom = 0
            elif regex[i]=='|':
                if natom==0: return None
                for k in xrange(natom-1):
                    dst.append(Parser.CONCAT)
                natom = 0
                nalt += 1
            elif regex[i]==')':
                if g==len(p): return None
                if natom==0 : return None
                for k in xrange(natom-1):
                    dst.append(Parser.CONCAT)
                natom = 0
                for k in xrange(nalt):
                    dst.append('|')
                g -= 1
                nalt  = p[g].nalt
                natom = p[g].natom
                natom += 1
            elif regex[i]=='*' or regex[i]=='+' or regex[i]=='?':
                if natom == 0: return None
                dst.append(regex[i])
            else:
                if natom > 1:
                    natom -= 1
                    dst.append(Parser.CONCAT)
                dst.append(regex[i])
                natom += 1
        for k in xrange(natom-1):
            dst.append(Parser.CONCAT)
        natom = 0
        for i in xrange(nalt):
            dst.append('|')
        
        return dst
        
    def _toPostfixNewBroken( self, program ):
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
        
    def postfix2WFSTnew( self ):
        """
          Generate a WFST from a postfix-format regular expression.
          This follows the modified Thompson algorithm described here:
          http://swtch.com/~rsc/regexp/regexp1.html
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
        
        self._printThomsponNew( s, states )
        
        return

    def postfix2WFSTclassic( self ):
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
                stack.append( self._star( stack.pop() ) )
            elif tok=="+":
                stack.append( self._plus( stack.pop() ) )
            elif tok=="?":
                stack.append( self._hatena( stack.pop() ) )
            elif tok=="|":
                r = stack.pop()
                l = stack.pop()
                stack.append( self._alt( l, r ) )
            elif tok==Parser.CONCAT:
                r = stack.pop()
                l = stack.pop()
                stack.append( self._append( l, r ) )
            else:
                tok = self._checkWeight(tok)
                stack.append(tok)
        fsa = stack.pop()
        self._printThomsponClassic( fsa )

        return 

    def _printThomsponClassic( self, fsa ):
        """Print out the WFST."""

        ofp = open("PREFIX.g.fst.txt".replace("PREFIX",self.prefix),"w")

        ofp.write("%s\t%s\t%s\n" % (0, fsa.start, self.eps))
        for state in fsa.arcs:
            for arc in fsa.arcs[state]:
                ofp.write("%s\t%s\t%s\t%s\n" % (state, arc[2], arc[0].strip(), arc[3]))
        ofp.write("%d\n" % (fsa.final))
        ofp.close()
        
        return
        
    def _star( self, s ):
        """Perform the 'star' operation."""

        if type(s)==str() or type(s)==unicode:
            fsa = WFST( start=self.max+1, eps=self.eps, semiring="standard" )
            fsa.add_arc( fsa.start+1, s, s, fsa.start+2 )
        else:
            fsa = s

        fsa.add_arc( fsa.start, self.eps, self.eps, fsa.start+1 )
        fsa.add_arc( fsa.start+2, self.eps, self.eps, fsa.start+3 )
        fsa.add_arc( fsa.start+2, self.eps, self.eps, fsa.start+1 )
        fsa.add_arc( fsa.start, self.eps, self.eps, fsa.start+3 )
        fsa.final = fsa.start+3
        self.max  = fsa.max
        self.isyms.update(fsa.isyms)
        
        return fsa

    def _plus( self, s ):
        if type(s)==unicode:
            fsa = WFST( start=self.max+1, eps=self.eps, semiring="standard" )
            fsa.add_arc( fsa.start, s, s, fsa.start+1 )
            fsa.final = fsa.start+1
        else:
            fsa = s
        fsa = self._append( fsa, fsa )
        self.isyms.update(fsa.isyms)
        return fsa

    def _hatena( self, s ):
        """Perform the 'zero or one' operation."""
        fsa = self._alt( s, self.eps )
        self.isyms.update(fsa.isyms)
        return fsa

    def _alt( self, l, r ):
        """Perform the 'alternate' operation."""
        if type(l)==str or type(l)==unicode:
            fsa1 = WFST( start=self.max+1, eps=self.eps, semiring="standard" )
            fsa1.add_arc( fsa1.start, self.eps, self.eps, fsa1.start+1 )
            fsa1.add_arc( fsa1.start+1, l, l, fsa1.start+2 )
            fsa1.final = fsa1.start+2
        else:
            fsa1 = l
            self.max += 1
            fsa1.add_arc( self.max, self.eps, self.eps, fsa1.start )
            fsa1.start = self.max
        if fsa1.max>self.max:
            self.max = fsa1.max

        if type(r)==str or type(r)==unicode:
            fsa2 = WFST( start=fsa1.start, eps=self.eps, semiring="standard" )
            fsa2.add_arc( fsa2.start, self.eps, self.eps, fsa2.start+1 )
            fsa2.add_arc( fsa2.start+1, r, r, fsa2.start+2 )
            fsa2.final = fsa2.start+2
        else:
            fsa2 = r
            fsa2.add_arc( fsa1.start, self.eps, self.eps, fsa2.start )
            fsa2.start = fsa1.start
        
        for state in fsa2.arcs:
            for arc in fsa2.arcs[state]:
                if state in fsa1.arcs:
                    fsa1.arcs[state].add( arc )
                else:
                    fsa1.arcs[state] = set([ arc ])

        if fsa1.max>=self.max:
            self.max = fsa1.max+1
        if fsa2.max>=self.max:
            self.max = fsa2.max+1
        fsa1.add_arc( fsa1.final, self.eps, self.eps, self.max ) 
        fsa1.add_arc( fsa2.final, self.eps, self.eps, self.max )
        fsa1.final = self.max
        self.isyms.update(fsa1.isyms)

        return fsa1
        

    def _append( self, l, r ):
        """Perform the 'concatenation' operation."""
        if type(l)==str() or type(l)==unicode:
            fsa1 = WFST( start=self.max+1, eps=self.eps, semiring="standard" )
            fsa1.add_arc( fsa1.start, l, l, fsa1.start+1 )
            fsa1.final = fsa1.start+1
        else:
            fsa1 = l
        if fsa1.final>self.max:
            self.max = fsa1.final

        if type(r)==str() or type(r)==unicode:
            fsa2 = WFST( start=self.max+1, eps=self.eps, semiring="standard" )
            fsa2.add_arc( fsa2.start, r, r, fsa2.start+1 )
            fsa2.final = fsa2.start+1
        else:
            fsa2 = r
        
        for state in fsa2.arcs:
            for arc in fsa2.arcs[state]:
                if state in fsa1.arcs:
                    fsa1.arcs[state].add( arc )
                else:
                    fsa1.arcs[state] = set([ arc ])
        fsa1.add_arc( fsa1.final, self.eps, self.eps, fsa2.start )
        fsa1.final = fsa2.final
        if fsa1.final>self.max:
            self.max = fsa1.final
        self.isyms.update(fsa1.isyms)
        return fsa1

    def _printThomsponNew( self, e, states ):
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
            word = parts[0].strip()
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
        
class paren( ):
    def __init__(self):
        self.nalt  = 0
        self.natom = 0

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
    parser.add_argument('--algorithm',     "-a", help='Specify the conversion algorithm. "classic" or "new".  Default is "new".', default="new" )
    parser.add_argument('--verbose',  "-v", help='Verbose mode.', default=False, action="store_true" )
    args = parser.parse_args()
    
    if args.verbose==True:
        print "Running regex2wfst with the following arguments:"
        for attr, value in args.__dict__.iteritems():
            print attr, "=", value
            
    gramm = Parser( args.grammar, prefix=args.prefix, eps=args.eps, algorithm=args.algorithm )
    gramm.regex2wfst()
    gramm.print_isyms()
                    
                    
                    
                    
                    
