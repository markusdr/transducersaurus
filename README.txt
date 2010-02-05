2010 02 03
Josef Novak

CascadeTools.py is a module which builds component transducers 
for Automatic Speech Recognition Cascades (ASR).  It contains 
classes suitable for building language model transducers from ARPA
format LMs, lexicon transducers, context-dependency transducers and acoustic 
model to context-dependency mappers.

It supports both HTK and Sphinx format pronunciation dictionaries 
as well as AMs.  However the latter may be dependent on the 
decoder.

It depends on the following python modules:
openfst
SphinxTrain

The SphinxTrain module is required only to read in the mdef from the 
Sphinx acoustic models.  

Along with the test data and models, you should be able to run the 
HTKnSphinx.py build script to build working cascades for use with 
both Sphinx and HTK acoustic models.

./HTKnSphinx.py -g data/wsj-2g.arpa --lhtk data/wsj-5k-htk.dic --lsphinx data/wsj-5k-sphinx.dic -m data/mdef -t data/tiedlist -s data/htk-hmm.osyms
