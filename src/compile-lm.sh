#!/bin/bash

if [ $# -eq 1 ] 
then
    echo "Removing .o files and executables..."
    rm gen-lm.o 
    rm LanguageModel.o
    rm gen-lm
    exit
fi
g++ -c gen-lm.cpp
g++ -c LanguageModel.cpp
g++ -o gen-lm gen-lm.o LanguageModel.o -lfst