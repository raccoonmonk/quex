# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.engine.state_machine.state.core        import DFA_State
from   quex.engine.analyzer.door_id_address_label  import DialDB
from   quex.engine.analyzer.state.transition_map         import TransitionMap
from   quex.engine.analyzer.state.entry            import Entry
from   quex.engine.analyzer.state.entry_action     import TransitionAction
from   quex.engine.analyzer.door_id_address_label  import DoorID
from   quex.engine.operations.operation_list       import OpList, Op
from   quex.engine.misc.tools                      import typed
from   quex.blackboard import setup as Setup
from   quex.constants  import E_R, \
                              E_IncidenceIDs, \
                              E_StateIndices

class Processor(object):
    __slots__ = ("_index", "entry")
    def __init__(self, StateIndex, TheEntry=None):
        self._index = StateIndex
        self.entry  = TheEntry
    
    @property
    def index(self):            return self._index

    def set_index(self, Value): assert isinstance(Value, int); self._index = Value

#__________________________________________________________________________
#
# FSM_State:
# 
#                  FSM_State
#                  .--------------------------------------------.
#  .-----.         |                                  .---------|
#  | 341 |--'load'--> Entry  ----->-----.             |tm(input)| 
#  '-----'         |  actions           |             |  'a' ------> 313
#  .-----.         |                    '             |  'c' ------> 142
#  | 412 |--'load'--> Entry  ---> input = *input_p -->|  'p' ------> 721
#  '-----'         |  actions           .             |  'q' ------> 313
#  .-----.         |                    |             |  'x' ------> 472
#  | 765 |--'load'--> Entry  --->-------'             |  'y' ------> 812
#  '-----'         |  actions                         |- - - - -|
#                  |                                  |drop out ---> 
#                  |                                  '---------|
#                  '--------------------------------------------'
#
# The entry actions depend on the state from which the state is entered.
# Next, the input pointer is dereferenced and 'input' is assigned. Based
# on the value of 'input' a subsequent state is targetted. The relation
# between 'input' and the target state is given by the 'TransitionMap'.
# If no state transition is possible, then 'drop out actions' are executed.
#__________________________________________________________________________
class FSM_State(Processor):
    __slots__ = ("map_target_index_to_character_set", 
                 "transition_map") 

    @typed(StateIndex=(int,int), TheTransitionMap=TransitionMap, dial_db=DialDB)
    def __init__(self, StateIndex, TheTransitionMap, dial_db):
        # Empty transition maps are reported as 'None'
        Processor.__init__(self, StateIndex, Entry(dial_db))
        self.map_target_index_to_character_set = None
        self.transition_map                    = TheTransitionMap

    @staticmethod
    def from_LinearState(S):
        assert False, "Currently Unused"
        #if EntryRecipe is not None:
        #    self.entry.enter_OpList(S.entry_transition_id,
        #                            S.recipe.get_entry_OpList())
        #self.on_drop_out = Recipe.get_drop_out_OpList()

    @staticmethod
    def from_MouthState(S):
        assert False, "Currently Unused"
        #for transition_id, recipe in S.entry_db.iteritems():
        #    self.entry.enter_OpList(transition_id,
        #                                 recipe.get_entry_OpList())
        #self.on_drop_out = S.recipe.get_drop_out_OpList()

    @staticmethod
    def from_State(SM_State, StateIndex, EngineType, dial_db):
        assert isinstance(SM_State, DFA_State)
        assert SM_State.target_map.is_DFA_compliant()
        assert isinstance(StateIndex, int)

        x = FSM_State(StateIndex, TransitionMap.from_TargetMap(SM_State.target_map), dial_db)

        # (*) Transition
        # Currently, the following is only used for path compression. If the alternative
        # is implemented, then the following is no longer necessary.
        x.map_target_index_to_character_set = SM_State.target_map.get_map()

        return x

    def prepare_for_reload(self, TheAnalyzer, BeforeReloadOpList=None, 
                           AfterReloadOpList=None, 
                           OnFailureDoorId=None):
        """Prepares state for reload. Reload procedure

            .- State 'X' ---.               
            |               |                .-- Reloader------. 
            | BUFFER LIMIT  |              .----------------.  |
            | CODE detected ------->-------| Door from X:   |  |
            |               |              | Actions before |  |
            |               |              | reload.        |  |
            |               |              '----------------'  |
            |               |                |        |        |
            |               |                |  reload buffer> |
            |    .----------------.          |        |        |
            |    | Door for       |---<-------(good)--*        |
            |    | RELOAD SUCCESS:|          |        |        |
            |    | Actions after  |          |      (bad)      |
            |    | Reload.        |          '------- |--------'
            |    '----------------'                   |
            |               |                .----------------.
            '---------------'                | Door for       |
                                             | RELOAD FAILURE |
                                             '----------------'
                                   
        (1) Create 'Door for RELOAD SUCCESS'. 
        (2) Determine 'Door for RELOAD FAILURE'.
        (3) Create 'Door from X' in Reloader.
        (4) Adapt state X's transition map, so that:
              BUFFER LIMIT CODE --> reload procedure.
        """
        assert self.transition_map is not None
        assert BeforeReloadOpList is None or isinstance(BeforeReloadOpList, OpList)
        assert AfterReloadOpList  is None or isinstance(AfterReloadOpList, OpList)

        if not TheAnalyzer.engine_type.subject_to_reload():
            # Engine type does not require reload => no reload. 
            return

        elif self.transition_map.is_only_drop_out():
            # If the state drops out anyway, then there is no need to reload.
            # -- The transition map is not adapted.
            # -- The reloader is not instrumented to reload for that state.
            return                      

        assert self.index in TheAnalyzer.state_db
        reload_state = TheAnalyzer.reload_state
        assert reload_state.index in (E_StateIndices.RELOAD_FORWARD, 
                                      E_StateIndices.RELOAD_BACKWARD)

        # (1) Door for RELOAD SUCCESS
        #
        after_cl = []
        if AfterReloadOpList is not None:
            after_cl.extend(AfterReloadOpList)
        after_cl.append(Op.InputPDereference())

        self.entry.enter_OpList(self.index, reload_state.index, OpList.from_iterable(after_cl))
        self.entry.categorize(self.index) # Categorize => DoorID is available.
        on_success_door_id = self.entry.get_door_id(self.index, reload_state.index)

        # (2) Determine Door for RELOAD FAILURE
        #
        if OnFailureDoorId:
            on_failure_door_id = OnFailureDoorId
        elif TheAnalyzer.is_init_state_forward(self.index):
            on_failure_door_id = DoorID.incidence(E_IncidenceIDs.END_OF_STREAM, 
                                                  self.entry.dial_db)
        else:
            on_failure_door_id = TheAnalyzer.drop_out_DoorID(self.index)
            if on_failure_door_id is None:
                on_failure_door_id = DoorID.incidence(E_IncidenceIDs.END_OF_STREAM, 
                                                      self.entry.dial_db)

        # (*) 'before_reload_op_list' checks whether the input pointer really stands
        #     on a border. If not transition target of 'buffer_limit_code' is entered.
        before_reload_op_list = self.handle_transition_on_buffer_limit_code(TheAnalyzer.engine_type.is_FORWARD(), 
                                                                            BeforeReloadOpList)

        # (3) Create 'Door from X' in Reloader
        assert on_failure_door_id != on_success_door_id
        reload_door_id = reload_state.add_state(self.index, 
                                                on_success_door_id, 
                                                on_failure_door_id, 
                                                before_reload_op_list)
        
        # (4) Adapt transition map: BUFFER LIMIT CODE --> reload_door_id
        #
        self.transition_map.set_target(Setup.buffer_limit_code, reload_door_id)
        return

    def handle_transition_on_buffer_limit_code(self, ForwardF, BeforeReloadOpList):
        """If there is a state transition to another state on the buffer limit code,
        then only transition to reload state, if the input pointer really stands on
        the border (buffer front or end of stream).

        RETURNS: New 'before_reload_op_list'
        """
        target_door_id = self.transition_map.get_target(Setup.buffer_limit_code)
        if not target_door_id: return BeforeReloadOpList

        if ForwardF: border_p = E_R.EndOfStreamP
        else:        border_p = E_R.BufferFrontP

        if not BeforeReloadOpList: result = []
        else:                      result = list(BeforeReloadOpList)
        result.insert(0, Op.GotoDoorIdIfInputPNotEqualPointer(target_door_id, border_p))
        return OpList.from_iterable(result)

    def get_string_array(self, InputF=True, EntryF=True, TransitionMapF=True, DropOutF=True):
        txt = [ "State %s:\n" % repr(self.index).replace("L", "") ]
        # if InputF:         txt.append("  .input: move position %s\n" % repr(self.input))
        if EntryF:         txt.append("  .entry:\n"); txt.append(repr(self.entry))
        if TransitionMapF: 
            txt.append(" -- .transition_map:\n")
            txt.extend(
                "    %s: %s\n" % (number_set, target_door_id)
                for number_set, target_door_id in self.transition_map
            )
        else:
            pass # txt.append("  .transition_map:\n")
        txt.append("\n")
        return txt

    def get_string(self, InputF=True, EntryF=True, TransitionMapF=True, DropOutF=True):
        return "".join(self.get_string_array(InputF, EntryF, TransitionMapF, DropOutF))

    def __repr__(self):
        return self.get_string()

#__________________________________________________________________________
#
# ReloadState:
#                  .--------------------------------------------.
#  .-----.         |                                            |
#  | 341 |--'load'--> S = 341;                                  |
#  '-----'         |  F = DropOut(341); --.            .----------> goto S
#  .-----.         |                      |           / success |
#  | 412 |--'load'--> S = 412;            |          /          |
#  '-----'         |  F = DropOut(412); --+--> Reload           |
#  .-----.         |                      |          \          |
#  | 765 |--'load'--> S = 765;            |           \ failure |
#  '-----'         |  F = DropOut(765); --'            '----------> goto F
#                  |                                            |
#                  '--------------------------------------------'
# 
# The entry of the reload state sets two variables: The address where to
# go if the reload was successful and the address where to go in case that
# the reload fails. 
#__________________________________________________________________________
class ReloadState(Processor):
    @typed(dial_db=DialDB)
    def __init__(self, EngineType, dial_db):
        if EngineType.is_FORWARD(): index = E_StateIndices.RELOAD_FORWARD
        else:                       index = E_StateIndices.RELOAD_BACKWARD
        Processor.__init__(self, index, Entry(dial_db))
        self.engine_type = EngineType
        self.dial_db     = dial_db

    def absorb(self, OtherReloadState):
        # Do not absorb RELOAD_FORWARD into RELOAD_BACKWARD, and vice versa.
        assert self.index == OtherReloadState.index
        self.entry.absorb(OtherReloadState.entry)

    @typed(StateIndex=(int,int), OnSuccessDoorId=DoorID, OnFailureDoorId=DoorID)
    def add_state(self, StateIndex, OnSuccessDoorId, OnFailureDoorId, BeforeReload=None):
        """Adds a state from where the reload state is entered. When reload is
        done it jumps to 'OnFailureDoorId' if the reload failed and to 'OnSuccessDoorId'
        if the reload succeeded.

        RETURNS: DoorID into the reload state. Jump to this DoorID in order
                 to trigger the reload for the state given by 'StateIndex'.
        """
        assert BeforeReload is None or isinstance(BeforeReload, OpList) 
        # Before reload: prepare after reload, the jump back to the reloading state.
        before_cl = OpList(Op.PrepareAfterReload(OnSuccessDoorId, OnFailureDoorId))
        if BeforeReload is not None:
            # May be, add additional commands
            before_cl = OpList.concatinate(before_cl, BeforeReload)

        # No two transitions into the reload state have the same OpList!
        # No two transitions can have the same DoorID!
        # => it is safe to assign a new DoorID withouth .categorize()
        ta         = TransitionAction(before_cl)
        # Assign a DoorID (without categorization) knowing that no such entry
        # into this state existed before.
        ta.door_id = self.dial_db.new_door_id(self.index)

        assert not self.entry.has_transition(self.index, StateIndex) # Cannot be in there twice!
        self.entry.enter(self.index, StateIndex, ta)

        return ta.door_id

    def add_mega_state(self, MegaStateIndex, StateKeyRegister, Iterable_StateKey_Index_Pairs, 
                       TheAnalyzer):
        """Implement a router from the MegaState-s door into the Reloader to
        the doors of the implemented states. 
        
                        Reload State
                       .--------------------------------- - -  -
                     .--------------.    on state-key
          reload --->| MegaState's  |       .---.
                     | Reload Door  |------>| 0 |-----> Reload Door of state[0]
                     '--------------'       | 1 |-----> Reload Door of state[1]
                       |                    | : |
                       :                    '---'
                       '--------------------------------- - -  -

        """
        def DoorID_provider(state_index):
            door_id = self.entry.get_door_id(self.index, state_index)
            if door_id is None:
                # The state implemented in the MegaState did not have a 
                # transition to 'ReloadState'. Thus, it was a total drop-out.
                # => Route to the state's drop-out.
                door_id = TheAnalyzer.drop_out_DoorID(state_index)
            return door_id

        cmd = Op.RouterOnStateKey(
            StateKeyRegister, MegaStateIndex,
            Iterable_StateKey_Index_Pairs,
            DoorID_provider
        )

        ta         = TransitionAction(OpList(cmd))
        # Assign a DoorID (without categorization) knowing that no such entry
        # into this state existed before.
        ta.door_id = self.dial_db.new_door_id(self.index)

        assert not self.entry.has_transition(self.index, MegaStateIndex) # Cannot be in there twice!
        self.entry.enter(self.index, MegaStateIndex, ta)

        return ta.door_id

