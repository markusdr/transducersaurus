#ifndef LEXICON_H
#define LEXICON_H
/*
 *  Lexicon.hpp 
 *  openPhone-proj
 *
 *  Created by Joe Novak on 11/02/18.
 *  Copyright 2011 __MyCompanyName__. All rights reserved.
 *
 */
#include <fst/fstlib.h>

using namespace fst;

class Lexicon2FST {
	/*
	 Convert a CMU-style lexicon to an equivalent FST suitable for building an LVCSR cascade.
	*/
public:
	ifstream         lexicon_fp;
	string		     lexicon_file;
	string		     line;
	bool		     tropical;
	string	     	 eps;

	//FST stuff
	VectorFst<LogArc>     lexiconfst;
	SymbolTable*     isyms;
	SymbolTable*     osyms;
	map<string,int>  lexicon_map;
	set<string>   aux_syms;
	set<string>   phones;

	
	Lexicon2FST( );
	
	Lexicon2FST( const char* lexicon );
	
	Lexicon2FST( const char* lexicon, SymbolTable* iosymbols );

	double log2tropical( double val );
	
	void generateEntry( vector<string> tokens );
	
	string join( vector<string> &tokens, string sep, int start, int end );
	
	void generateFST( );
};

#endif // LEXICON_H //
