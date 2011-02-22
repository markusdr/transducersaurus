README.txt
2011-02-22
Josef Novak

Transducersaurus is a module which builds component WFSTs 
for Automatic Speech Recognition Cascades (ASR).  It contains 
classes suitable for building language model transducers from ARPA
format LMs, lexicon transducers, context-dependency transducers and acoustic 
model to context-dependency mappers.

It provides both simple python prototypes and more robust as well as much faster
C++ implementations of all the basic WFST algorithms needed to generate a standard 
LVCSR WFST cascade. It supports cascade generation for both the Juicer and TCubed 
WFST decoders.  Sphinx support is on the way.

See the prototypes directory for more information.
