#!/usr/bin/python
import re
from collections import defaultdict

class Lexicon( ):

    """Build a lexicon transducer."""

    def __init__( self, dictfile, prefix="lexicon" ):
        """Initialize some basic variables."""
        self.dictfile   = dictfile
        self.prons   = defaultdict(int)
        self.eps     = "<eps>"
        self.aux     = set([])
        self.phones  = set([])
        self.isyms   = set([])
        self.osyms   = set([])
        self.start   = 0
        self.last_s  = 1
        self.prefix  = prefix

    def generate_lexicon_transducer( self ):
        """
           Generate lexicon entries for a generic dictionary.
           Format should be:
           -----------------
             WORD\tW ER D
           -----------------
        """
        dict_fp = open(self.dictfile)
        for entry in dict_fp.readlines():
            entry = entry.strip()
            phones = re.split(r"\s+",entry)
            word   = phones.pop(0)
            pron   = " ".join(phones)
            self.prons[pron] += 1
            
            print self.start, self.last_s, phones[0], word 
            self.isyms.add(phones[0])
            self.phones.add(phones[0])
            phones.pop(0)

            self.osyms.add(word)
            for p in phones:
                print self.last_s, self.last_s+1, p, self.eps
                self.isyms.add(p)
                self.phones.add(p)
                self.last_s += 1
                
            aux_sym = "#10%d"%self.prons[pron]
            self.isyms.add(aux_sym)
            self.aux.add(aux_sym)
            print self.last_s, self.last_s+1, aux_sym, self.eps
            self.last_s += 1
            print self.last_s
            self.last_s += 1
        dict_fp.close()
        return

    def print_isyms( self ):
        isym_f   = "%s.l.isyms" % self.prefix
        isyms_fp = open( isym_f,"w" )
        isyms_fp.write("%s %d\n" % (self.eps, 0))
        for i,sym in enumerate(self.isyms):
            isyms_fp.write("%s %d\n" % (sym, i+1))
        isyms_fp.close()
        return

    def print_osyms( self ):
        osym_f   = "%s.l.osyms" % self.prefix
        osyms_fp = open( osym_f,"w" )
        osyms_fp.write("%s %d\n" % (self.eps, 0))
        for i,sym in enumerate(self.osyms):
            osyms_fp.write("%s %d\n" % (sym, i+1))
        osyms_fp.close()
        return
            
    def print_phones( self ):
        phones_fp = open("%s.phons"%self.prefix,"w")
        for p in self.phones:
            phones_fp.write("%s\n"%p)
        phones_fp.close()
        return

    def print_aux( self ):
        aux_fp = open("%s.aux"%self.prefix,"w")
        for a in self.aux:
            aux_fp.write("%s\n"%a)
        aux_fp.close()
        return

    def print_all_syms( self ):
        self.print_isyms()
        self.print_osyms()
        return
            

if __name__=="__main__":
    import sys
    L = Lexicon( sys.argv[1], prefix=sys.argv[2] )
    L.generate_lexicon_transducer()
    L.print_all_syms()
    L.print_aux()
    L.print_phones()
