#!/usr/bin/python
import re

class ContextDependency( ):
    """
    Context dependency transducer.
    Use an HTK format tiedlist to handle logical->physical triphone mapping.
    """

    def __init__( self, phons, aux, tiedlist, start="<start>", prefix="cd", eps="<eps>", sil="sil" ):
        self.phons_f  = phons
        self.sil      = sil
        self.phons    = set([])
        self.aux      = set([])
        self.aux_f    = aux
        self.eps      = eps
        self.prefix   = prefix
        self.start    = start
        self.ssyms    = set([])
        self.isyms    = [self.eps]
        self.tied     = {}
        self.osyms    = set([])
        self.tiedlist = tiedlist
        self.ssyms.add(self.start)
        self._load_list( self.phons_f, "phons" )
        self._load_list( self.aux_f, "aux" )
        self._load_tiedlist( )

    def _load_list( self, filename, ltype ):
        """Load a list of phonemes or aux symbols.  One per line."""
        fp = open(filename,"r")
        for line in fp:
            line = line.strip()
            if ltype=="phons":
                self.phons.add(line)
            else:
                self.aux.add(line)
        fp.close()
        return

    def _load_tiedlist( self ):
        """Load the tiedlist.  Track the ids."""
        fp = open(self.tiedlist,"r")

        for line in fp:
            line = line.strip()
            parts = line.split()
            if len(parts)==1:
                self.tied[parts[0]]  = parts[0]
                self.isyms.append(parts[0])
            elif len(parts)==2:
                self.tied[parts[0]] = parts[1]
        fp.close()
        return

    def _check_sym( self, lp, mp, rp ):
        """
          Check a sym against the tiedlist.
          Keep trying to back off to something reasonable.
          If all else fails slot in an <eps> arc - however 
           it is probably better to raise an error in this case.
        """
        
        if lp+"-"+mp+"+"+rp in self.tied:
            return self.tied[lp+"-"+mp+"+"+rp]
        elif lp+"-"+mp in self.tied:
            return self.tied[lp+"-"+mp]
        elif mp+"+"+rp in self.tied:
            return self.tied[mp+"+"+rp]
        elif lp+"+"+mp in self.tied:
            return self.tied[lp+"+"+mp]
        elif mp+"-"+rp in self.tied:
            return self.tied[mp+"-"+rp]
        elif mp in self.tied:
            return self.tied[mp]
        elif lp in self.tied:
            return self.tied[lp]
        elif rp in self.tied:
            return self.tied[rp]
        else:
            return self.eps

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

        if lp==self.start: isym  = self.sil
        if lp==self.start: issym = self.start
        
        print issym, ossym, isym, osym
        return

    def _make_final( self, lp, rp ):
        """Make a final state."""
        fssym = lp+','+rp
        print fssym
        return

    def _make_aux( self, lp, rp ):
        """Generate auxiliary symbol arcs."""
        issym = lp+','+rp

        for a in self.aux:
            print issym, issym, self.eps, a
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
            self._make_arc( self.start, self.sil, lp )
            self._make_aux( self.sil, lp )
            #Monophone arcs
            self._make_arc( self.sil, lp, self.sil )
            self._make_final( lp, self.sil )
            for mp in self.phons:
                #Initial to Internal arcs
                self._make_arc( self.sil, lp, mp )
                #Internal to Final arcs
                self._make_arc( lp, mp, self.sil )
                self._make_aux( lp, mp )
                for rp in self.phons:
                    #Internal to Internal arcs
                    self._make_arc( lp, mp, rp )
        for a in self.aux:
            self.osyms.add(a)
        return

    def print_isyms( self ):
        isym_f   = "%s.c.isyms" % self.prefix
        isyms_fp = open( isym_f,"w" )
        for i,sym in enumerate(self.isyms):
            isyms_fp.write("%s %d\n" % (sym, i))
        isyms_fp.close()
        return

    def print_osyms( self ):
        osym_f   = "%s.c.osyms" % self.prefix
        osyms_fp = open( osym_f,"w" )
        osyms_fp.write("%s %d\n" % (self.eps, 0))
        osyms_fp.write("%s %d\n" % (self.sil, 1))
        for i,sym in enumerate(self.osyms):
            osyms_fp.write("%s %d\n" % (sym, i+2))
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
    C = ContextDependency( sys.argv[1], sys.argv[2], sys.argv[3], prefix=sys.argv[4] )
    C.generate_deterministic()
    C.print_all_syms()
