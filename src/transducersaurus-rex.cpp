#include "Lexicon.hpp"
#include "LanguageModel.hpp"
#include "ContextDependency.hpp"
#include <stdio.h>
#include <string>
#include <fst/fstlib.h>

using namespace fst;

int main( int argc, const char* argv[] ) {
	
	//Build the LM FST
	printf("Generating the LM FST...\n");
	Arpa2OpenFST G( argv[1] );
	G.eps = "<eps>";
	G.tropical = false;
	G.generateFST();
	G.arpafst.Write("g.fst");
	
	//Build the Lexicon FST
	printf("Generating the Lexicon FST...\n");
	Lexicon2FST L( argv[2], G.isyms );
	L.generateFST();
	L.lexiconfst.Write("l.fst");
	//Build the Context Dependency FST
	printf("Generating the CD FST...\n");
	ContextDependency2FST C( L.phones, L.aux_syms, L.isyms );
	C.generateDeterministicAux();
	C.cdfst.Write("c.fst");
	//Build up the cascade
	printf("Generating LG...\n");
	Closure( &L.lexiconfst, CLOSURE_STAR );
	
	OLabelCompare<LogArc> ocomp;
	ILabelCompare<LogArc> icomp;
	ArcSort( &G.arpafst, icomp );
	ArcSort( &L.lexiconfst, ocomp );
	
	VectorFst<LogArc>  ndlg;
	ndlg = ComposeFst<LogArc> ( L.lexiconfst, G.arpafst );
	VectorFst<LogArc> lg;
	ndlg.Write("ndlg.fst");
	printf("Determinizing LG...\n");
	Determinize(ndlg, &lg);
	
	printf("Generating CLG...\n");
	VectorFst<LogArc> clg;
	ArcSort( &C.cdfst, ocomp );
	clg = ComposeFst<LogArc> ( C.cdfst, lg );
	clg.Write("clg.fst");
	
	return 0;
}