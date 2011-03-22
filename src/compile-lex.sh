#!/bin/bash

if [ $# -eq 1 ] 
then
    echo "Removing .o files and executables..."
    rm gen-lex.o 
    rm Lexicon.o
    rm gen-lex
    exit
fi
g++ -c gen-lex.cpp
g++ -c Lexicon.cpp
g++ -o gen-lex gen-lex.o Lexicon.o -lfst