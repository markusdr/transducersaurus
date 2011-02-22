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

    def __init__( self, arpaifile, arpaofile, eps="<eps>", max_order=0, sil="<sil>", prefix="test", auto_order=True ):
        self.arpaifile = arpaifile
        self.arpaofile = arpaofile
        self.ssyms    = set([])
        self.isyms    = set([])
        self.osyms    = set([])
        self.eps      = eps
        self.sil      = sil
        #Just in case
        self.isyms.add(self.sil)
        self.osyms.add(self.sil)
        #----
        self.order    = 0
        self.tropical = True
        self.max_order = max_order
        self.prefix    = prefix
        self.auto_order = auto_order

    def to_tropical( self, val ):
        """
           Convert values to the tropical semiring.
        """
        logval = math.log(10.0) * float(val) * -1.0
        return logval

    def make_arc( self, istate, ostate, isym, osym, weight=0.0 ):
        """
           Build a single arc.  Add symbols to the symbol tables
           as necessary, but ignore epsilons.
        """
        if not istate==self.eps: self.ssyms.add(istate)
        if not ostate==self.eps: self.ssyms.add(ostate)
        
        if not isym==self.eps: self.isyms.add(isym)
        if not osym==self.eps: self.osyms.add(osym)

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
        arpa_ofp.write(self.make_arc( "<start>", "<s>", "<s>", "<s>", 0.0 ))
        for line in arpa_ifp:
            line = line.strip()
            #Process based on n-gram order
            if self.order>0 and not line=="" and not line.startswith("\\"):
                parts = re.split(r"\s+",line)
                if self.order==1:
                    if parts[1]=="</s>":
                        arpa_ofp.write( self.make_arc( self.eps, "</s>", "</s>", "</s>", parts[0] ) )
                    elif parts[1]=="<s>":
                        arpa_ofp.write( self.make_arc( "<s>", self.eps, self.eps, self.eps, parts[2] ) )
                    else:
                        weight = "0.0"
                        if len(parts)==3: weight = parts[2]
                        arpa_ofp.write( self.make_arc( parts[1], self.eps, self.eps, self.eps, parts[2] ) )
                        arpa_ofp.write( self.make_arc( self.eps, parts[1], parts[self.order], parts[self.order], parts[0] ) )
                elif self.order<self.max_order:
                    if parts[self.order]=="</s>":
                        arpa_ofp.write( self.make_arc( ",".join(parts[1:self.order]), parts[self.order], parts[self.order], parts[self.order], parts[0] ) )
                    else :
                        weight = "0.0"
                        if len(parts)==self.order+2: weight = parts[-1]
                        arpa_ofp.write( self.make_arc( ",".join(parts[1:self.order+1]), ",".join(parts[2:self.order+1]), self.eps, self.eps, weight ) )
                        arpa_ofp.write( self.make_arc( ",".join(parts[1:self.order]), ",".join(parts[1:self.order+1]), parts[self.order], parts[self.order], parts[0] ) )
                elif self.order==self.max_order:
                    if parts[self.order]=="</s>":
                        arpa_ofp.write( self.make_arc( ",".join(parts[1:self.order]), parts[self.order], parts[self.order], parts[self.order], parts[0] ) )
                    else:
                        arpa_ofp.write( self.make_arc( ",".join(parts[1:self.order]), ",".join(parts[2:self.order+2]), parts[self.order], parts[self.order], parts[0] ) )
                else:
                    pass
            #Check the current n-gram order
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
        arpa_ofp.write("</s>\n")
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
    #Example command:
    # /arpa2fst.py train.arpa train.fst.txt train
    
    arpa = ArpaLM( sys.argv[1], sys.argv[2], prefix=sys.argv[3] )
    arpa.arpa2fst( )
    arpa.print_all_syms( )
