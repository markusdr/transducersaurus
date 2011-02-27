#!/bin/bash
# Same as make-cascade-clgt.sh, but does not build the silclass
#  transducer.  Only generates a generic CLG cascade.
#This version uses on-the-fly static composition.
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
#  See the python script below for details, but the basic rules are:
#  **Unique words (not pronunciations) MUST appear in the EXACT same order as the reference
#    pronunciation dictionary.
#  **Any symbols that are NOT in the reference dictionary MUST come at the
#    END of the list - see <UNK> in the script below.
#  It's crazy but it's the only way it works.
#  Other problems may occur depending on the value of LC_ALL
#   which defines the sort order on your linux machine.

echo "Generating the word symbols list..."
python2.5 ./check-vocab.py ${dict} ${arpa} ${prefix}
echo "Generating G WFST..."
python2.5 ./arpa2fst.py ${arpa} ${prefix}.g.fst.txt ${prefix}

echo "Generating L WFST..."
python2.5 ./lexicon2fst.py ${dict} ${prefix} > ${prefix}.l.fst.txt

#Juicer is VERY picky about symbol ordering. 
#  Input symbols must EXACTLY match the order in which the 
#  ~h definitions appear in the hmmdefs file (NOT the tiedlist file [they are often slightly different])
grep "^~h " ${hmmdefs} | perl -e'my $cnt=1; print "<eps> 0\n"; while(<>){chomp; s/^~h \"//; s/\"$//; print $_." ".$cnt."\n"; $cnt++;}' > ${prefix}.hmm.syms

echo "Compiling L WFST..."
fstcompile --isymbols=${prefix}.l.isyms --osymbols=${prefix}.word.syms ${prefix}.l.fst.txt  |  fstclosure - | fstdeterminize - | fstarcsort --sort_type=ilabel - > ${prefix}.l.fst
echo "Generating C WFST..."
python2.5 ./cd2fst.py ${prefix}.phons ${prefix}.aux ${tiedlist} ${prefix} > ${prefix}.c.fst.txt
echo "Compiling C WFST..."
fstcompile --ssymbols=${prefix}.c.ssyms --isymbols=${prefix}.hmm.syms --osymbols=${prefix}.l.isyms ${prefix}.c.fst.txt | fstinvert - | fstdeterminize - | fstinvert - | fstarcsort --sort_type=olabel - > ${prefix}.c.fst


echo "fstcompose ${prefix}.c.fst ${prefix}.l.fst | fstconvert --fst_type=olabel_lookahead --save_relabel_opairs=cl.rlbl.txt - > ${prefix}.cl.lkhd.fst"
fstcompose ${prefix}.c.fst ${prefix}.l.fst | fstconvert --fst_type=olabel_lookahead --save_relabel_opairs=cl.rlbl.txt - > ${prefix}.cl.lkhd.fst
echo "Compiling G WFST..."
fstcompile --acceptor=true --ssymbols=${prefix}.g.ssyms --isymbols=${prefix}.word.syms ${prefix}.g.fst.txt | fstrelabel --relabel_ipairs=cl.rlbl.txt - | fstarcsort - > ${prefix}.g.rlbl.fst
echo "Composing with lookahead..."
echo "fstcompose ${prefix}.cl.lkhd.fst ${prefix}.g.rlbl.fst > ${prefix}.clg.lkhd.fst"
fstcompose ${prefix}.cl.lkhd.fst ${prefix}.g.rlbl.fst | fstprint - > ${prefix}.clg.lkhd.fst.txt
echo "Compiling to AT&T format..."
fsmcompile -t ${prefix}.clg.lkhd.fst.txt > ${prefix}.clg.lkhd.fsm

echo "Done building cascade.  Run juicer test with:"
echo "./juicer-test.sh ${prefix}.clg.fst.txt ${dict} ${prefix}.word.syms ${prefix}.hmm.syms ${hmmdefs}"
