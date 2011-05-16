#!/usr/bin/python
#########################################
# Copyright (c) [2010-2011], Josef Robert Novak
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
#  modification, are permitted #provided that the following conditions
#  are met:
#
# * Redistributions of source code must retain the above copyright 
#    notice, this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above 
#    copyright notice, this list of #conditions and the following 
#    disclaimer in the documentation and/or other materials provided 
#    with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT 
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS 
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE 
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, 
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES 
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR 
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) 
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, 
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) 
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED 
# OF THE POSSIBILITY OF SUCH DAMAGE.
#########################################
import re, math

class Silclass( ):

    def __init__( self, vocabfile, sil="<sil>", eps="<eps>", silperc=0.117, prefix="silclass", failure=None ):
        self.vocabfile = vocabfile
        self.sil       = sil
        self.eps       = eps
        self.silperc   = silperc
        self.nosilperc = 1.0-silperc
        self.vocab     = set([])
        self.failure   = failure
        self.isyms     = set([self.sil])
        self.osyms     = set([self.sil])
        if failure:
            self.isyms.add(failure)
            self.osyms.add(failure)
        self.prefix    = prefix

    def read_vocab( self ):
        vocab_fp = open( self.vocabfile,"r" )
        for line in vocab_fp:
            line = line.strip()
            sym, id = re.split(r"\s+",line)
            if int(id)==0:
                continue
            self.vocab.add(sym)
        vocab_fp.close()
        return

    def log2tropical( self, val ):
        tropval = math.log(float(val)) * -1.0
        return tropval 

    def generate_silclass( self ):
        """Generate the silence class transducer."""
        count = 1
        silclass_fp = open("PREFIX.t.fst.txt".replace("PREFIX",self.prefix),"w")
        for word in self.vocab:
            if word==self.sil:
                continue
            silclass_fp.write("%d %d %s %s\n" % (0, count, word, word))
            silclass_fp.write("%d %d %s %s %f\n" % (count, count, self.eps, self.sil, self.log2tropical(self.silperc)))
            silclass_fp.write("%d %d %s %s %f\n" % (count, 0, self.eps, self.eps, self.log2tropical(self.nosilperc)))
            self.isyms.add(word)
            self.osyms.add(word)
            count += 1
        if self.failure:
            silclass_fp.write("0 0 %s %s\n" % (self.failure, self.failure))
        silclass_fp.write("0\n")
        silclass_fp.close()
        return

    def print_isyms( self ):
        ofp = open( "%s.t.isyms"%self.prefix, "w" )
        ofp.write("%s 0\n"%self.eps)
        for i,sym in enumerate(self.isyms):
            ofp.write("%s %d\n"%(sym,i+1))
        ofp.close()
        return

    def print_osyms( self ):
        ofp = open( "%s.t.osyms"%self.prefix, "w" )
        ofp.write("%s 0\n"%self.eps)
        for i, sym  in enumerate(self.osyms):
            ofp.write("%s %d\n"%(sym,i+1))
        ofp.close()
        return

    def print_all_syms( self ):
        self.print_isyms()
        self.print_osyms()


if __name__=="__main__":
    import sys

    silclass = Silclass( sys.argv[1], prefix=sys.argv[2] )
    silclass.read_vocab( )
    silclass.generate_silclass( )
    silclass.print_all_syms( )
