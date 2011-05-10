#!/usr/bin/python
import re, math

class Silclass( ):

    def __init__( self, vocabfile, sil="<sil>", eps="<eps>", silperc=0.117, prefix="silclass", failure=None ):
        self.vocabfile = vocabfile
        self.sil       = sil
        self.eps       = eps
        self.silperc   = silperc
        self.nosilperc = 1.0-silperc
        self.vocab     = set([])
        self.failure   = failure
        self.isyms     = set([self.sil])
        self.osyms     = set([self.sil])
        if failure:
            self.isyms.add(failure)
            self.osyms.add(failure)
        self.prefix    = prefix

    def read_vocab( self ):
        vocab_fp = open( self.vocabfile,"r" )
        for line in vocab_fp:
            line = line.strip()
            sym, id = re.split(r"\s+",line)
            if int(id)==0:
                continue
            self.vocab.add(sym)
        vocab_fp.close()
        return

    def log2tropical( self, val ):
        tropval = math.log(float(val)) * -1.0
        return tropval 

    def generate_silclass( self ):
        """Generate the silence class transducer."""
        count = 1
        silclass_fp = open("PREFIX.t.fst.txt".replace("PREFIX",self.prefix),"w")
        for word in self.vocab:
            if word==self.sil:
                continue
            silclass_fp.write("%d %d %s %s\n" % (0, count, word, word))
            silclass_fp.write("%d %d %s %s %f\n" % (count, count, self.eps, self.sil, self.log2tropical(self.silperc)))
            silclass_fp.write("%d %d %s %s %f\n" % (count, 0, self.eps, self.eps, self.log2tropical(self.nosilperc)))
            self.isyms.add(word)
            self.osyms.add(word)
            count += 1
        if self.failure:
            silclass_fp.write("0 0 %s %s\n" % (self.failure, self.failure))
        silclass_fp.write("0\n")
        silclass_fp.close()
        return

    def print_isyms( self ):
        ofp = open( "%s.t.isyms"%self.prefix, "w" )
        ofp.write("%s 0\n"%self.eps)
        for i,sym in enumerate(self.isyms):
            ofp.write("%s %d\n"%(sym,i+1))
        ofp.close()
        return

    def print_osyms( self ):
        ofp = open( "%s.t.osyms"%self.prefix, "w" )
        ofp.write("%s 0\n"%self.eps)
        for i, sym  in enumerate(self.osyms):
            ofp.write("%s %d\n"%(sym,i+1))
        ofp.close()
        return

    def print_all_syms( self ):
        self.print_isyms()
        self.print_osyms()


if __name__=="__main__":
    import sys

    silclass = Silclass( sys.argv[1], prefix=sys.argv[2] )
    silclass.read_vocab( )
    silclass.generate_silclass( )
    silclass.print_all_syms( )
