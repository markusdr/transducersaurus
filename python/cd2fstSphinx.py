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
import re
from t3mdef import T3Mdef

class ContextDependencySphinx( ):
    """
    Context dependency transducer.
    Use an HTK format tiedlist to handle logical->physical triphone mapping.
    """

    def __init__( self, mdef, aux, start="<start>", prefix="cd", eps="<eps>", sil="SIL", auxout=0, minimal=True ):
        self.sil      = sil
        self.mdef_file = mdef
        self.mdef     = None
        self.cd_ofp   = open("PREFIX.c.fst.txt".replace("PREFIX",prefix),"w")
        self.phons    = set([])
        self.aux      = set([])
        self.aux_f    = aux
        self.auxout   = auxout
        self.eps      = eps
        self.prefix   = prefix
        self.start    = start
        self.ssyms    = set([])
        self.isyms    = set([])
        self.osyms    = set([])
        self.tied     = {}
        self.seen     = set([])
        self._mapper_arcs = set([])
        self.ssyms.add(self.start)
        self._load_list( self.aux_f, "aux" )
        self._load_mdef( minimal=minimal )
        self._init_mapper( )
        
    def _init_mapper( self ):
        #if self.auxout==True:
        self.mapper_ofp = open("PREFIX.d.fst.txt".replace("PREFIX",self.prefix),"w")
        return
        
    def _write_mapper_arc( self, mapped, orig ):
        arc = "0 0 MAPPED ORIG\n".replace("MAPPED",mapped).replace("ORIG",orig)
        if not arc in self._mapper_arcs:
            self.mapper_ofp.write(arc)
            self._mapper_arcs.add(arc)
        return

    def _load_list( self, filename, ltype ):
        """Load a list of phonemes or aux symbols.  One per line."""
        fp = open(filename,"r")
        for line in fp:
            line = line.strip()
            self.aux.add(line)
        fp.close()
        return

    def _load_mdef( self, minimal ):
        """Load the tiedlist.  Track the ids."""
        self.mdef = T3Mdef( self.mdef_file )
        if minimal==True:
            fp = open("PREFIX.phons".replace("PREFIX",self.prefix), "r")
            for phon in fp:
                phon = phon.strip()
                self.phons.add(phon)
        else:
            for n in xrange(0,self.mdef.n_ci):
                for pos in ['b','i','e','s']:
                    self.phons.add(self.mdef.allfields[n][0]+"_"+pos)
        return

    def _check_sym_condensed( self, lp, mp, rp ):
        """
          Check a sym against the tiedlist.
          Keep trying to back off to something reasonable.
          If all else fails slot in an <eps> arc - however 
           it is probably better to raise an error in this case.
        """
        pos = ""

        if (lp,mp,rp,pos) in self.mdef.tiedlist:
            return lp+"-"+mp+"_"+pos+"+"+rp
        poslist = set(['b','i','e','s'])
        if pos: poslist.remove(pos)
        for pos in poslist:
            if (lp,mp,rp,pos) in self.mdef.tiedlist:
                return lp+"-"+mp+"_"+pos+"+"+rp
        if ('-',mp,'-','-') in self.mdef.tiedlist:
            return mp
        return '0'
        
    def _check_sym( self, lp, mp, rp ):
    
        lp = re.sub(r"_[bies]","",lp)
        rp = re.sub(r"_[bies]","",rp)
        orig   = lp+"-"+mp+"+"+rp

        def cmpsym( lp, mp, rp ):
            if lp==self.start:
                return self.eps
            mp,pos = mp.split("_")
            poslist = { 
                'b':set(['i','s','e']),
                'i':set(['b','s','e']),
                's':set(['b','i','e']),
                'e':set(['i','s','b'])
                }
            if (lp,mp,rp,pos) in self.mdef.tiedlist:
                return lp+"-"+mp+"_"+pos+"+"+rp
            for p in poslist[pos]:
                if (lp,mp,rp,p) in self.mdef.tiedlist:
                    return lp+"-"+mp+"_"+p+"+"+rp
            if ('-',mp,'-','-') in self.mdef.tiedlist:
                return mp
            else:
                return self.eps

        mapped = cmpsym( lp, mp, rp )
        self._write_mapper_arc( mapped, orig )
        if self.auxout>0:
            return orig
            
        return mapped

    def _make_condensed_arc( self, lp, mp, rp, pos=None ):
        """
           Generate an arc.
             lp: left-monophone
             mp: middle-monophone
             rp: right-monophone
        """
        
        issym = lp+','+mp
        ossym = mp+','+rp
        self.ssyms.add(issym)
        self.ssyms.add(ossym)

        if mp==self.sil: 
            isym = self.sil
            osym = self.sil
            #Don't make duplicate sil arcs!
            if (issym,ossym,self.sil) in self.seen:
                return
            else:
                self.seen.add((issym,ossym,self.sil))
        else:
            isym = self._check_sym( lp, mp, rp, pos )
            if pos: 
                osym = mp+"_"+pos
            else:   
                osym = mp
        self.isyms.add(isym)
        self.osyms.add(osym)

        if lp==self.eps: 
            issym = self.start

        self.cd_ofp.write("%s %s %s %s\n" % (issym, ossym, isym, osym))
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
        self.ssyms.add(issym)
        self.ssyms.add(ossym)
        isym  = self._check_sym(lp, mp, rp)
        osym  = rp
        self.osyms.add(osym)
        self.isyms.add(isym)
        
        if lp==self.start: issym = self.start

        self.cd_ofp.write("%s %s %s %s\n" % (issym, ossym, isym, osym))
        return

    def _make_final( self, lp, rp ):
        """Make a final state."""
        fssym = lp+','+rp
        self.cd_ofp.write("%s\n"%(fssym))
        return

    def _make_aux( self, lp, rp ):
        """Generate auxiliary symbol arcs."""
        issym = lp+','+rp
        
        for a in self.aux:
            if self.auxout>0:
                self.cd_ofp.write("%s %s %s %s\n" % (issym, issym, a, a))
                if self.auxout==1:
                    self._write_mapper_arc( self.eps, a )
                elif self.auxout==2:
                    self._write_mapper_arc( a, a )
            else:
                self.cd_ofp.write("%s %s %s %s\n" % (issym, issym, self.eps, a))
        return

    def generate_nondeterministic_condensed( self ):
        """
           Generate the context dependency transducer.
             lp: left-monophone
             mp: middle-monophone
             rp: right-monophone
             pos: position information for sphinx models
        """
        for lp in self.phons:
            #Monophone arcs
            self._make_arc( self.eps, lp, self.eps )
            self._make_final( lp, self.eps )
            for mp in self.phons:
                for pos in ['b','i','e','s']:
                    #Initial to Internal arcs
                    self._make_arc( self.eps, lp, mp, pos )
                    #Internal to Final arcs
                    self._make_arc( lp, mp, self.eps, pos )
                    self._make_aux( lp, mp )
                    for rp in self.phons:
                        #Internal to Internal arcs
                        self._make_arc( lp, mp, rp, pos )
                            
        for a in self.aux:
            self.osyms.add(a)
            self.isyms.add(a)

        return
        
    def generate_deterministic( self ):
        """
           Generate the context dependency transducer.
             lp: left-monophone
             mp: middle-monophone
             rp: right-monophone
        """

        for lp in self.phons:
            #Initial arcs
            self._make_arc( self.start, self.eps, lp )
            self._make_aux( self.eps, lp )
            #Monophone arcs
            self._make_arc( self.eps, lp, self.eps )
            self._make_final( lp, self.eps )
            for mp in self.phons:
                #Initial to Internal arcs
                self._make_arc( self.eps, lp, mp )
                #Internal to Final arcs
                self._make_arc( lp, mp, self.eps )
                self._make_aux( lp, mp )
                for rp in self.phons:
                    #Internal to Internal arcs
                    self._make_arc( lp, mp, rp )
        for a in self.aux:
            self.osyms.add(a)
            self.isyms.add(a)
        if self.auxout>0:
            self.mapper_ofp.write("0\n")
            self.mapper_ofp.close()
        self.cd_ofp.close()
        return

    def print_hmmsyms( self ):
        isym_f   = "%s.hmm.syms" % self.prefix
        isyms_fp = open( isym_f,"w" )
        isyms_fp.write("%s %d\n" % (self.eps,0))
        cnt = 0
        for i,fields in enumerate(self.mdef.allfields):
            if fields[1] == "-":
                isyms_fp.write("%s %d\n" % (fields[0], i+1))
            else:
                isyms_fp.write("%s-%s_%s+%s %d\n" % (fields[1], fields[0], fields[3], fields[2], i+1))
            cnt = i+1
        for a in self.aux:
            isyms_fp.write("%s %d\n" %(a, cnt))
            cnt += 1
        isyms_fp.close()
        return
        
    def print_isyms( self ):
        isym_f   = "%s.c.isyms" % self.prefix
        isyms_fp = open( isym_f,"w" )
        isyms_fp.write("%s %d\n" % (self.eps,0))
        for i,sym in enumerate(self.isyms):
            isyms_fp.write("%s %d\n" % (sym, i+1))
        isyms_fp.close()
        return

    def print_osyms( self ):
        osym_f   = "%s.c.osyms" % self.prefix
        osyms_fp = open( osym_f,"w" )
        osyms_fp.write("%s %d\n" % (self.eps, 0))
        for i,sym in enumerate(self.osyms):
            osyms_fp.write("%s %d\n" % (sym, i+1))
        osyms_fp.close()
        return

    def print_ssyms( self ):
        ssym_f   = "%s.c.ssyms" % self.prefix
        ssyms_fp = open( ssym_f,"w" )
        ssyms_fp.write("%s %d\n" % (self.eps, 0))
        for i,sym in enumerate(self.ssyms):
            ssyms_fp.write("%s %d\n" % (sym, i+1))
        ssyms_fp.close()
        return

    def print_all_syms( self ):
        self.print_ssyms()
        self.print_isyms()
        self.print_osyms()
        self.print_hmmsyms()
        return

if __name__=="__main__":
    import sys
    C = ContextDependencySphinx( sys.argv[1], sys.argv[2], prefix=sys.argv[3] )
    C.generate_deterministic()
    C.print_all_syms()
