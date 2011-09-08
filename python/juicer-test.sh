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

#Just run the decoder
juicer \
    -inputFormat htk \
    -lmScaleFactor 13 \
    -inputFName jtune/tune-ju-htk.scp \
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
    -outSymsFName ${osyms} 

