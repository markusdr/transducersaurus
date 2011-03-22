#include "LanguageModel.hpp"
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

	
Arpa2OpenFST::Arpa2OpenFST( ) {
	//Default constructor.
	cout << "Class ARPA2TextFST requires an input ARPA-format LM..." << endl;
}
	
Arpa2OpenFST::Arpa2OpenFST ( const char* arpa_lm ) {
	arpa_lm_fp.open( arpa_lm );
	arpa_lm_file = arpa_lm;
	tropical     = true;
	max_order    = 0;
	eps          = "<eps>";
	start        = "<start>";
	sb           = "<s>";
	se           = "</s>";
		
	//Initialize the fst and symbol tables
	ssyms = new SymbolTable("ssyms");
	isyms = new SymbolTable("isyms");
	osyms = new SymbolTable("osyms");
	arpafst.AddState(); 
	arpafst.SetStart(0);
	ssyms->AddSymbol(start);
	arpafst.AddState();
	arpafst.SetFinal(1,0.0);
	ssyms->AddSymbol(se,1);
	isyms->AddSymbol(eps,0);
	osyms->AddSymbol(eps,0);
}

Arpa2OpenFST::Arpa2OpenFST ( const char* arpa_lm, SymbolTable* iosymbols ) {
	//Allow the the user to specify the input/output symbol table explicitly
	//Useful during cascade construction
	arpa_lm_fp.open( arpa_lm );
	arpa_lm_file = arpa_lm;
	tropical     = true;
	max_order    = 0;
	eps          = "<eps>";
	start        = "<start>";
	sb           = "<s>";
	se           = "</s>";
	
	//Initialize the fst and symbol tables
	ssyms = new SymbolTable("ssyms");
	isyms = iosymbols;
	osyms = iosymbols;
	arpafst.AddState(); 
	arpafst.SetStart(0);
	ssyms->AddSymbol(start);
	arpafst.AddState();
	arpafst.SetFinal(1,0.0);
	ssyms->AddSymbol(se,1);
	isyms->AddSymbol(eps,0);
	osyms->AddSymbol(eps,0);
}

double Arpa2OpenFST::log2tropical( double val ) {
	return val * -1.0;
}
	
void Arpa2OpenFST::make_arc( string istate, string ostate, string isym, string osym, double weight ){
	//Build up an arc for the WFST.  Weights default to the Log semiring.
	if( ssyms->Find(istate) == -1 ){
		int new_ssym_id = arpafst.AddState();
		ssyms->AddSymbol( istate, new_ssym_id );
	}
	if( ssyms->Find(ostate) == -1 ){
		int new_ssym_id = arpafst.AddState();
		ssyms->AddSymbol( ostate, new_ssym_id );
	}
	weight = log2tropical(weight);
	arpafst.AddArc( ssyms->Find(istate), LogArc( isyms->AddSymbol(isym), osyms->AddSymbol(osym), weight, ssyms->Find(ostate)) );
	return;
}
	
string Arpa2OpenFST::join( vector<string> &tokens, string sep, int start, int end ){
	//Join the elements of a string vector into a single string
	stringstream ss;
	for( int i=start; i<end; i++ ){
		if(i != start)
			ss << sep;
		ss << tokens[i];
	}
	return ss.str();
}
	
void Arpa2OpenFST::generateFST ( ) {
	if( arpa_lm_fp.is_open() ){
		make_arc( 
				 start,           //Input state label
				 sb,              //Output state label
				 sb,              //Input label
				 sb,              //Output label
				 0.0              //Weight
				 );
		while( arpa_lm_fp.good() ){
			getline( arpa_lm_fp, line );
			
			if( current_order > 0 && line.compare("") != 0 && line.compare(0,1,"\\") != 0 ){
				//Process data based on N-gram order
				vector<string> tokens;
				istringstream iss(line);
				
				copy( istream_iterator<string>(iss),
					 istream_iterator<string>(),
					 back_inserter<vector<string> >(tokens)
					 );
				//Handle the unigrams
				if( current_order == 1 ){
					if( tokens[1].compare(se) == 0 ){
						make_arc( 
								 eps, 
								 se, 
								 se, 
								 se, 
								 atof(tokens[0].c_str()) 
								 );
					}else if( tokens[1].compare(sb) == 0 ){
						double weight = tokens.size()==3 ? atof(tokens[2].c_str()) : 0.0;
						make_arc( 
								 eps, 
								 sb, 
								 eps, 
								 eps, 
								 weight 
								 );
					}else{
						double weight = tokens.size()==3 ? atof(tokens[2].c_str()) : 0.0;
						make_arc( 
								 tokens[1], 
								 eps, 
								 eps, 
								 eps, 
								 weight 
								 );
						make_arc( 
								 eps, 
								 tokens[1], 
								 tokens[current_order], 
								 tokens[current_order], 
								 atof(tokens[0].c_str())
								 );
					}
					//Handle the middle-order N-grams
				}else if( current_order < max_order ){
					if( tokens[current_order].compare(se) == 0 ){
						make_arc( 
								 join(tokens, ",", 1, current_order), 
								 tokens[current_order], 
								 tokens[current_order], 
								 tokens[current_order], 
								 atof(tokens[0].c_str()) 
								 );
					}else{
						double weight = tokens.size()==current_order+2 ? atof(tokens[tokens.size()-1].c_str()) : 0.0;
						make_arc( 
								 join(tokens, ",", 1, current_order+1), 
								 join(tokens, ",", 2, current_order+1), 
								 eps, 
								 eps, 
								 weight
								 );
						make_arc( 
								 join(tokens, ",", 1, current_order), 
								 join(tokens, ",", 1, current_order+1), 
								 tokens[current_order], 
								 tokens[current_order], 
								 atof(tokens[0].c_str())
								 );
					}
					//Handle the N-order N-grams
				}else if( current_order==max_order ){
					if( tokens[current_order].compare(se) == 0 ){
						make_arc( 
								 join(tokens, ",", 1, current_order), 
								 tokens[current_order], 
								 tokens[current_order], 
								 tokens[current_order], 
								 atof(tokens[0].c_str()) 
								 );
					}else{
						make_arc( 
								 join(tokens, ",", 1, current_order), 
								 join(tokens, ",", 2, current_order+1), 
								 tokens[current_order], 
								 tokens[current_order], 
								 atof(tokens[0].c_str())
								 );
					}
				}
			}
			
			//Parse the header/footer/meta-data.  This is not foolproof.
			//Random header info starting with '\' or 'ngram', etc. may cause problems.
			if( line.size() > 4 && line.compare( 0, 5, "ngram" ) == 0 )
				max_order = (size_t)atoi(&line[6])>max_order ? atoi(&line[6]) : max_order;
			else if( line.compare( "\\data\\" ) == 0 )
				continue;
			else if( line.compare( "\\end\\" ) == 0 )
				break;
			else if( line.size() > 0 && line.compare( 0, 1, "\\" ) == 0 ){
				line.replace(0, 1, "");
				line.replace(1, 7, "");
				current_order = atoi(&line[0]);
			}
		}
		arpa_lm_fp.close();
	}else{
		cout << "Unable to open file: " << arpa_lm_file << endl;
	}
}




