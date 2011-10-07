#!/usr/bin/python
import sys, tokenize, re
from cStringIO import StringIO
from Token import *

TWOARGS = re.compile(r"^(\.|\*|union)$")
ONEARG  = re.compile(r"^(det|min|push|rmeps|epsn|sync|proj)$")

class Transducersaurus( ):
    """
      Transducersauricize everything.
    """

    def __init__(self, command, kwargs=None ):
        self.command  = command
        self.kwargs   = kwargs
        self.tokens   = []
        self.tokenize_command( )

    def tokenize_command( self ):
        """
          Tokenize the input command. Based on the nice article,
             http://effbot.org/zone/simple-top-down-parsing.htm            
        """
        stack  = []
        
        for tok_data in tokenize.generate_tokens(StringIO(self.command).next):
            token = TokenFactory( tok_data, self.kwargs )
            if token.CLASS == tokenize.ENDMARKER:
                break

            if token.TYPE=='OPERATOR':
                while len(stack)>0 and not stack[-1].NAME=="(":
                    if stack[-1].PREC > token.PREC :
                        self.tokens.append(stack.pop())
                    else:
                        break
                stack.append(token)
            elif token.TYPE=='ASR' or token.TYPE=='WFST':
                self.tokens.append(token)
            elif token.TYPE=='BRARG':
                stack.append(token)
            elif token.TYPE=='BRACKET':
                if token.NAME=='[':
                    stack.append(token)
                elif token.NAME==']':
                    brarg = stack.pop()
                    oargs = []
                    while not brarg.NAME=='[':
                        oargs.append(brarg.NAME)
                        brarg = stack.pop()
                    brarg = stack.pop()
                    brarg.set_options(oargs)
                    stack.append(brarg)
            elif token.TYPE=='PAREN':
                if token.NAME=='(':
                    stack.append(token)
                elif token.NAME==')':
                    paren = stack.pop()
                    while not paren.NAME=='(':
                        self.tokens.append(paren)
                        paren = stack.pop()
        while len(stack)>0: 
            self.tokens.append(stack.pop())
        return 

    def generate_cascade( self ):
        """
          Parse the token list and generate commands
           as required.  All the heavy work is done by
           the token objects themselves.
        """
        stack = []
        
        while len(self.tokens)>0:
            token = self.tokens.pop(0)
            if TWOARGS.match(token.NAME):
                r = stack.pop()
                l = stack.pop()
                stack.append( token.build_command(l, r) )
            elif ONEARG.match(token.NAME):
                l = stack.pop()
                stack.append( token.build_command(l) )
            else:
                token.build_command( )
                stack.append( token )
        return

t = Transducersaurus( sys.argv[1] )

t.generate_cascade()
