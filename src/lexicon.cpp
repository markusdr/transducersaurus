/*
 *  lexicon.cpp
 *  openPhone-proj
 *
 *  Created by Joe Novak on 11/02/18.
 *  Copyright 2011 __MyCompanyName__. All rights reserved.
 *
 */
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

class Lexicon2FST {
	/*
	 Convert a CMU-style lexicon to an equivalent FST suitable for building an LVCSR cascade.
	*/
public:
	ifstream      lexicon_fp;
	string		  lexicon_file;
	string		  line;
	bool		  tropical;
	//default values set
	string		  eps;
	//FST stuff
	StdVectorFst  lexiconfst;
	SymbolTable*  isyms;
	SymbolTable*  osyms;
	map<string,int>  lexicon_map;

	
	Lexicon2FST( ) {
		//Default constructor
		cout << "Lexicon2FST requires an input pronunciation lexicon." << endl;
	}
	
	Lexicon2FST( const char* lexicon ){
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

	double log2tropical( double val ) {
		return log(10.0) * val * -1.0;
	}
	
	void generateEntry( vector<string> tokens ){
		//Generate a single lexicon entry
		int nextState = lexiconfst.AddState();
		string pron = join(tokens, " ", 1, tokens.size());
		lexicon_map[pron]++;
		lexiconfst.AddArc( lexiconfst.Start(), StdArc( isyms->AddSymbol(tokens[1]), osyms->AddSymbol(tokens[0]), 0.0, nextState) );
		for( int i=2; i<tokens.size(); i++ ){
			lexiconfst.AddArc( nextState, StdArc( isyms->AddSymbol(tokens[i]), osyms->Find(eps), 0.0, nextState+1) );
			nextState = lexiconfst.AddState();
		}
		char* auxsym;
		sprintf(auxsym, "#10%d", lexicon_map[pron]);
		lexiconfst.AddArc( nextState, StdArc( isyms->AddSymbol(auxsym), osyms->Find(eps), 0.0, nextState+1) );
		lexiconfst.AddState();
		lexiconfst.SetFinal(nextState+1, 0.0);
		return;
	}
	
	string join( vector<string> &tokens, string sep, int start, int end ){
		//Join the elements of a string vector into a single string
		stringstream ss;
		for( size_t i=start; i<end; i++ ){
			if(i != start)
				ss << sep;
			ss << tokens[i];
		}
		return ss.str();
	}
	
	void generateFST( ){
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
				cout << "generating an entry..." << endl;
				cout << line << endl;
				generateEntry( tokens );
			}
			cout << "shutting down.." << endl;
			lexicon_fp.close();
		}else{
			cout << "Couldn't open the file, something went terribly wrong!" << endl;
		}
		return;
	}
};

int main( int argc, const char* argv[] ) {
	Lexicon2FST l2tfst( argv[1] );
	l2tfst.generateFST();
	l2tfst.lexiconfst.Write("lex.fst");
	l2tfst.isyms->WriteText("lex.isyms");
	l2tfst.osyms->WriteText("lex.osyms");
	return 0;
}	
