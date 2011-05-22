#include <stdio.h>
#include <string>
#include <fst/fstlib.h>
#include <iostream>
#include <getopt.h>
#include <float.h>
/*
 Normalize the weights in an input WFST.
 Iterate through the states and make sure they sum
 to 1.0.  Assumes that the input WFST was constructed
 in the log semiring.
*/

using namespace fst;


void normalize_fst( const char* ifile, const char* ofile, int verbose ){
    if( verbose==1 )
        cout << "Normalizing FST: " << ifile << endl;
    MutableFst<LogArc> *model = MutableFst<LogArc>::Read( ifile );
    
    LogArc::StateId istate = model->Start();
    for( StateIterator<MutableFst<LogArc> > siter(*model); !siter.Done(); siter.Next() ){
        LogArc::StateId sid = siter.Value();
        LogArc::Weight id_tot = LogArc::Weight::Zero();
        for( MutableArcIterator<MutableFst<LogArc> > aiter(model, sid); !aiter.Done(); aiter.Next() ){
            LogArc arc = aiter.Value();
            id_tot = Plus(id_tot, arc.weight);
        }
	if( ! (id_tot.Value() <= DBL_MAX && id_tot.Value() >= -DBL_MAX) ){
	  //If our 'sum' is 'Infinity' we are probably in the start state or some 
          // other undesirable node.  Just skip normalization in this case.
	  if( verbose==1 )
	    cout << "Infinity for state: " << sid << " Check value: " << id_tot << endl;
	  continue;
	}
	if( verbose==1 )
	  cout << "IdTotal:\t" << id_tot << "\t" << exp(id_tot.Value()) << "\tsid\t" << sid << endl;

        LogArc::Weight new_tot = LogArc::Weight::Zero();
        for( MutableArcIterator<MutableFst<LogArc> > aiter(model, sid); !aiter.Done(); aiter.Next() ){
            LogArc arc = aiter.Value();
            arc.weight = arc.weight.Value() - id_tot.Value();
            new_tot = Plus(new_tot, arc.weight);
            aiter.SetValue(arc);
        }
        if( verbose==1 )
            cout << "NewIdTotal:\t" << new_tot << "\t" << exp(new_tot.Value()) << endl;
    }
    if( verbose==1 )
        cout << "Writing normalized FST: " << ofile << endl;
    model->Write(ofile);
    
}

int main( int argc, char **argv ) {
    int c;
    /* Flags */
    int ifile_flag   = 0;
    int ofile_flag   = 0;
    int verbose_flag = 0;
    /* File names */
    const char* ifile;
    const char* ofile;
    int verbose = 0;
    /* Help Info */
    char help_info[1024];
    sprintf(help_info,"Syntax: %s -i ifile.fst -o ofile.fst [-v]\n\
Required:\n\
  -i --ifile: Input WFST. Must be constructed in the log semiring. Use '-' to specify stdin.\n\
  -o --ofile: Output WFST name.  Will also be constructed in the log semiring. Use '-' to specify stdout.\n\
Optional:\n\
  -v --verbose: Verbose output. Prints pre-normalized and normalized totals for each state.\n\
  -h --help: Print this help message.\n\n", argv[0]); 

    /* Begin argument parsing */
    while( 1 ){
        static struct option long_options[] = 
        {
            /* These options set a flag. */
            {"ifile",     required_argument, 0, 'i'},
            {"ofile",     required_argument, 0, 'o'},
            {"verbose",   no_argument, 0, 'v'},
            {"help",      no_argument, 0, 'h'},
            {0, 0, 0, 0}
        };
        /* getopt_long stores the option index here. */
        int option_index = 0;
        
        c = getopt_long ( argc, argv, "hvi:o:", long_options, &option_index );
        
        /* Detect the end of the options. */
        if( c == -1 )
            break;
        
        switch ( c ) {
            case 0:
                if(long_options[option_index].flag != 0)
                    break;
            case 'i':
                ifile_flag = 1;
                ifile = (strcmp(optarg,"-") != 0) ? optarg : "";
                break;
            case 'o':
                ofile_flag = 1;
                ofile = (strcmp(optarg,"-") != 0) ? optarg : "";
                break;
            case 'v':
                verbose_flag = 1;
                break;
            case 'h':
	        printf("%s", help_info);
	        exit(0);
	        break;
	    case '?':
	        printf("%s", help_info);
	        exit(0);
	        break;
            default:
                abort();
        }
    }
    
    if( ifile_flag==0 || ofile_flag==0 ){
        printf( "%s", help_info );
        exit(0);
    }
    
    
    normalize_fst( ifile, ofile, verbose_flag );
    
    return 0;
}
