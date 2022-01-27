# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from quex.engine.misc.tree_walker   import TreeWalker

def do(A, B): 
    """Detect if 'A' and 'B' match on common lexemes.

       RETURNS: True, if they do.
                False, else.
    """
    if A.is_Empty() or B.is_Empty(): return True

    detector = SameDetector(A, B)
    detector.do((A.init_state_index, B.init_state_index))

    return not detector.result

class SameDetector(TreeWalker):
    """Find acceptance states of 'A' which are reachable by walking along 
    possible paths in 'B'. 
       
    -- If an acceptance state in A ('A') is reached, then a pair
       (B_StateIndex, A_StateIndex) is appended to 'self.result'. 

    """
    def __init__(self, A, B):
        self.sm_a     = A  # DFA of the higher priority pattern
        self.sm_b     = B  # DFA of the lower priority pattern
        self.result   = False
        self.done_set = set()
        TreeWalker.__init__(self)

    def on_enter(self, Args):
        # (*) Update the information about the 'trace of acceptances'
        A_StateIndex, B_StateIndex = Args
        if A_StateIndex in self.done_set: return None
        else:                             self.done_set.add(A_StateIndex)
        A_State = self.sm_a.states[A_StateIndex]
        B_State = self.sm_b.states[B_StateIndex]

        if A_State.is_acceptance() and B_State.is_acceptance():
            self.result  = True
            self.abort_f = True
            return None

        # Follow the path of common trigger sets
        sub_node_list = []
        for a_target, a_trigger_set in A_State.target_map:
            for b_target, b_trigger_set in B_State.target_map:
                if not b_trigger_set.has_intersection(a_trigger_set): continue
                # Some of the transition in 'A' is covered by a transition in 'B'.
                sub_node_list.append( (a_target, b_target) )

        return sub_node_list

    def on_finished(self, Args):
        pass
