#!/usr/bin/python
import re
from copy import deepcopy

#Shorthand for the DSL
label_map = {
    'weights'  : 'w', 'w' : 'w',
    'labels'   : 's', 's' : 's',
    'log'      : 'l', 'l' : 'l',
    'tropical' : 't', 't' : 't',
    'standard' : 't', 'symbols' : 's',
    'pweights' : 'e', 'e' : 'e',
    'plabels'  : 'a', 'a' : 'a',
    'output'   : 'o', 'o' : 'o',
    }
option_map = {
    'w' : '--encode_weights',
    's' : '--encode_labels',
    'l' : '--arc_type',
    't' : '--arc_type',
    'e' : '--push_weights',
    'a' : '--push_labels',
    'o' : '--project_output',
}
semiring_map = {
    'l' : 'log',
    't' : 'standard',
}
#Registers available options for each of the
# supported OpenFst binaries and syntactic tokens  
# defined by the DSL.  Option settings are not exhaustive.
option_registry = { 
    'push'  : {
        "opts":{
                '--push_weights':'false',   
                '--push_labels':'false',
                '--encode_weights':'false',
                '--encode_labels':'false',
                '--arc_type':'standard',
                },
        'type' :'OPERATOR',
        'binary':'fstpush',
        'prec':10,
        },
    'det'   : {
        "opts":{
                '--encode_weights':'false', 
                '--encode_labels':'false', 
                '--arc_type':'standard',
                '--delta':None,
                },
        'type' :'OPERATOR',
        'binary':'fstdeterminize PREFIX.FST1.fst > PREFIX.detFST1.fst',
        'prec':10,
        },
    'proj'  : {
        "opts":{
                '--arc_type':'standard',
                '--project_output':'false',
                },
        'type':'OPERATOR',
        'binary':'fstproject',
        'prec':10,
        },
    'min'   : {
        "opts":{
                '--encode_weights':'false', 
                '--encode_labels':'false', 
                '--arc_type':'standard',
                '--delta':None,
                },
        'type' :'OPERATOR',
        'binary':'fstminimize',
        'prec':10,
        },
    'rmeps'   : {
        "opts":{
                '--encode_weights':'false', 
                '--encode_labels':'false', 
                '--arc_type':'standard', 
                },
        'type' :'OPERATOR',
        'binary':'fstrmepsilon',
        'prec':10,
        },
    'epsn'   : {
        "opts":{
                '--encode_weights':'false', 
                '--encode_labels':'false', 
                '--arc_type':'standard',
                },
        'type' :'OPERATOR',
        'binary':'fstepsnormalize',
        'prec':10,
        },
    'rev' : {
        "opts":{'--arc_type':'standard',},
        'type' : 'OPERATOR',
        'binary' : 'fstreverse',
        'prec':10,
        },
    'inv' : {
        "opts":{'--arc_type':'standard',},
        'type' : 'OPERATOR',
        'binary' : 'fstinvert',
        'prec':10,
        },
    'sync' : {
        "opts":{'--arc_type':'standard',},
        'type' : 'OPERATOR',
        'binary' : 'fstsynchronize',
        'prec':10,
        },
    '*' :   {
        "opts":{'--arc_type':'standard',},
        'type' : 'OPERATOR',
        'binary' : 'fstcompose PREFIX.FST1.fst PREFIX.FST2.fst > PREFIX.FST1FST2.fst',
        'prec':5,
        },
    '.' : {
        "opts":{'--arc_type':'standard',},
        'type' : 'OPERATOR',
        'binary' : 'fstcompose PREFIX.FST1.lkhd.fst PREFIX.FST2.rlbl.fst > PREFIX.FST1FST2.lkhd.fst',
        'prec':5,
        },
    '(' : { "opts":{}, 'type' : 'PAREN',   'binary':None, 'prec' : None },
    ')' : { "opts":{}, 'type' : 'PAREN',   'binary':None, 'prec' : None },
    '[' : { "opts":{}, 'type' : 'BRACKET', 'binary':None, 'prec' : None },
    ']' : { "opts":{}, 'type' : 'BRACKET', 'binary':None, 'prec' : None },
    ',' : { "opts":{}, 'type' : 'COMMA',   'binary':None, 'prec' : None },
    'l' : { "opts":{}, 'type' : 'BRARG',   'binary':None, 'prec' : 2 },
    'w' : { "opts":{}, 'type' : 'BRARG',   'binary':None, 'prec' : 2 },
    't' : { "opts":{}, 'type' : 'BRARG',   'binary':None, 'prec' : 2 },
    's' : { "opts":{}, 'type' : 'BRARG',   'binary':None, 'prec' : 2 },
    'e' : { "opts":{}, 'type' : 'BRARG',   'binary':None, 'prec' : 2 },
    'a' : { "opts":{}, 'type' : 'BRARG',   'binary':None, 'prec' : 2 },
    'H' : { "opts":{}, 'type' : 'ASR',     'binary':'fstcompile', 'prec' : None },
    'C' : { "opts":{}, 'type' : 'ASR',     'binary':'fstcompile', 'prec' : None },
    'L' : { "opts":{}, 'type' : 'ASR',     'binary':'fstcompile', 'prec' : None },
    'G' : { "opts":{}, 'type' : 'ASR',     'binary':'fstcompile', 'prec' : None },
    'T' : { "opts":{}, 'type' : 'ASR',     'binary':'fstcompile', 'prec' : None },
    }

class Token( ):
    
    def __init__( self ):
        self.CLASS    = None
        self.RAWNAME  = None
        self.PREC     = None
        self.TYPE     = None
        self.NAME     = None
        self.BINARY   = None
        self.OPTS     = None
    
    def _set_option( self, opt ):
        """
            Update a value for a pre-existing key, or add a new key/value pair.
        """
        pass
    
    def set_options( self, opts ):
        """
            Update a list of options.
        """
        pass

    def build_command( self, *args ):
        if len(args)==0:
            print "fstcompile", self.NAME
            return
        new_name = self.NAME + "".join([x.NAME for x in args])
        if len(args)==2:
            print self.BINARY.replace("FST1",args[0].NAME).replace("FST2",args[1].NAME)
        elif len(args)==1:
            print self.BINARY.replace("FST1",args[0].NAME)
        token = TokenFactory( [1,new_name] )
        return token


def TokenFactory( tok_data, *kwargs ):
    """Build token objects according to option specifications."""

    token   = Token()
    
    token.CLASS    = tok_data[0]
    token.RAWNAME  = tok_data[1]
    opt_data       = re.split(r"_+",tok_data[1])
    token.NAME     = opt_data.pop(0)
    if token.NAME in option_registry:
        token.TYPE    = option_registry[token.NAME]['type']
        token.BINARY  = option_registry[token.NAME]['binary']
        token.PREC    = option_registry[token.NAME]['prec']
        token.OPTS    = deepcopy(option_registry[token.NAME]['opts'])
    else:
        token.TYPE    = "WFST"       # Custom user defined WFST
        token.BINARY  = "fstcompile" # Default command is to compile. Check at runtime.
        token.PREC    = None
        token.OPTS    = {'--arc_type':'standard'}
    
    for opt in opt_data:
        for o in list(opt):
            if label_map[o]=="l" or label_map[o]=="t":
                token.OPTS[option_map[label_map[o]]] = semiring_map[label_map[o]]
            else:
                token.OPTS[option_map[label_map[o]]] = 'true'

    return token 
