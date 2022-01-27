# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from quex.engine.misc.tools import flatten
from quex.constants  import E_IncidenceIDs, E_TransitionN

from collections     import namedtuple
from itertools       import islice
#______________________________________________________________________________
# Result of the analysis: For each state there is a list of AcceptSequences
# each one representing a path through the state machine to that state. An 
# AcceptSequences is a list of AcceptCondition objects.
# 
AcceptCondition = namedtuple("AcceptCondition", 
                             ("acceptance_id", 
                              "acceptance_condition_set", 
                              "accepting_state_index", 
                              "positioning_state_index",
                              "transition_n_since_positioning"))

class AcceptSequence:
    def __init__(self, AcceptanceTrace):
        self.__sequence = [
           AcceptCondition(x.acceptance_id, 
                           x.acceptance_condition_set, 
                           x.accepting_state_index, 
                           x.positioning_state_index, 
                           x.transition_n_since_positioning)
           for x in AcceptanceTrace
        ]

    def acceptance_behavior_equal(self, Other):
        if len(self.__sequence) != len(Other.__sequence):    
            return False
        for x, y in zip(self.__sequence, Other.__sequence):
            if   x.acceptance_condition_set != y.acceptance_condition_set: return False
            elif x.acceptance_id  != y.acceptance_id:  return False
        return True

    def __iter__(self):
        return iter(self.__sequence)

    def get_string(self, Indent=0):
        txt = [ " " * (Indent*4) + "p-id           pre-id   as-i     ps-i     tnsp\n"]
        for x in self.__sequence:
            #012345678012345678012345678012345678012345678
            acc_condition_str = "NONE"
            if x.acceptance_condition_set:
                acc_condition_str = ", ".join("%s" % ac for ac in x.acceptance_condition_set)
            txt.append(" " * (Indent*4) + "%-15s%-9s%-9s%-9s%-9s\n" % ( \
                        x.acceptance_id, acc_condition_str,
                        x.accepting_state_index, x.positioning_state_index,
                        x.transition_n_since_positioning))
        return "".join(txt)

    def __str__(self):
        return self.get_string()

class PositioningInfo(object):
    __slots__ = ("acceptance_condition_set", 
                 "acceptance_id",
                 "transition_n_since_positioning", 
                 "positioning_state_index_set")
    def __init__(self, TheAcceptCondition):
        self.acceptance_condition_set       = TheAcceptCondition.acceptance_condition_set
        self.acceptance_id                  = TheAcceptCondition.acceptance_id
        self.transition_n_since_positioning = TheAcceptCondition.transition_n_since_positioning
        self.positioning_state_index_set    = set([ TheAcceptCondition.positioning_state_index ])

    def register(self, TheAcceptCondition):
        self.positioning_state_index_set.add(TheAcceptCondition.positioning_state_index)

        if self.transition_n_since_positioning != TheAcceptCondition.transition_n_since_positioning:
            self.transition_n_since_positioning = E_TransitionN.VOID

    def __repr__(self):
        acc_condition_str = "NONE"
        if self.acceptance_condition_set:
            acc_condition_str = ", ".join("%s" % ac for ac in self.acceptance_condition_set)
        txt  = ".acceptance_id                  = %s\n" % repr(self.acceptance_id) 
        txt += ".acceptance_condition_set       = %s\n" % acc_condition_str
        txt += ".transition_n_since_positioning = %s\n" % repr(self.transition_n_since_positioning)
        txt += ".positioning_state_index_set    = %s\n" % repr(self.positioning_state_index_set) 
        return txt

class MergedTraces:
    """Merge multiple traces to a state and provide basic information about
    acceptance and position restore behavior.
    """
    def __init__(self, TraceList):
        self.__list = [ AcceptSequence(x.acceptance_trace) for x in TraceList ]

        # (*) Uniform Acceptance Sequence
        #
        #         map: state_index --> acceptance pattern
        #
        # If all paths to a state show the same acceptance pattern, than this
        # pattern is stored. Otherwise, the state index is related to None.
        self.__uniform_acceptance_sequence  = -1 # Undone

        # (*) Positioning info:
        #
        #     map:  (state_index) --> (acceptance_id) --> positioning info
        #
        self.__positioning_info             = -1 # Undone

    def uniform_acceptance_sequence(self):
        """
        This function draws conclusions on the input acceptance behavior at
        drop-out based on different paths through the same state. Basis for
        the analysis are the PathTrace objects of a state specified as
        'ThePathTraceList'.

        Uniform Acceptance:

          For any possible path to 'this' state the acceptance pattern is the
          same. That is, it accepts exactly the same pattern under the same pre
          contexts and in the same sequence of precedence.

        The 'acceptance_trace' of a _Trace object reflects the precedence of
        acceptance. 

        RETURNS: list of AcceptInfo() - uniform acceptance pattern.
                 None                 - acceptance pattern is not uniform.
        """
        if self.__uniform_acceptance_sequence != -1:
            return self.__uniform_acceptance_sequence

        prototype = self.__list[0]
        for accept_sequence in islice(self.__list, 1, None):
            if not accept_sequence.acceptance_behavior_equal(prototype): 
                self.__uniform_acceptance_sequence = None
                break
        else:
            self.__uniform_acceptance_sequence = prototype

        return self.__uniform_acceptance_sequence

    def acceptance_sequence_prototype(self):
        assert self.__list
        return self.__list[0]

    def accepting_state_index_list(self):
        return flatten(
            (x.accepting_state_index for x in acceptance_sequence)
            for acceptance_sequence in self.__list
        )

    def positioning_info(self):
        """
        Conclusions on the input positioning behavior at drop-out based on
        different paths through the same state.  Basis for the analysis are the
        PathTrace objects of a state specified as 'ThePathTraceList'.

        RETURNS: For a given state's PathTrace list a dictionary that maps:

                            acceptance_id --> PositioningInfo

        --------------------------------------------------------------------
        
        There are the following alternatives for setting the input position:
        
           (1) 'lexeme_start_p + 1' in case of failure.

           (2) 'input_p + offset' if the number of transitions between
               any storing state and the current state is does not differ 
               dependent on the path taken (and does not contain loops).
        
           (3) 'input_p = position_register[i]' if (1) and (2) are not
               not the case.

        The detection of loops has been accomplished during the construction
        of the PathTrace objects for each state. This function focusses on
        the possibility to have different paths to the same state with
        different positioning behaviors.
        """
        if self.__positioning_info != -1: 
            return self.__positioning_info

        positioning_info_by_pattern_id = {}
        # -- If the positioning differs for one element in the trace list, or 
        # -- one element has undetermined positioning, 
        # => then the acceptance relates to undetermined positioning.
        for acceptance_sequence in self.__list:
            for x in acceptance_sequence:
                assert x.acceptance_id != E_IncidenceIDs.VOID

                if x.acceptance_id not in positioning_info_by_pattern_id: 
                    positioning_info_by_pattern_id[x.acceptance_id] = PositioningInfo(x)
                else:
                    positioning_info_by_pattern_id[x.acceptance_id].register(x)

        self.__positioning_info = list(positioning_info_by_pattern_id.values())
        return self.__positioning_info

    def __iter__(self):
        return iter(self.__list)

