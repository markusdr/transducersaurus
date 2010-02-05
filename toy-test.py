#!/usr/bin/python
import openfst
from CascadeTools import *
import sys, os

def build_lex_example( dictfile, dict_type, lextype ):
    L = Lexicon( dictfile, lextype=lextype, dict_type=dict_type, loggerID="cmu.%s"%lextype )
    L.generate_lexicon_transducer()
    fst="exmodels/L.fst"; isyms="exmodels/L.isyms"; osyms="exmodels/L.osyms"; pdf="exgraphs/L-%s.pdf"%lextype
    L.wfst.Write(fst)
    L.isyms.WriteText(isyms)
    L.osyms.WriteText(osyms)
    command = "fstdraw --portrait=true --isymbols=%s --osymbols=%s < %s | dot -Tpdf > %s" % (isyms, osyms, fst, pdf)
    os.system(command)
    return L

def build_lex_examples( dictfile ):
    lextypes = tuple(["default", "noloop", "allaux", "nosync"])
    for lextype in lextypes:
        build_lex_example( dictfile, "cmu", lextype )
    return

def build_toy_cascade( lmfile, dictfile, mdef, connect=True, minimize=True ):
    """Build a toy cascade from the toy CMU data and generate graphs for all the intermediate results."""
    ############################################################
    #Generate L the lexicon
    L = build_lex_example( dictfile, "cmu", "default" )
    #Generate G the grammar
    G = Arpa2FST( lmfile, isyms=L.osyms, purgecrud=False )
    G.generate_lm()
    if connect: openfst.Connect(G.wfst)
    #Compose the L and G transducers
    LG = openfst.StdVectorFst()
    openfst.Compose(L.wfst,G.wfst,LG)
    #Determinize the LG cascade and sort the result
    LGdet = openfst.StdVectorFst()
    openfst.Determinize(LG,LGdet)
    openfst.ArcSortInput(LGdet)
    #Generate C the context dependency transducer and sort the result
    C = ContextDependency(L.phons, L.aux, osyms=L.isyms)
    C.generate_deterministic()
    openfst.ArcSortOutput(C.wfst)
    #Compose C with the LG cascade
    CLG = openfst.StdVectorFst()
    openfst.Compose(C.wfst,LGdet,CLG)
    #Determinize the LG cascade, minimize and sort the result
    CLGdet = openfst.StdVectorFst()
    openfst.Determinize(CLG,CLGdet)
    if minimize: openfst.Minimize(CLGdet)
    openfst.ArcSortInput(CLGdet)
    #Generate D the mapper transducer, assuming a Sphinx mdef file
    # and sort the result
    D = SphinxMapper( mdef, C.isyms, C.osyms )
    D.generate_d()       
    openfst.ArcSortOutput(D.wfst)       
    #Compose D with the CLG cascade.  This will also remove the 
    # auxiliary symbols that were generated for the lexicon transducer.
    DCLG = openfst.StdVectorFst()
    openfst.Compose(D.wfst,CLGdet,DCLG)
    ###########################################################
    #Write out the various components and symbol tables
    G.wfst.Write("exmodels/G.fst")
    G.isyms.WriteText("exmodels/G.isyms")
    G.ssyms.WriteText("exmodels/G.ssyms")
    LGdet.Write("exmodels/LG.fst")
    C.isyms.WriteText("exmodels/C.isyms")
    CLGdet.Write("exmodels/CLG.fst")
    C.wfst.Write("exmodels/C.fst")
    C.osyms.WriteText("exmodels/C.osyms")
    CLGdet.Write("exmodels/CLGopt.fst")
    DCLG.Write("exmodels/dCLG.fst")
    D.hmmsyms.WriteText("exmodels/D.isyms")
    ############################################################
    #Draw the graphs
    if connect:
        #if we connected the grammar graph the ssymbols will no longer work right.  This is really annoying but shikatanaine!
        os.system("fstdraw --portrait=true --isymbols=%s --acceptor=true < %s | dot -Tpdf > %s" % ("exmodels/G.isyms","exmodels/G.fst", "exgraphs/G.pdf"))
    else:
        os.system("fstdraw --portrait=true --ssymbols=%s --isymbols=%s --acceptor=true < %s | dot -Tpdf > %s" % ("G.ssyms","G.isyms","G.fst", "G.pdf"))
    os.system("fstdraw --portrait=true --isymbols=%s --osymbols=%s --acceptor=true < %s | dot -Tpdf > %s" % ("exmodels/L.isyms", "exmodels/G.isyms", "exmodels/LG.fst",     "exgraphs/LG.pdf"))
    os.system("fstdraw --portrait=true --isymbols=%s --osymbols=%s --acceptor=true < %s | dot -Tpdf > %s" % ("exmodels/C.isyms", "exmodels/G.isyms", "exmodels/CLG.fst",    "exgraphs/CLG.pdf"))
    os.system("fstdraw --portrait=true --isymbols=%s --osymbols=%s --acceptor=true < %s | dot -Tpdf > %s" % ("exmodels/C.isyms", "exmodels/C.osyms", "exmodels/C.fst",      "exgraphs/C.pdf"))
    os.system("fstdraw --portrait=true --isymbols=%s --osymbols=%s --acceptor=true < %s | dot -Tpdf > %s" % ("exmodels/C.isyms", "exmodels/G.isyms", "exmodels/CLGopt.fst", "exgraphs/CLGopt.pdf"))
    os.system("fstdraw --portrait=true --isymbols=%s --osymbols=%s --acceptor=true < %s | dot -Tpdf > %s" % ("exmodels/D.isyms",      "exmodels/G.isyms", "exmodels/dCLG.fst",   "exgraphs/dCLG.pdf"))

    return

if __name__=="__main__":
    build_toy_cascade(sys.argv[1], sys.argv[2], sys.argv[3])
    build_lex_examples(sys.argv[2])
