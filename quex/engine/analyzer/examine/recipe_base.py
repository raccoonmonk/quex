# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
"""PURPOSE:

This file defines the base class for all 'recipes' as defined in [DOC].
No object is supposed to be instantiated of class 'Recipe'. Instead, concrete 
classes need to be derived from it. The derived concrete classes can then 
instantiate objects. 

The derived concrete class of 'Recipe' implements the specification of a 
particular considered behavior. 

The 'Recipe' class defines an 'interface' in the Java sense, and an 'abstract
class' in the C++ sense. It consists of '@staticmethod'-s and member functions.
The derived class must follow the same exact scheme. Only then, the derived
recipe fits the algorithm of analysis.

The appropriate way to add a new investigated behavior is to copy the class 
'Recipe', rename it, derive the new-named class from 'Recipe' and fill its
functions with meaningful content.

(C) Frank-Rene Schaefer
"""
class Recipe:
    """Base class for SCR recipes. The general recipe depends on:

        -- The current state.
        -- Constants which can be pre-determined.
        -- Register contents which are developed at run-time.

    A derived class MUST implement:

       .__init__(): taking a list of SCR relevant operations.

    A derived class CAN implement:

       .from_spring(): Constructs a recipe from a spring states.

       .get_SCR_by_state_index(): generator that provides an iterable
              over pairs of (state index, SCR). That is usefull, if the
              SCR differs from state to state.

       .get_initial_springs(): determines the set of initial springs. By
              default, the sole initial spring is simply the init state.

    See [DOC] the according DEFINITION.
    """
    @classmethod
    def UNDETERMINED(cls, RequiredVariableSet):
        assert False, "To be implemented in derived class"

    @classmethod
    def INITIAL(cls, RequiredVariableSet):
        assert False, "To be implemented in derived class"


    @staticmethod
    def tag_iterable(db, StateIndexIterable, VariableId):
        """Add VariableId to every dictionary entry 'db[si]' where 'si' is
        provided by the 'StateIndexIterable'.
        """
        for si in StateIndexIterable:
            db[si].add(VariableId)

    @staticmethod
    def cmd_iterable(SM, CmdType):
        """Iterate over all states and commands which are concerned of the
        given command type.
        """
        for si, state in SM.states.items():
            for cmd in state.single_entry.get_iterable(CmdType):
                yield si, cmd

