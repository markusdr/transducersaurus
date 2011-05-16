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
import re

class WFST( ):
    """A simple Weighted Finite-State Transducer base class."""

    def __init__( self, start=0, acceptor=True, isyms=None, eps="<eps>", semiring="standard", arcs={}, states={}, final=0 ):
        self.start  = start
        self.final  = final
        self.max    = start
        self.eps    = eps
        self.isyms  = self._set_isyms( isyms )
        self.arcs   = arcs

    def _set_isyms( self, isyms ):
        if isyms==None:
            return set([])
        else:
            return isyms

    def add_arc( self, istate, isym, osym, ostate, weight=0.0 ):
        if istate in self.arcs:
            self.arcs[istate].add( tuple([isym, osym, ostate, weight]) )
        else:
            self.arcs[istate] = set([ tuple([isym, osym, ostate, weight]) ])
        if istate>self.max:
            self.max=istate
        if ostate>self.max:
            self.max=ostate
            
        if isym not in self.isyms and not isym==self.eps:
            self.isyms.add(isym)
        
        return

    def del_arc( self, istate, isym, osym, ostate, weight=0.0 ):
        if not istate in self.arcs:
            print "State: (%d) not in arc table..." % istate
            return

        arc = tuple([isym, osym, ostate, weight])
        if arc in self.arcs[istate]:
            self.arcs[istate].remove(arc)

        return
