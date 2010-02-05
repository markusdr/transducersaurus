#!/usr/bin/python
import openfst
from CascadeTools import *
import sys, os

def build_lex_example( dictfile, dict_type, lextype ):
    L = Lexicon( dictfile, lextype=lextype, dict_type=dict_type, loggerID="cmu.%s"%lextype )
    L.generate_lexicon_transducer()
    fst="exmodels/L-test.fst"; isyms="exmodels/L-test.isyms"; osyms="exmodels/L-test.osyms"; pdf="exmodels/L-test-%s.pdf"%lextype
    L.wfst.Write(fst)
    L.isyms.WriteText(isyms)
    L.osyms.WriteText(osyms)
    command = "fstdraw --portrait=true --isymbols=%s --osymbols=%s < %s | dot -Tpdf > exmodels/%s" % (isyms, osyms, fst, pdf)
    print "Generating: %s" % pdf
    os.system(command)
    return L

def build_lm_example( lmfile, isyms ):
    G = Arpa2FST( lmfile, isyms=isyms )
    G.generate_lm()
    openfst.Connect(G.wfst)
    G.wfst.Write("exmodels/G.fst")
    G.isyms.WriteText("exmodels/G.isyms")
    G.ssyms.WriteText("exmodels/G.ssyms")
    print "Generating: %s" % "exmodels/G.pdf"
    #os.system("fstdraw --portrait=true --ssymbols=%s --isymbols=%s --acceptor=true < %s | dot -Tpdf > %s" % ("G.ssyms","G.isyms","G.fst", "G.pdf"))
    os.system("fstdraw --portrait=true --isymbols=%s --acceptor=true < %s | dot -Tpdf > %s" % ("exmodels/G.isyms","exmodels/G.fst", "exmodels/G.pdf"))
    return G

def build_examples( dictfile ):
    lextypes = tuple(["default", "noloop", "allaux", "nosync"])
    for lextype in lextypes:
        build_lex_example( dictfile, "cmu", lextype )
    return


if __name__=="__main__":
    L = build_lex_example( sys.argv[1], "cmu", "default" )
    G = build_lm_example(  sys.argv[2], L.osyms )
    LG = openfst.StdVectorFst()
    openfst.Compose(L.wfst,G.wfst,LG)
    LGdet = openfst.StdVectorFst()
    openfst.Determinize(LG,LGdet)
    openfst.ArcSortInput(LGdet)
    LGdet.Write("exmodels/LG.fst")
    os.system("fstdraw --portrait=true --isymbols=%s --osymbols=%s --acceptor=true < %s | dot -Tpdf > %s" % ("exmodels/L-test.isyms","exmodels/G.isyms","exmodels/LG.fst", "exmodels/LG.pdf"))
    C = ContextDependency(L.phons, L.aux, osyms=L.isyms)
    C.generate_deterministic()
    openfst.ArcSortOutput(C.wfst)
    CLG = openfst.StdVectorFst()
    openfst.Compose(C.wfst,LGdet,CLG)
    CLGdet = openfst.StdVectorFst()
    openfst.Determinize(CLG,CLGdet)
    C.isyms.WriteText("exmodels/C-test.isyms")
    CLGdet.Write("exmodels/CLG.fst")
    C.wfst.Write("exmodels/C.fst")
    C.osyms.WriteText("exmodels/C.osyms")
    os.system("fstdraw --portrait=true --isymbols=%s --osymbols=%s --acceptor=true < %s | dot -Tpdf > %s" % ("exmodels/C-test.isyms","exmodels/G.isyms","exmodels/CLG.fst", "exmodels/CLG.pdf"))
    os.system("fstdraw --portrait=true --isymbols=%s --osymbols=%s --acceptor=true < %s | dot -Tpdf > %s" % ("exmodels/C-test.isyms","exmodels/C.osyms","exmodels/C.fst", "exmodels/C.pdf"))
    openfst.Minimize(CLGdet)
    CLGdet.Write("exmodels/CLGopt.fst")
    os.system("fstdraw --portrait=true --isymbols=%s --osymbols=%s --acceptor=true < %s | dot -Tpdf > %s" % ("exmodels/C-test.isyms","exmodels/G.isyms","exmodels/CLGopt.fst", "exmodels/CLGopt.pdf"))
    D = SphinxMapper( sys.argv[3], C.isyms, C.osyms )
    D.generate_d()       
    openfst.ArcSortOutput(D.wfst)       
    openfst.ArcSortInput(CLGdet)
    DCLG = openfst.StdVectorFst()
    openfst.Compose(D.wfst,CLGdet,DCLG)
    openfst.RmEpsilon(DCLG)
    DCLG.Write("exmodels/dCLG.fst")
    D.hmmsyms.WriteText("exmodels/D.isyms")
    os.system("fstdraw --portrait=true --isymbols=%s --osymbols=%s --acceptor=true < %s | dot -Tpdf > %s" % ("exmodels/D.isyms","exmodels/G.isyms","exmodels/dCLG.fst", "exmodels/dCLG.pdf"))
