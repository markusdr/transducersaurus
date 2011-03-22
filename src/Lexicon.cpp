/*
 *  lexicon.cpp
 *  openPhone-proj
 *
 *  Created by Joe Novak on 11/02/18.
 *  Copyright 2011 __MyCompanyName__. All rights reserved.
 *
 */
#include "Lexicon.hpp"
#include <iostream>
#include <fstream>
#include <string>
#include <iterator>
#include <vector>
#include <sstream>
#include <set>
#include <math.h>
#include <fst/fstlib.h>

using namespace fst;


Lexicon2FST::Lexicon2FST( ) {
	//Default constructor
	cout << "Lexicon2FST requires an input pronunciation lexicon." << endl;
}
	
Lexicon2FST::Lexicon2FST( const char* lexicon ){
	lexicon_fp.open( lexicon );
	lexicon_file = lexicon;
	tropical = false;
	eps = "<eps>";

	isyms = new SymbolTable("isyms");
	osyms = new SymbolTable("osyms");
	lexiconfst.AddState(); 
	lexiconfst.SetStart(0);
	isyms->AddSymbol(eps,0);
	osyms->AddSymbol(eps,0);
}

Lexicon2FST::Lexicon2FST( const char* lexicon, SymbolTable* iosymbols ){
	lexicon_fp.open( lexicon );
	lexicon_file = lexicon;
	tropical = false;
	eps = "<eps>";
	
	isyms = new SymbolTable("isyms");
	osyms = iosymbols;
	lexiconfst.AddState(); 
	lexiconfst.SetStart(0);
	isyms->AddSymbol(eps,0);
	osyms->AddSymbol(eps,0);
}

double Lexicon2FST::log2tropical( double val ) {
		return val * -1.0;
}
	
void Lexicon2FST::generateEntry( vector<string> tokens ){
	//Generate a single lexicon entry
	int nextState = lexiconfst.AddState();
	string pron = join(tokens, " ", 1, tokens.size());
	lexicon_map[pron]++;
	lexiconfst.AddArc( lexiconfst.Start(), LogArc( isyms->AddSymbol(tokens[1]), osyms->AddSymbol(tokens[0]), 0.0, nextState) );
	phones.insert(tokens[1]);
	for( size_t i=2; i<tokens.size(); i++ ){
		lexiconfst.AddArc( nextState, LogArc( isyms->AddSymbol(tokens[i]), osyms->Find(eps), 0.0, nextState+1) );
		nextState = lexiconfst.AddState();
		phones.insert(tokens[i]);
	}
	char auxsym [50];
	sprintf(auxsym, "#10%d", lexicon_map[pron]);
	aux_syms.insert(auxsym);
	lexiconfst.AddArc( nextState, LogArc( isyms->AddSymbol(auxsym), osyms->Find(eps), 0.0, nextState+1) );
	lexiconfst.AddState();
	lexiconfst.SetFinal(nextState+1, 0.0);
	return;
}
	
string Lexicon2FST::join( vector<string> &tokens, string sep, int start, int end ){
	//Join the elements of a string vector into a single string
	stringstream ss;
	for( int i=start; i<end; i++ ){
		if(i != start)
			ss << sep;
		ss << tokens[i];
	}
	return ss.str();
}
	
void Lexicon2FST::generateFST( ){
	if( lexicon_fp.is_open() ){
		while( lexicon_fp.good() ){
			//Read one line
			getline( lexicon_fp, line );
			if( line.compare("")==0 )
				continue;
			//Tokenize the line.  Word should be first token.
			// Remaining tokens will be Phonemes.
			//----------------------
			// TEST   T EH S T
			//----------------------
			//CMU-style (2), (3), etc. will be treated as normal 
			// entries.  Preprocess to avoid this.
			vector<string> tokens;
			istringstream iss(line);
			copy( istream_iterator<string>(iss),
				 istream_iterator<string>(),
				 back_inserter<vector<string> >(tokens)
				 );
			//cout << "generating an entry..." << endl;
			//cout << line << endl;
			generateEntry( tokens );
		}
		lexicon_fp.close();
	}else{
		cout << "Couldn't open the file, something went terribly wrong!" << endl;
	}
	return;
}

