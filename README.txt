2010-02-03
Josef Novak

Transducersaurus is a module which builds component WFSTs 
for Automatic Speech Recognition Cascades (ASR).  It contains 
classes suitable for building language model transducers from ARPA
format LMs, lexicon transducers, context-dependency transducers and acoustic 
model to context-dependency mappers.

It supports both HTK and Sphinx format pronunciation dictionaries 
as well as AMs.  However the latter may be dependent on the 
decoder.

It depends on the following python modules:
pyopenfst

Along with the test data you should be able to run the 
toy-test.py build script to build some working examples and 
corresponding graphs.  

Building the graphs also requires the graphviz package.

./toy-test.py cmudata/toy-all.dic ./cmudata/toy.3g.arpa cmudata/rm1.1000.mdef
