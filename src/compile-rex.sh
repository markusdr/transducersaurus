#!/bin/bash

if [ $# -eq 1 ] 
then
    echo "Removing .o files and executables..."
    rm Lexicon.o
    rm ContextDependency.o
    rm LanguageModel.o
    rm transducersaurus-rex.o
    exit
fi
echo "Compiling ContextDependency.cpp..."
g++ -Wall -Werror -O2 -c ContextDependency.cpp
echo "Compiling Lexicon.cpp..."
g++ -Wall -Werror -O2 -c Lexicon.cpp
echo "Compiling LanguageModel.cpp..."
g++ -Wall -Werror -O2 -c LanguageModel.cpp
echo "Compiling transducersauru-rex.cpp..."
g++ -Wall -Werror -O2 -c transducersaurus-rex.cpp
echo "Compiling transducersauru-rex..."
g++ -Wall -Werror -O2 -o transducersaurus-rex transducersaurus-rex.o ContextDependency.o Lexicon.o LanguageModel.o -lfst
