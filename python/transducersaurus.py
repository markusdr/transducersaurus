#!/usr/bin/python
import re, os
from checkVocab import *
from silclass2fst import Silclass 
from arpa2fst import ArpaLM
from lexicon2fst import Lexicon
from cd2fst import ContextDependency
from cd2fstSphinx import ContextDependencySphinx
from hmm2wfst import hmm2wfst


class GenerateCascade( ):
    """
	   Generate WFST-based cascades from an ARPA-format LM, 
	   pronunciation lexicon and acoustic model information.
	   Supports both Sphinx and HTK format acoustic models.
	   
	   Additional options include a built-in combination and 
	   optimization routine parser.
    """
    
    def __init__( self, tiedlist, lexicon, arpa, buildcommand, hmmdefs=None, prefix="test", basedir="", 
                  amtype="htk", semiring="log", failure=None, auxout=3, encode_weights=False, encode_labels=False,
                  eps="<eps>", sil="sil", convert=None, p_semiring=None, m_semiring=None ):
        self._grammar       = re.compile(r"\s*(?:(push|rmeps|det|min|\*|\.)|([HCLGT])|([\)\(]))")
        self.tiedlist       = tiedlist
        self.lexicon        = lexicon
        self.arpa           = arpa
        self.buildcommand   = buildcommand.replace(" ","")
        self.hmmdefs        = hmmdefs
        self.basedir        = basedir
        self.prefix         = self._set_prefix(prefix)
        self.amtype         = amtype
        self.semiring       = semiring
        self.p_semiring     = self._set_p_semiring(p_semiring)
        self.m_semiring     = self._set_m_semiring(m_semiring)
        self.encode_weights = encode_weights
        self.encode_labels  = encode_labels
        self.failure        = failure
        self.eps            = eps
        self.sil            = sil
        self.auxout         = self._set_aux( auxout )
        self.wfsts          = set([])
        self.postfix        = self._toPostfix(self.buildcommand)
        self.convert        = convert
        self.word_osyms	    = None
        self.am_isyms       = None
        
    def _set_p_semiring( self, p_semiring ):
        """Set the semiring to use for pushing, if applicable."""
        
        if p_semiring==None:
            return self.semiring
        
        return p_semiring

    def _set_m_semiring( self, m_semiring ):
        """Set the semiring to use for pushing, if applicable."""
        
        if m_semiring==None:
            return self.semiring
        
        return m_semiring
            
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
            self.basedir = prefix+"-"+self.buildcommand.replace("(","a").replace(")","b").replace("*","c").replace(".","o")
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
        prec = { 'det':10, 'min':10, 'rmeps':10, 'push':10, '*':5, '.':5 }
        if prec[op]<=prec[top]:
            return True
        else:
            return False

    def _toPostfix( self, program ):
        """
	   Tokenize and convert an infix expression to postfix notation
	   based on the regex grammar specified in self._grammar
        """
        tokens = []
        stack  = []
        for op, fst, paren in  self._grammar.findall(program):
            if op:
                while len(stack)>0 and not stack[-1]=="(":
                    if self._opGTE( stack[-1], op ):
                        tokens.append(stack.pop())
                    else:
                        break
                stack.append(op)
            elif fst:
                self.wfsts.add(fst)
                tokens.append(fst)
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
            elif tok=="det":
                l = stack.pop()
                stack.append(self._determinize(l))
            elif tok=="min":
                l = stack.pop()
                stack.append(self._minimize(l))
            elif tok=="push":
                l = stack.pop()
                stack.append(self._push(l))
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

        print "Relabeling right-hand composition operand..."
        command = "fstrelabel --relabel_ipairs=PREFIX.FST1FST2.rlbl.txt PREFIX.FST2.fst | fstarcsort - > PREFIX.FST2.rlbl.fst"
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

    def _determinize( self, l ):
        """
           Run determinization on an input WFST.
        """
        if l.lower()=="l" and self.semiring=="log":
            #Determinizing an un-weighted lexicon in the log semiring will cause chaos
            command = "fstprint PREFIX.FST.fst | fstcompile - | fstdeterminize - | fstprint - | fstcompile --arc_type=log - > PREFIX.detFST.fst" 
        else:
            command = "fstdeterminize PREFIX.FST.fst > PREFIX.detFST.fst" 
        command = command.replace("PREFIX",self.prefix).replace("FST",l.lower())
        print command
        os.system( command )
        self.final_fst = "detFST".replace("FST",l.lower())
        return self.final_fst

    def _minimize( self, l ):
        """
           Run minimization on an input WFST.  By default this 
           also calls 'fstencode', encoding both labels and weights.
           The result could be further mininimized by not encoding these
           portions, however it tends to be more costly to do so
           and the additional benefits are generally limited.  

           At some point I'll add the encoding options to transducersaurus.
           In the meantime, the default behavior can be modified by editing the 
           command value below.
        """
        command = ""
        if self.m_semiring==self.semiring:
            command = "fstencode --encode_labels=ENCL --encode_weights=ENCW PREFIX.FST.fst PREFIX.codex | fstminimize - | fstencode --decode=true - PREFIX.codex > PREFIX.minFST.fst"
        else:
            command = "fstprint PREFIX.FST.fst | fstcompile --arc_type=MSEMIRING - | fstencode --encode_labels=ENCL --encode_weights=ENCW - PREFIX.codex | fstminimize - | fstencode --decode=true - PREFIX.codex | fstprint - | fstcompile --arc_type=SEMIRING - > PREFIX.minFST.fst"
        command = command.replace("ENCL",self.encode_labels.__str__().lower()).replace("ENCW",self.encode_weights.__str__().lower())
        command = command.replace("MSEMIRING",self.m_semiring).replace("SEMIRING",self.semiring)
        command = command.replace("PREFIX",self.prefix).replace("FST",l.lower())
        print command
        os.system( command )
        self.final_fst = "minFST".replace("FST",l.lower())
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

    def _push( self, l ):
        """
           Weight push an input WFST.
           By default the build semiring will be used.  This behavior 
            can be over-ridden by explicitly specifying a push semiring for 
            'ps' (log or standard).
           See 'fstpush --help' for more dadvanced behavior.
        """
        
        if self.p_semiring==self.semiring:
            command = "fstpush --push_weights=true PREFIX.FST.fst > PREFIX.puFST.fst"
        else:
            command = "fstprint PREFIX.FST.fst | fstcompile --arc_type=PSEMIRING - | fstpush --push_weights=true - | fstprint - | fstcompile --arc_type=SEMIRING - > PREFIX.puFST.fst"
        command = command.replace("PREFIX",self.prefix).replace("FST",l.lower()).replace("PSEMIRING",self.p_semiring).replace("SEMIRING",self.semiring)
        print command
        os.system(command)
        self.final_fst = "puFST".replace("FST",l.lower())

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
            print "Building G: ARPA LM transducer..."
            arpa = ArpaLM( self.arpa, "PREFIX.g.fst.txt".replace("PREFIX",self.prefix), prefix=self.prefix, eps=self.eps, boff=self.failure)
            arpa.arpa2fst( )
            arpa.print_all_syms( )
            print "Compiling G..."
            command = "fstcompile --arc_type=SEMIRING --acceptor=true --ssymbols=PREFIX.g.ssyms --isymbols=WORDS PREFIX.g.fst.txt | fstarcsort --sort_type=ilabel - > PREFIX.g.fst"
            command = command.replace("SEMIRING",self.semiring).replace("PREFIX",self.prefix).replace("WORDS",self.word_osyms)
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
    parser = argparse.ArgumentParser(description=example)
    parser.add_argument('--amtype',     "-a", help='Acoustic model type.  May be set to "htk" or "sphinx".', default="htk" )
    parser.add_argument('--auxout',     "-o", help='Generate explicit input aux labels for the context-dependency transducer. Will automatically generate appropriate symbols based on cascade requirements.  Supported values are: "0"=No input aux symbols; "1"=Map c-level triphones to the AM, generate no input aux symbols; "2"=Generate input aux symbols for C, map arcs to AM, map arcs to H level; "3"=Determine behaviour automatically (recommended).', default=3, type=int )
    parser.add_argument('--basedir',    "-b", help='Base directory for model storage.', default="", required=False)
    parser.add_argument('--command',    "-c", help='Build command specifying OpenFST composition and optimization operations.\nValid operators are\n\t"*" - composition,\n\t"." - static on-the-fly composition,\n\t"det" - determinization,\n\t"min" - minimization', required=True)
    parser.add_argument('--convert',    "-n", help='Convert the final cascade to either Juicer or TCubed format.  Valid values are "t" (tcubed), "j" (juicer) or "tj" for both.', default=None, required=False )
    parser.add_argument('--eps',        "-e", help='Epsilon symbol.', default="<eps>")
    parser.add_argument('--failure',    "-f", help='Use failure transitions to represent back-off arcs in the LM.', default=None, required=False )
    parser.add_argument('--grammar',    "-g", help='An ARPA format language model.', required=True)
    parser.add_argument('--hmmdefs',    "-d", help='hmmdefs file.  Needed for HTK acoustic models.', default=None, required=False )
    parser.add_argument('--lexicon',    "-l", help='List of words to transcribe.', required=True)
    parser.add_argument('--no_compile', "-z", help='Specify whether or not to run the component compilation routines.  Set to false if you have already built your components and just want to combine and optimize them.', default=False, action="store_true")
    parser.add_argument('--prefix',     "-p", help='A file prefix.  Will be prepended to all model files created during cascade generation.', default="test")
    parser.add_argument('--semiring',   "-r", help='Semiring to use during cascade construction. May be set to "log" or "standard" (tropical).  Use "standard" if your build command includes OTF composition.', default="log" )
    parser.add_argument('--psemiring',  "-u", help="Semiring to use for pushing operations.  Defaults to the value of '--semiring'.", default=None )
    parser.add_argument('--msemiring',  "-m", help="Semiring to use for minimization operations.  Defaults to the value of '--semiring'.", default=None )
    parser.add_argument('--ew',               help="Argument for fstminimize: encode_weights. Defaults to False.", default=False, action="store_true" )
    parser.add_argument('--el',               help="Argument for fstminimize: encode_labels. Defaults to False.", default=False, action="store_true" )
    parser.add_argument('--sil',        "-s", help='Silence monophone symbol.', default="sil")
    parser.add_argument('--tiedlist',   "-t", help='Acoustic model tied list. mdef file for Sphinx, tiedlist file for HTK', required=True)
    parser.add_argument('--verbose',    "-v", help='Verbose mode.', default=False, action="store_true")
    args = parser.parse_args()

    if args.amtype=="htk" and args.hmmdefs==None:
        print "HTK format AMs require an hmmdefs file.  Please specify one."
        sys.exit()
    if '.' in args.command and args.semiring=="log":
        print """WARNING: Your build command includes at least one call to OTF compose, but you have specified the log semiring.  
       Determinization of the lexicon transducer will be performed in the tropical semiring."""
    if args.verbose:
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
        p_semiring=args.psemiring,
        m_semiring=args.msemiring,
        encode_weights=args.ew,
        encode_labels=args.el,
        eps=args.eps,
        sil=args.sil,
        auxout=args.auxout,
        failure=args.failure,
        basedir=args.basedir,
        convert=args.convert
    )
    if args.no_compile==False:
        cascade.compileFSTs( )
    cascade.generateCascade( )
	


