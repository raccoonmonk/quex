# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.engine.misc.interval_handling             import NumberSet, \
                                                             Interval
from   quex.engine.state_machine.state.target_map_ops import E_Border
from   quex.constants                                 import E_StateIndices
from   quex.blackboard                                import setup as Setup
from   quex.engine.misc.tools                         import typed

from   operator import attrgetter

class TargetMap:
    """Members:

       __db:      map: target index --> NumberSet that triggers to target

       __epsilon_target_index_list: list of target states that are entered via epsilon 
                                    transition.
    """
    def __init__(self, DB=None, ETIL=None):
        if DB is None: self.__db = {}   
        else:          self.__db = DB
        if ETIL is None: self.__epsilon_target_index_list = [] 
        else:            self.__epsilon_target_index_list = ETIL 
        ## OPTIMIZATION OPTION: Store the trigger map in a 'cache' variable. This, however,
        ## requires that all possible changes to the database need to annulate the cache value.
        ## self.__DEBUG_trigger_map = None

    def clone(self, ReplDbStateIndex=None):
        """If 'ReplDbStateIndex' is specified, then only those transitions are cloned
        which appear in the dictionary!
        """
        if ReplDbStateIndex is None:
            db   = dict((tsi, trigger_set.clone()) 
                        for tsi, trigger_set in self.__db.items())
            etil = list(self.__epsilon_target_index_list)
        else:
            db   = dict((ReplDbStateIndex[tsi], trigger_set.clone()) 
                        for tsi, trigger_set in self.__db.items()
                        if tsi in ReplDbStateIndex)
            etil = list(ReplDbStateIndex[tsi] for tsi in self.__epsilon_target_index_list)
        return TargetMap(DB=db, ETIL=etil) 

    def clear(self, TriggerMap=None):
        if TriggerMap is not None:
            assert isinstance(TriggerMap, dict)
            self.__db = TriggerMap
        else:
            # Do not set default value 'TriggerMap={}' since this creates the same
            # default object for all calls of this function.
            self.__db = {}
        self.__epsilon_target_index_list = [] 

    def is_empty(self):
        return not self.__db and not self.__epsilon_target_index_list

    def is_DFA_compliant(self):
        """Checks if the current state transitions are DFA compliant, i.e. it
           investigates if trigger sets pointing to different targets intersect.
           RETURNS:  True  => OK
                    False => Same triggers point to different target. This cannot
                             be part of a deterministic finite automaton (DFA).
        """
        # DFA's do not have epsilon transitions
        if len(self.__epsilon_target_index_list) != 0: return False

        # check whether trigger sets intersect
        all_trigger_sets = NumberSet()
        for trigger_set in self.__db.values():
            if all_trigger_sets.has_intersection(trigger_set): 
                return False
            else:
                all_trigger_sets.unite_with(trigger_set)

        return True

    def add_epsilon_target_state(self, TargetStateIdx):
        if TargetStateIdx not in self.__epsilon_target_index_list:
            self.__epsilon_target_index_list.append(TargetStateIdx)

    def add_transition(self, Trigger, TargetStateIdx): 
        """Adds a transition according to trigger and target index.
           RETURNS: The target state index (may be created newly).
        """
        assert type(TargetStateIdx) == int \
               or TargetStateIdx is None \
               or TargetStateIdx in E_StateIndices, "%s" % TargetStateIdx.__class__.__name__
        assert Trigger.__class__ in (int, int, list, Interval, NumberSet) or Trigger is None

        if Trigger is None: # This is a shorthand to trigger via the remaining triggers
            Trigger = self.get_trigger_set_union().get_complement(Setup.buffer_encoding.source_set)
        elif type(Trigger) == int: Trigger = Interval(int(Trigger), int(Trigger+1))
        elif type(Trigger) == int:  Trigger = Interval(Trigger, Trigger+1)
        elif type(Trigger) == list: Trigger = NumberSet(Trigger, ArgumentIsYoursF=True)

        if Trigger.__class__ == Interval:  
            if TargetStateIdx in self.__db: 
                self.__db[TargetStateIdx].add_interval(Trigger)
            else:
                self.__db[TargetStateIdx] = NumberSet(Trigger, ArgumentIsYoursF=True)
        else:
            if TargetStateIdx in self.__db: 
                self.__db[TargetStateIdx].unite_with(Trigger)
            else:
                self.__db[TargetStateIdx] = Trigger

        return TargetStateIdx

    def delete_transitions_to_target(self, TargetIdx):
        if TargetIdx in self.__db:
            del self.__db[TargetIdx]
        self.delete_epsilon_target_state(TargetIdx)

    def delete_epsilon_target_state(self, TargetStateIdx):
        if TargetStateIdx in self.__epsilon_target_index_list:
            del self.__epsilon_target_index_list[self.__epsilon_target_index_list.index(TargetStateIdx)]

    def delete_transitions_on_empty_trigger_sets(self):
        for target_index, trigger_set in list(self.__db.items()):
            if trigger_set.is_empty(): del self.__db[target_index]

    def get_transition_n(self):
        return len(self.__db)

    def get_trigger_set_union(self):
        interval_list = []
        for trigger_set in self.__db.values():
            interval_list.extend(trigger_set.get_intervals())
        return NumberSet.from_IntervalList(interval_list)

    def get_drop_out_trigger_set_union(self):
        """This function returns the union of all trigger sets that do not
           transit to any target.
        """
        return self.get_trigger_set_union().get_complement(Setup.buffer_encoding.source_set)

    def get_epsilon_target_state_index_list(self):
        return self.__epsilon_target_index_list

    def iterable_target_state_indices(self):
        for state_index in self.__db.keys():
            yield state_index
        for state_index in self.__epsilon_target_index_list:
            yield state_index

    def get_target_state_index_list(self):
        """Union of target states that can be reached either via epsilon transition
           or 'real' transition via character.
        """
        result = set(self.__db.keys())
        result.update(self.__epsilon_target_index_list)
        return list(result)

    def get_resulting_target_state_index(self, Trigger):
        """This function makes sense for DFA's"""
        for target_index, trigger_set in list(self.__db.items()):
            if trigger_set.contains(Trigger): return target_index
        return None

    def get_resulting_target_state_index_list_if_complete(self, Trigger):
        result       = []
        subtractable = None
        for target_index, trigger_set in self.__db.items():
            if trigger_set.has_intersection(Trigger) and target_index not in result:
                result.append(target_index) 
                if not subtractable: subtractable = trigger_set.clone()
                else:                subtractable.unite_with(trigger_set)

        if   subtractable is None and Trigger:  return None
        elif subtractable.is_superset(Trigger): return result # All of 'Trigger' is covered
        else:                                   return None

    def get_resulting_target_state_index_list(self, Trigger):
        result = []
        if Trigger.__class__.__name__ == "NumberSet":
            for target_index, trigger_set in list(self.__db.items()):
                if trigger_set.has_intersection(Trigger) and target_index not in result:
                    result.append(target_index) 

        else:
            for target_index, trigger_set in list(self.__db.items()):
                if trigger_set.contains(Trigger) and target_index not in result:
                    result.append(target_index) 

        if len(self.__epsilon_target_index_list) != 0:
            for target_index in self.__epsilon_target_index_list:
                if target_index not in result:
                    result.append(self.__epsilon_target_index_list)

        return result

    def __iter__(self):
        if self.__db:
            for target_si, trigger_set in self.__db.items():
                yield target_si, trigger_set
        for target_si in self.__epsilon_target_index_list:
            yield target_si, None

    def get_map(self):
        return self.__db

    def update(self, Other):
        self.__db.update(Other.__db)
        self.__epsilon_target_index_list.extend(Other.__epsilon_target_index_list)

    def absorb_target_map(self, Db):
        for ti, trigger_set in Db.items():
            reference = self.__db.get(ti)
            if reference is not None: reference.unite_with(trigger_set)
            else:                     self.__db[ti] = trigger_set.clone()

    def get_trigger_set_line_up(self, Key=None):
        ## WATCH AND SEE THAT WE COULD CACHE HERE AND GAIN A LOT OF SPEED during construction
        ## if self.__dict__.has_key("NONSENSE"): 
        ##    self.NONSENSE += 1
        ##    print "## called", self.NONSENSE
        ## else:
        ##    self.NONSENSE = 1
        """Lines the triggers up on a 'time line'. A target is triggered by
           certain characters that belong to 'set' (trigger sets). Those sets
           are imagined as ranges on a time line. The 'history' is described
           by means of history items. Each item tells whether a range begins
           or ends, and what target state is reached in that range.

           [0, 10] [90, 95] [100, 200] ---> TargetState0
           [20, 89]                    ---> TargetState1
           [96, 99] [201, 205]         ---> TargetState2

           results in a 'history':

           0:  begin of TargetState0
           10: end of   TargetState0
           11: begin of DropOut
           20: begin of TargetState1
           89: end of   TargetState1
           90: begin of TargetState0
           95: end of   TargetState0
           96: begin of TargetState2
           99: end of   TargetState2
           100 ...
           
        """
        # (*) create a 'history', i.e. note down any change on the trigger set combination
        #     (here the alphabet plays the role of a time scale)
                
        history = []
        # NOTE: This function only deals with non-epsilon triggers. Empty
        #       ranges in 'history' are dealt with in '.get_trigger_map()'. 
        for target_idx, trigger_set in self.__db.items():
            interval_list = trigger_set.get_intervals(PromiseToTreatWellF=True)
            for interval in interval_list: 
                # add information about start and end of current interval
                if interval.is_empty(): continue
                history.append(history_item(interval.begin, E_Border.BEGIN, target_idx, Key))
                history.append(history_item(interval.end, E_Border.END, target_idx, Key))

        # (*) sort history according to position
        history.sort(key=attrgetter("position"))

        return history      

    def replace_triggers(self, Db):
        """Db: 
            
                    ScalarValue ---> ReplacementNumberSet

        Whenever a 'ScalarValue' of 'Db' occurs in a trigger set, it
        is replaced by all characters in the 'ReplacementNumberSet'.
        """
        for trigger, replacement_set in Db.items():
            for target_idx, trigger_set in self.__db.items():
                if not trigger_set.contains(trigger): continue
                trigger_set.cut(trigger)
                trigger_set.unite_with(replacement_set)
            
    def replace_target_indices(self, ReplacementDict):
        new_db = {}
        for target_idx, trigger_set in self.__db.items():
            # In case of no entry in the ReplacementDict, then
            # the old target index remains.
            new_idx = ReplacementDict.get(target_idx, target_idx)
            entry = new_db.get(new_idx)
            if entry is not None: entry.unite_with(trigger_set)
            else:                 new_db[new_idx] = trigger_set.clone()

        # By assigning a new_db, the old one is left for garbage collection
        self.__db = new_db

        for i in range(len(self.__epsilon_target_index_list)):
            target_idx     = self.__epsilon_target_index_list[i] 
            new_idx = ReplacementDict.get(target_idx)
            if new_idx is None: continue
            self.__epsilon_target_index_list[i] = new_idx
            
    def minimum(self):
        if not self.__db: return None
        return min(trigger_set.minimum() for trigger_set in self.__db.values())

    def least_greater_bound(self):
        if not self.__db: return None
        return max(trigger_set.least_greater_bound() for trigger_set in self.__db.values())

    @typed(CharCode=(int,int))
    def has_trigger(self, CharCode):
        if self.get_resulting_target_state_index(CharCode) is None: return False
        else:                                                       return True

    @typed(TriggerSet=NumberSet)
    def has_intersection(self, TriggerSet):
        return any(trigger_set.has_intersection(TriggerSet)
                   for trigger_set in self.__db.values())

    def has_target(self, TargetState):
        if TargetState in self.__db:                    return True
        elif TargetState in self.__epsilon_target_index_list: return True
        else:                                                 return False

    def has_one_of_triggers(self, CharacterCodeList):
        assert type(CharacterCodeList) == list
        for code in CharacterCodeList:
            if self.has_trigger(code): return True
        return False

    def get_string(self, FillStr, StateIndexMap, Option="utf8"):
        def state_index_string(StateIndexMap, Si):
            if StateIndexMap is None: 
                return "%05i" % Si
            elif Si in StateIndexMap:                     
                try:    return "%05i" % StateIndexMap[Si]
                except: return "%s" % StateIndexMap[Si]
            else:
                return "((missing %s))" % Si
            
        # print out transitionts
        sorted_transitions = list(self.get_map().items())
        sorted_transitions.sort(key=lambda x: x[1].minimum())

        msg = ""
        # normal state transitions
        for target_state_index, trigger_set in sorted_transitions:
            if Option == "utf8": trigger_str = trigger_set.get_utf8_string()
            else:                trigger_str = trigger_set.get_string(Option)
            target_str = state_index_string(StateIndexMap, target_state_index)
                
            msg += "%s == %s ==> %s\n" % (FillStr, trigger_str, target_str)

        # epsilon transitions
        if len(self.__epsilon_target_index_list) != 0:
            txt_list = [
                state_index_string(StateIndexMap, ti) for ti in self.__epsilon_target_index_list
            ]
            msg += "%s ==<epsilon>==> %s" % (FillStr, ", ".join(txt_list))
        else:
            msg += "%s" % FillStr

        msg += "\n"

        return msg

    def get_graphviz_string(self, OwnStateIdx, StateIndexMap, Option="utf8"):
        assert Option in ("hex", "dec", "utf8")
        sorted_transitions = list(self.get_map().items())
        sorted_transitions.sort(key=lambda x: x[1].minimum())

        msg = ""
        # normal state transitions
        for target_state_index, trigger_set in sorted_transitions:
            if Option == "utf8": trigger_str = trigger_set.get_utf8_string()
            else:                trigger_str = trigger_set.get_string(Option)
            if StateIndexMap is None: target_str  = "%i" % target_state_index
            else:                     target_str  = "%i" % StateIndexMap[target_state_index]
            msg += "%i -> %s [label =\"%s\"];\n" % (OwnStateIdx, target_str, trigger_str.replace("\"", ""))

        # epsilon transitions
        for ti in self.__epsilon_target_index_list:
            if StateIndexMap is None: target_str = "%i" % int(ti) 
            else:                     target_str = "%i" % int(StateIndexMap[ti]) 
            msg += "%i -> %s [label =\"<epsilon>\"];\n" % (OwnStateIdx, target_str)

        # Escape backslashed characters
        return msg.replace("\\", "\\\\")

    def ambiguities_possible(self):
        """RETURNS: False, if ambiguities are not possible!
                    True, if.
        """
        if   self.__epsilon_target_index_list: return True
        elif len(self.__db) == 1:              return False

        trigger_set_list = sorted(iter(self.__db.values()), key=lambda x: x.minimum())
        for i in range(len(trigger_set_list)-1):
            if trigger_set_list[i].least_greater_bound() > trigger_set_list[i+1].minimum():
                return True
        else:
            return False

class history_item(object):
    """To be used by: member function 'get_trigger_set_line_up(self)'
    """
    __slots__ = ('position', 'change', 'target_idx', 'key')
    def __init__(self, Position, ChangeF, TargetIdx, Key=None):
        self.position   = Position
        self.change     = ChangeF
        self.target_idx = TargetIdx 
        self.key        = Key
        
    def __repr__(self):         
        if self.change == E_Border.BEGIN: ChangeStr = "begin"
        else:                             ChangeStr = "end"
        return "%i: %s %s" % (self.position, ChangeStr, self.target_idx)

    def __eq__(self, Other):
        return     self.position   == Other.position \
               and self.change     == Other.change   \
               and self.target_idx == Other.target_idx 
