#!/usr/bin/python
import re
from t3mdef import T3Mdef

class ContextDependency( ):
    """
    Context dependency transducer.
    Use an HTK format tiedlist to handle logical->physical triphone mapping.
    """

    def __init__( self, mdef, aux, start="<start>", prefix="cd", eps="<eps>", sil="SIL" ):
        self.sil      = sil
        self.mdef_file = mdef
        self.mdef     = None
        self.phons    = set([])
        self.aux      = set([])
        self.aux_f    = aux
        self.eps      = eps
        self.prefix   = prefix
        self.start    = start
        self.ssyms    = set([])
        self.isyms    = set([])
        self.osyms    = set([])
        self.tied     = {}
        self.seen     = set([])
        self.ssyms.add(self.start)
        self._load_list( self.aux_f, "aux" )
        self._load_mdef( )

    def _load_list( self, filename, ltype ):
        """Load a list of phonemes or aux symbols.  One per line."""
        fp = open(filename,"r")
        for line in fp:
            line = line.strip()
            self.aux.add(line)
        fp.close()
        return

    def _load_mdef( self ):
        """Load the tiedlist.  Track the ids."""
        self.mdef = T3Mdef( self.mdef_file )
        for n in xrange(0,self.mdef.n_ci):
            self.phons.add(self.mdef.allfields[n][0])
        return

    def _check_sym( self, lp, mp, rp, pos ):
        """
          Check a sym against the tiedlist.
          Keep trying to back off to something reasonable.
          If all else fails slot in an <eps> arc - however 
           it is probably better to raise an error in this case.
        """
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

    def _make_arc( self, lp, mp, rp, pos=None ):
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

        print issym, ossym, isym, osym
        return

    def _make_final( self, lp, rp ):
        """Make a final state."""
        fssym = lp+','+rp
        print fssym
        return

    def _make_aux( self, lp, rp ):
        """Generate auxiliary symbol arcs. Don't make duplicates."""
        issym = lp+','+rp

        for a in self.aux:
            if (issym,issym,self.eps,a) in self.seen:
                continue
            else:
                print issym, issym, self.eps, a
                self.seen.add((issym,issym,self.eps,a))
        return

    def generate_deterministic( self ):
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
            self._make_aux( lp, self.eps )
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

    def print_isyms( self ):
        isym_f   = "%s.c.isyms" % self.prefix
        isyms_fp = open( isym_f,"w" )
        isyms_fp.write("%s %d\n" % (self.eps,0))
        for i,fields in enumerate(self.mdef.allfields):
            if fields[1] == "-":
                isyms_fp.write("%s %d\n" % (fields[0], i+1))
            else:
                isyms_fp.write("%s-%s_%s+%s %d\n" % (fields[1], fields[0], fields[3], fields[2], i+1))
        for i,a in enumerate(self.aux):
            isyms_fp.write("%s %d\n" % (a, len(self.mdef.allfields)+i+1))
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
        return

if __name__=="__main__":
    import sys
    C = ContextDependency( sys.argv[1], sys.argv[2], prefix=sys.argv[3] )
    C.generate_deterministic()
    C.print_all_syms()
