#include "LanguageModel.hpp"
#include <stdio.h>
#include <string>


int main( int argc, const char* argv[] ) {
  Arpa2OpenFST a2tfst( argv[1] );
  a2tfst.eps = "<eps>";
  a2tfst.tropical = false;
  a2tfst.generateFST();
  a2tfst.arpafst.Write("test.fst");
  a2tfst.ssyms->WriteText("test.ssyms");
  a2tfst.isyms->WriteText("test.isyms");
  a2tfst.osyms->WriteText("test.osyms");
  return 0;
}
