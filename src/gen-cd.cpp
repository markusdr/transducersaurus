#include "ContextDependency.hpp"
#include <stdio.h>
#include <getopt.h>
#include <string>



int main( int argc, char **argv ) {
	int c;
	/* Flags */
	int tropical_flag = 0;
	int nondet_flag   = 0;
	int exaux_flag    = 0;
	int aux_file_flag = 0;
	int phones_file_flag = 0;
	/* File names */
	const char* phones_file;
	const char* aux_file;
	const char* prefix = "cd";
	/* Help Info */
	char help_info[1024];
	sprintf(help_info, "Syntax: %s -p phones -a aux [-t] [-n] [-e]\n\
Required:\n\
  -p --phones: File containing a list of monophones, one per line\n\
  -a --aux:    File containing a list of auxiliary symbols, one per line\n\
Optional:\n\
  -t --tropical: Use the tropical semiring.\n\
  -n --nondet: Build a non-deterministic transducer.  Default is deterministic.\n\
  -e --explicit-aux: Generate explicit auxiliary arcs.  Default does not generate arcs.\n\
  -h --help: Pring this help message.\n\n", argv[0]);
	
	/*Begin argument parsing*/
	while( 1 ){
		static struct option long_options[] =
		{
			/* These options set a flag. */
			{"phones",       required_argument, 0, 'p'},
			{"aux",          required_argument, 0, 'a'},
			{"prefix",       required_argument, 0, 'x'},
			{"tropical",     no_argument, &tropical_flag, 1},
			{"non-det",      no_argument, &nondet_flag, 1},
			{"explicit-aux", no_argument, &exaux_flag, 1},
			{"help",         no_argument, 0, 'h'},
			{0, 0, 0, 0}
		};
		/* getopt_long stores the option index here. */
		int option_index = 0;
		
		c = getopt_long (argc, argv, "tnehp:a:x:", long_options, &option_index);
		
		/* Detect the end of the options. */
		if (c == -1)
			break;
		
		switch( c ){
			case 0:
				/* If this option set a flag, do nothing else now. */
				if (long_options[option_index].flag != 0)
					break;
			case 'p':
				phones_file_flag = 1;
				phones_file = optarg;
				break;
			case 'a':
				aux_file_flag = 1;
				aux_file = optarg;
				break;
			case 'x':
				prefix = optarg;
				break;
			case 't':
				tropical_flag = 1;
				break;
			case 'n':
				nondet_flag = 1;
				break;
			case 'e':
				exaux_flag = 1;
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
				abort ();
		}
	}
	
	if( phones_file_flag==0 || aux_file_flag ==0 ){
		printf( "%s", help_info );
		exit(0);
	}
	
	//Best way to build a generic pointer to reference either the base or child class??
	//I'd like to get rid of these for-loops for 'printing'.
	if( tropical_flag==0 ){
		ContextDependency2FST::ContextDependency2FST cdfst( phones_file, aux_file );
		if( exaux_flag==0 && nondet_flag==0 ){
			//Default behavior
			cdfst.generateDeterministic();
		}else if( exaux_flag==1 && nondet_flag==0 ){
			cdfst.generateDeterministicAux();
		}else if( exaux_flag==0 && nondet_flag==1 ){
			cdfst.generateNonDeterministic();
		}else if (exaux_flag==1 && nondet_flag==1 ) {
			cdfst.generateNonDeterministicAux();
		}
		char fstname[1024];
		sprintf(fstname, "%s.fst", prefix);
		cdfst.cdfst.Write(fstname);
		char fstisyms[1024];
		sprintf(fstisyms, "%s.isyms", prefix);
		cdfst.isyms->WriteText(fstisyms);
		char fstosyms[1024];
		sprintf(fstosyms, "%s.osyms", prefix);
		cdfst.osyms->WriteText(fstosyms);
		char fstssyms[1024];
		sprintf(fstssyms, "%s.ssyms", prefix);
		cdfst.ssyms->WriteText(fstssyms);
	}else if( tropical_flag==1 ){
		ContextDependency2TropicalFST::ContextDependency2TropicalFST cdfst( phones_file, aux_file );
		if( exaux_flag==0 && nondet_flag==0 ){
			//Default behavior
			cdfst.generateDeterministic();
		}else if( exaux_flag==1 && nondet_flag==0 ){
			cdfst.generateDeterministicAux();
		}else if( exaux_flag==0 && nondet_flag==1 ){
			cdfst.generateNonDeterministic();
		}else if (exaux_flag==1 && nondet_flag==1 ) {
			cdfst.generateNonDeterministicAux();
		}
		char fstname[1024];
		sprintf(fstname, "%s.fst", prefix);
		cdfst.cdfst.Write(fstname);
		char fstisyms[1024];
		sprintf(fstisyms, "%s.isyms", prefix);
		cdfst.isyms->WriteText(fstisyms);
		char fstosyms[1024];
		sprintf(fstosyms, "%s.osyms", prefix);
		cdfst.osyms->WriteText(fstosyms);
		char fstssyms[1024];
		sprintf(fstssyms, "%s.ssyms", prefix);
		cdfst.ssyms->WriteText(fstssyms);
	}

	return 0;
}
