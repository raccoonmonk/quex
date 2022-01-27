# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
"""
_______________________________________________________________________________

PURPOSE: Reduction of run-time effort of the lexical analyzer. 

Acceptance and input position storages may be spared depending on the paths of
the state machine graph. 
_______________________________________________________________________________
EXPLANATION:

Formally an FSM consists of a set of states that are related by their
transitions. Each state is an object of class FSM_State and has the following
components:

    * entry:          actions to be performed at the entry of the state.

    * input:          what happens to get the next character.

    * transition_map: a map that tells what state is to be entered 
                      as a reaction to the current input character.

There's global 'drop-out' state which has entries from each state. The entries
of the 'drop-out' state inhibit the operations upon drop-out of each state.

_______________________________________________________________________________
(C) 2010-2019 Frank-Rene Schaefer
ABSOLUTELY NO WARRANTY
_______________________________________________________________________________
"""
from   quex.engine.analyzer.state.entry             import Entry
from   quex.engine.analyzer.state.core              import Processor, \
                                                           FSM_State
from   quex.engine.analyzer.state.entry_action      import TransitionAction
from   quex.engine.operations.operation_list        import Op, \
                                                           OpList

from   quex.engine.state_machine.core               import DFA
from   quex.engine.state_machine.state.single_entry import SeAccept      

from   quex.engine.misc.tools                       import typed
from   quex.constants   import E_Op, \
                               E_R, \
                               E_StateIndices

import itertools
from   operator         import itemgetter

class FSM:
    """A 'FSM', in Quex-Lingo, is a finite state automaton where entries 
    from different transitions are each associated with dedicated actions.

                  events
           ...   ----->---[ Action 0 ]---.               .--->   ...
                                          \     .-----.-'
           ...   ----->---[ Action 1 ]-----+---( State )----->   ...
                                          /     '-----'
           ...   ----->---[ Action 2 ]---'        

    A 'FSM' must be considered in contrast to a 'DFA', a finite state machine
    where all transitions into a state trigger the same action.
    """
    def __init__(self, EngineType, InitStateIndex, dial_db):
        self.__engine_type      = EngineType
        self.__init_state_index = InitStateIndex
        self.__state_db         = {}
        self.__state_machine_id = None
        self.dial_db            = dial_db
        self.drop_out           = Processor(E_StateIndices.DROP_OUT, Entry(self.dial_db))

    @typed(SM=DFA, OnBeforeEntry=OpList)
    def _prepare_states(self, SM, OnBeforeEntry):
        self.__acceptance_state_index_list = SM.acceptance_state_index_list()
        self.__state_machine_id            = SM.get_id()

        # (*) From/To Databases
        #
        #     from_db:  state_index --> states from which it is entered.
        #     to_db:    state_index --> states which it enters
        #
        self._to_db   = SM.get_to_db()
        self._from_db = SM.get_from_db()

        # (*) Prepare FSM_State Objects
        self.__state_db.update(
            (state_index, self.prepare_state(state, state_index, OnBeforeEntry))
            for state_index, state in sorted(iter(SM.states.items()), key=itemgetter(0))
        )

        self.__mega_state_list          = []
        self.__non_mega_state_index_set = set(state_index for state_index in SM.states.keys())

    def add_mega_states(self, MegaStateList):
        """Add MegaState-s into the analyzer and remove the states which are 
        represented by them.
        """
        for mega_state in MegaStateList:
            state_index_set = mega_state.implemented_state_index_set()
            for state_index in state_index_set:
                self.remove_state(state_index)

        self.__mega_state_list          = MegaStateList
        self.__non_mega_state_index_set = set(self.__state_db.keys())

        self.__state_db.update(
           (mega_state.index, mega_state) for mega_state in MegaStateList
        )

    def remove_state(self, StateIndex):
        if StateIndex in self.__non_mega_state_index_set:
            self.__non_mega_state_index_set.remove(StateIndex)
        self.__state_db.pop(StateIndex)

    @property
    def mega_state_list(self):             return self.__mega_state_list
    @property
    def non_mega_state_index_set(self):    return self.__non_mega_state_index_set
    @property
    def state_brief_db_for_printing(self): return self._state_brief_db_for_printing
    @property
    def state_db(self):                    return self.__state_db
    @property
    def init_state_index(self):            return self.__init_state_index
    @property
    def position_register_map(self):       return self._position_register_map
    @property
    def state_machine_id(self):            return self.__state_machine_id
    @property
    def engine_type(self):                 return self.__engine_type
    @property
    def to_db(self):
        """Map: state_index --> list of states which can be reached starting from state_index."""
        return self._to_db
    @property
    def from_db(self):
        """Map: state_index --> list of states which which lie on a path to state_index."""
        return self._from_db

    def iterable_target_state_indices(self, StateIndex):
        for i in sorted(self.__state_db[StateIndex].map_target_index_to_character_set.keys()):
            yield i
        yield None

    @typed(OnBeforeEntry=OpList)
    def prepare_state(self, OldState, StateIndex, OnBeforeEntry):
        """Prepares states to increment the input/read pointer and dereferences it
        to access the lexatom for the state transition triggering.
        
        REQUIRES: 'self.init_state_forward_f', 'self.engine_type', 'self._from_db'.
        """
        state = FSM_State.from_State(OldState, StateIndex, self.engine_type, 
                                     self.dial_db)

        cmd_list = []
        if self.engine_type.is_BACKWARD_PRE_CONTEXT():
            cmd_list.extend(
                 Op.PreContextOK(cmd.acceptance_id()) 
                 for cmd in OldState.single_entry.get_iterable(SeAccept)
            )

        if self.engine_type.is_FORWARD(): cmd_list.append(Op.Increment(E_R.InputP))
        else:                             cmd_list.append(Op.Decrement(E_R.InputP))

        if state.transition_map is None and False: 
            # NOTE: We need a way to disable this exception for PathWalkerState-s(!)
            #       It's safe, not to allow it, in general.
            #------------------------------------------------------------------------
            # If the state has no further transitions then the input character does 
            # not have to be read. This is so, since without a transition map, the 
            # state immediately drops out. The drop out transits to a terminal. 
            # Then, the next action will happen from the init state where we work
            # on the same position. If required the reload happens at that moment,
            # NOT before the empty transition block.
            #
            # This is not true for Path Walker States, so we offer the option 
            # 'ForceInputDereferencingF'
            assert StateIndex != self.init_state_index # Empty state machine! --> impossible

        else:
            cmd_list.append(Op.InputPDereference())

        ta = TransitionAction(OpList.from_iterable(cmd_list))

        # NOTE: The 'from reload transition' is implemented by 'prepare_for_reload()'
        for source_state_index in self._from_db[StateIndex]: 
            assert source_state_index != E_StateIndices.BEFORE_ENTRY
            state.entry.enter(StateIndex, source_state_index, ta.clone())

        if StateIndex == self.init_state_index:
            if self.engine_type.is_FORWARD():
                on_entry_op_list = OnBeforeEntry.clone()
                on_entry_op_list.append(Op.InputPDereference())
                ta = TransitionAction(on_entry_op_list)
            state.entry.enter_state_machine_entry(self.__state_machine_id, 
                                                  StateIndex, ta)

        return state

    def prepare_DoorIDs(self):
        """Assign DoorID-s to transition actions and relate transitions to DoorID-s.
        """
        for si, state in sorted(iter(self.__state_db.items()), key=itemgetter(0)):
            state.entry.categorize(state.index)

        self.drop_out.entry.categorize(E_StateIndices.DROP_OUT)

        for si, state in sorted(iter(self.__state_db.items()), key=itemgetter(0)):
            assert state.transition_map is not None
            state.transition_map = state.transition_map.relate_to_DoorIDs(self, state.index)

        return 

    def drop_out_DoorID(self, StateIndex):
        """RETURNS: DoorID of the drop-out catcher for the state of the given
                    'StateIndex'
                    None -- if there is no drop out for the given state.
        """
        drop_out_door_id = self.drop_out.entry.get_door_id(E_StateIndices.DROP_OUT, StateIndex)
        #assert drop_out_door_id is not None
        return drop_out_door_id
                                      
    def init_state(self):
        return self.state_db[self.init_state_index]

    def get_depth_db(self):
        """Determine a database which tells about the minimum distance to the initial state.

            map: state_index ---> min. number of transitions from the initial state.

        """
        depth_db = { self.__init_state_index: 0, }

        work_set   = set(self.__state_db.keys())
        work_set.remove(self.__init_state_index)
        last_level = set([ self.__init_state_index ])
        level_it   = itertools.count(start=1)
        while len(work_set):
            level_i    = next(level_it)
            len_before = len(work_set)
            this_level = set()
            for state_index in last_level:
                for i in self.iterable_target_state_indices(state_index):
                    if   i not in work_set: continue
                    elif i in depth_db:     continue 
                    depth_db[i] = level_i
                    this_level.add(i)
                    work_set.remove(i)
            assert len_before != len(work_set), "There are orphaned states!" 
            last_level = this_level

        return depth_db

    def last_acceptance_variable_required(self):
        """If one entry stores the last_acceptance, then the 
           correspondent variable is required to be defined.
        """
        if not self.__engine_type.is_FORWARD(): 
            return False
        for entry in map(lambda x: x.entry, iter(self.__state_db.values())):
            if entry.has_command(E_Op.Accepter): return True
        return False

    def is_init_state_forward(self, StateIndex):
        return StateIndex == self.init_state_index and self.engine_type.is_FORWARD()     
                
    def __iter__(self):
        for x in list(self.__state_db.values()):
            yield x

    def __repr__(self):
        # Provide some type of order that is oriented towards the content of the states.
        # This helps to compare analyzers where the state identifiers differ, but the
        # states should be the same.
        def order(X):
            side_info = 0
            if len(X.transition_map) != 0: 
                side_info = max(trigger_set.size() for trigger_set, t in X.transition_map)
            return (len(X.transition_map), side_info, X.index)

        txt = [ repr(state) for state in sorted(iter(self.__state_db.values()), key=order) ]
        return "".join(txt)

