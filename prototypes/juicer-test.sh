#!/bin/bash

if [ $# != 5 ]
then
    echo "SYNTAX: $0 <wfst> <dict> <osyms> <hsyms> <hmmdefs>"
    exit 1;
fi
wfst=${1}
dict=${2}
osyms=${3}
hsyms=${4}
hmmdefs=${5}

#dump the sil tokens, fix the '<s>'/'</s>' mismatching...
/usr/bin/juicer \
    -inputFormat htk \
    -lmScaleFactor 13 \
    -inputFName jtune/tune-ju-htk-1.scp \
    -htkModelsFName ${hmmdefs} \
    -mainBeam 230 \
    -threading \
    -sentStartWord "<s>" \
    -sentEndWord "</s>" \
    -silMonophone "sil" \
    -lexFName ${dict} \
    -pauseMonophone "sp" \
    -inSymsFName ${hsyms} \
    -fsmFName ${wfst} \
    -outSymsFName ${osyms} | \
    perl -e'while(<>){chomp; @_ = split(/\s+/); shift(@_); pop(@_); $_ = join(" ",@_); s/<sil>//g; $_ = "<s> ".$_." </s>"; s/\s+/ /g; print $_."\n";}'


