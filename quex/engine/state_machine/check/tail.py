# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
"""PURPOSE: 

      Given two state machines A and T, determine whether A ends with T.

"""
import quex.engine.state_machine.check.outrun    as     outrun
import quex.engine.state_machine.algebra.reverse as     reverse
from   quex.engine.misc.tree_walker              import TreeWalker

def do(A, T):
    """Checks: (1) whether there is a sequence that matches 'T' and the end of 'A'.
               (2) whether there is a sequence that does not match 'T' and still
                   match the end of 'A'.

    RETURNS: [0] True, ALL ending sequences of 'A' match 'T'.
                 False, else.
             [1] True, if there are some ending sequences of 'A' that match 'T'.
                 False, else.
    """
    Ar = reverse.do(A)
    Tr = reverse.do(T)
    
    # Does 'T' match AT LEAST ONE tail of 'A'?
    # == Are there paths in 'Tr' to their acceptance states that are
    #    also present in 'Ar'?
    common_tail_exists_f   = len(outrun.commonality(Tr, Ar)) != 0
    # Are there tails in 'A' which are not covered by 'T'?
    # == Are there paths in 'Ar' which are not covered by paths in 'Tr'?
    uncommon_tail_exists_f = diversion(Ar, Tr)

    return common_tail_exists_f and not uncommon_tail_exists_f, \
           common_tail_exists_f

def diversion(High, Low):
    """Detect paths in Low that divert from High starting from the state-pairs 
    mentioned in 'StartStatePairList'. The 'StartStatePairList' is a list
    of pairs (state index of High, state index of Low) where to start the 
    searches.
    
    RETURNS: True  -- if there are paths in Low that divert
             False -- if all paths from acceptance states in High are 
                      also in Low.
    """
    detector = DiversionWalker(High, Low)
    detector.do([(High.init_state_index, Low.init_state_index)])
    return detector.result

class DiversionWalker(TreeWalker):
    """Checks whether 'Low' can walk paths which are not covered by 'High'. 

    This is NOT THE SAME as the DiversionWalker of 'outrun'. The DiversionWalker
    of 'outrun' marks 'True' upon acceptance of Low.


       -- If a step in Low is detected which is not feasible in High, 
          then Low has outrun High after match.

          Set 'result = True' and abort.
    """
    def __init__(self, High, Low):
        self.high     = High  # DFA of the higher priority pattern
        self.low      = Low   # DFA of the lower priority pattern
        self.result   = False # Low cannot outrun High
        self.done_set = set()
        TreeWalker.__init__(self)

    def on_enter(self, Args):
        # (*) Update the information about the 'trace of acceptances'
        High_StateIndex, Low_StateIndex = Args
        if Low_StateIndex in self.done_set: return None
        else:                               self.done_set.add(Low_StateIndex)

        Low_State  = self.low.states[Low_StateIndex]
        High_State = self.high.states[High_StateIndex]

        # Low reaches acceptance state before High.
        # => No further investigation. 
        # Note, that here we are in states *after* a matching high-prio pattern 
        # (after the high-prio acceptance states).
        if Low_State.is_acceptance() and not High_State.is_acceptance():
            # At 'outrun's DiversionWalker: self.result  = True 
            #                               self.abort_f = True
            return None

        sub_node_list = []
        for b_target, b_trigger_set in Low_State.target_map:
            b_remaining_triggers = b_trigger_set.clone()
            for a_target, a_trigger_set in High_State.target_map:
                if b_trigger_set.has_intersection(a_trigger_set): 
                    # The transition in 'A' is covered by a transition in 'B'.
                    sub_node_list.append( (a_target, b_target) )
                    b_remaining_triggers.subtract(a_trigger_set)

            if not b_remaining_triggers.is_empty():
                # Low contains triggers not present in High. 
                # => Low 'diverts' from High.
                self.result  = True 
                self.abort_f = True
                return None

        # (*) Recurse to all sub nodes
        return sub_node_list

    def on_finished(self, Args):
        pass


