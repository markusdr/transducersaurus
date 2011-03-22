#include "Lexicon.hpp"
#include <stdio.h>
#include <string>

int main( int argc, const char* argv[] ) {
  Lexicon2FST l2tfst( argv[1] );
  l2tfst.generateFST();
  l2tfst.lexiconfst.Write("lex.fst");
  l2tfst.isyms->WriteText("lex.isyms");
  l2tfst.osyms->WriteText("lex.osyms");
  return 0;
}
