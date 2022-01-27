# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.input.code.base   import SourceRef, CodeFragment, SourceRef_VOID
from   quex.engine.misc.tools import typed, print_callstack

from   copy import deepcopy

class CodeUser(CodeFragment):
    """User code as it is taken from some input file. It contains:

          .get_code() -- list of strings or text formatting instructions
                         (including possibly annotations about its source code origin)
          .sr         -- the source reference where it was taken from
          .mode_name  -- Mode where the code was defined
    """
    def __init__(self, Code, SourceReference):
        CodeFragment.__init__(self, Code, SourceReference)

    def clone(self):
        result = CodeUser(deepcopy(self.get_code()), self.sr)
        return result

CodeUser_NULL = CodeUser([], SourceRef())

