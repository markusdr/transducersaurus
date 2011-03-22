#ifndef CONTEXTDEPENDENCY_H
#define CONTEXTDEPENDENCY_H
#include <fst/fstlib.h>
//Issues: I do not understand why the constructors for tropical
//  do not properly overload the base constructors. 
//  The C++-force is still weak in this one.

class ContextDependency2FST {
	/*
	 Build a context-dependency transducer from a list of phonemes and
	 optionally a list of auxilliary symbols.
	 Uses the Log semiring - this is the default because it 
	 is generally preferable for ASR cascades.
	 
	 This is a generic approach:
	   -*- Builds *all* possible logical triphones 
		   given the input phoneme list
	   -*- Acoustic Model agnostic; this approach can be used for either HTK or Sphinx
	       acoustic models.  An additional 'mapper' FST is used to map the 
	       logical triphones to corresponding physical triphones as defined in 
	       and HTK triphone list or a Sphinx mdef file.
	*/
	
public:
	std::string	       eps;
	std::string		   sil;
	std::string	       start;
	fst::SymbolTable*  ssyms;
	fst::SymbolTable*  isyms;
	fst::SymbolTable*  osyms;
	std::set<string>   aux_syms;
	std::set<string>   phones;
	fst::VectorFst<fst::LogArc>  cdfst;
	
	ContextDependency2FST( );
	
	ContextDependency2FST( const char* cd, const char* aux );
	
	ContextDependency2FST( std::set<string> cd, std::set<string> aux );
	
	ContextDependency2FST( std::set<string> cd, std::set<string> aux, fst::SymbolTable* iosymbols );
	
	void generateDeterministic( );
	
	void generateDeterministicAux( );
	
	void generateNonDeterministic( );
	
	void generateNonDeterministicAux( );
	
	void init(const char *cd, const char *aux);

protected:
	
	virtual void make_arc( string lp, string mp, string rp );
	
	virtual void make_aux( string lp, string rp );
	
	virtual void make_final( string lp, string rp );
};



class ContextDependency2TropicalFST : public ContextDependency2FST {
	/*
	 Build a context-dependency transducer from a list of phonemes and
	 optionally a list of auxilliary symbols.
	 Uses the Tropical semiring.
	 */
	
public:
	fst::StdVectorFst  cdfst;

	ContextDependency2TropicalFST( const char* cd, const char* aux ); 
	/*The tropical constructions behave strangely if I try to use the base-class constructor.
	  Why???: ContextDependency2FST( cd, aux ) {} */
	
	ContextDependency2TropicalFST( std::set<string> cd, std::set<string> aux ) : ContextDependency2FST( cd, aux ) {}
	
	ContextDependency2TropicalFST( std::set<string> cd, std::set<string> aux, fst::SymbolTable* iosymbols );	
protected:
	virtual void make_arc( string lp, string mp, string rp );
	
	virtual void make_aux( string lp, string rp );
	
	virtual void make_final( string lp, string rp );
};

#endif // CONTEXTDEPENDENCY_H //
