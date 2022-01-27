# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.engine.misc.interval_handling  import NumberSet, Interval
from   quex.engine.misc.tools              import flatten
from   quex.constants import E_Border

from   collections import defaultdict

assert E_Border.BEGIN > E_Border.END

def get_elementary_trigger_sets(TM):
    """Considers the trigger dictionary that contains a mapping from target 
    state index to the trigger set that triggers to it: 
 
               target_state_index   --->   trigger_set 

    The trigger sets of different target state indices may intersect. As a result,
    this function produces a list of pairs:

              [ state_index_list, elementary_trigger_set ]

    where the elementary trigger set is the set of all triggers that trigger
    at the same time to all states in the state_index_list. The list contains 
    for one state_index_list only one elementary_trigger_set. All elementary
    trigger sets are disjunct, i.e. they do not intersect.

      NOTE: A general solution of this problem would have to consider the 
            inspection of all possible subset combinations. The number of 
            combinations for N trigger sets is 2^N - which potentially blows
            the calculation power of the computer. Excessive optimizations
            would have to be programmed, if not the following were the case: 

      NOTE: Fortunately, we are dealing with one dimensional sets! Thus, there is
            a very effective way to determine the elementary trigger sets. Imagine
            three trigger sets stretching over the range of numbers as follows:

    different targets, e.g. T0, T1, T2 are triggered by different sets of letters
    in the alphabet. 
                                                              letters of alphabet
                ---------------------------------------------------->

            T0  [---------)       [----------)
            T1          [------)      [-----)
            T2              [----------------------)    

    => elementary sets: 
 
       only T0  [-------)
       T0, T1           [-)
       only T1            [-)
       T1, T2               [--)
       only T2                 [---)          [----)
       T0, T2                      [---)     [)
       T0, T1, T2                      [-----)
    """
    # (*) Accumulate the transitions for all states in the state list.
    #     transitions to the same target state are combined by union.
    history = _get_plain_line_up([ TM ])

    # (*) build the elementary subset list 
    combinations           = {}          # use dictionary for uniqueness
    current_interval_begin = None
    current_target_indices = {}          # use dictionary for uniqueness
    current_target_epsilon_closure = []
    for item in history:
        # -- add interval and target indice combination to the data
        #    (only build interval when current begin is there, 
        #     when the interval size is not zero, and
        #     when the epsilon closure of target states is not empty)                   
        if     current_interval_begin is not None      \
           and current_interval_begin != item.position \
           and len(current_target_indices) != 0:

            interval = Interval(current_interval_begin, item.position)

            # key = tuple(current_target_epsilon_closure) 
            key = tuple(sorted(current_target_epsilon_closure))
            combination = combinations.get(key)
            if combination is None:
                combinations[key] = NumberSet(interval, ArgumentIsYoursF=True)
            else:
                combination.unite_with(interval)
       
        # -- BEGIN / END of interval:
        #    add or delete a target state to the set of currently considered target states
        #    NOTE: More than one state can trigger on the same range to the same target state.
        #          Thus, one needs to keep track of the 'opened' target states.
        if item.change == E_Border.BEGIN:
            if item.target_idx in current_target_indices:
                current_target_indices[item.target_idx] += 1
            else:
                current_target_indices[item.target_idx] = 1
        else:        # == E_Border.END
            assert item.target_idx in current_target_indices
            if current_target_indices[item.target_idx] > 1:
                current_target_indices[item.target_idx] -= 1
            else:    
                del current_target_indices[item.target_idx] 

        # -- re-compute the epsilon closure of the target states
        current_target_epsilon_closure = current_target_indices

        # -- set the begin of interval to come
        current_interval_begin = item.position                      

    # (*) create the list of pairs [target-index-combination, trigger_set] 
    return combinations

def get_intersection_line_up(TargetMapList):
    """Considers a list of target maps which are to be associated to be active
    in parallel. It determines what 'target_state_setup'-s are triggered by
    what lexatoms. A 'target_state_setup' is a list where

        target_state_setup[i] = target state of 'TargetMapList[i]'

    As a result a dictionary is produced that maps from 'target_state_setup'-s
    (in terms of tuples) to NumberSet-s by which they are triggered.
    
    RETURNS: map: target_state_setup --> NumberSet
    """
    result = {}
    for begin, end, target_state_setup in _line_up_iterable(TargetMapList):
        if None in target_state_setup: continue
        _enter(result, begin, end, target_state_setup)

    return result

def get_intersection_line_up_2(TargetMapList):
    """Same as 'get_intersection_line_up()' only that 'None' is setup for 
    targets that do not transit on an interval.

    YIELDS: pairs (target_state_setup, NumberSet)
    """
    result = {}
    for begin, end, target_state_setup in _line_up_iterable(TargetMapList):
        _enter(result, begin, end, target_state_setup)

    return iter(result.items())

def _get_plain_line_up(TargetMapList):
    return sorted(flatten(target_map.get_trigger_set_line_up(Key=i)
                                        for i, target_map in enumerate(TargetMapList)), 
                  key=lambda x: (x.position, x.change, x.target_idx))

def _line_up_iterable(TargetMapList):
    """YIELDS: (begin, end, target_state_setup)

    where 'begin' and 'end' define the interval for which a target state 
    combination is triggered. 
    'target_state_setup[i]' tells where 'TargetMapList[i]' is targetting
    for the given interval.
    """
    line_up = _get_plain_line_up(TargetMapList)

    target_state_setup = [None] * len(TargetMapList)
    last_begin         = None
    for item in line_up:
        if last_begin is not None and last_begin != item.position:
            yield last_begin, item.position, tuple(target_state_setup)
       
        if item.change == E_Border.BEGIN:
            target_state_setup[item.key] = item.target_idx
        else:        # == E_Border.END
            target_state_setup[item.key] = None

        last_begin = item.position

def _enter(result, begin, end, target_state_setup):
    entry = result.get(target_state_setup)
    if entry is None: result[target_state_setup] = NumberSet.from_range(begin, end)
    else:             entry.quick_append_interval(Interval(begin, end))

# NO USES YET: 'MultiOccurrenceNumberList'
# Candidate to support list based-indexing for caches.
# in "DFA.get_elementary_trigger_sets(self, StateIdxList, ...)"
class MultiOccurrenceNumberList(object):
    __slots__ = ("db", "hash_value")

    def __init__(self):
        self.db         = defaultdict(int)
        self.hash_value = 0

    def enter(self, X):
        if X not in self.db:
            self.hash_value ^= X
        else:
            self.db[X] += 1

    def remove(self, X):
        self.db[X] -= 1
        if not self.db[X]:
            self.hash_value ^= X

    def __hash__(self):
        return self.hash_value

    def __eq__(self, Other):
        # Clean self and other.
        for x, occurrence_n in list(self.db.keys()):
            if not occurrence_n: del self.db[x]
            other_occurrence = Other.db.get(x)
            # '0' or 'None'
            if not other_occurrence: return False

        for x, occurrence_n in Other.db.keys():
            if not occurrence_n: continue
            if x not in self.db: return False
        return True
