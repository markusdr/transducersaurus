#ifndef LANGUAGEMODEL_H
#define LANGUAGEMODEL_H
/*
 *  LanguageModel.hpp
 *  openPhone-proj
 *
 *  Created by Joe Novak on 11/02/18.
 *  Copyright 2011 __MyCompanyName__. All rights reserved.
 *
 */
#include <fst/fstlib.h>

using namespace fst;

class Arpa2OpenFST {
	/*
	 Convert an arbitrary ARPA format N-gram language model of 
	 order N to an equivalent OpenFST-based WFST.
	 
	 -- Back-off weights are handled as normal epsilon-arcs
	 
	 -- Any 'missing' back-offs are automatically set to '0.0'
	 however the actual value should be semiring dependent.
	 
	 -- Completely missing lower-order N-grams will be ignored.  
	 In some interpolated models this seems to occasionally lead to 
	 non-coaccessible states.  Other possible options might be to
	 -*- Generate the missing N-grams (but this seems wrong)
	 -*- Force the higher-order N-gram to sentence-end
	 
	 -- In this simple implementation the names for the symbols tables 
	 are fixed to 'ssyms', 'isyms', and 'osyms'.  The default epsilon
	 symbol is '<eps>' but can be set to whatever the user prefers.
	 */  
	
public: 
	ifstream      arpa_lm_fp;
	string		  arpa_lm_file;
	string		  line;
	bool		  tropical;
	size_t		  max_order;
	size_t		  current_order;
	//default values set
	string		  eps;
	string		  start;    //start tag
	string		  sb;		//sentence begin tag
	string		  se;		//sentence end tag
	//FST stuff
	VectorFst<LogArc>  arpafst;
	SymbolTable*   ssyms;
	SymbolTable*   isyms;
	SymbolTable*   osyms;
	
	
	Arpa2OpenFST( );
	
	Arpa2OpenFST ( const char* arpa_lm );
	
	Arpa2OpenFST ( const char* arpa_lm, SymbolTable* iosymbols );
	
	double log2tropical( double val );
	
	void make_arc( string istate, string ostate, string isym, string osym, double weight );
	
	string join( vector<string> &tokens, string sep, int start, int end );
	
	void generateFST ( );
	
};

#endif // LANGUAGEMODEL_H //

