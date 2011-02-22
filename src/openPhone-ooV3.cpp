#include <iostream>
#include <fstream>
#include <string>
#include <iterator>
#include <vector>
#include <sstream>
#include <set>
#include <math.h>

using namespace std;


class Arpa2TextFST {
	/*
	 Convert an arbitrary ARPA format N-gram language model of 
	 order N to an equivalent WFST.
	 
	 -- Back-off weights are handled as normal epsilon-arcs
	 
	 -- Any 'missing' back-offs are automatically set to '0.0'
	    however the actual value should be semiring dependent.
	 
	 -- Completely missing lower-order N-grams will be ignored.  
	    In some interpolated models this seems to occasionally lead to 
	    non-coaccessible states.  Other possible options might be to
		-*- Generate the missing N-grams (but this seems wrong)
	    -*- Force the higher-order N-gram to sentence-end
	 
	    Either way requires tracking the existing N-grams, which is 
	    annoying in this text-only context.
	 
	 -- In this simple implementation the names for the symbols tables 
	    are fixed to 'ssyms', 'isyms', and 'osyms'.  The default epsilon
	    symbol is '<eps>' but can be set to whatever the user prefers.
	*/     

public: 
	ifstream     arpa_lm_fp;
	string       arpa_lm_file;
	string       line;
	bool         tropical;
	int          max_order;       //What order is the N-gram model?
	int          current_order;
	//these are fixed
	string       eps;
	string       start;   //start tag
	string       sb;      //sentence begin
	string       se;      //sentence end
	set<string>  ssyms;
	set<string>  isyms;
	set<string>  osyms;
	
	Arpa2TextFST( ) {
		//Default constructor.
		cout << "Class ARPA2TextFST requires an input ARPA-format LM..." << endl;
	};
	
	Arpa2TextFST ( const char* arpa_lm ) {
		arpa_lm_fp.open( arpa_lm );
		arpa_lm_file = arpa_lm;
		tropical     = false;
		max_order    = 0;
		eps          = "<eps>";
		start        = "<start>";
		sb           = "<s>";
		se           = "</s>";
    }
	
	void generateFST ( ) {
		if( arpa_lm_fp.is_open() ){
			make_text_arc( 
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
							make_text_arc( 
										  eps, 
										  se, 
										  se, 
										  se, 
										  atof(tokens[0].c_str()) 
										  );
						}else if( tokens[1].compare(sb) == 0 ){
							double weight = tokens.size()==3 ? atof(tokens[2].c_str()) : 0.0;
							make_text_arc( 
										  eps, 
										  sb, 
										  eps, 
										  eps, 
										  weight 
										  );
						}else{
							double weight = tokens.size()==3 ? atof(tokens[2].c_str()) : 0.0;
							make_text_arc( 
										  tokens[1], 
										  eps, 
										  eps, 
										  eps, 
										  weight 
										  );
							make_text_arc( 
										  eps, 
										  tokens[1], 
										  tokens[current_order], 
										  tokens[current_order], 
										  atof(tokens[0].c_str())
										  );
						}
					//Handle the middle-order N-grams
					}else if( current_order < max_order ){
						if( tokens[current_order].compare("</s>") == 0 ){
							make_text_arc( 
										  join(tokens, ",", 1, current_order), 
										  tokens[current_order], 
										  tokens[current_order], 
										  tokens[current_order], 
										  atof(tokens[0].c_str()) 
										  );
						
						}else{
							double weight = tokens.size()==current_order+2 ? atof(tokens[tokens.size()-1].c_str()) : 0.0;
							make_text_arc( 
										  join(tokens, ",", 1, current_order+1), 
										  join(tokens, ",", 2, current_order+1), 
										  eps, 
										  eps, 
										  weight
										  );
							make_text_arc( 
										  join(tokens, ",", 1, current_order), 
										  join(tokens, ",", 1, current_order+1), 
										  tokens[current_order], 
										  tokens[current_order], 
										  atof(tokens[0].c_str())
										  );
						}
				    //Handle the N-order N-grams
					}else if( current_order==max_order ){
						if( tokens[current_order].compare("</s>") == 0 ){
							make_text_arc( 
										  join(tokens, ",", 1, current_order), 
										  tokens[current_order], 
										  tokens[current_order], 
										  tokens[current_order], 
										  atof(tokens[0].c_str()) 
										  );
						}else{
							make_text_arc( 
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
				if( line.size() > 4 && line.compare( 0, 5, "ngram" ) == 0 ){
					max_order = atoi(&line[6])>max_order ? atoi(&line[6]) : max_order;
				}else if( line.compare( "\\data\\" ) == 0 )
					continue;
				else if( line.compare( "\\end\\" ) == 0 ){
					cout << se << endl;
					break;
				}else if( line.size() > 0 && line.compare( 0, 1, "\\" ) == 0 ){
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

	double log2tropical( double val ) {
		return log(10.0) * val * -1.0;
	}
	
	void make_text_arc( string istate, string ostate, string isym, string osym, double weight ){
		//Build up an arc for the WFST.  Weights default to the Log semiring.
		if( istate.compare(eps) != 0 ) ssyms.insert(istate);
		if( ostate.compare(eps) != 0 ) ssyms.insert(ostate);
		if( isym.compare(eps)   != 0 ) isyms.insert(isym);
		if( osym.compare(eps)   != 0 ) osyms.insert(osym);
		if( tropical==true )           weight = log2tropical(weight);
		cout << istate << "\t" << ostate << "\t" << isym << "\t" << osym << "\t" << weight << endl;
		return;
	}
	
	void print_all_syms( const char* prefix="" ){
		char fname[1024];
		sprintf(fname, "%sssyms", prefix);
		print_syms( ssyms, fname );
		sprintf(fname, "%sisyms", prefix);
		print_syms( isyms, fname );
		sprintf(fname, "%sosyms", prefix);
		print_syms( osyms, fname );
	}
	
	void print_syms( set<string> syms, const char* ofile ){
		//Print a symbols table to a file
		ofstream syms_ofp( ofile );
		set<string>::iterator symsIter;
		int count = 0;
		syms_ofp << eps << "\t" << count << endl;
		count++;
		for( symsIter=syms.begin(); symsIter != syms.end(); symsIter++ ){
			syms_ofp << *symsIter << "\t" << count << endl;
			count++;
		}
		syms_ofp.close();
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
};

class Arpa2TextFSTg2p : public Arpa2TextFST {
	/*
	 Child class of basic Arpa2TextFST.  Modified to build a G2P WFST model.
	 
	 -- This class has been specifically designed to deal with
	    grapheme-to-phoneme pronunciation models and expects the 
	    tokens to be of the form P:G, where 'P' corresponds to a 
		phoneme and 'G' to a grapheme unit.  These tokens are split
	    into output and input respectively, creating a WFST rather 
	    than a standard WFSA.
	 */
	
public:
	
	Arpa2TextFSTg2p( const char* arpa_lm ) : Arpa2TextFST( arpa_lm ) {
		//Just call the parent constructor.
	}
	
	void generateFST ( ) {
		if( arpa_lm_fp.is_open() ){
			make_text_arc( 
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
							make_text_arc( 
										  eps, 
										  se, 
										  se, 
										  se, 
										  atof(tokens[0].c_str()) 
										  );
						}else if( tokens[1].compare(sb) == 0 ){
							double weight = tokens.size()==3 ? atof(tokens[2].c_str()) : 0.0;
							make_text_arc( 
										  eps, 
										  sb, 
										  eps, 
										  eps, 
										  weight 
										  );
						}else{
							double weight = tokens.size()==3 ? atof(tokens[2].c_str()) : 0.0;
							make_text_arc( 
										  tokens[1], 
										  eps, 
										  eps, 
										  eps, 
										  weight 
										  );
							make_text_arc_gp( 
										  eps, 
										  tokens[1], 
										  tokens[current_order], 
										  tokens[current_order], 
										  atof(tokens[0].c_str())
										  );
						}
						//Handle the middle-order N-grams
					}else if( current_order < max_order ){
						if( tokens[current_order].compare("</s>") == 0 ){
							make_text_arc( 
										  join(tokens, ",", 1, current_order), 
										  tokens[current_order], 
										  tokens[current_order], 
										  tokens[current_order], 
										  atof(tokens[0].c_str()) 
										  );
							
						}else{
							double weight = tokens.size()==current_order+2 ? atof(tokens[tokens.size()-1].c_str()) : 0.0;
							make_text_arc( 
										  join(tokens, ",", 1, current_order+1), 
										  join(tokens, ",", 2, current_order+1), 
										  eps, 
										  eps, 
										  weight
										  );
							make_text_arc_gp( 
										  join(tokens, ",", 1, current_order), 
										  join(tokens, ",", 1, current_order+1), 
										  tokens[current_order], 
										  tokens[current_order], 
										  atof(tokens[0].c_str())
										  );
						}
						//Handle the N-order N-grams
					}else if( current_order==max_order ){
						if( tokens[current_order].compare("</s>") == 0 ){
							make_text_arc( 
										  join(tokens, ",", 1, current_order), 
										  tokens[current_order], 
										  tokens[current_order], 
										  tokens[current_order], 
										  atof(tokens[0].c_str()) 
										  );
						}else{
							make_text_arc_gp( 
										  join(tokens, ",", 1, current_order), 
										  join(tokens, ",", 2, current_order+1), 
										  tokens[current_order], 
										  tokens[current_order], 
										  atof(tokens[0].c_str())
										  );
						}
					}
				}
				
				if( line.size() > 4 && line.compare( 0, 5, "ngram" ) == 0 ){
					max_order = atoi(&line[6])>max_order ? atoi(&line[6]) : max_order;
				}else if( line.compare( "\\data\\" ) == 0 )
					continue;
				else if( line.compare( "\\end\\" ) == 0 ){
					cout << se << endl;
					break;
				}else if( line.size() > 0 && line.compare( 0, 1, "\\" ) == 0 ){
					line.replace(0, 1, "");
					line.replace(1, 7, "");
					current_order = atoi(&line[0]);
				}
			}
			arpa_lm_fp.close();
		}else{
			cout << "Unable to open file, or file has already been closed: " << arpa_lm_file << endl;
		}
	}
	
	vector<string> split_token( string token ) {
		//Split an input Phoneme:Grapheme token into its constituent parts
		vector<string> pg;
		pg.push_back(token.substr( 0, token.find_first_of(":") ));		//phoneme
		pg.push_back(token.substr( token.find_first_of(":")+1, token.size()-(token.find_first_of(":")+1) )); //grapheme
		return pg;
	}
	
	void make_text_arc_gp( string istate, string ostate, string isym, string osym, double weight ){
		//Build up a special G2P arc for the WFST.  Weights default to the Log semiring.
		vector<string> pg = split_token( isym );
		isym = pg[1]; //set input symbol to the grapheme
		osym = pg[0]; //set output symbol to the phoneme
		if( istate.compare(eps) != 0 ) ssyms.insert(istate);
		if( ostate.compare(eps) != 0 ) ssyms.insert(ostate);
		if( isym.compare(eps)   != 0 ) isyms.insert(isym);
		if( osym.compare(eps)   != 0 ) osyms.insert(osym);
		if( tropical==true )           weight = log2tropical(weight);
		cout << istate << "\t" << ostate << "\t" << isym << "\t" << osym << "\t" << weight << endl;
		return;
	}
};

int main( int argc, const char* argv[] ) {
	Arpa2TextFSTg2p a2tfst( argv[1] ); 
	a2tfst.eps = "<eps>";
	a2tfst.tropical = false;
	a2tfst.generateFST();
	a2tfst.print_all_syms( );
	return 0;
}

