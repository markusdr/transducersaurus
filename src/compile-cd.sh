#!/bin/bash

if [ $# -eq 1 ] 
then
    echo "Removing .o files and executables..."
    rm *.o
    rm gen-cd
    exit
fi
g++ -c gen-cd.cpp
g++ -c ContextDependency.cpp
g++ -o gen-cd gen-cd.o ContextDependency.o -lfst