# Copyright (c) 2010 Josef Robert Novak
#
# You may copy and modify this freely under the same terms as
# Sphinx-III

"""Read/write Sphinx-III model definition files.

This module reads and writes the text format model definiton (triphone
to senone mapping) files used by SphinxTrain, Sphinx-III, and
PocketSphinx.

MODIFIED on 12-22-2010 by Josef Novak 
Added an array of mdef lines for easier processing,
self.allfields = []
Probably a better way to do this but I can't tell from the code.
"""

__author__ = "Josef Robert Novak <novakj@gavo.t.u-tokyo.ac.jp>"
__version__ = "$Revision: $"

#from numpy import ones, empty

def open(file):
    return T3Mdef(file)

class T3Mdef:
    "Read Sphinx-III format model definition files as required by tcubed"
    def __init__(self, filename):
        self.info = {}
        if filename != None:
            self.read(filename)

    def read(self, filename):
        self.fh = file(filename)

        while True:
            version = self.fh.readline().rstrip()
            if not version.startswith("#"):
                break
        if version != "0.3":
            raise Exception("Model definition version %s is not 0.3" % version)
        info = {}
        while True:
            spam = self.fh.readline().rstrip()
            if spam.startswith("#"):
                break
            val, key = spam.split()
            info[key] = int(val)
        self.n_phone = info['n_base'] + info['n_tri']
        self.n_ci = info['n_base']
        self.n_tri = info['n_tri']
        self.n_ci_sen = info['n_tied_ci_state']
        self.n_sen = info['n_tied_state']
        self.n_tmat = info['n_tied_tmat']
        self.tiedlist = {}
        # Skip field description lines
        spam = self.fh.readline().rstrip()
        spam = self.fh.readline().rstrip()
        
        #tcubed doesn't require much mdef organization. we just want the mdef lines
        self.allfields = []
        while True:
            spam = self.fh.readline().rstrip()
            if spam == "":
                break
            fields = spam.split()
            self.allfields.append(fields)
            triphone = (fields[1],fields[0], fields[2], fields[3])
            self.tiedlist[triphone] = len(self.allfields)
            
