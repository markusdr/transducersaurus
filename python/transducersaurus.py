#!/usr/bin/python
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
#########################################
import re, os
from checkVocab import *
from silclass2fst import Silclass 
from arpa2fst import ArpaLM
from lexicon2fst import Lexicon
from cd2fst import ContextDependency
from cd2fstSphinx import ContextDependencySphinx
from hmm2wfst import hmm2wfst
from regex2wfst import *

__version__="0.0.0.6"

class GenerateCascade( ):
    """
	   Generate WFST-based cascades from an ARPA-format LM, 
	   pronunciation lexicon and acoustic model information.
	   Supports both Sphinx and HTK format acoustic models.
	   
	   Additional options include a built-in combination and 
	   optimization routine parser.
    """
    
    def __init__( self, tiedlist, lexicon, arpa, buildcommand, hmmdefs=None, prefix="test",
                  amtype="htk", semiring="log", failure=None, auxout=3, basedir="",
                  eps="<eps>", sil="sil", convert=None, order=0, regex=False, normalizeG=False ):
        
        self._grammar = re.compile(
             r"""\s*(?:
                (push(?:_[lt])? | rmeps | det(?:_[lt])? | min(?:_(?:[ws]*[lt]?) | (?:[lt]?[ws]*))? | \* | \.) | #Operators and operations
                ([HCLGT]) |  #WFST components
                ([\)\(])  |  #Order of operations parens
                ([\[\]])  |  #Optional argument brackets
                (log|tropical|standard|trop|el|ew|weights|labels|symbols),? | #Optional bracket arguments
                (.) ) #Left overs
              """, re.X
            )
        self.tiedlist       = tiedlist
        self.lexicon        = lexicon
        self.arpa           = arpa
        self.order          = order
        self.buildcommand   = buildcommand.replace(" ","")
        self.hmmdefs        = hmmdefs
        self.basedir        = basedir
        self.prefix         = self._set_prefix(prefix)
        self.amtype         = amtype
        self.semiring       = semiring
        self.failure        = failure
        self.eps            = eps
        self.sil            = sil
        self.auxout         = self._set_aux( auxout )
        self.wfsts          = set([])
        self.postfix        = self._toPostfix(self.buildcommand)
        self.convert        = convert
        self.regex          = regex
        self.normalize       = self._set_normalize( normalizeG )
        self.word_osyms	    = None
        self.am_isyms       = None
        
    def _set_normalize( self, normalizeG ):
        """
          Run the WFST normalization program.
          All this does is normalize the arc weights for each state.
        """
        if normalizeG==True:
            return "| ./normalizeG -i - -o - "
        else:
            return ""
        
    def _set_aux( self, auxout ):
        #this should work for now but is not very future proof.
        if not auxout==3:
            return auxout
        
        if "H" in self.buildcommand:
            return 2
        elif self.buildcommand.startswith("C") or self.buildcommand.startswith("("):
            return 0
        else:
            return 1
        return 

    def _set_prefix( self, prefix ):
        if self.basedir=="auto":
            self.basedir = self.buildcommand.replace("(","a").replace(")","b").replace("*","c").replace(".","o")
            self.basedir = self.basedir.replace("[","_").replace("log","l").replace("tropical","t").replace("weights","w")
            self.basedir = self.basedir.replace("labels","s").replace("trop","t").replace("standard","t")
            self.basedir = self.basedir.replace("ew","w").replace("el","s").replace(",","").replace("]","")
            self.basedir = re.sub(r"(_[swlt]+)_",r"\1",self.basedir)
            self.basedir = prefix + "-" + self.basedir
        if self.basedir:
            if not os.path.exists(self.basedir):
                print "Creating dir: %s" % self.basedir
                os.makedirs(self.basedir)
        prefix = os.path.join(self.basedir,prefix)
        return prefix 
        
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
        
        def check_prec( oper, prec ):
            if oper in prec:
                return prec[oper]
            else:
                for key in prec:
                    if not type(key)==str and key.match(oper):
                        return prec[key]

        op_prec  = check_prec( op, prec )
        top_prec = check_prec( top, prec )

        if op_prec <= top_prec:
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
                raise SyntaxError, "Bad token: %s"%lo
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
                stack.append(self._determinize(l, tok))
            elif tok.startswith("min"):
                l = stack.pop()
                stack.append(self._minimize(l, tok))
            elif tok.startswith("push"):
                l = stack.pop()
                stack.append(self._push(l, tok))
            elif tok=="rmeps":
                l = stack.pop()
                stack.append(self._rmepsilon(l) )
            else:
                stack.append(tok)
				
        if self.auxout>0:
            self._mapper( )
        if self.convert:
            self.convertTcubedJuicer( )
        return
		
    def _mapper( self ):
        """
           Map any non-AM symbols including AUX or Failure transitions 
           to the epsilon symbol and replace the input symbols list with the 
           ordering that corresponds to the acoustic model.  
       
           Also performs mapping of logical triphones to physical triphones.
 
           Should only be necessary with --auxout flag.  Otherwise this work 
           will be folded into the construction of the C FST.  Should only be
           relevant to models based on HTK acoustic models.
        """
                   
        command=""

        if 'H' in self.wfsts:
            command="""
fstcompile --arc_type=SEMIRING --osymbols=PREFIX.h.isyms PREFIX.e.fst.txt | 
fstarcsort --sort_type=olabel - | 
fstcompose - PREFIX.FST.fst > PREFIX.eFST.fst"""
            command=command.replace("\n"," ").replace("SEMIRING",self.semiring).replace("PREFIX",self.prefix).replace("FST",self.final_fst)
            self.final_fst = "eFST".replace("FST",self.final_fst)
        elif 'C' in self.wfsts:
            command="""
fstcompile --arc_type=SEMIRING --isymbols=PREFIX.hmm.syms --osymbols=PREFIX.c.isyms PREFIX.d.fst.txt | 
fstarcsort --sort_type=olabel - | 
fstcompose - PREFIX.FST.fst > PREFIX.dFST.fst"""
            command=command.replace("\n"," ").replace("SEMIRING",self.semiring).replace("PREFIX",self.prefix).replace("FST",self.final_fst)
            self.final_fst = "dFST".replace("FST",self.final_fst)
        else:
            print "Requested mapper but no C or H fst. Aborting..."
            return

        print command
        os.system( command )

        return
		
    def _compose( self, l, r ):
        """
           Run standard composition on two input WFSTs.
        """

        #If the left-hand component is the HMM WFST we need to 
        # map the C-level symbols to the AM prior to composition.
        #This is a little bit nasty but should get the job done.
        if l=="H":
            command="""
fstcompile --arc_type=SEMIRING --isymbols=PREFIX.hmm.syms --osymbols=PREFIX.c.isyms PREFIX.d.fst.txt | 
fstarcsort --sort_type=olabel - | 
fstcompose - PREFIX.FST.fst > PREFIX.dFST.fst"""
            command=command.replace("\n"," ").replace("SEMIRING",self.semiring).replace("PREFIX",self.prefix).replace("FST",self.final_fst)
            r = "dFST".replace("FST",r.lower())
            print command
            os.system( command )

        if l=="G" and r=="T":
            command = "fstcompose PREFIX.FST1.fst PREFIX.FST2.fst | fstproject --project_output=true - | fstarcsort --sort_type=ilabel - > PREFIX.FST1FST2.fst"
        else:
            command = "fstcompose PREFIX.FST1.fst PREFIX.FST2.fst > PREFIX.FST1FST2.fst"
        command = command.replace("PREFIX",self.prefix).replace("FST1",l.lower()).replace("FST2",r.lower())
        print command
        os.system( command )
        self.final_fst = "FST1FST2".replace("FST1",l.lower()).replace("FST2",r.lower())
        return self.final_fst
		
    def _composeOTF( self, l, r ):
        """
           Run static on-the-fly composition
           on two input WFSTs.
        """

        #If the left-hand component is the HMM WFST we need to 
        # map the C-level symbols to the AM prior to composition.
        #This is a little bit nasty but should get the job done.
        if l=="H":
            command="""
fstcompile --arc_type=SEMIRING --isymbols=PREFIX.hmm.syms --osymbols=PREFIX.c.isyms PREFIX.d.fst.txt | 
fstarcsort --sort_type=olabel - | 
fstcompose - PREFIX.FST.fst > PREFIX.dFST.fst"""
            command=command.replace("\n"," ").replace("SEMIRING",self.semiring).replace("PREFIX",self.prefix).replace("FST",self.final_fst)
            r = "dFST".replace("FST",r.lower())
            print command
            os.system( command )

        print "Converting left-hand composition operand..."
        command = "fstconvert --fst_type=olabel_lookahead --save_relabel_opairs=PREFIX.FST1FST2.rlbl.txt PREFIX.FST1.fst > PREFIX.FST1.lkhd.fst"
        command = command.replace("PREFIX",self.prefix).replace("FST1",l.lower()).replace("FST2",r.lower())
        print command
        os.system( command )

        print "Fixing any possible bogus misses in the relabeler..."
        fixRelabel(
            "PREFIX.FST1FST2.rlbl.txt".replace("PREFIX",self.prefix).replace("FST1",l.lower()).replace("FST2",r.lower()), 
            new_relabel="PREFIX.FST1FST2.rlbl.fix.txt".replace("PREFIX",self.prefix).replace("FST1",l.lower()).replace("FST2",r.lower())
            )

        print "Relabeling right-hand composition operand..."
        command = "fstrelabel --relabel_ipairs=PREFIX.FST1FST2.rlbl.fix.txt PREFIX.FST2.fst | fstarcsort - > PREFIX.FST2.rlbl.fst"
        command = command.replace("PREFIX",self.prefix).replace("FST1",l.lower()).replace("FST2",r.lower())
        print command
        os.system( command )
        
        print "Performing OTF composition..."
        command = "fstcompose PREFIX.FST1.lkhd.fst PREFIX.FST2.rlbl.fst > PREFIX.FST1FST2.lkhd.fst"
        command = command.replace("PREFIX",self.prefix).replace("FST1",l.lower()).replace("FST2",r.lower())
        print command
        os.system( command )
        self.final_fst = "FST1FST2.lkhd".replace("FST1",l.lower()).replace("FST2",r.lower())
        return self.final_fst

    def _check_opts( self, tok ):
        """Check for any auxiliary arguments passed to the operation."""
        
        encode_weights = False
        encode_labels  = False
        semiring       = self.semiring
        
        opt = ""; args = ""
        parts = tok.split("_")
        opt = parts[0]
        if len(parts)==2: args = parts[1]
        
        for arg in list(args):
            if arg=="w":
                encode_weights = True
            elif arg=="s":
                encode_labels  = True
            elif arg=="l":
                semiring = "log"
            elif arg=="t":
                semiring = "standard"
              
        if not args=="":
            args = "_"+args
        
        return encode_weights, encode_labels, semiring, args
                
    def _determinize( self, l, tok ):
        """
           Run determinization on an input WFST.
           Also handles optional calls to fstencode or operation specific semiring changes.
        """
        
        encode_weights, encode_labels, semiring, args = self._check_opts( tok )
        
        if l.lower()=="l" and self.semiring=="log":
            #Determinizing an un-weighted lexicon in the log semiring will result in chaos
            print "Performing determinization of unweighted lexicon in the tropical semiring."
            command = "fstprint PREFIX.FST.fst | fstcompile - | fstdeterminize - | fstprint - | fstcompile --arc_type=log - > PREFIX.detARGSFST.fst"
        elif encode_weights==True or encode_labels==True:
            if semiring==self.semiring:
                command = "fstencode --encode_labels=ENCL --encode_weights=ENCW PREFIX.FST.fst PREFIX.codex | fstdeterminize - | fstencode --decode=true - PREFIX.codex > PREFIX.detARGSFST.fst"
            else:
                command = "fstprint PREFIX.FST.fst | fstcompile --arc_type=DSEMIRING - | fstencode --encode_labels=ENCL --encode_weights=ENCW - PREFIX.codex | fstdeterminize - | fstencode --decode=true - PREFIX.codex | fstprint - | fstcompile --arc_type=SEMIRING - > PREFIX.detARGSFST.fst"
        elif semiring==self.semiring:
            command = "fstdeterminize PREFIX.FST.fst > PREFIX.detFST.fst" 
        else:
            command = "fstprint PREFIX.FST.fst | fstcompile --arc_type=DSEMIRING - | fstdeterminize - | fstprint - | fstcompile --arc_type=SEMIRING - > PREFIX.detARGSFST.fst"
            
        command = command.replace("ENCL",encode_labels.__str__().lower()).replace("ENCW",encode_weights.__str__().lower())
        command = command.replace("DSEMIRING",semiring).replace("SEMIRING",self.semiring)
        command = command.replace("PREFIX",self.prefix).replace("FST",l.lower()).replace("ARGS",args)
        
        print command
        os.system( command )
        self.final_fst = "detARGSFST".replace("FST",l.lower()).replace("ARGS",args)
        
        return self.final_fst

    def _minimize( self, l, tok ):
        """
           Run minimization on an input WFST.
           Also handles optional calls to fstencode or operation specific semiring changes.
        """
        
        encode_weights, encode_labels, semiring, args = self._check_opts( tok )
        
        if encode_weights==True or encode_labels==True:
            if semiring==self.semiring:
                command = "fstencode --encode_labels=ENCL --encode_weights=ENCW PREFIX.FST.fst PREFIX.codex | fstminimize - | fstencode --decode=true - PREFIX.codex > PREFIX.minARGSFST.fst"
            else:
                command = "fstprint PREFIX.FST.fst | fstcompile --arc_type=MSEMIRING - | fstencode --encode_labels=ENCL --encode_weights=ENCW - PREFIX.codex | fstminimize - | fstencode --decode=true - PREFIX.codex | fstprint - | fstcompile --arc_type=SEMIRING - > PREFIX.minARGSFST.fst"
        elif semiring==self.semiring:
            command = "fstminimize PREFIX.FST.fst > PREFIX.minFST.fst"
        else:
            command = "fstprint PREFIX.FST.fst | fstcompile --arc_type=MSEMIRING - | fstminimize - | fstprint - | fstcompile --arc_type=SEMIRING - > PREFIX.minARGSFST.fst"
            
        command = command.replace("ENCL",encode_labels.__str__().lower()).replace("ENCW",encode_weights.__str__().lower())
        command = command.replace("MSEMIRING",semiring).replace("SEMIRING",self.semiring)
        command = command.replace("PREFIX",self.prefix).replace("FST",l.lower()).replace("ARGS",args)

        print command
        os.system( command )
        self.final_fst = "minARGSFST".replace("FST",l.lower()).replace("ARGS",args)
        
        return self.final_fst

    def _rmepsilon( self, l ):
        """
          Epsilon remove an input WFST.  
          This is not recommended for large inputs, but playing with it 
          may prove instructive.  Using failure transitions for the LM
          will however, reduce the memory requirements.
        """

        command = "fstrmepsilon PREFIX.FST.fst > PREFIX.rmFST.fst"
        command = command.replace("PREFIX",self.prefix).replace("FST",l.lower())
        print command
        os.system( command )
        self.final_fst = "rmFST".replace("FST",l.lower())
        
        return self.final_fst

    def _push( self, l, tok ):
        """
           Weight push an input WFST.
           By default the build semiring will be used.  This behavior 
            can be over-ridden by explicitly specifying a push semiring for 
            'ps' (log or standard).
           See 'fstpush --help' for more dadvanced behavior.
        """
        
        encode_weights, encode_labels, semiring, args = self._check_opts( tok )

        if encode_weights==True or encode_labels==True:
            if semiring==self.semiring:
                command = "fstencode --encode_labels=ENCL --encode_weights=ENCW PREFIX.FST.fst PREFIX.codex | fstpush --push_weights=true - | fstencode --decode=true - PREFIX.codex > PREFIX.puARGSFST.fst"
            else:
                command = "fstprint PREFIX.FST.fst | fstcompile --arc_type=MSEMIRING - | fstencode --encode_labels=ENCL --encode_weights=ENCW - PREFIX.codex | fstpush --push_weights=true - | fstencode --decode=true - PREFIX.codex | fstprint - | fstcompile --arc_type=SEMIRING - > PREFIX.puARGSFST.fst"
        elif semiring==self.semiring:
            command = "fstpush --push_weights=true PREFIX.FST.fst > PREFIX.puFST.fst"
        else:
            command = "fstprint PREFIX.FST.fst | fstcompile --arc_type=MSEMIRING - | fstpush --push_weights=true - | fstprint - | fstcompile --arc_type=SEMIRING - > PREFIX.puARGSFST.fst"

        command = command.replace("ENCL",encode_labels.__str__().lower()).replace("ENCW",encode_weights.__str__().lower())
        command = command.replace("PSEMIRING",semiring).replace("SEMIRING",self.semiring)
        command = command.replace("PREFIX",self.prefix).replace("FST",l.lower()).replace("ARGS",args)

        print command
        os.system(command)
        self.final_fst = "puARGSFST".replace("FST",l.lower()).replace("ARGS",args)

        return self.final_fst

    def _checkVocab( self ):
        """
           Check the input vocabulary and generate the global
           output symbols table.
        """
        vocab, self.word_osyms, lastid = load_vocab_from_lexicon( self.lexicon, prefix=self.prefix, eps=self.eps, failure=self.failure )
        
        missing = check_arpa_vocab( self.arpa, vocab, self.word_osyms, lastid )
        print "Missing LM words were added to %s: %s" % (self.word_osyms,missing)
        return 
		
    def compileFSTs( self ):
        """
           Generate, compile and register the basic component FSTs.
           Build in a right-to-left fashion.
        """
        if 'L' in self.wfsts and 'G' in self.wfsts:
            self._checkVocab( )
            
        if 'T' in self.wfsts:
            print "Building T: silence class transducer..."
            silclass = Silclass( self.word_osyms, eps=self.eps, silperc=0.117, prefix=self.prefix, failure=self.failure )
            silclass.read_vocab( )
            silclass.generate_silclass( )
            silclass.print_all_syms( )
            print "Compiling T..."
            command = "fstcompile --isymbols=WORDS --osymbols=WORDS --arc_type=SEMIRING PREFIX.t.fst.txt | fstarcsort --sort_type=ilabel - > PREFIX.t.fst"
            command = command.replace("WORDS",self.word_osyms).replace("PREFIX",self.prefix).replace("SEMIRING",self.semiring)
            os.system( command )
        if 'G' in self.wfsts:
            print "Building G: Grammar transducer..."
            if self.regex:
                print "JFSG style grammar."
                jfsg = Parser( self.arpa, prefix=self.prefix, eps=self.eps, algorithm=self.regex )
                jfsg.regex2wfst()
                jfsg.print_isyms()
                command = "fstcompile --arc_type=SEMIRING --acceptor=true --isymbols=WORDS PREFIX.g.fst.txt | fstarcsort --sort_type=ilabel - > PREFIX.g.fst"
                command = command.replace("SEMIRING",self.semiring).replace("PREFIX",self.prefix).replace("WORDS",self.word_osyms)
            else:
                print "ARPA format LM."
                arpa = ArpaLM( self.arpa, "PREFIX.g.fst.txt".replace("PREFIX",self.prefix), prefix=self.prefix, eps=self.eps, boff=self.failure, maxorder=self.order )
                arpa.arpa2fst( )
                arpa.print_all_syms( )
                print "Compiling G..."
                command = "fstcompile --arc_type=SEMIRING --acceptor=true --ssymbols=PREFIX.g.ssyms --isymbols=WORDS PREFIX.g.fst.txt | fstarcsort --sort_type=ilabel - NORMALIZE > PREFIX.g.fst"
                command = command.replace("SEMIRING",self.semiring).replace("PREFIX",self.prefix).replace("WORDS",self.word_osyms).replace("NORMALIZE", self.normalize)
                #os.system(command)
                #print "Normalizing G..."
                #command = "./normalizeG -i PREFIXun.g.fst -o PREFIX.g.fst".replace("PREFIX",self.prefix)
            os.system( command )
        if 'L' in self.wfsts:
            print "Building L: lexicon transducer..."
            L = Lexicon( self.lexicon, prefix=self.prefix, lextype=self.amtype, eps=self.eps, sil=self.sil, failure=self.failure )
            L.generate_lexicon_transducer()
            L.print_all_syms()
            L.print_aux()
            L.print_phones()
            print "Compiling L..."
            command = "fstcompile --arc_type=SEMIRING --isymbols=PREFIX.l.isyms --osymbols=WORDS PREFIX.l.fst.txt | fstclosure - | fstarcsort --sort_type=olabel - > PREFIX.l.fst"
            command = command.replace("SEMIRING",self.semiring).replace("PREFIX",self.prefix).replace("WORDS",self.word_osyms)
            os.system( command )
        if 'C' in self.wfsts:
            if self.amtype=="htk":
                print "Building C: HTK-format context-dependency transducer..."
                C = ContextDependency( 
                    "PREFIX.phons".replace("PREFIX",self.prefix), "PREFIX.aux".replace("PREFIX",self.prefix), 
                    tiedlist=self.tiedlist, prefix=self.prefix, eps=self.eps, sil=self.sil, auxout=self.auxout )
                C.generate_deterministic()
                C.print_all_syms()
                print "Generating HTK input symbols..."
                make_hmmsyms( self.hmmdefs, self.eps, self.prefix, C.aux )
            elif self.amtype=="sphinx":
                print "Building C: Sphinx-format context-dependency transducer..."
                C = ContextDependencySphinx( self.tiedlist, "PREFIX.aux".replace("PREFIX",self.prefix), prefix=self.prefix, auxout=self.auxout )
                C.generate_deterministic()
                C.print_all_syms()
            print "Compiling C..."
            if self.auxout>0 or 'H' in self.wfsts:
                command = "fstcompile --arc_type=SEMIRING --ssymbols=PREFIX.c.ssyms --isymbols=PREFIX.c.isyms --osymbols=PREFIX.l.isyms PREFIX.c.fst.txt | fstarcsort --sort_type=olabel - > PREFIX.c.fst"
            else:
                command = "fstcompile --arc_type=SEMIRING --ssymbols=PREFIX.c.ssyms --isymbols=PREFIX.hmm.syms --osymbols=PREFIX.l.isyms PREFIX.c.fst.txt | fstarcsort --sort_type=olabel - > PREFIX.c.fst"
            command = command.replace("SEMIRING",self.semiring).replace("PREFIX",self.prefix) 
            os.system( command )
        if 'H' in self.wfsts:
            print "Building H: Sphinx format HMM transducer..."
            H = hmm2wfst( 
                self.tiedlist, amtype=self.amtype, 
                eps=self.eps, aux_file="PREFIX.aux".replace("PREFIX",self.prefix), 
                prefix=self.prefix, auxout=self.auxout, isyms_file="PREFIX.hmm.syms".replace("PREFIX",self.prefix)
                )
            H.mdef2wfst( )
            if self.auxout:
                command = "fstcompile --arc_type=SEMIRING --isymbols=PREFIX.h.isyms --osymbols=PREFIX.hmm.syms PREFIX.h.fst.txt | fstarcsort --sort_type=olabel - > PREFIX.h.fst"
                H.makemapper( )
            else:
                command = "fstcompile --arc_type=SEMIRING --osymbols=PREFIX.hmm.syms PREFIX.h.fst.txt | fstarcsort --sort_type=olabel - > PREFIX.h.fst"
            H.write_isyms( )
            command = command.replace("SEMIRING",self.semiring).replace("PREFIX",self.prefix)
            print "Compiling H..."
            os.system( command )
        return

    def convertTcubedJuicer( self ):
        """
            Convert the final cascade to AT&T format or txt format
            for use inside of TCubed or Juicer.
        """
        
        if self.convert.lower()=="t":
            print "Converting final cascade PREFIX.FINAL to AT&T format...".replace("FINAL",self.final_fst).replace("PREFIX",self.prefix)
            command = "fstprint PREFIX.FINAL.fst | fsmcompile -t > PREFIX.FINAL.fsm".replace("FINAL",self.final_fst).replace("PREFIX",self.prefix)
            os.system( command )
            print "PREFIX.FINAL.fsm".replace("FINAL",self.final_fst).replace("PREFIX",self.prefix)
        elif self.convert.lower()=="j": 
            print "Converting final cascade PREFIX.FINAL to text format...".replace("FINAL",self.final_fst).replace("PREFIX",self.prefix)
            command = "fstprint PREFIX.FINAL.fst > PREFIX.FINAL.fst.txt".replace("FINAL",self.final_fst).replace("PREFIX",self.prefix)
            os.system( command )
            print "PREFIX.FINAL.fst.txt".replace("FINAL",self.final_fst).replace("PREFIX",self.prefix)
        elif self.convert.lower()=="tj" or self.tj.lower()=="jt":
            print "Converting final cascade PREFIX.FINAL to AT&T format...".replace("FINAL",self.final_fst).replace("PREFIX",self.prefix)
            command = "fstprint PREFIX.FINAL.fst | fsmcompile -t > PREFIX.FINAL.fsm".replace("FINAL",self.final_fst).replace("PREFIX",self.prefix)
            os.system( command )
            print "PREFIX.FINAL.fsm".replace("FINAL",self.final_fst).replace("PREFIX",self.prefix)
            print "Converting final cascade PREFIX.FINAL to text format...".replace("FINAL",self.final_fst).replace("PREFIX",self.prefix)
            command = "fstprint PREFIX.FINAL.fst > PREFIX.FINAL.fst.txt".replace("FINAL",self.final_fst).replace("PREFIX",self.prefix)
            os.system( command )
            print "PREFIX.FINAL.fst.txt".replace("FINAL",self.final_fst).replace("PREFIX",self.prefix)
        else:
            print "Conversion command: %s is not a valid command.  Aborting." % self.tj
            return
        print "PREFIX.word.syms".replace("PREFIX",self.prefix)
        return
            
def print_args( args ):
    print "Running with the following arguments:"
    for attr, value in args.__dict__.iteritems():
        print attr, "=", value
    return 
    

if __name__=="__main__":
    import sys, operator, re, argparse

    example = """./transducersaurus.py --tiedlist tiedlist --hmmdefs hmmdefs --lexicon lexicon.dic --grammar lm3g.arpa --prefix test --command "(C*det(L*G)" """
    grammar_info = """
WFST Cascade Grammar description:

Examples: 
    CLGT cascade using static lookahead composition:
          (C*det(L)).(G*T)
    CLG cascade using standard composition, one call to determinize:
          C*det(L*G)
    CLGT cascade with final minimization and determinization:
          min(det((C*det(L)).(G*T)))
    CLGT cascade with final minimization and determinization, minimization will be performed with label-encoding:
          min[labels](det((C*det(L)).(G*T)))
    HCLGT cascade with final determinization and pushing, pushing will be performed in the log semiring, 
      with label-encoding, the first call to determinize will be performed in the log semiring, using weight-encoding:
          push[log,labels](det(min(H*(det((C*det_lw(L)).(G*T))))))
          
The WFST compilation DSL supports the following WFST components:
  * H - HMM level transducer (Sphinx format only)
  * C - Context-dependencty transducer (Sphinx or HTK)
  * L - Lexicon transducer (Sphinx or HTK)
  * G - Grammar, ARPA format stochastic langauge models
  * T - Silence class transducer
  
Operations:
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

It is also possible to specify label and/or weight encoding for the 'push', 'det', and 'min' operations:
  * shorthand, using 'min' as an example:
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
    parser = argparse.ArgumentParser(description=example, epilog=grammar_info, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--amtype',     "-a", help='Acoustic model type.  May be set to "htk" or "sphinx".', default="htk" )
    parser.add_argument('--auxout',     "-o", help='Generate explicit input aux labels for the context-dependency transducer. Will automatically generate appropriate symbols based on cascade requirements.  Supported values are: "0"=No input aux symbols; "1"=Map c-level triphones to the AM, generate no input aux symbols; "2"=Generate input aux symbols for C, map arcs to AM, map arcs to H level; "3"=Determine behaviour automatically (recommended).', default=3, type=int )
    parser.add_argument('--basedir',    "-b", help='Base directory for model storage.', default="", required=False)
    parser.add_argument('--command',    "-c", help='Build command specifying OpenFST composition and optimization operations.\nValid operators are\n\t"*" - composition,\n\t"." - static on-the-fly composition,\n\t"det" - determinization,\n\t"min" - minimization', required=True)
    parser.add_argument('--version',    "-V", help='Print Version information and exit.', action="version", version="transducersaurus.py: V%s"%(__version__) )
    parser.add_argument('--convert',    "-n", help='Convert the final cascade to either Juicer or TCubed format.  Valid values are "t" (tcubed), "j" (juicer) or "tj" for both.', default=None, required=False )
    parser.add_argument('--eps',        "-e", help='Epsilon symbol.', default="<eps>")
    parser.add_argument('--failure',    "-f", help='Use failure transitions to represent back-off arcs in the LM.', default=None, required=False )
    parser.add_argument('--grammar',    "-g", help='An input grammar file.  May be an ARPA format LM or a JFSG style grammar.', required=True)
    parser.add_argument('--hmmdefs',    "-d", help='hmmdefs file.  Needed for HTK acoustic models.', default=None, required=False )
    parser.add_argument('--lexicon',    "-l", help='List of words to transcribe.', required=True)
    parser.add_argument('--no_compile', "-z", help='Specify whether or not to run the component compilation routines.  Set to false if you have already built your components and just want to combine and optimize them.', default=False, action="store_true")
    parser.add_argument('--prefix',     "-p", help='A file prefix.  Will be prepended to all model files created during cascade generation.', default="test")
    parser.add_argument('--semiring',   "-r", help='Semiring to use during cascade construction. May be set to "log" or "standard" (tropical).  Use "standard" if your build command includes OTF composition.', default="log" )
    parser.add_argument('--order',      "-O", help='Build N-grams only up to "--order". Default behavior is to build *all* N-grams.', default=0, type=int )
    parser.add_argument('--sil',        "-s", help='Silence monophone symbol.', default="sil")
    parser.add_argument('--jfsg',       "-j", help='The grammar is a regular expression/JFSG style grammar. Specify "classic" or "new" for the algorithm.', default=None )
    parser.add_argument('--tiedlist',   "-t", help='Acoustic model tied list. mdef file for Sphinx, tiedlist file for HTK', required=True)
    parser.add_argument('--normalize',  "-N", help='Normalize arc weights for each state in the LM WFSA.', default=False, action="store_true" )
    parser.add_argument('--verbose',    "-v", help='Verbose mode.', default=False, action="store_true")
    args = parser.parse_args()

    if "version" in args.__dict__:
        print "Transducersaurus version:", __version__
        sys.exit()
    if args.amtype=="htk" and args.hmmdefs==None:
        print "HTK format AMs require an hmmdefs file.  Please specify one."
        sys.exit()
    if '.' in args.command and args.semiring=="log":
        print """WARNING: Your build command includes at least one call to OTF compose, but you have specified the log semiring.  
       Determinization of the lexicon transducer will be performed in the tropical semiring."""
    if args.verbose:
        print "Version:", __version__
        print_args( args )
	
    
    cascade = GenerateCascade( 
        args.tiedlist, 
        args.lexicon, 
        args.grammar, 
        args.command, 
        hmmdefs=args.hmmdefs, 
        prefix=args.prefix, 
        amtype=args.amtype, 
        semiring=args.semiring, 
        order=args.order,
        eps=args.eps,
        sil=args.sil,
        auxout=args.auxout,
        failure=args.failure,
        basedir=args.basedir,
        convert=args.convert,
        regex=args.jfsg,
        normalizeG=args.normalize
    )
    if args.no_compile==False:
        cascade.compileFSTs( )
    cascade.generateCascade( )
