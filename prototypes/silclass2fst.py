#!/usr/bin/python
import re, math

class Silclass( ):

    def __init__( self, vocabfile, sil="<sil>", eps="<eps>", silperc=0.117, prefix="silclass" ):
        self.vocabfile = vocabfile
        self.sil       = sil
        self.eps       = eps
        self.silperc   = silperc
        self.nosilperc = 1.0-silperc
        self.vocab     = set([])
        self.isyms     = set([])
        self.isyms.add(self.sil)
        self.osyms     = set([])
        self.osyms.add(self.sil)
        self.prefix    = prefix

    def read_vocab( self ):
        vocab_fp = open( self.vocabfile,"r" )
        for line in vocab_fp:
            line = line.strip()
            self.vocab.add(line)
        vocab_fp.close()
        return

    def log2tropical( self, val ):
        tropval = math.log(10)*float(val)*-1
        return tropval 

    def generate_silclass( self ):
        """Generate the silence class transducer."""
        count = 1
        for word in self.vocab:
            if word==self.sil:
                continue
            print 0, count, word, word
            print count, count, self.eps, self.sil, self.log2tropical(self.silperc)
            print count, 0, self.eps, self.eps, self.log2tropical(self.nosilperc)
            self.isyms.add(word)
            self.osyms.add(word)
            count += 1
        print 0
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
