#!/bin/bash
#Builds a sandbox environment for the
# python prototype tools.

if [ $# != 1 ]
then
    echo "SYNTAX: ${0} path/to/sandbox/"
    exit
fi

if [ -d ${1} ]
then
    echo "Directory \"${1}\" already exists. Using existing directory."
else
    mkdir ${1}
fi

cp python/* ${1}

echo "Compiling 'normalizeG' WFST arc-weight normalizer."
cd cpp
g++ -O2 -o normalizeG normalizeG.cpp -lfst -ldl
cp normalizeG ../${1}
cd ..

echo "Copied python prototype build scripts and normalizeG to: ${1}..."
echo "See transducersaurus/README.txt for additional testing details."