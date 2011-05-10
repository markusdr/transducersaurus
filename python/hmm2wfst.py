#!/usr/bin/python
from t3mdef import T3Mdef
from collections import defaultdict
import re

class hmm2wfst( ):
    """
       Generate the H-level transducer.
       Expects an AT&T text-format hmm.hmm file as input.
       The format should be transparent however, looking at a 
        Sphinx AM mdef file.
    """
    def __init__( self, hmm_file, prefix="test", amtype="sphinx", aux_file=None, eps="<eps>", auxout=0, isyms_file=None ):
        self.hmm_file  = hmm_file
        self.isyms_map = self._make_isym_map( isyms_file )
        self.aux       = self._read_aux( aux_file )
        self.haux      = set([])
        self.stateseqs = defaultdict(int)
        self.auxout    = auxout
        self.prefix    = prefix
        self.amtype    = amtype
        self.eps       = eps
        self.mapsyms   = set([])
        self.isyms     = set([a for a in self.aux])
        self.hmm_file_ofp = open( "PREFIX.h.fst.txt".replace("PREFIX",self.prefix), "w" )

    def _make_isym_map( self, isyms_file ):
        """Open isym file."""

        if isyms_file==None:
            return None

        isyms_ifp = open( isyms_file, "r" )
        isym_map = { }
        for line in isyms_ifp:
            line = line.strip()
            sym, id = re.split(r"\s+",line)
            isym_map[sym] = id
        isyms_ifp.close()

        return isym_map

    def makemapper( self ):
        mapper_ofp = open( "PREFIX.e.fst.txt".replace("PREFIX",self.prefix), "w" )

        for sym in self.mapsyms:
            mapper_ofp.write("0\t0\t%d\t%d\n" % (sym, sym))
        for a in self.aux:
            mapper_ofp.write("0\t0\t0\t%s\n" % (a))
        for a in self.haux:
            mapper_ofp.write("0\t0\t0\t%s\n" % (a))
        mapper_ofp.write("0\n")
        mapper_ofp.close()

        return
    
    def mdef2wfst( self ):
        """Read through the tiedlist."""
        ssym = 1

        self.mdef = T3Mdef( self.hmm_file )

        self._gen_aux( 0 )

        for n in xrange( 0, self.mdef.n_phone ):
            hisym = ""
            if n < self.mdef.n_ci:
                hisym = self.mdef.allfields[n][0]
            else:
                hisym = self.mdef.allfields[n][1] + "-" \
                    + self.mdef.allfields[n][0] + "_" + self.mdef.allfields[n][3] + "+" \
                    + self.mdef.allfields[n][2]
            if not self.isyms_map==None and hisym not in self.isyms_map:
                continue

            hmms = tuple([ int(i)+1 for i in self.mdef.allfields[n][6:9] ])
            #state 1
            self.hmm_file_ofp.write("%d\t%d\t%s\t%s\n" % (
                    0,
                    ssym,
                    hmms[0],
                    hisym ) )
            self.hmm_file_ofp.write("%d\t%d\t%s\t%s\n" % (
                    ssym,
                    ssym,
                    hmms[0],
                    self.eps ) )
            #self._gen_aux( ssym )
            #state 2
            self.hmm_file_ofp.write("%d\t%d\t%s\t%s\n"  % (
                    ssym,
                    ssym+1,
                    hmms[1],
                    self.eps ) )
            self.hmm_file_ofp.write("%d\t%d\t%s\t%s\n"  % (
                    ssym+1,
                    ssym+1,
                    hmms[1],
                    self.eps ) )
            #state 3
            self.hmm_file_ofp.write("%d\t%d\t%s\t%s\n"  % (
                    ssym+1,
                    ssym+2,
                    hmms[2],
                    self.eps ) )
            self.hmm_file_ofp.write("%d\t%d\t%s\t%s\n"  % (
                    ssym+2,
                    ssym+2,
                    hmms[2],
                    self.eps ) )
                    
            self.stateseqs[hmms] += 1
            haux = "#2000%d"%(self.stateseqs[hmms]-1)
            self.isyms.add(haux)
            
            self.hmm_file_ofp.write("%d\t%d\t%s\t%s\n"  % (
                    ssym+2,
                    ssym+3,
                    haux,
                    self.eps ) )
            self.hmm_file_ofp.write("%d\t%d\t%s\t%s\n" % (
                    ssym+3,
                    0,
                    self.eps,
                    self.eps ) )
            self.mapsyms = self.mapsyms.union(hmms)
            self.haux.add(haux)
            ssym += 4

        self.isyms = self.isyms.union(self.mapsyms)
        self.hmm_file_ofp.write("0\n")
        self.hmm_file_ofp.close()

        return

    def write_isyms( self ):
        """Write the input symbols table."""

        isyms_ofp = open("PREFIX.h.isyms".replace("PREFIX",self.prefix), "w")
        isyms_ofp.write("%s 0\n" % (self.eps))

        for i,isym in enumerate(self.isyms):
            isyms_ofp.write("%s %d\n" % (isym, i+1))
        isyms_ofp.close( )

        return
    
    def _read_aux( self, aux_file ):
        aux = set([])
        if aux_file==None:
            return aux
        aux_file_fp = open( aux_file, "r" )
        for line in aux_file_fp:
            line = line.strip()
            aux.add(line)
        return aux

    def _gen_aux( self, ssym ):
        """Generate the auxiliary symbol arcs."""

        for asym in self.aux:
            if self.auxout>0:
                self.hmm_file_ofp.write("%d\t%d\t%s\t%s\n" % (ssym, ssym, asym, asym))
            else:
                self.hmm_file_ofp.write("%d\t%d\t%s\t%s\n" % (ssym, ssym, self.eps, asym))
        return

    def hmm2wfst( self ):
        hmm_file_ifp = open( self.hmm_file, "r" )
        ssym = 2
        esym = 1
        self._gen_aux( 0 )
        self._gen_aux( 1 )
        for line in hmm_file_ifp:
            line = line.strip()
            hisym, crud, s1, s2, s3 = line.split("\t")
            self.hmm_file_ofp.write("%d\t%d\t%s\t%s\n" % (0,ssym,s1,hisym))
            self._gen_aux( ssym )
            self.hmm_file_ofp.write("%d\t%d\t%s\t0\n"  % (ssym,ssym+1,s2))
            self.hmm_file_ofp.write("%d\t%d\t%s\t0\n"  % (ssym+1,esym,s3))
            ssym += 2
        self.hmm_file_ofp.write("%d\n" % (esym))
        hmm_file_ifp.close()
        self.hmm_file_ofp.close()
        return


if __name__=="__main__":
    import os, sys, argparse
    example = """./hmm2wfst.py --hmm hmm.hmm --aux aux.list --prefix test"""
    parser = argparse.ArgumentParser(description=example)
    parser.add_argument("--hmm",     "-m", help="hmm.hmm file generated during AM conversion.", required=True )
    parser.add_argument("--aux",     "-a", help="Auxiliary symbols list.", default=None )
    parser.add_argument("--prefix",  "-p", help="Filename prefix.", default="test" )
    parser.add_argument("--amtype",  "-t", help="Acoustic Model type. 'sphinx', or 'htk'.", default="sphinx" )
    parser.add_argument("--eps",     "-e", help="Epsilon symbol.", default="<eps>" )
    parser.add_argument("--isyms",   "-i", help="Input symbols for C. Used for mapping if supplied.", default=None )
    parser.add_argument("--auxout",  "-o", help="Generate input auxiliary symbols. Set to 0, 1, or 2.", default=0, type=int )
    parser.add_argument("--verbose", "-v", help="Verbose mode.", default=False, action="store_true" )
    args = parser.parse_args( )

    if args.verbose==True:
        print "Running with the following arguments:"
        for attr, value in args.__dict__.iteritems():
            print attr, "=", value        
    
    h2w = hmm2wfst( 
        args.hmm, 
        aux_file=args.aux, 
        prefix=args.prefix,
        amtype=args.amtype,
        eps=args.eps,
        isyms_file=args.isyms,
        auxout=args.auxout
        )
    h2w.mdef2wfst( )
    h2w.makemapper( )
    h2w.write_isyms( )
