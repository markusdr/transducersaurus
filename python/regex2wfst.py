#!/usr/bin/python
# -*- mode: python; coding: utf-8 -*-
#########################################
# Copyright (c) [2010-2011], Josef Robert Novak
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
#  modification, are permitted #provided that the following conditions
#  are met:
#
# * Redistributions of source code must retain the above copyright 
#    notice, this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above 
#    copyright notice, this list of #conditions and the following 
#    disclaimer in the documentation and/or other materials provided 
#    with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT 
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS 
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE 
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, 
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES 
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR 
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) 
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, 
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED 
# OF THE POSSIBILITY OF SUCH DAMAGE.
#
# Build an fst from a regular expression
# This implementation follows the modified Thompson algorithm described here:
#   http://swtch.com/~rsc/regexp/regexp1.html
#########################################
import re

class paren( ):
    def __init__(self):
        self.nalt  = 0
        self.natom = 0

class state( ):
    """A state object."""
    def __init__(self, nstate=0, c=None, sout=None, sout2=None ):
        self.c = c
        self.sout  = sout
        self.sout2 = sout2
        self.nstate = nstate #state identifier

class frag( ):
    """Frament of an NFA."""
    def __init__( self, startstate=state(), ptrlist=[None] ):
        self.startstate = startstate #start state
        self.ptrlist    = ptrlist    #outgoing ptrs 


class Regex2WFST( ):
    """Build up the FSA"""
    def __init__( self, regex_file, prefix="prefix", eps="<eps>" ):
        self.language = re.compile(r"""\s*(?: 
                        ([\*\+\?\|]) |            #Operators
                        ([\)\(])   |              #Parentheses
                        (\[\s*[+\-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+\-]?\d+)?\s*\]) | #Weight 
                        ([^\[\]\|\(\)\?\+\*\s]+)  #Words/Tokens
                        )""", re.X )
        self.match = "256"
        self.split = "257"
        self.nstate = 0
        self.eps        = eps
        self.prefix     = prefix
        self.tokens     = self.parse_grammar_file( regex_file )
        self.fsa_ofp    = open("%s.g.fst.txt" % self.prefix, "w")
        self.isyms_ofp  = open("%s.g.isyms"   % self.prefix, "w")
        self.isyms      = set([])
        self.dst        = None   
        self.e          = None
        self.states     = None

    def _split_token( self, token ):
        s = ""; w = ""
        for op, paren, weight, word in self.language.findall(token):
            if    word:   s = word
            elif  weight: w = weight.replace("[","").replace("]","")
        self.isyms.add(s)
        return s, w

    def re2post( self ):
        """Convert the regex to postfix format."""
        p      = [paren() for i in xrange(100)]
        g      = 0
        dst    = []
        nalt   = 0
        natom  = 0
        for i in xrange(len(self.tokens)):
            if self.tokens[i]=='(':
                if natom > 1:
                    natom -= 1
                    dst.append('.')
                p[g].nalt = nalt
                p[g].natom = natom
                g += 1
                nalt  = 0
                natom = 0
            elif self.tokens[i]=='|':
                if natom==0: return None
                for k in xrange(natom-1):
                    dst.append('.')
                natom = 0
                nalt += 1
            elif self.tokens[i]==')':
                if g==len(p): return None
                if natom==0 : return None
                for k in xrange(natom-1):
                    dst.append('.')
                natom = 0
                for k in xrange(nalt):
                    dst.append('|')
                g -= 1
                nalt  = p[g].nalt
                natom = p[g].natom
                natom += 1
            elif self.tokens[i]=='*' or self.tokens[i]=='+' or self.tokens[i]=='?':
                if natom == 0: return None
                dst.append(self.tokens[i])
            else:
                if natom > 1:
                    natom -= 1
                    dst.append('.')
                dst.append(self.tokens[i])
                natom += 1
        for k in xrange(natom-1):
            dst.append('.')
        natom = 0
        for i in xrange(nalt):
            dst.append('|')

        self.dst = dst
        return

    def patch( self, e1, state, states ):
        """Patch two frags together."""
        def l2pupdate( nstate, x): pass
        for ptr in e1.ptrlist:
            for out in ptr[1]:
                ptr[1][out] = state.nstate
                if   out == "sout"  and states[ptr[0]].sout ==None: states[ptr[0]].sout  = state.nstate 
                elif out == "sout2" and states[ptr[0]].sout2==None: states[ptr[0]].sout2 = state.nstate
                else: pass
        return e1,states

    def append( self, ptrlist1, ptrlist2):
        newptrlist = ptrlist1
        newptrlist.extend(ptrlist2)
        return newptrlist

    def post2nfa( self ):
        """Convert postfix-style regex to an nfa."""
        nstate=0
        stackp = []
        states = {}
        for p in xrange(len(self.dst)):
            if self.dst[p]==".":
                e2 = stackp.pop(-1)
                e1 = stackp.pop(-1)
                e1, states = self.patch( e1, e2.startstate, states )
                stackp.append( frag( startstate=e1.startstate, ptrlist=e2.ptrlist ) )
            elif self.dst[p]=="|":
                e2 = stackp.pop(-1)
                e1 = stackp.pop(-1)
                states[nstate]=state( nstate=nstate, c=self.match, sout=e1.startstate.nstate, sout2=e2.startstate.nstate )
                stackp.append( frag( startstate=states[nstate], ptrlist=self.append(e1.ptrlist, e2.ptrlist) ) )
                nstate += 1
            elif self.dst[p]=="*":
                e1 = stackp.pop(-1)
                states[nstate]=state( nstate=nstate, c=self.match, sout=e1.startstate.nstate )
                e1, states = self.patch( e1, states[nstate], states )
                stackp.append( frag( 
                        startstate=states[nstate], 
                        ptrlist=[(nstate,{'sout2':states[nstate].sout2})]
                        ) )            
                nstate += 1
            elif self.dst[p]=="?":
                e1 = stackp.pop(-1)
                states[nstate]=state( nstate=nstate, c=self.match, sout=e1.startstate.nstate, sout2=None )
                stackp.append( frag( 
                        startstate=states[nstate], 
                        ptrlist=self.append(e1.ptrlist, [(nstate,{'sout2':states[nstate].sout2})]) 
                        ) )
                nstate += 1
            elif self.dst[p]=="+":
                e1 = stackp.pop(-1)
                states[nstate]=state( nstate=nstate, c=self.match, sout=e1.startstate.nstate, sout2=None )
                e1, states = self.patch( e1, states[nstate], states )
                self.patch( e1, states[nstate], states )
                stackp.append( frag(
                        startstate=e1.startstate,
                        ptrlist=[(nstate,{'sout2':states[nstate].sout2})]
                        ) )
                nstate += 1
            else:
                states[nstate]=state( nstate=nstate, c=self.dst[p], sout=None, sout2=None )
                stackp.append( frag( startstate=states[nstate], ptrlist=[(nstate,{'sout':states[nstate].sout})] ) )
                nstate += 1
        e1 = stackp.pop(-1)
        states[nstate]=state( nstate=nstate, c=self.split, sout=-1, sout2=-1 )
        e1, states = self.patch( e1, states[nstate], states )
    
        self.e = e1
        self.states = states
        return
                        
    def fsaprint( self ):
        """Print out the fsa in ATT/OpenFST format."""
        for s in self.states:
            if self.states[s].sout==-1:
                self.fsa_ofp.write("%s "% self.states[s].nstate)
                continue
            word = self.eps
            word = self.states[s].c
            if self.states[s].c.find("+")>-1: 
                pw = self.states[s].c.split("+")
                self.states[s].c = pw[0]
                word = pw[1]
            if self.states[s].c == self.match: 
                self.states[s].c = self.eps

            sym, weight = self._split_token( self.states[s].c )
            self.fsa_ofp.write("%s %s %s %s\n" % (self.states[s].nstate, self.states[s].sout, sym.encode("utf8"), weight))
            if not self.states[s].sout2==None:
                self.fsa_ofp.write("%s %s %s %s\n" % (self.states[s].nstate, self.states[s].sout2, sym.encode("utf8"), weight))
        self.fsa_ofp.close()

        self.isyms_ofp.write("%s 0\n" % self.eps)
        for i, sym in enumerate(self.isyms):
            self.isyms_ofp.write("%s %d\n" % (sym, i+1))
        self.isyms_ofp.close()
        return 

    def parse_grammar_file( self, grammar_file ):
        """Build a regexp grammar up from a JSGF-style definition."""
        grammar     = ""
        grammar_id  = "$GRAMMAR" #This is the top-level ID
        grammar_ifp = open( grammar_file, "r" )
        subexps = {}
        for line in grammar_ifp:
            line = line.strip()
            line = re.sub(r"\s+"," ",line)
            if not len(re.findall(r"::=",line))==1:
                continue
            id, expr = re.split(r"\s*::=\s*",line)
            if not re.match(r"^\$[a-zA-Z0-9_\-\.]+$",id):
                raise SyntaxError, "Subexpression ID: '%s' does not conform to ID syntax: /^\$[a-zA-Z0-9_\-\.]+$/"
            subexps[id] = expr
        grammar_ifp.close()
        
        if len(subexps.keys())==0:
            #We already have a single regex expression, just return it
            grammar = open(grammar_file,"r").read()
        elif len(subexps.keys())>0 and not grammar_id in subexps:
            raise SyntaxError, "Top-level expression ID, '$GRAMMAR' not found."
        else:
            grammar = self.build_grammar( subexps[grammar_id], subexps )

        tokens = [self.eps]
        prev = [False,""]
        for op, paren, weight, word in self.language.findall( grammar ):
            if    paren:  tokens.append(paren); prev=[False,paren]
            elif  word:   tokens.append(word);  prev=[True,word]
            elif  weight:
                if prev[0]==True: prev[1]=tokens[-1]; tokens[-1] += weight
                else:          tokens.append(self.eps+weight)
                prev==[False,weight]
            else:         tokens.append(op);    prev=[False,op]
        return tokens

    def build_grammar( self, grammar_part, subexps ):
        """Recursively build up the full grammar."""
        id_finder = re.compile(r"""\s*(?: 
                                 (\$[a-zA-Z0-9_\-\.]+)  #IDs 
                               )""", re.X )
        for id in id_finder.findall(grammar_part):
            if id:
                grammar_part = grammar_part.replace(id, subexps[id])
                grammar_part = self.build_grammar( grammar_part, subexps )
                break
        return grammar_part



if __name__=="__main__":
    import sys, argparse
    
    example = "%s --grammar gramm.txt --eps '<eps>' --prefix test" % sys.argv[0]
    parser  = argparse.ArgumentParser( description=example )
    parser.add_argument('--grammar',  "-g", help='Regular expression-based grammar.', required=True )
    parser.add_argument('--prefix',   "-p", help='Output files prefix.', default="test" )
    parser.add_argument('--eps',      "-e", help='The epsilson token.', default="<eps>" )
    parser.add_argument('--verbose',  "-v", help='Verbose mode.', default=False, action="store_true" )
    args = parser.parse_args()
    
    if args.verbose==True:
        print "Running regex2wfst with the following arguments:"
        for attr, value in args.__dict__.iteritems():
            print attr, "=", value
            
    r2f = Regex2WFST( args.grammar, prefix=args.prefix, eps=args.eps )
    r2f.re2post( )
    r2f.post2nfa( )
    r2f.fsaprint( )


