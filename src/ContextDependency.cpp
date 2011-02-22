/*
 *  ContextDependency.cpp
 *  openPhone-proj
 *
 *  Created by Joe Novak on 11/02/18.
 *  Copyright 2011 __MyCompanyName__. All rights reserved.
 *
 */
#include "ContextDependency.hpp"
#include <iostream>
#include <fstream>
#include <string>
#include <iterator>
#include <vector>
#include <set>
#include <math.h>
#include <fst/fstlib.h>

using namespace fst;


ContextDependency2FST::ContextDependency2FST( ) { }

ContextDependency2FST::ContextDependency2FST( const char* cd, const char* aux ){
	//Constructor for text files
	init( cd, aux );
	//Set default values
	eps   = "<eps>";
	start = "<start>";
	
	ssyms = new SymbolTable("ssyms");
	isyms = new SymbolTable("isyms");
	osyms = new SymbolTable("osyms");
	cdfst.AddState(); 
	cdfst.SetStart(0);
	ssyms->AddSymbol(start,0);
	isyms->AddSymbol(eps,0);
	osyms->AddSymbol(eps,0);
}
/*
ContextDependency2TropicalFST::ContextDependency2TropicalFST( ) {
	//Default constructor
	cout << "Tropical2FST requires an input pronunciation lexicon." << endl;
}
*/
ContextDependency2TropicalFST::ContextDependency2TropicalFST( const char* cd, const char* aux ){
	//Constructor for text files
	init( cd, aux );
	//Set default values
	eps   = "<eps>";
	start = "<start>";
	
	ssyms = new SymbolTable("ssyms");
	isyms = new SymbolTable("isyms");
	osyms = new SymbolTable("osyms");
	cdfst.AddState(); 
	cdfst.SetStart(0);
	ssyms->AddSymbol(start,0);
	isyms->AddSymbol(eps,0);
	osyms->AddSymbol(eps,0);
}

ContextDependency2FST::ContextDependency2FST( set<string> cd, set<string> aux ){
	//Constructor for text files
	phones = cd;
	aux_syms = aux;
	//Set default values
	eps   = "<eps>";
	start = "<start>";
	ssyms = new SymbolTable("ssyms");
	isyms = new SymbolTable("isyms");
	osyms = new SymbolTable("osyms");
	cdfst.AddState(); 
	cdfst.SetStart(0);
	ssyms->AddSymbol(start,0);
	isyms->AddSymbol(eps,0);
	osyms->AddSymbol(eps,0);
}

void ContextDependency2FST::init( const char* cd, const char* aux ) {
	//Read in a list of phonemes and a list of auxiliary symbols
	//Expects one symbol per line!!!
	ifstream      cd_fp;
	ifstream      aux_fp;
	string	      line;
	cd_fp.open( cd );
	if( cd_fp.is_open() ){
		while( cd_fp.good() ){
			getline( cd_fp, line );
			if( line.compare("")==0 ) 
				continue;
			phones.insert(line);
		};
		cd_fp.close();
	}else{
		cout << "Something wrong with phoneme list file..." << endl;
	}
	
	aux_fp.open( aux );
	if( aux_fp.is_open() ){
		while( aux_fp.good() ){
			getline( aux_fp, line );
			if( line.compare("")==0 )
				continue;
			aux_syms.insert(line);
		}
		aux_fp.close();
	}else {
		cerr << "Something wrong with the aux list file..." << endl;
	}
}
		 
	
	
void ContextDependency2FST::make_arc( string lp, string mp, string rp ){
	/*
	 Generate a normal arc for the CD transducer.
	 lp: left-monophone
	 mp: middle-monophone
	 rp: right-monophone
	 */
	string issym = lp+","+mp;
	string ossym = mp+","+rp;
	string isym  = lp+"-"+mp+"+"+rp;
	string osym  = rp;
	if( lp.compare(start)==0 ){
		isym  = eps;
		issym = start;
	}
	if( ssyms->Find(issym)==-1 )
		ssyms->AddSymbol(issym, cdfst.AddState() );
	if( ssyms->Find(ossym)==-1 )
		ssyms->AddSymbol(ossym, cdfst.AddState() );
		
	cdfst.AddArc( 
				 ssyms->Find(issym), 
				 LogArc( 
						isyms->AddSymbol(isym), 
						osyms->AddSymbol(osym), 
						LogArc::Weight::One(), 
						ssyms->Find(ossym)
						) 
				 );
	return;
}


void ContextDependency2FST::make_aux( string lp, string rp ){
	//Generate auxiliary symbol arcs.
	string issym = lp+","+rp;
	
	set<string>::iterator au;
	for( au=aux_syms.begin(); au!=aux_syms.end(); au++){
		isyms->AddSymbol(*au);
		osyms->AddSymbol(*au);
		cdfst.AddArc( 
					 ssyms->Find(issym), 
					 LogArc(
							isyms->Find(*au), 
							osyms->Find(*au), 
							LogArc::Weight::One(), 
							ssyms->Find(issym)
							) 
					 );
	}
	return;
}

void ContextDependency2FST::make_final( string lp, string rp ){
	//Generate a final state
	string fssym = lp+","+rp;
	cdfst.SetFinal( ssyms->Find(fssym), LogArc::Weight::One() );
	return;
}

void ContextDependency2FST::generateDeterministic( ){
	/*
	 Generate an inverted, deterministic, triphone context-dependency transducer.
	 lp: left-monophone
	 mp: middle-monophone
	 rp: right-monophone
	 */
	set<string>::iterator lp;
	for( lp=phones.begin(); lp!=phones.end(); lp++ ){
		//Initial arcs
		make_arc( start, eps, *lp );
		//Monophone arcs
		make_arc( eps, *lp, eps );
		make_final( *lp, eps );
		set<string>::iterator mp;
		for( mp=phones.begin(); mp!=phones.end(); mp++ ){
			//Initial to Internal arcs
			make_arc( eps, *lp, *mp );
			//Internal to Final arcs
			make_arc( *lp, *mp, eps );
			set<string>::iterator rp;
			for( rp=phones.begin(); rp!=phones.end(); rp++ ){
				//Internal to Internal arcs
				make_arc( *lp, *mp, *rp );
			}
		}
	}
}

void ContextDependency2FST::generateDeterministicAux( ){
	/*
	 Generate an inverted, deterministic, triphone context-dependency transducer.
	 Also generate explicit auxiliary arcs.
	 lp: left-monophone
	 mp: middle-monophone
	 rp: right-monophone
	 */
		
	set<string>::iterator lp;
	for( lp=phones.begin(); lp!=phones.end(); lp++ ){
		//Initial arcs
		make_arc( start, eps, *lp );
		//Monophone arcs
		make_arc( eps, *lp, eps );
		//Auxiliary arcs
		make_aux( eps, *lp );
		//Set final states
		make_final( *lp, eps );
		set<string>::iterator mp;
		for( mp=phones.begin(); mp!=phones.end(); mp++ ){
			//Initial to Internal arcs
			make_arc( eps, *lp, *mp );
			//Internal to Final arcs
			make_arc( *lp, *mp, eps );
			//Auxiliary symbols
			make_aux( *lp, *mp );
			set<string>::iterator rp;
			for( rp=phones.begin(); rp!=phones.end(); rp++ ){
				//Internal to Internal arcs
				make_arc( *lp, *mp, *rp );
			}
		}
	}
}

void ContextDependency2FST::generateNonDeterministic( ){
	//Generating Non-deterministic triphone context-dependency transducer
	set<string>::iterator lp;
	for ( lp=phones.begin(); lp!=phones.end(); lp++ ) {
		//Monophone arcs
		make_arc( start, *lp, eps );
		make_final( *lp, eps );
		set<string>::iterator mp;
		for( mp=phones.begin(); mp!=phones.end(); mp++ ){
			//Initial arcs
			make_arc( start, *lp, *mp );
			//Internal to final arcs
			make_arc( *lp, *mp, eps );
			set<string>::iterator rp;
			for( rp=phones.begin(); rp!=phones.end(); rp++ ){
				make_arc( *lp, *mp, *rp );
			}
		}
	}
	return;
}

void ContextDependency2FST::generateNonDeterministicAux( ){
	//Generating Non-deterministic triphone context-dependency transducer
	set<string>::iterator lp;
	for ( lp=phones.begin(); lp!=phones.end(); lp++ ) {
		//Monophone arcs
		make_arc( start, *lp, eps );
		make_final( *lp, eps );
		make_aux( *lp, eps );
		set<string>::iterator mp;
		for( mp=phones.begin(); mp!=phones.end(); mp++ ){
			//Initial arcs
			make_arc( start, *lp, *mp );
			//Internal to final arcs
			make_arc( *lp, *mp, eps );
			make_aux( *lp, *mp );
			set<string>::iterator rp;
			for( rp=phones.begin(); rp!=phones.end(); rp++ ){
				make_arc( *lp, *mp, *rp );
			}
		}
	}
	return;
}



/********Tropical Semiring-specific Methods************/

void ContextDependency2TropicalFST::make_aux( string lp, string rp ){
	//Generate auxiliary symbol arcs.
	string issym = lp+","+rp;
	set<string>::iterator au;
	for( au=aux_syms.begin(); au!=aux_syms.end(); au++){
		isyms->AddSymbol(*au);
		osyms->AddSymbol(*au);
		cdfst.AddArc( 
					 ssyms->Find(issym), 
					 StdArc(
							isyms->Find(*au), 
							osyms->Find(*au), 
							StdArc::Weight::One(), 
							ssyms->Find(issym)
							) 
					 );
	}
	return;
}


void ContextDependency2TropicalFST::make_arc( string lp, string mp, string rp ){
	/*
	 Generate a normal arc for the CD transducer.
	 lp: left-monophone
	 mp: middle-monophone
	 rp: right-monophone
	 */
	
	string issym = lp+","+mp;
	string ossym = mp+","+rp;
	string isym  = lp+"-"+mp+"+"+rp;
	string osym  = rp;
	if( lp.compare(start)==0 ){
		isym  = eps;
		issym = start;
	}
	if( ssyms->Find(issym)==-1 )
		ssyms->AddSymbol(issym, cdfst.AddState() );
	if( ssyms->Find(ossym)==-1 )
		ssyms->AddSymbol(ossym, cdfst.AddState() );

	cdfst.AddArc( 
				 ssyms->Find(issym), 
				 StdArc( 
						isyms->AddSymbol(isym), 
						osyms->AddSymbol(osym), 
						StdArc::Weight::One(), 
						ssyms->Find(ossym)
						) 
				 );
	
	return;
}

void ContextDependency2TropicalFST::make_final( string lp, string rp ){
	//Generate a final state
	string fssym = lp+","+rp;
	cdfst.SetFinal( ssyms->Find(fssym), StdArc::Weight::One() );
	return;
}
