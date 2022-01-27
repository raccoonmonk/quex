# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
"""PURPOSE: Reduction of run-time effort of the lexical analyzer. 

Acceptance and input position storages may be spared depending on the paths of
the state machine graph. 

(C) 2015-2019 Frank-Rene Schaefer
_______________________________________________________________________________
"""
from   quex.engine.analyzer.door_id_address_label   import DialDB
import quex.engine.analyzer.trace_analysis.core                    as trace_analysis
import quex.engine.analyzer.trace_analysis.position_register_map   as position_register_map
from   quex.engine.analyzer.core                    import FSM
from   quex.engine.analyzer.state.core              import ReloadState
import quex.engine.operations.operation_list_on_drop_out  as operation_list_on_drop_out
from   quex.engine.operations.se_operations         import SeAccept, \
                                                           SeStoreInputPosition
from   quex.engine.operations.operation_list        import Op, \
                                                           OpList
import quex.engine.analyzer.mega_state.analyzer     as     mega_state_analyzer
import quex.engine.analyzer.engine_supply_factory   as     engine
import quex.engine.state_machine.construction.combination as     combination

from   quex.engine.state_machine.core               import DFA
import quex.engine.state_machine.algebra.reverse    as     reverse
import quex.engine.misc.error                       as     error

from   quex.engine.misc.tools                       import typed
import quex.output.transform_to_encoding            as     transform_to_encoding

from   quex.blackboard  import setup as Setup, \
                               signal_lexatoms
from   quex.constants   import E_StateIndices, \
                               E_TransitionN
from   operator         import itemgetter

@typed(dial_db=DialDB)
def do(SmOrSmList, EngineType=engine.FORWARD, 
       ReloadStateExtern=None, OnBeforeReload=None, OnAfterReload=None, 
       OnBeforeEntry=None, dial_db=None, OnReloadFailureDoorId=None, CutF=True, 
       ReverseF=False, StateMachineId=None, AlllowInitStateAcceptF=False, TraceAnalysisF=True,
       ReturnStateIndicesOfUntransformedSmF=False):

    assert dial_db is not None
    assert not ReturnStateIndicesOfUntransformedSmF or not ReverseF

    SM, state_indices_of_untransformed_sm = _prepare(SmOrSmList, 
                                                     StateMachineId, 
                                                     ReverseF, 
                                                     AlllowInitStateAcceptF, 
                                                     CutF)

    # Generate FSM from DFA
    analyzer = FSM_Builder.do(SM, EngineType, ReloadStateExtern, 
                              OnBeforeEntry, dial_db=dial_db, 
                              TraceAnalysisF=TraceAnalysisF, 
                              OptimizeF=True,
                              PrepareReloadF=True,
                              OnBeforeReload=OnBeforeReload,
                              OnAfterReload=OnAfterReload,
                              OnReloadFailureDoorId=OnReloadFailureDoorId)

    # FSM_State.transition_map:        Interval --> DoorID
    # MegaState.transition_map:        Interval --> TargetByStateKey
    #                               or Interval --> DoorID
    if ReturnStateIndicesOfUntransformedSmF:
        return analyzer, state_indices_of_untransformed_sm
    else:
        return analyzer

class FSM_Builder:
    def __init__(self, SM, EngineType, dial_db):
        self.__r = FSM(EngineType, SM.init_state_index, dial_db)

    @classmethod
    @typed(SM=DFA, EngineType=engine.Base, OnBeforeEntry=(OpList, None))
    def do(cls, SM, EngineType, ReloadStateExtern=None, OnBeforeEntry=None, dial_db=None, 
           TraceAnalysisF=True, OptimizeF=False, PrepareReloadF=False, OnBeforeReload=None, 
           OnAfterReload=None, OnReloadFailureDoorId=None):
        """ReloadStateExtern is only to be specified if the analyzer needs
        to be embedded in another one.
        """
        builder = cls(SM, EngineType, dial_db) \
           .analyse_and_prepare_state_entries_and_drop_outs(SM, EngineType, OnBeforeEntry, TraceAnalysisF) 

        if OptimizeF:
           builder.optimize() 

        if PrepareReloadF:
           builder.prepare_reload(EngineType, ReloadStateExtern, OnBeforeReload, OnAfterReload, OnReloadFailureDoorId) 

        if Setup.compression_type_list: 
           builder.find_and_construct_mega_states()

        return builder.result

    @property
    def result(self):
        return self.__r

    def analyse_and_prepare_state_entries_and_drop_outs(self, SM, EngineType, OnBeforeEntry=None, TraceAnalysisF=True):
        if OnBeforeEntry is None: OnBeforeEntry = OpList()

        result = self.__r
        result._prepare_states(SM, OnBeforeEntry)
        result._position_register_map = None

        if   EngineType.is_BACKWARD_INPUT_POSITION():
            self.__prepare_entries_and_drop_out_without_position_recovery(EngineType, SM,
                                                 operation_list_on_drop_out.do_backward_input_position_detection)
        elif EngineType.is_BACKWARD_PRE_CONTEXT():
            self.__prepare_entries_and_drop_out_without_position_recovery(EngineType, SM,
                                                 operation_list_on_drop_out.do_backward_pre_context)
        elif TraceAnalysisF:
            state_info_db = trace_analysis.do(SM, result._to_db)
            self.__prepare_entries_and_drop_out(EngineType, state_info_db)
            # (*) Position Register Map (Used in 'optimizer.py')
            if EngineType.requires_position_register_map():
                result._position_register_map = position_register_map.do(state_info_db)

        else:
            self.__prepare_drop_outs_directly(EngineType, SM)
            self.__prepare_entries_directly(EngineType, SM)
            result._position_register_map = position_register_map.pseudo(SM)

        return self

    def optimize(self):
        """Use information about position storage registers that can be shared.
           Replace old register values with new ones.
        """
        result = self.__r
        for state in result.state_db.values():
            state.entry.replace_position_registers(result.position_register_map)
            state.entry.delete_superfluous_commands()

        result.drop_out.entry.replace_position_registers(result.position_register_map)
        return self

    def prepare_reload(self, EngineType, ReloadStateExtern, OnBeforeReload, OnAfterReload, OnReloadFailureDoorId):
        result = self.__r
        self._prepare_reload_state(ReloadStateExtern, EngineType)

        # DoorID-s required by '.prepare_for_reload()'
        result.prepare_DoorIDs()

        # Prepare the reload BEFORE mega state compression!
        # (Null-operation, in case no reload required.)
        # TransitionMap:              On BufferLimitCode --> ReloadState
        # ReloadState.door of state:  OnBeforeReload
        #                             prepare goto on reload success and reload fail
        # State.door of ReloadState:  OnAfterReload (when reload was a success).
        for si, state in sorted(iter(result.state_db.items()), key=itemgetter(0)):
            # Null-operation, in case no reload required.
            state.prepare_for_reload(result, OnBeforeReload, OnAfterReload,
                                     OnFailureDoorId=OnReloadFailureDoorId) 
        return self

    def _prepare_reload_state(self, ReloadStateExtern, EngineType):
        result = self.__r
        if ReloadStateExtern is None:
            result.reload_state          = ReloadState(EngineType=EngineType, dial_db=result.dial_db)
            result.reload_state_extern_f = False
        else:
            result.reload_state          = ReloadStateExtern
            result.reload_state_extern_f = True

    def __prepare_entries_and_drop_out_without_position_recovery(self, EngineType, SM, _getCmdListOnDropOut):
        """ATTENTION: This only works, if no input position need to be stored at any time.

        """
        result = self.__r
        if hasattr(EngineType, "bipd_incidence_id"): bipd_incidence_id = EngineType.bipd_incidence_id()
        else:                                        bipd_incidence_id = None

        for state_index, state in sorted(iter(SM.states.items()), key=itemgetter(0)):
            if not result.state_db[state_index].transition_map.has_drop_out(): continue
            result.drop_out.entry.enter_OpList(E_StateIndices.DROP_OUT, 
                                             state_index, 
                                             _getCmdListOnDropOut(state, result.dial_db, bipd_incidence_id))
                                                  
        result._position_register_map = None

    def __prepare_entries_directly(self, EngineType, SM):
        result = self.__r

        for si, state in SM.states.items():
            entry = result.state_db[si].entry
            for cmd in state.single_entry.get_iterable(SeAccept):
                entry.add_Accepter_on_all(cmd.acceptance_condition_set(), 
                                          cmd.acceptance_id())
                if not cmd.restore_position_register_f():
                    entry.add_StoreInputPosition_on_all(AccConditionSet  = cmd.acceptance_condition_set(),
                                                        PositionRegister = cmd.acceptance_id(), 
                                                        Offset           = -1)

            for cmd in state.single_entry.get_iterable(SeStoreInputPosition):
                entry.add_StoreInputPosition_on_all(AccConditionSet  = cmd.acceptance_condition_set(),
                                                    PositionRegister = cmd.acceptance_id(), 
                                                    Offset           = -1)

    def __prepare_drop_outs_directly(self, EngineType, SM):
        result = self.__r

        # Upon drop-out: restore position of acceptance and goto terminal
        # If acceptance, restore position, goto terminal
        # UNIFORM Acceptance scheme for all paths through the state.
        #     -- Apply the uniform accepter. 
        #     -- No related state needs to store acceptance.
        general_terminal_router = Op.RouterByLastAcceptance()
        for acceptance_id in SM.acceptance_id_set():
            general_terminal_router.content.add(acceptance_id, E_TransitionN.VOID)
        general_cmd_list = operation_list_on_drop_out.do(None, general_terminal_router)

        # Let all states use the same terminal router for drop-out
        for si in SM.states:
            result.drop_out.entry.enter_OpList(E_StateIndices.DROP_OUT, si, 
                                               general_cmd_list.clone())

    def __prepare_entries_and_drop_out(self, EngineType, state_info_db):
        """This is the 'heart' of the whole analysis.
        """
        result = self.__r
        # (*) Drop Out Behavior
        #     The PathTrace objects tell what to do at drop_out. From this, the
        #     required entry actions of states can be derived.
        self._configure_all_drop_outs(state_info_db)

        # (*) Entry Behavior
        #     Implement the required entry actions.
        self._configure_all_entries(state_info_db) 

        # TODO: This belongs into the 'builder'
        result._state_brief_db_for_printing = state_info_db

    def _configure_all_drop_outs(self, state_info_db):
        result = self.__r
        for si, state_info in sorted(iter(state_info_db.items()), key=itemgetter(0)):
            if not result.state_db[si].transition_map.has_drop_out(): continue

            op_list = self._drop_out_configure(si, state_info, 
                                              state_info_db.acceptance_condition_db)
            result.drop_out.entry.enter_OpList(E_StateIndices.DROP_OUT, si, op_list)
        
    def _drop_out_configure(self, StateIndex, state_brief, acceptance_condition_db):
        """____________________________________________________________________
        Every analysis step ends with a 'drop-out'. At this moment it is
        decided what pattern has won. Also, the input position pointer must be
        set so that it indicates the right location where the next step starts
        the analysis. 

        Consequently, a drop-out action contains two elements:

         -- Acceptance: Either the winning pattern's acceptance id is determined
            from the state machine's graph, or it is given by the setting of
            variable 'last_acceptance' (as set by the accepting state). 

         -- Terminal Router: Modify input position for next analysis step and
            goto terminal correspondent to the winning pattern (by acceptance_id).
        _______________________________________________________________________
        """
        if state_brief.restore.acceptance_sequence is not None:
            # UNIFORM Acceptance scheme for all paths through the state.
            #     -- Apply the uniform accepter. 
            #     -- No related state needs to store acceptance.
            accepter = Op.Accepter() 
            accepter.content.absorb((acceptance_condition_db[acceptance_id], acceptance_id) 
                                    for acceptance_id in state_brief.restore.acceptance_sequence) 
        else:
            # NON-UNIFORM: Different paths result in different acceptances schemes.
            # -- The acceptance must be stored in the state where it occurs, 
            # -- It must be restored in 'this' state.
            accepter = None # Only rely on 'last_acceptance' being stored.

        # (*) Terminal Router
        terminal_router = Op.RouterByLastAcceptance()
        for acceptance_id, restore_brief in state_brief.restore.position_db.items():
            terminal_router.content.add(acceptance_id, 
                                        restore_brief.transition_n_since_positioning)

        return operation_list_on_drop_out.do(accepter, terminal_router)

    def _configure_all_entries(self, state_info_db):
        """DropOut objects may rely on acceptances and input positions being 
           stored. This storage happens at state entries.
           
           Function 'drop_out_configure()' registers which states have to store
           the input position and which ones have to store acceptances. These
           tasks are specified in the two members:

                 require_acceptance_storage_db
                 position_storage_db

           It is tried to postpone the storing as much as possible along the
           state paths from store to restore. Thus, some states may not have to
           store, and thus the lexical analyzer becomes a little faster.
        """
        self._implement_required_acceptance_storage(state_info_db)
        self._implement_required_position_storage(state_info_db)

    def _implement_required_acceptance_storage(self, state_info_db):
        """
        Storing Acceptance / Postpone as much as possible.
        
        The stored 'last_acceptance' is only needed at the first time
        when it is restored. So, we could walk along the path from the 
        accepting state to the end of the path and see when this happens.
        
        Critical case:
        
          State V --- "acceptance = A" -->-.
                                            \
                                             State Y ----->  State Z
                                            /
          State W --- "acceptance = B" -->-'
        
        That is, if state Y is entered from state V is shall store 'A'
        as accepted, if it is entered from state W is shall store 'B'.
        In this case, we cannot walk the path further, and say that when
        state Z is entered it has to store 'A'. This would cancel the
        possibility of having 'B' accepted here. There is good news:
        
        ! During the 'drop_out_configure()' the last acceptance is restored    !
        ! if and only if there are at least two paths with differing           !
        ! acceptance patterns. Thus, it is sufficient to consider the restore  !
        ! of acceptance in the drop_out as a terminal condition.               !

        EXCEPTION:

        When a state is reached that is part of '__dangerous_positioning_state_set'
        then it is not safe to assume that all sub-paths have been considered.
        The acceptance must be stored immediately.
        """
        result = self.__r
        # Not Postponed: Collected acceptances to be stored in the acceptance states itself.
        #
        # Here, storing Acceptance cannot be deferred to subsequent states, because
        # the first state that restores acceptance is the acceptance state itself.
        #
        # (1) Restore only happens if there is non-uniform acceptance. See 
        #     function 'drop_out_configure(...)'. 
        # (2) Non-uniform acceptance only happens, if there are multiple paths
        #     to the same state with different trailing acceptances.
        # (3) If there was an absolute acceptance, then all previous trailing 
        #     acceptance were deleted (longest match). This contradicts (2).
        #
        # (4) => Thus, there are only pre-contexted acceptances in such a state.
        #
        # It is possible that a deferred acceptance are already present in the doors. But, 
        # since they all come from trailing acceptances, we know that the acceptance of
        # this state preceeds (longest match). Thus, all the acceptances we add here 
        # preceed the already mentioned ones. Since they all trigger on lexemes of the
        # same length, the only precendence criteria is the acceptance_id.
        # 
        for si, state_brief in state_info_db.items():
            entry = result.state_db[si].entry
            for acceptance_id in state_brief.store.acceptance_sequence:
                entry.add_Accepter_on_all(state_info_db.acceptance_condition_db[acceptance_id], 
                                          acceptance_id)

    def _implement_required_position_storage(self, state_info_db):
        """
        Store Input Position / Postpone as much as possible.

        Before we do not reach a state that actually restores the position, it
        does make little sense to store the input position. 

                         Critical Point: Loops and Forks

        If a loop is reached then the input position can no longer be determined
        by the transition number. The good news is that during 'drop_out_configure'
        any state that has undetermined positioning restores the input position.
        Thus 'restore_position_f(register)' is enough to catch this case.
        """
        result = self.__r
        def iterable(state_info_db):
            for storing_si, state_brief in state_info_db.items():
                for acceptance_id, target_states_in_direction_of_restore in state_brief.store.position_db.items():
                    for target_si in target_states_in_direction_of_restore: 
                        yield storing_si, acceptance_id, target_si

        for storing_si, acceptance_id, target_si in iterable(state_info_db):
            # Store input position upon entry into successor states of the 
            # position storing state.
            acceptance_condition_set = state_info_db.acceptance_condition_db[acceptance_id] 
            entry                    = result.state_db[target_si].entry
            entry.add_StoreInputPosition(StateIndex       = target_si, 
                                         FromStateIndex   = storing_si, 
                                         AccConditionSet  = acceptance_condition_set,
                                         PositionRegister = acceptance_id, 
                                         Offset           = 0)

    def find_and_construct_mega_states(self):
        result = self.__r
        mega_state_analyzer.do(result)
        # Prepare Reload:
        # (Null-operation, in case no reload required.)
        # TransitionMap:                  On BufferLimitCode --> ReloadState
        # ReloadState.door of mega state: Router to doors of implemented states.
        for state in result.mega_state_list:
            state.prepare_again_for_reload(result) 

        return self

def _prepare(SmOrSmList, StateMachineId, ReverseF, AlllowInitStateAcceptF, CutF):
    def _reverse(sm):
        backup_id = sm.get_id()
        if ReverseF: sm = reverse.do(sm, EnsureDFA_f=True)
        sm.set_id(backup_id)
        return sm

    def _combine(sm_list):
        sr = sm_list[0].sr
        result = combination.do(sm_list, FilterDominatedOriginsF=False, 
                                AlllowInitStateAcceptF=AlllowInitStateAcceptF)
        result.sr = sr
        return result

    def _check(sm):
        if not CutF: return
        error_name = sm.delete_named_number_list(signal_lexatoms(Setup)) 
        if not error_name: return
        error.log("Pattern is empty after deletion of signal lexatom '%s'" % error_name, sm.sr)

    assert SmOrSmList

    if ReverseF:
        if type(SmOrSmList) != list:
            SM = _reverse(transform_to_encoding.do(SmOrSmList))
        else:
            SM = _combine([ _reverse(transform_to_encoding.do(sm)) for sm in SmOrSmList ])

        # Since transformation must happen before reversion, it is impossible to
        # determine state indices of the untransformed sm.
        # Such functionality is not required for reversed DFAs, anyway.
        state_indices_of_untransformed_sm = None
    else:
        if type(SmOrSmList) != list:
            state_indices_of_untransformed_sm = set(SmOrSmList.states.keys())
            SM                                = transform_to_encoding.do(SmOrSmList)
        else:
            combined_sm                       = _combine(SmOrSmList)
            state_indices_of_untransformed_sm = set(combined_sm.states.keys())
            SM                                = transform_to_encoding.do(combined_sm, OriginalSmList=SmOrSmList)
        
    if StateMachineId is not None: SM.set_id(StateMachineId)

    _check(SM)

    return SM, state_indices_of_untransformed_sm

