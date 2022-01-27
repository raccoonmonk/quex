# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.input.code.base           import SourceRef
from   quex.engine.misc.tools         import typed
from   quex.engine.state_machine.core import DFA
from   quex.engine.misc.interval_handling  import NumberSet
from   quex.output.syntax_elements    import Argument

class MacroCall:
    @typed(ArgumentList=[Argument], SourceTxt=str, ReferenceSr=(None, SourceRef))
    def __init__(self, ArgumentList, SourceTxt, ReferenceSr):
        self.argument_list = ArgumentList
        self.source_txt    = SourceTxt
        self.sr            = ReferenceSr

class PatternShorthand:
    def __init__(self, Name="", Value=None, SourceReference=None, RE=""):
        """A NumberSet is represented as 'DFA'. Only upon evaluation it can
        be seen whether the DFA can be represented as NumberSet.
        """
        def _adapt(X):
            # The 'PatternShorthand' can only contain 'integer' or 'DFA' objects
            if isinstance(X, NumberSet): return DFA.from_character_set(X)
            else:                        return X

        self.name    = Name
        self.__value = _adapt(Value)

        if SourceReference is None: SourceReference = SourceRef()
        self.sr                 = SourceReference
        self.regular_expression = RE

    def get_DFA(self):
        if not isinstance(self.__value, DFA): return None
        else:                                 return self.__value.clone()

    def get_NumberSet(self):
        if not isinstance(self.__value, DFA): return None
        result = self.__value.get_number_set()

        if result is None: return None
        else:              return result.clone()

    def get_MacroCall(self):
        if not isinstance(self.__value, MacroCall): return None
        else:                                       return self.__value

    def get_integer(self):
        if isinstance(self.__value, int): return self.__value
        else:                                     return None

