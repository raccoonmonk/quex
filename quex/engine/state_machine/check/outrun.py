# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from quex.engine.misc.tree_walker   import TreeWalker

def do(High, Low): 
    """Check whether lower priority pattern 'Low' can outrun by length a 
       pattern 'High' even though 'High' has matched. 
       
       EXAMPLE: High:  print
                Low:   [a-z]+

       If a stream contains "printer", then 'Low' would match even though
       'High' could have matched if 'Low' was not there. The writer of 'High'
       might be surprised if he was not aware of 'Low'.

       Less obvious is:   High: alb|albertikus
                          Low:  albert

       where the low priority pattern may match on "albert" after the high-prio
       pattern has matched on "alb". If the lexeme does not complete
       "albertikus", then the low priority pattern wins.

       RETURNS: True, if 'Low' might outrun a lexeme that matches 'High'.
                False, 'Low' can never outrun a lexeme matched by 'High'.
    """
    # Step 1: Find acceptance states which are reached while walking
    #         along paths of 'High' that are also inside 'Low'.
    result = commonality(High, Low)
    if len(result) == 0:
        return False

    # Step 2: Detect paths in Low that divert from High starting from
    #         the acceptance states collected in step 1.
    verdict_f = diversion(High, Low, result)

    # RETURNS (explained): 
    # True    There are acceptance states in High can be reached by paths that
    #         are also are feasible in Low; Low then diverts from those 
    #         paths, i.e. there are paths in Low which are not in High.
    # False   Else.
    return verdict_f

def commonality(High, Low):
    """Find acceptance states which are reached while walking along paths 
    of 'High' that are also inside 'Low'.
    """
    collector = CommonalityWalker(High, Low)
    collector.do([(High.init_state_index, Low.init_state_index)])
    # collector.result: List of pairs (HighIndex, LowIndex) 
    #
    #  HighIndex = index of acceptance state in 'High' that has been reached.
    #  LowIndex  = index of state in 'Low' that was reached when walking
    #              along the path to 'HighIndex'.
    #
    return collector.result

def diversion(High, Low, StartStatePairList=None):
    """Detect paths in Low that divert from High starting from the state-pairs 
    mentioned in 'StartStatePairList'. The 'StartStatePairList' is a list
    of pairs (state index of High, state index of Low) where to start the 
    searches.
    
    RETURNS: True  -- if there are paths in Low that divert
             False -- if all paths from acceptance states in High are 
                      also in Low.
    """
    if StartStatePairList is None:
        StartStatePairList = [(High.init_state_index, Low.init_state_index)]

    # Start searching for diversion from the critical acceptance states in High.
    detector = DiversionWalker(High, Low)
    detector.do(StartStatePairList)
    return detector.result

class CommonalityWalker(TreeWalker):
    """Find acceptance states of 'High' which are reachable by walking along 
    possible paths in 'Low'. 
       
       -- If an acceptance state in High ('A') is reached, then a pair
          (Low_StateIndex, High_StateIndex) is appended to 'self.result'. 

    Later, DiversionWalker will walk along paths of 'Low' starting from these 
    detected states to see whether it diverts.
    """
    def __init__(self, High, Low):
        self.high     = High # DFA of the higher priority pattern
        self.low      = Low  # DFA of the lower priority pattern
        self.result   = []
        self.done_set = set()
        TreeWalker.__init__(self)

    def on_enter(self, Args):
        # (*) Update the information about the 'trace of acceptances'
        High_StateIndex, Low_StateIndex = Args
        if High_StateIndex in self.done_set: return None
        else:                                self.done_set.add(High_StateIndex)
        High_State = self.high.states[High_StateIndex]

        # Register any acceptance state reached in the high-prio pattern while
        # walking also along paths in 'low'. Need to specify the associated
        # state index of the low-prio pattern, so that the subsequent search
        # knows where to start.
        if High_State.is_acceptance():
            self.result.append( (High_StateIndex, Low_StateIndex) )
            return None

        # Follow the path of common trigger sets
        Low_State     = self.low.states[Low_StateIndex]
        sub_node_list = []
        for a_target, a_trigger_set in High_State.target_map:
            for b_target, b_trigger_set in Low_State.target_map:
                if b_trigger_set.has_intersection(a_trigger_set): 
                    # Some of the transition in 'High' is covered by a transition in 'Low'.
                    sub_node_list.append( (a_target, b_target) )

        return sub_node_list

    def on_finished(self, Args):
        pass

class DiversionWalker(TreeWalker):
    """Checks whether 'Low' can walk paths which are not covered by 'High'. 

    Start states can be specified (For 'outrun' start at the acceptance states 
    of 'High' and their counterpart in 'Low').

       -- If an acceptance state in Low is reached while High does
          not accept, then Low has outrun High after match. 
          
          Set 'result = True' and abort.

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
            self.result  = True 
            self.abort_f = True
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


