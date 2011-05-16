#!/usr/bin/python
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
