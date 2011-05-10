#!/usr/bin/python
import re, math

class ArpaLM( ):
    """
       Class to convert an ARPA-format LM to WFST format.
       
       NOTE: This class will convert arbitrary length n-gram models, but
             it does not perform special handling of missing back-off NODES.
             It does add default back-off ARCS for missing back-off WEIGHTS.
       NOTE: If your model contains '<eps>' as a regular symbol, make sure you
             change the epsilon symbol or you will be in for a world of hurt!
    """

    def __init__( self, arpaifile, arpaofile, eps="<eps>", maxorder=0, sil="<sil>", prefix="test", sb="<s>", se="</s>", boff=None ):
        self.arpaifile = arpaifile
        self.arpaofile = arpaofile
        self.ssyms    = set([])
        self.isyms    = set([])
        self.osyms    = set([])
        self.eps      = eps
        self.sil      = sil
        self.sb       = sb
        self.se       = se
        if boff: 
            self.boff = boff
            self.ssyms.add(self.boff)
            self.isyms.add(self.boff)
        else:    self.boff = self.eps
        #Just in case
        self.isyms.add(self.sil)
        self.osyms.add(self.sil)
        #----
        self.order    = 0
        self.tropical = True
        self.max_order = int(maxorder)
        self.prefix    = prefix
        if maxorder==0: self.auto_order = True
        else:           self.auto_order = False

    def to_tropical( self, val ):
        """
           Convert values to the tropical semiring. 
           Juicer has a fit if we don't do this...
        """
        logval = math.log(10.0) * float(val) * -1.0
        return logval

    def make_arc( self, istate, ostate, isym, osym, weight=0.0 ):
        """
           Build a single arc.  Add symbols to the symbol tables
           as necessary, but ignore epsilons.
        """
        if not istate==self.boff: self.ssyms.add(istate)
        if not ostate==self.boff: self.ssyms.add(ostate)
        
        if not isym==self.boff: self.isyms.add(isym)
        if not osym==self.boff: self.osyms.add(osym)

        if self.tropical:
            arc = "%s\t%s\t%s\t%f\n" % (istate, ostate, isym, self.to_tropical(weight))
        else:
            arc = "%s\t%s\t%s\t%f\n" % (istate, ostate, isym, float(weight))
        return arc

    def arpa2fst( self ):
        """
           Convert an arbitrary length ARPA-format n-gram LM to WFST format.
        """

        arpa_ifp = open(self.arpaifile, "r")
        arpa_ofp = open(self.arpaofile, "w")
        arpa_ofp.write(self.make_arc( "<start>", self.sb, self.sb, self.sb, 0.0 ))
        for line in arpa_ifp:
            line = line.strip()
            #Process based on n-gram order
            #print self.order
            if self.order>0 and not line=="" and not line.startswith("\\"):
                parts = re.split(r"\s+",line)
                #Handle unigrams
                if self.order==1:
                    if self.max_order==1:
                        arpa_ofp.write( self.make_arc( self.sb, self.sb, parts[1], parts[1], float(parts[0]) ) )
                    elif parts[1]==self.se:
                        arpa_ofp.write( self.make_arc( self.boff, self.se, self.se, self.se, parts[0] ) )
                        #arpa_ofp.write( self.make_arc( self.se, self.boff, self.boff, self.boff, 0.0 ) )
                    elif parts[1]==self.sb:
                        arpa_ofp.write( self.make_arc( self.sb, self.boff, self.boff, self.boff, parts[2] ) )
                    else:
                        weight = "0.0"
                        if len(parts)==3: weight = parts[2]
                        arpa_ofp.write( self.make_arc( parts[1], self.boff, self.boff, self.boff, weight ) )
                        arpa_ofp.write( self.make_arc( self.boff, parts[1], parts[self.order], parts[self.order], parts[0] ) )
                #Handle middle-order N-grams
                elif self.order<self.max_order:
                    if parts[self.order]==self.se:
                        arpa_ofp.write( self.make_arc( ",".join(parts[1:self.order]), parts[self.order], parts[self.order], parts[self.order], parts[0] ) )
                    else :
                        weight = "0.0"
                        if len(parts)==self.order+2: weight = parts[-1]
                        arpa_ofp.write( self.make_arc( ",".join(parts[1:self.order+1]), ",".join(parts[2:self.order+1]), self.boff, self.boff, weight ) )
                        arpa_ofp.write( self.make_arc( ",".join(parts[1:self.order]), ",".join(parts[1:self.order+1]), parts[self.order], parts[self.order], parts[0] ) )
                #Handle N-order N-grams
                elif self.order==self.max_order:
                    if parts[self.order]==self.se:
                        arpa_ofp.write( self.make_arc( ",".join(parts[1:self.order]), parts[self.order], parts[self.order], parts[self.order], parts[0] ) )
                    else:
                        arpa_ofp.write( self.make_arc( ",".join(parts[1:self.order]), ",".join(parts[2:self.order+1]), parts[self.order], parts[self.order], parts[0] ) )
                else:
                    pass
            #Check the current n-gram order and other LM meta-data
            #NOTE: NOT super robust!!!
            if line.startswith("ngram "):
                line = line.replace("ngram ","")
                line = re.sub(r"=.*","", line)
                if self.auto_order:
                    self.max_order = int(line)
            elif line.startswith("\\data"):
                pass
            elif line.startswith("\\end"):
                break
            elif line.startswith("\\"):
                self.order = int(line.replace("\\","").replace("-grams:",""))
                
        arpa_ifp.close()
        if self.max_order==1:
            arpa_ofp.write("%s\n" % self.sb)
        else:
            arpa_ofp.write("%s\n" % self.se)
        arpa_ofp.close()
        return

    def print_all_syms( self ):
        """Macro to print all symbols tables."""
        self.print_ssyms( )
        self.print_isyms( )
        self.print_osyms( )
        return

    def print_ssyms( self ):
        """
           Print out a symbols table.
        """
        ofp = open("%s.g.ssyms"%self.prefix,"w")
        ofp.write("%s 0\n"%self.eps)
        for i,sym in enumerate(self.ssyms):
            ofp.write("%s %d\n"%(sym,i+1))
        ofp.close()
        return

    def print_isyms( self ):
        """
           Print out a symbols table.
        """
        ofp = open("%s.g.isyms"%self.prefix,"w")
        ofp.write("%s 0\n"%self.eps)
        for i,sym in enumerate(self.isyms):
            ofp.write("%s %d\n"%(sym,i+1))
        ofp.close()
        return

    def print_osyms( self ):
        """
           Print out a symbols table.
        """
        ofp = open("%s.g.osyms"%self.prefix,"w")
        ofp.write("%s 0\n"%self.eps)
        for i,sym in enumerate(self.osyms):
            ofp.write("%s %d\n"%(sym,i+1))
        ofp.close()
        return


if __name__=="__main__":
    import sys, os
    import argparse
    #Example command:
    # /arpa2fst.py train.arpa train.fst.txt train
    example = "%s --arpa LM --eps '<eps>' --prefix test" % sys.argv[0]
    parser  = argparse.ArgumentParser( description=example )
    parser.add_argument('--arpa',      "-a", help='ARPA format language model.', required=True )
    parser.add_argument('--prefix',    "-p", help='Prefix to be appended to all output files.', default="test" )
    parser.add_argument('--maxorder',  "-o", help='Explicitly specify the order of the output N-gram model.', default=0 )
    parser.add_argument('--eps',       "-e", help='Epsilon symbol, defaults to <eps>.', default="<eps>" )
    parser.add_argument('--sb',        "-b", help='Specify the sentence begin marker. Defaults to <s>.', default="<s>" )
    parser.add_argument('--se',        "-l", help='Specify the sentence end marker.  Defaults to </s>.', default="</s>" )
    parser.add_argument('--boff',      "-f", help='Specify explicit backoff marker.  Defaults to None, in which case the epsilon marker is used. <f> is common.', default=None)
    parser.add_argument('--sil',       "-s", help='Specify the optional silence marker.  Defaults to <sil>.', default="<sil>" )
    parser.add_argument('--verbose',   "-v", help='Verbose mode.', default=False, action="store_true" )
    args = parser.parse_args()

    if args.verbose==True:
        print "Running with the following arguments:"
        for attr, value in args.__dict__.iteritems():
            print attr, "=", value        

    arpa = ArpaLM( 
        args.arpa, 
        "%s.g.fst.txt" % (args.prefix), 
        prefix=args.prefix, 
        sb=args.sb, 
        se=args.se,
        sil=args.sil,
        maxorder=args.maxorder,
        eps=args.eps,
        boff=args.boff
        )
    arpa.arpa2fst( )
    arpa.print_all_syms( )
