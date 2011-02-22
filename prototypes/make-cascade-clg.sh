#!/bin/bash
# Same as make-cascade-clgt.sh, but does not build the silclass
#  transducer.  Only generates a generic CLG cascade.
if [ $# != 5 ]
then
    echo "SYNTAX: ${0} <arpalm> <dictionary> <prefix> <hmmdefs> <tiedlist>"
    exit
fi
arpa=${1}
dict=${2}
prefix=${3}
hmmdefs=${4}
tiedlist=${5}

#Juicer is VERY picky about the symbol order.
#  See the perl one-liner below for details, but the basic rules are:
#  **Unique words (not pronunciations) MUST appear in the EXACT same order as the reference
#    pronunciation dictionary.
#  **Any symbols that are NOT in the reference dictionary MUST come at the
#    END of the list - see <UNK> in the script below.
#  It's crazy but it's the only way it works.
#  Other problems may occur depending on the value of LC_ALL
#   which defines the sort order on your linux machine.
cat ${dict} | perl -e' 
my $cnt=1; 
my %syms; 
print "<eps> 0\n"; 
while(<>){ 
  chomp; 
  @_ = split(/\s+/); 
  if( ! exists $syms{$_[0]} ){ 
    print $_[0]."\t".$cnt."\n"; 
    $syms{$_[0]} = 
    $cnt; $cnt++;
  } 
} 
print "<UNK> ".$cnt."\n";' > ${prefix}.word.syms

echo "Generating G WFST..."
#We'll skip proper <UNK> handling for now
./arpa2fst.py ${arpa} ${prefix}.g.fst.txt ${prefix}
echo "Compiling G WFST..."
fstcompile --arc_type=log --acceptor=true --ssymbols=${prefix}.g.ssyms --isymbols=${prefix}.word.syms ${prefix}.g.fst.txt | fstarcsort --sort_type=ilabel - > ${prefix}.g.fst

echo "Generating L WFST..."
./lexicon2fst.py ${dict} ${prefix} > ${prefix}.l.fst.txt
echo "Compiling L WFST..."
fstcompile --arc_type=log --isymbols=${prefix}.l.isyms --osymbols=${prefix}.word.syms ${prefix}.l.fst.txt | fstclosure - |  fstarcsort --sort_type=olabel - > ${prefix}.l.fst

echo "Generating C WFST..."
./cd2fst.py phons aux ${tiedlist} ${prefix} > ${prefix}.c.fst.txt

echo "Compiling C WFST..."
#Juicer is VERY picky about symbol ordering. 
#  Input symbols must EXACTLY match the order in which the 
#  ~h definitions appear in the hmmdefs file (NOT the tiedlist file [they are often slightly different])
grep "^~h " ${hmmdefs} | perl -e'my $cnt=1; print "<eps> 0\n"; while(<>){chomp; s/^~h \"//; s/\"$//; print $_." ".$cnt."\n"; $cnt++;}' > ${prefix}.hmm.syms
fstcompile --arc_type=log --ssymbols=${prefix}.c.ssyms --isymbols=${prefix}.hmm.syms --osymbols=${prefix}.l.isyms ${prefix}.c.fst.txt > ${prefix}.c.fst

echo "Performing L*G Composition and Determinization..."
fstcompose ${prefix}.l.fst ${prefix}.g.fst | fstdeterminize - > ${prefix}.lg.fst
echo "Performing C*LG Composition..."
fstcompose ${prefix}.c.fst ${prefix}.lg.fst | fstprint - > ${prefix}.clg.fst.txt

echo "Done building cascade.  Run juicer test with:"
echo "./juicer-test.sh ${prefix}.clg.fst.txt ${dict} ${prefix}.word.syms ${prefix}.hmm.syms ${hmmdefs}"