# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.engine.state_machine.core            import DFA
from   quex.engine.pattern                       import Pattern
from   quex.engine.misc.tools                    import typed
from   quex.constants                            import E_AcceptanceCondition

class Checker:
    def __init__(self, SuperSM, CandidateSM):
        assert isinstance(SuperSM, DFA),     SuperSM.__class__.__name__
        assert isinstance(CandidateSM, DFA), CandidateSM.__class__.__name__

        self.sub   = CandidateSM
        self.super = SuperSM
        self.visited_state_index_set = set()

    def do(self):
        """RETURNS: 
        
             True  - if SuperSM matches all the patterns that CandidateSM
                     can match. 
             False - if not 

           In other words, SuperSM is a 'Super DFA' of Candidate, if
           the set of patterns matched by 'CandidateSM' a subset of the set of
           patterns matched by 'SuperSM'.                            
        """
        return self.__dive(self.sub.init_state_index, [self.super.init_state_index])

    def __dive(self, SubSM_StateIndex, SuperSM_StateIndexList):
        """SubSM_StateIndex:       refers to a state in the alleged subset state machine.

           SuperSM_StateIndexList: list of states in the 'super set' state machine that
                                   was reached by the same trigger set as SubSM_StateIndex.      
                                   They are the set of states that can 'shadow' the current
                                   state indexed by 'SubSM_StateIndex'.
        """
        # (*) Determine the states behind the indices
        sub_state        = self.sub.states[SubSM_StateIndex]
        super_state_list = [self.super.states[index] for index in SuperSM_StateIndexList]
        #     Bookkeeping
        self.visited_state_index_set.add(SubSM_StateIndex)
        #     Union of all triggers were the 'shadowing' super states trigger.
        #     (For speed considerations, keep it in prepared, so it does not have to 
        #      be computed each time it is required.)
        super_trigger_set_union_db = dict(
            (index, self.super.states[index].target_map.get_trigger_set_union())
            for index in SuperSM_StateIndexList
        )

        # (*) CONDITION:
        #
        # For every trigger (event) in the 'sub sm state' that triggers to a follow-up state
        # there must be pendant triggering from the shadowing 'super sm states'.
        #
        # If a trigger set triggers to an 'acceptance' state, then all shadowing 'super sm states' 
        # must trigger to an 'acceptance' state. Thus, saying that the 'super sm' also recognizes
        # the pattern that was reached until here can be matched by the 'super set sm'. If not
        # all shadowing state machines would trigger on the trigger set to an acceptance state,
        # this means that there is a path to an acceptance state in 'subset sm' that the 'super
        # sm' has no correspondance. Thus, then the claim to be a super set state machine can
        # be denied.
        #
        for target_index, trigger_set in sub_state.target_map:
            target_state = self.sub.states[target_index]

            # (*) Require that all shadowing states in the 'super sm' trigger to a valid
            #     target state on all triggers in the trigger set. 
            #     
            #     This is true, if the union of all trigger sets of a shadowing 'super state'
            #     covers the trigger set. It's not true, if not. Thus, use set subtraction:
            for index in SuperSM_StateIndexList:
                if trigger_set.difference(super_trigger_set_union_db[index]).is_empty() == False:
                    return False

            # (*) Collect the states in the 'super set sm' that can be reached via the 'trigger_set'
            super_target_state_index_set = set()
            for super_state in super_state_list:
                super_target_state_index_set.update(super_state.target_map.get_resulting_target_state_index_list(trigger_set))

            # (*) The acceptance condition: 
            if target_state.is_acceptance():
                # (*) Require that all target states in 'super sm' reached by 'trigger_set' are 
                #     acceptance states, otherwise the alleged 'sub sm' has found a pattern which
                #     is matched by it and which is not matched by 'super sm'. Thus, the claim 
                #     that the alleged 'sub sm' is a sub set state machine can be repudiated.
                for index in super_target_state_index_set:
                    if self.super.states[index].is_acceptance() == False: return False

            # (*) No need to go along loops, do not follow paths to states already visited.
            if target_index not in self.visited_state_index_set:
                if self.__dive(target_index, super_target_state_index_set) == False: return False

        # If the condition held for all sub-pathes of all trigger_sets then we can report
        # that the currently investigated sub-path supports the claim that 'sub sm' is a
        # sub set state machine of 'super sm'.
        return True

@typed(A=(DFA, Pattern), B=(DFA, Pattern))
def do(A, B):
    """RETURNS: True  - if A == SUPERSET of B
                False - if not
    """
    if isinstance(A, DFA):
        assert isinstance(B, DFA)
        return Checker(A, B).do()

    assert not isinstance(B, DFA)
    # (*) Core Pattern ________________________________________________________
    #
    #     (including the mounted post context, if there is one).
    #
    # NOTE: Post-conditions do not change anything, since they match only when
    #       the whole lexeme has matched (from begin to end of post condition).
    #       Post-conditions only tell something about the place where the 
    #       analyzer returns after the match.
    superset_f = Checker(A.sm, B.sm).do()

    if not superset_f: return False

    # NOW: For the core state machines it holds: 
    #
    #               'core(A)' matches a super set of 'core(B)'.
    #

    # (*) Pre-Condition _______________________________________________________
    #
    # If 'A' has a restriction that 'B' has not, 
    # => 'A' cannot be a superset of 'B'.
    if           A.sm.has_acceptance_condition(E_AcceptanceCondition.END_OF_STREAM) \
         and not B.sm.has_acceptance_condition(E_AcceptanceCondition.END_OF_STREAM):  return False
    elif         A.sm.has_acceptance_condition(E_AcceptanceCondition.BEGIN_OF_LINE) \
         and not B.sm.has_acceptance_condition(E_AcceptanceCondition.BEGIN_OF_LINE):   return False
    # here: not(A) or B => Either A does not have the condition or B has it too.
    elif         A.sm.has_acceptance_condition(E_AcceptanceCondition.BEGIN_OF_STREAM) \
         and not B.sm.has_acceptance_condition(E_AcceptanceCondition.BEGIN_OF_STREAM): return False
    # here: not(A) or B => Either A does not have the condition or B has it too.
    elif     (A.sm_pre_context_to_be_reversed is not None) \
         and (B.sm_pre_context_to_be_reversed is None):                return False
    # here: not(A) or B => Either A does not have the condition or B has it too.
    elif     (A.sm_pre_context_to_be_reversed is None) \
         and (B.sm_pre_context_to_be_reversed is not None):            return True

    # 'A' and be either have both pre-context, or none.
    if A.sm_pre_context_to_be_reversed is None: return True
    else:                        return Checker(B.sm_pre_context_to_be_reversed, A.sm_pre_context_to_be_reversed).do()

