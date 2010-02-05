#!/usr/bin/python
#CascadeTools V-0.1

"""
Copyright (c) 2010 Josef R. Novak
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions
are met:
1. Redistributions of source code must retain the above copyright
   notice, this list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright
   notice, this list of conditions and the following disclaimer in the
   documentation and/or other materials provided with the distribution.
3. The name of the author may not be used to endorse or promote products
   derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE AUTHOR ``AS IS'' AND ANY EXPRESS OR
IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES
OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import openfst, re
from collections import defaultdict
import logging, sys, re, math
#This is only necessary for the Sphinx D mapper. 
#Would probably be best to remove the dependency at some point
from SphinxTrain.s3mdef import S3Mdef

def setup_logger( verbose=None, loggerID="" ):
    LEVELS = {
        '5': logging.DEBUG,
        '4': logging.INFO,
        '3': logging.WARNING,
        '2': logging.ERROR,
        '1': logging.CRITICAL
        }
    level   = LEVELS.get(verbose, logging.NOTSET)
    logger  = logging.getLogger(loggerID)
    logger.setLevel(level)
    handler = logging.StreamHandler()
    handler.setLevel(level)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s") 
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

class Arpa2FST():
    def __init__( self, arpalm, order=3, esym="-", start="<start>", sStart="<s>", sEnd="</s>", verbose="4", isyms=None, loggerID="default" ):
        #Setup logging
        self.logger = setup_logger( verbose=verbose, loggerID="CascadeTools.G.%s"%loggerID )
        #Init
        self.arpalm = open(arpalm,"r")
        self.esym   = esym
        self.start  = start
        self.sStart = sStart
        self.sEnd   = sEnd
        #This should *DEFINITELY* be done in the log semiring, as described in P. Dixon SLP 2009
        # as should all the other wfsts, and optimization operations.
        # Unfortunately the bindings do not currently support it.
        self.wfst   = openfst.StdVectorFst()
        self.isyms  = isyms
        self._init_wfst()
        self.arpaHeader = {'maxOrd':0}

    def generate_lm( self ):
        self._read_arpa_header()
        for i in xrange(self.arpaHeader['maxOrd']):
            self._process_Ngrams()
        self.arpalm.close()
        return
    
    def _init_wfst( self ):
        """Initialize the G wfst.  This requires a little bit of work."""
        self.state  = self.wfst.Start()
        self.state  = self.wfst.AddState()
        self.wfst.SetStart(self.state)
        self.ssyms  = openfst.SymbolTable("ssyms")
        self.sStartState = self.wfst.AddState()
        self.fstate = self.wfst.AddState()
        self.estate = self.wfst.AddState()
        self.ssyms.AddSymbol(self.start, self.state)
        self.ssyms.AddSymbol(self.sStart, self.sStartState)
        self.ssyms.AddSymbol(self.sEnd, self.fstate)
        if not self.isyms:
            self.isyms  = openfst.SymbolTable("isyms")
            self.isyms.AddSymbol("-")
        self.wfst.AddArc(self.wfst.Start(), self.isyms.AddSymbol(self.sStart), self.isyms.AddSymbol(self.sStart),  0.0, self.sStartState)
        self.wfst.SetFinal(self.fstate,0.0)
        self.ssyms.AddSymbol(self.esym,self.estate)
        return

    def _read_arpa_header( self ):
        headerBegin = False
        headerEnd   = False
        for line in self.arpalm:
            if headerBegin==True:
                line = line.replace("ngram ","").strip()
                if line=="":
                    headerEnd=True
                    return
                ord, num = line.split("=")
                self.arpaHeader[ord] = int(num)
                if int(ord)>self.arpaHeader['maxOrd']:
                    self.arpaHeader['maxOrd'] = int(ord)
            if re.match(r"\\data\\",line):
                headerBegin=True
        return

    def _process_Ngrams( self ):
        """Process individual Ngram orders.  This is where the "interesting" stuff happens."""
        self.c_ord = 0
        gramBegin   = False
        for line in self.arpalm:
            line = line.strip()
            if gramBegin:
                if line=="":
                    return
                grams = re.split(r"\s+",line)
                if self.c_ord==1:
                    weight = grams.pop(0)
                    boff   = grams.pop(-1)
                    self._write_arc( grams, [self.esym], self.esym, float(boff)  )
                    self._write_arc( [self.esym], grams, grams[0], float(weight) )
                else:
                    weight = grams.pop(0)
                    if self.c_ord<self.arpaHeader['maxOrd']:
                        boff   = grams.pop(-1)
                        self._write_arc( grams[:self.c_ord], grams[self.c_ord-1:], grams[-1], float(boff) )
                        self._write_arc( grams[:self.c_ord-1], grams[self.c_ord-2:], self.esym, float(weight) )
                    else:
                        self._write_arc( grams[:self.c_ord-1], grams[self.c_ord-self.arpaHeader['maxOrd']+1:], grams[-1], float(weight) )
            if re.match(r"\\[0-9]+\-grams:",line):
                gramBegin=True
                line = line.replace("\\","").replace("-grams:","")
                self.c_ord = int(line)
                self.logger.info( "Current order: %d" % self.c_ord )
        return
    
    def _write_arc( self, input, output, word, weight ):
        """
           Write and Arc.  The Allauzen 2003 paper describes an 'exact' epsilon free algorithm.
           This version ignores it in favor of simplicity.  This is a bit of a hack.
        """

        #These arcs screw up the network.  It isn't 100% clear they should be ignored but...
        if weight==-99:                          return
        if '</s>' in output:                     output = ['</s>']
        if input==['</s>']:                      return
        if word==self.esym and output==['</s>']: return

        weight = math.log(10.0) * -1.0 * weight
        issym  = "_".join(input)
        #This seems to work better, although strictly speaking it's rather questionable.
        ossym  = "_".join(output)
        if issym=="": issym = self.esym
        if ossym=="": ossym = self.esym
        if self.ssyms.Find(issym)>-1:
            istate = self.ssyms.Find(issym)
        else:
            istate = self.wfst.AddState()
            self.ssyms.AddSymbol(issym, istate)
        if self.ssyms.Find(ossym)>-1:
            ostate = self.ssyms.Find(ossym)
        else:
            ostate = self.wfst.AddState()
            self.ssyms.AddSymbol(ossym,ostate)
        isym   = self.isyms.AddSymbol(word)
        self.logger.debug("%s %s %s %f" % (issym, ossym, word, weight))
        self.wfst.AddArc(istate, isym, isym, weight, ostate)
        return

class ContextDependency():
    """Context Dependency transducer."""
    
    def __init__( self, phons, aux, verbose='4', start="<start>", isyms=None, basename="test",
                  osyms=None, ssyms=None, ofile=None, invert=True, determinize=True, eps="-", loggerID="default" ):
        #Setup logging
        self.logger = setup_logger( verbose=verbose, loggerID="CascadeTools.C.%s"%loggerID )
        #Init
        self.wfst  = openfst.StdVectorFst()
        self.state = self.wfst.Start()
        self.state = self.wfst.AddState()
        self.wfst.SetStart(self.state)
        self.phons = set(phons)
        self.aux   = set(aux)
        self.start = start
        self.eps   = eps
        self.isyms = self._init_syms( basename, isyms )
        self.osyms = self._init_syms( basename, osyms )
        self.ssyms = self._init_syms( basename, ssyms )
        self.ssyms.AddSymbol(self.start, self.state)
        self.invert = invert
        self.determinize = determinize

    def _init_syms( self, basename, syms=None ):
        """Initialize the symbols table.  The epsilon symbol must be set."""
        if syms==None:
            syms = openfst.SymbolTable(basename)
            syms.AddSymbol("-")  #This should probably be done at object initialization as it is required.
            for aux in self.aux:
                syms.AddSymbol(aux)
        return syms
                   
    def generate_deterministic( self ):
        """
           Generate the context dependency transducer.
             lp: left-monophone
             mp: middle-monophone
             rp: right-monophone
        """
        self.logger.info("Generating deterministic triphone context-dependency transducer...")
        for lp in self.phons:
            #Initial arcs
            self._make_arc( self.start, self.eps, lp )
            self._do_aux( self.eps, lp )
            #Monophone arcs
            self._make_arc( self.eps, lp, self.eps )
            self._make_final( lp, self.eps )
            for mp in self.phons:
                #Initial to Internal arcs
                self._make_arc( self.eps, lp, mp )
                #Internal to Final arcs
                self._make_arc( lp, mp, self.eps )
                self._do_aux( lp, mp )
                for rp in self.phons:
                    #Internal to Internal arcs
                    self._make_arc( lp, mp, rp )
        return

    def generate_non_deterministic( self ):
        self.logger.info("Generating Non-deterministic triphone context-dependency transducer...")
        for lp in self.phons:
            #Monophone arcs
            self._make_arc( self.start, lp, self.eps )
            self._make_final( lp, self.eps )
            self._do_aux( lp, self.eps )
            for mp in self.phons:
                #Initial arcs
                self._make_arc( self.start, lp, mp )
                #Internal to final
                self._make_arc( lp, mp, self.eps )
                self._do_aux( lp, mp )
                for rp in self.phons:
                    #Internal to internal arcs
                    self._make_arc( lp, mp, rp )
        return

    def _do_aux( self, lp, rp ):
        """Generate auxiliary symbol arcs."""
        issym = lp+','+rp
        if self.ssyms.Find( issym )==-1:
            istate = self.wfst.AddState()
            ostate = istate
            self.ssyms.AddSymbol( issym, istate )
        else:
            istate = self.ssyms.Find( issym )
            ostate = istate
        for a in self.aux:
            isym = self.isyms.AddSymbol(a)
            osym = self.osyms.AddSymbol(a)
            self.wfst.AddArc(istate-1, isym, osym, 0.0, ostate-1)
        return

    def _make_final( self, lp, rp ):
        """Make a final state."""
        fssym = lp+','+rp
        if self.ssyms.Find( fssym )==-1:
            raise "Requested final state does not exist: %s" % fssym
        fstate = self.ssyms.Find( fssym )
        self.wfst.SetFinal(fstate-1,0.0)
        return
    
    def _make_arc( self, lp, mp, rp ):
        """
           Generate an arc.
             lp: left-monophone
             mp: middle-monophone
             rp: right-monophone
        """
        issym = lp+','+mp
        ossym = mp+','+rp
        isym   = lp+'-'+mp+'+'+rp
        if self.determinize:
            osym = rp
            if lp==self.start:
                isym = self.eps
        else:
            osym = mp
            if lp==self.start:
                istate = lp+',*'
                isym   = self.eps+'-'+mp+'+'+rp
                
        #We invert by default.  Undo this if requested.
        if not self.invert:
            tmp  = isym
            isym = osym
            osym = tmp
        #Add symbols/states as needed.
        if self.ssyms.Find( issym )==-1:
            istate = self.wfst.AddState()
            self.ssyms.AddSymbol( issym, istate )
        else:
            istate = self.ssyms.Find( issym )
        if self.ssyms.Find( ossym )==-1:
            ostate = self.wfst.AddState()
            self.ssyms.AddSymbol( ossym, ostate )
        else:
            ostate = self.ssyms.Find( ossym )
        isym   = self.isyms.AddSymbol( isym )
        osym   = self.osyms.AddSymbol( osym )
        #Finally generate the arc
        self.wfst.AddArc( istate-1, isym, osym, 0.0, ostate-1 )
        return


class Lexicon( ):
    """Build a lexicon transducer."""
    def __init__( self, dictfile, dict_type="cmu", basename="testapp", lextype="default", isyms=None, osyms=None, verbose='4', loggerID="" ):
        #Setup logging
        self.logger = setup_logger( verbose=verbose, loggerID="CascadeTools.L.%s.%s"%(dict_type,loggerID) )
        #Init
        self.LEXTYPES = { 
            'default':self._gen_entry,
            'noloop' :self._gen_entry_no_loop,
            'allaux' :self._gen_entry_all_aux,
            'nosync' :self._gen_entry_all_aux_no_loop_no_sync,
            }
        self.lextype = lextype
        self.gen_entry = self.LEXTYPES.get(self.lextype, 'default')
        self.wfst  = openfst.StdVectorFst()
        self.state = self.wfst.Start()
        self.state = self.wfst.AddState()
        self.wfst.SetStart(self.state)
        self.lextype = lextype
        self.isyms = self._init_syms("%s.isyms"%basename, syms=isyms)
        self.isyms.AddSymbol("<unk>")
        self.isyms.AddSymbol("<UNK>")
        self.osyms = self._init_syms("%s.osyms"%basename, syms=osyms)
        self.aux   = set([])
        self.phons = set([])
        self.dict_type = dict_type
        self.load_dict = { 
            "cmu" : self._load_cmudict,
            "htk" : self._load_htkdict,
            }                
        self.pdict = self.load_dict[dict_type](dictfile)

    def _init_syms( self, basename, syms=None ):
        """Initialize the symbols table.  The epsilon symbol must be set."""
        if syms==None:
            syms = openfst.SymbolTable(basename)
        syms.AddSymbol("-")  #This should probably be done at object initialization as it is required.
        return syms
                   
    def generate_lexicon_transducer( self ):
        """Generate the lexicon transducer."""
        self.logger.info("Generating lexicon transducer of type: %s" % self.lextype)
        for pron in self.pdict:
            self.gen_entry( pron )
        if self.lextype=='default' or self.lextype=='allaux':
            self.wfst.SetFinal(self.wfst.Start(),0.0)
        return 

    def write_lexicon_transducer( self, fstname ):
        """Print out the fst."""
        self.logger.info("Printing the WFST to: %s" % fstname)
        self.wfst.Write(fstname)
        
    def _gen_entry_no_loop( self, pron ):
        """
           Generate entries for a pronunciation.  
           Less compact, and requires closure before it can be composed.
        """
        first_word = self.pdict[pron].pop(0)
        #An initial monophone pronunciation
        if len(pron)==1:
            self.phons.add(pron[0])
            state = self.wfst.AddState()
            self.wfst.AddArc(
                self.wfst.Start(),
                self.isyms.AddSymbol(pron[0]),
                self.osyms.AddSymbol(first_word),
                0.0,
                state
                )
            self.wfst.SetFinal(state,0.0)
        #An initial multiphone pronunciation
        elif len(pron)>1:
            self.phons.add(pron[0])
            state = self.wfst.AddState()
            self.wfst.AddArc(
                self.wfst.Start(),
                self.isyms.AddSymbol(pron[0]),
                self.osyms.AddSymbol(first_word),
                0.0,
                state
                )
            for j in xrange(0,len(pron)-1):
                nextstate = self.wfst.AddState()
                self.phons.add(pron[j+1])
                self.wfst.AddArc( state, self.isyms.AddSymbol(pron[j+1]), openfst.epsilon, 0.0, nextstate )
                state = nextstate
            self.wfst.SetFinal(nextstate,0.0)
            self.phons.add(pron[len(pron)-1])
        #Iterate through any additional pronunciations
        for i,word in enumerate( self.pdict[pron] ):
            state = self.wfst.AddState()
            self.wfst.AddArc( self.wfst.Start(), self.isyms.AddSymbol(pron[0]), self.osyms.AddSymbol(word), 0.0, state )
            self.phons.add(pron[0])
            for j in xrange(0,len(pron)-1):
                nextstate = self.wfst.AddState()
                self.phons.add(pron[j+1])
                self.wfst.AddArc( state, self.isyms.AddSymbol(pron[j+1]), openfst.epsilon, 0.0, nextstate )
                state = nextstate
            nextstate = self.wfst.AddState()
            self.wfst.AddArc( state, self.isyms.AddSymbol("#%d"%i), openfst.epsilon, 0.0, nextstate )
            self.wfst.SetFinal( nextstate, 0.0 )
            self.aux.add("#%d"%i)
        return

    def _gen_entry( self, pron ):
        """
           Generate entries for a pronunciation.  The sphinx entries can be more compact.
           This is the most concise but least clear entry-type.  It creates an 
           epsilon-free, closed lexicon transducer which simply loops through the start state.
           Auxiliary symbols are only added where absolutely necessary, 
        """

        if self.dict_type=="cmu":
            #We can squeeze a little more efficiency out of the sphinx entries thanks to
            # the positional triphones.
            first_word = self.pdict[pron].pop(0)
            #An initial monophone pronunciation
            if len(pron)==1:
                self.phons.add(pron[0])
                self.wfst.AddArc(
                    self.wfst.Start(),
                    self.isyms.AddSymbol(pron[0]),
                    self.osyms.AddSymbol(first_word),
                    0.0,
                    self.wfst.Start()
                    )
             #An initial multiphone pronunciation
            elif len(pron)>1:
                state = self.wfst.AddState()
                self.wfst.AddArc( self.wfst.Start(), self.isyms.AddSymbol(pron[0]), self.osyms.AddSymbol(first_word), 0.0, state )
                self.phons.add(pron[0])
                for j in xrange(0,len(pron)-2):
                    nextstate = self.wfst.AddState()
                    self.phons.add(pron[j+1])
                    self.wfst.AddArc( state, self.isyms.AddSymbol(pron[j+1]), openfst.epsilon, 0.0, nextstate )
                    state = nextstate
                self.wfst.AddArc( state, self.isyms.AddSymbol(pron[len(pron)-1]), openfst.epsilon, 0.0, self.wfst.Start() )
                self.phons.add(pron[len(pron)-1])
        #Iterate through any additional pronunciations
        for i,word in enumerate( self.pdict[pron] ):
            state = self.wfst.AddState()
            self.wfst.AddArc( self.wfst.Start(), self.isyms.AddSymbol(pron[0]), self.osyms.AddSymbol(word), 0.0, state )
            self.phons.add(pron[0])
            for j in xrange(0,len(pron)-1):
                nextstate = self.wfst.AddState()
                self.phons.add(pron[j+1])
                self.wfst.AddArc( state, self.isyms.AddSymbol(pron[j+1]), openfst.epsilon, 0.0, nextstate )
                state = nextstate
            self.wfst.AddArc( state, self.isyms.AddSymbol("#%d"%i), openfst.epsilon, 0.0, self.wfst.Start() )
            self.aux.add("#%d"%i)
        return

    def _gen_entry_all_aux( self, pron ):
        """
           Generate entries for a pronunciation.  
           This is the most concise but least clear entry-type.  It creates an 
           epsilon-free, closed lexicon transducer which simply loops through the start state.
           Auxiliary symbols are only added where absolutely necessary, 
        """
        for i,word in enumerate( self.pdict[pron] ):
            state = self.wfst.AddState()
            self.wfst.AddArc( self.wfst.Start(), self.isyms.AddSymbol(pron[0]), self.osyms.AddSymbol(word), 0.0, state )
            self.phons.add(pron[0])
            for j in xrange(0,len(pron)-1):
                nextstate = self.wfst.AddState()
                self.phons.add(pron[j+1])
                self.wfst.AddArc( state, self.isyms.AddSymbol(pron[j+1]), openfst.epsilon, 0.0, nextstate )
                state = nextstate
            self.wfst.AddArc( state, self.isyms.AddSymbol("#%d"%i), openfst.epsilon, 0.0, self.wfst.Start() )
            self.aux.add("#%d"%i)
        return

    def _gen_entry_all_aux_no_loop_no_sync( self, pron ):
        """
           Least efficient example.
        """
        for i,word in enumerate( self.pdict[pron] ):
            state = self.wfst.AddState()
            self.wfst.AddArc( self.wfst.Start(), openfst.epsilon, self.osyms.AddSymbol(word), 0.0, state )
            self.phons.add(pron[0])
            for j in xrange(0,len(pron)):
                nextstate = self.wfst.AddState()
                self.phons.add(pron[j])
                self.wfst.AddArc( state, self.isyms.AddSymbol(pron[j]), openfst.epsilon, 0.0, nextstate )
                state = nextstate
            nextstate = self.wfst.AddState()
            self.wfst.AddArc( state, self.isyms.AddSymbol("#%d"%i), openfst.epsilon, 0.0, nextstate )
            self.wfst.SetFinal( nextstate, 0.0 )
            self.aux.add("#%d"%i)
        return

    def _load_htkdict( self, dictfile ):
        """Load an HTK format pronunciation dictionary."""
        #This doesn't actually parse a real HTK format dictionary yet. 
        # rather it just ignores positional information.
        htk_dict = defaultdict(list)
        dict_fp = open( dictfile, "r" )
        for entry in dict_fp.readlines():
            pronunciation = re.split(r"\s+",entry.strip())
            word  = pronunciation.pop(0)
            htk_dict[tuple(pronunciation)].append( word )
        for pron in htk_dict:
            self.logger.debug("%s: %s" % (pron, ";".join(htk_dict[pron])))
        dict_fp.close()
        return htk_dict
    
    def _load_cmudict( self, dictfile ):
        """Load a CMU format pronunciation dictionary.  Generates positional information."""
        cmu_dict = defaultdict(list)
        dict_fp = open( dictfile, "r" )
        for entry in dict_fp.readlines():
            pronunciation = re.split(r"\s+",entry.strip())
            word = pronunciation.pop(0)
            if len(pronunciation)==1 :
                pronunciation[0] += "_s"
            else:
                for i,p in enumerate(pronunciation):
                    if i==0:
                        pronunciation[i] += "_b"
                    elif i==len(pronunciation)-1:
                        pronunciation[i] += "_e"
                    else:
                        pronunciation[i] += "_i"
            cmu_dict[tuple(pronunciation)].append(word)
        dict_fp.close()
        return cmu_dict

class SphinxMapper():
    """
       This class generates a 'mapping' transducer suitable for transducing 
       logical triphones from a context-dependent triphone transducer into 
       physical triphones contained in a Sphinx mdef file.  HTK models 
       employ a separate mapper.
 
       At present this class only supports mapping to physical triphones.  It 
       is also possible to map directly to the unique underlying senone sequences,
       e.g., the unique tuples: (tmat_id, s1, s2, s3) as defined in the mdef, but
       experiments showed that this results in a trivial gain which may not justify
       the additional complexity.
    """
    def __init__( self, mdef, cisyms, cosyms, verbose="4",eps="-", sil="SIL" ):
        #Setup logging
        self.logger = setup_logger( verbose=verbose, loggerID="CascadeTools.D-Sphinx" )
        #Init
        # D wfst
        self.wfst  = openfst.StdVectorFst()
        self.state = self.wfst.Start()
        self.state = self.wfst.AddState()
        self.wfst.SetStart(self.state)
        # Aux wfst: may be combined but this is clearer
        self.auxwfst  = openfst.StdVectorFst()
        self.astate   = self.auxwfst.Start()
        self.astate   = self.auxwfst.AddState()
        self.auxwfst.SetStart(self.astate)
        self.auxwfst.SetFinal(self.astate,0.0)
        self.mdef  = S3Mdef(filename=mdef)
        self.cisyms         = cisyms
        self.cosyms         = cosyms
        self.mono, self.aux = self._mono_aux_from_syms()
        self.sphinxformat = True
        self.eps          = eps
        self.sil          = sil #careful of this. should probably handle auto-magically. 
                                # if this doesn't match the CLG cascade problems will result.
        self.hmmsyms      = openfst.SymbolTable("hmmsyms")
        self._hmmsyms_from_mdef()
        self.types = ( "e", "s", "b", "i" )
        self.auxhash = set([])
        #This is a somewhat arbitrary heuristic
        self.type_map = {
            "e": ("s","i","b"),
            "s": ("i","b","e"),
            "b": ("i","s","e"),
            "i": ("b","s","e")
            }

    def generate_d( self ):
        if self.sphinxformat:
            self._do_sphinx_format()
        return

    def _mono_aux_from_syms( self ):
        auxre = re.compile(r"^#[0-9]+$")
        phons = set([])
        aux   = set([])
        for i in range(1,self.cosyms.NumSymbols()):
            if auxre.match(self.cosyms.Find(i)):
                aux.add(self.cosyms.Find(i))
            else:
                phons.add(self.cosyms.Find(i))
        self.logger.debug("PHONES: %s"%(", ".join(phons)))
        self.logger.debug("AUX   : %s"%(", ".join(aux)))
        return phons, aux

    def _do_sphinx_format( self ):
        """
           Print out D assuming sphinx format. 
        """
        pos = re.compile(r"_[ebsi]")
        for lp in self.mono:
            lpf = pos.sub("",lp)
            if self.cisyms.Find("--"+lp+"+-")>-1:
                self.wfst.AddArc(
                    self.wfst.Start(),
                    self.hmmsyms.AddSymbol(pos.sub("",lp)),
                    self.cisyms.Find("--"+lp+"+-"),
                    0.0,
                    self.wfst.Start()
                    )
            for mp in self.mono:
                t = re.sub(r".*?_","",mp)
                mpf = pos.sub("",mp)
                #Only print the arcs that actually exist in the final CD transducer.
                # slight loss of generality but probably OK for this example.
                if self.cisyms.Find(self._connect(self.eps,mp,lp))>-1:
                    self.wfst.AddArc(
                        self.wfst.Start(),
                        self.hmmsyms.AddSymbol(self.sil),
                        self.cisyms.Find(self._connect(self.eps,mp,lp)),
                        0.0,
                        self.wfst.Start()
                        )
                if self.cisyms.Find(self._connect(lp,mp,self.eps))>-1:
                    self.wfst.AddArc(
                        self.wfst.Start(),
                        self.hmmsyms.AddSymbol(self.sil),
                        self.cisyms.Find(self._connect(lp,mp,self.eps)),
                        0.0,
                        self.wfst.Start()
                        )
                for rp in self.mono:
                    rpf = pos.sub("",rp)
                    if self.cisyms.Find(self._connect(lp,mp,rp))>-1:
                        self.wfst.AddArc(
                            self.wfst.Start(),
                            self._map_triphone(lpf,mpf,rpf,ptype=t),
                            self.cisyms.Find(self._connect(lp,mp,rp)),
                            0.0,
                            self.wfst.Start()
                            )
        #Handle the auxiliary symbol replacement
        for aux in self.aux:
            self.wfst.AddArc(self.wfst.Start(), openfst.epsilon, self.cisyms.Find(aux), 0.0, self.wfst.Start())

        self.wfst.SetFinal(self.wfst.Start(),0.0)
        #Default output label sort
        openfst.ArcSortOutput(self.wfst)
        return

    def _connect( self, lp, mp, rp, ptype=None ):
        tri = lp+"-"+mp+"+"+rp
        if ptype:
            tri += "_"+ptype
        return tri

    def _map_triphone( self, lp, mp, rp, ptype=None ):
        """Map logical triphones onto a physical equivalent in the mdef."""
        #Mapping to senone sequences instead might be slightly more efficient
        #  however it will eliminate generality, readability, and in expts. does not
        #  make any measurable contribution to RTF vs. Accy.
        if self.hmmsyms.Find(self._connect(lp,mp,rp,ptype=ptype))>-1:
            return self.hmmsyms.Find(self._connect(lp,mp,rp,ptype=ptype))
        for nt in self.type_map[ptype]:
            if self.hmmsyms.Find(self._connect(lp,mp,rp,ptype=nt))>-1:
                return self.hmmsyms.Find(self._connect(lp,mp,rp,ptype=nt))
        if self.hmmsyms.Find(mp)>-1:
            return self.hmmsyms.Find(mp)
        print "NOTHING FOR: %s %s %s %s" % (lp, mp, rp, ptype)
        return -1

    def _hmmsyms_from_mdef( self ):
        #The mdef trimap is not a hash. This is annoying.
        self.hmmsyms.AddSymbol("-",0)
        for i, entry in enumerate(self.mdef.trimap):
            newtri = self._format_phone(tuple([entry[0], entry[1], entry[2], entry[3]]))
            self.hmmsyms.AddSymbol(newtri,i+1)
        return

    def _format_phone( self, ci_cd ):
        """Format the mdef phones.  This convention will need to be followed in all top-level transducers."""
        #monophone case
        if ci_cd[1] == "-":
            formatted = ci_cd[0]
        #context-dependent triphone case
        else:
            formatted = ci_cd[1] + '-' + ci_cd[0] + '+' + ci_cd[2] + '_' + ci_cd[3]
        self.logger.debug("Input: %s %s %s %s\tOutput: %s" % ( ci_cd[0], ci_cd[1], ci_cd[2], ci_cd[3], formatted ))
        return formatted
        
class HTKMapper():
    """
    Class to generate a mapping transducer which maps between the HTK tiedlist
    and the converted AM hmm.syms file. 

    This is still screwing something up.
    """
    
    def __init__( self, tiedlist, hmmsyms, cisyms, cosyms, verbose="4", sil="sil" ):
        #Setup logging
        self.logger = setup_logger( verbose=verbose, loggerID="CascadeTools.D-HTK" )
        #Init
        self.sil      = sil
        self.hmmsyms  = hmmsyms
        self.osyms    = cisyms
        self.cosyms   = cosyms
        self.mono, self.aux = self._mono_aux_from_syms( )
        self.wfst     = openfst.StdVectorFst( )
        self.start    = self.wfst.Start( )
        self.start    = self.wfst.AddState( )
        self.wfst.SetStart(self.start)
        self.tiedlist = self._load_tiedlist( tiedlist )
        
    def _load_tiedlist( self, tiedlist ):
        """Convert the HTK tiedlist into a hash suitable for downstream operations."""
        #We could add some of the arcs here, but it makes things a bit more confusing.
        tiedlist_fp = open(tiedlist,"r")
        tiedhash    = {}
        for line in tiedlist_fp:
            line  = line.strip()
            parts = re.split(r"\s+",line)
            if len(parts)==2:
                tiedhash[parts[0]] = parts[1]
            else:
                tiedhash[parts[0]] = parts[0]

        tiedlist_fp.close()
        return tiedhash

    def _mono_aux_from_syms( self ):
        auxre = re.compile(r"^#[0-9]+$")
        phons = set([])
        aux   = set([])
        for i in range(1,self.cosyms.NumSymbols()):
            if auxre.match(self.cosyms.Find(i)):
                aux.add(self.cosyms.Find(i))
            else:
                phons.add(self.cosyms.Find(i))
        self.logger.debug("PHONES: %s"%(", ".join(phons)))
        self.logger.debug("AUX   : %s"%(", ".join(aux))) 
        return phons, aux                                            

    def generate_d( self ):
        """Generate the arcs for the mapper transducer."""
        for lp in self.mono:
            if self.osyms.Find("--"+lp+"--")>-1: 
                #if this doesn't exist in hmmsyms as well, we're in trouble
                if self.hmmsyms.Find(self.lp)>-1:
                    self.wfst.AddArc(self.wfst.Start(), self.hmmsyms.Find(self.lp), self.osyms.Find("--"+lp+"--"), 0.0, self.wfst.Start())
                else:
                    self.logger.debug("Missing mono: %s" % self.lp)
            for mp in self.mono:
                #if these don't exist in hmmsyms as well, we're in trouble
                if self.osyms.Find(lp+"-"+mp+"+-")>-1:
                    self.wfst.AddArc(self.wfst.Start(), self.hmmsyms.Find(self.sil), self.osyms.Find(lp+"-"+mp+"+-"), 0.0, self.wfst.Start())
                if self.osyms.Find("--"+mp+"+"+lp)>-1:
                    self.wfst.AddArc(self.wfst.Start(), self.hmmsyms.Find(self.sil), self.osyms.Find("--"+mp+"+"+lp), 0.0, self.wfst.Start())
                for rp in self.mono:
                    #again, we aren't really doing enough checking here. things could go wrong.
                    if self.osyms.Find(lp+"-"+mp+"+"+rp)>-1:
                        if self.tiedlist.has_key(lp+"-"+mp+"+"+rp):
                            if self.hmmsyms.Find(self.tiedlist[lp+"-"+mp+"+"+rp])>-1:
                                self.wfst.AddArc(self.wfst.Start(), self.hmmsyms.Find(self.tiedlist[lp+"-"+mp+"+"+rp]), self.osyms.Find(lp+"-"+mp+"+"+rp), 0.0, self.wfst.Start())
                            else:
                                self.logger.debug("Missing tri: %s->%s trying to backoff..." % (self.tiedlist[lp+"-"+mp+"+"+rp],lp+"-"+mp+"+"+rp))
                        elif self.tiedlist.has_key(mp):
                            if self.hmmsyms.Find(self.tiedlist[mp])>-1:
                                self.wfst.AddArc(self.wfst.Start(), self.hmmsyms.Find(self.tiedlist[mp]), self.osyms.Find(lp+"-"+mp+"+"+rp), 0.0, self.wfst.Start())
                            else:
                                self.logger.debug("Cant find backoff for: %s -> %s..." % (mp, lp+"-"+mp+"+"+rp))
        #handle the auxiliary symbols
        for aux in self.aux:
            self.wfst.AddArc(self.wfst.Start(), openfst.epsilon, self.osyms.Find(aux), 0.0, self.wfst.Start())
        self.wfst.SetFinal(self.wfst.Start(),0.0)
        openfst.ArcSortOutput(self.wfst)
        return



if __name__=="__main__":
    print "CascadeTools.py:  This module doesn't actually do anything on it's own.  Write your own application that utilizes the components."
