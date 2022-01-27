# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.constants import E_R
from   quex.engine.analyzer.door_id_address_label   import DoorID
from   quex.engine.operations.operation_list import OpList, \
                                                    Op

def do(TheAccepter, TheTerminalRouter):
    """If there is no stored acceptance involved, then one can directly
    conclude from the pre-contexts to the acceptance_id. Then the drop-
    out action can be described as a sequence of checks

       # [0] Check          [1] Position and Goto Terminal
       if   pre_context_32: input_p = x; goto terminal_893;
       elif pre_context_32: goto terminal_893;
       elif pre_context_32: input_p = x; goto terminal_893;
       elif pre_context_32: goto terminal_893;

    Such a configuration is considered trivial. No restore is involved.
    """
    # If the 'last_acceptance' is not determined in this state, then it
    # must bee derived from previous storages. We cannot simplify here.
    if TheAccepter is None: 
        return OpList(TheTerminalRouter)

    elif not TheAccepter.content.has_acceptance_without_pre_context():
        # If no pre-context is met, then 'last_acceptance' needs to be 
        # considered.
        return OpList(TheAccepter, TheTerminalRouter)

    else:
        def router_element(TerminalRouter, AcceptanceId):
            for x in TerminalRouter:
                if x.acceptance_id == AcceptanceId: return x
            assert False  # There MUST be an element for each acceptance_id!

        router = TheTerminalRouter.content

        return OpList.from_iterable(
            Op.IfAcceptanceConditionSetPositionAndGoto(check.acceptance_condition_set, 
                                                       router_element(router, check.acceptance_id))
            for check in TheAccepter.content
        )

def do_backward_pre_context(DFA_State, dial_db, IncidenceId=None):
    return OpList(Op.GotoDoorId(DoorID.global_end_of_pre_context_check(dial_db)))

def do_backward_input_position_detection(DFA_State, dial_db, BipdIncidenceId):
    if DFA_State.is_acceptance():
        incidence_id = BipdIncidenceId
        return OpList(
            Op.QuexDebug('pattern %i: backward input position detected\\n' % incidence_id),
            Op.Increment(E_R.InputP), 
            Op.GotoDoorId(DoorID.bipd_return(incidence_id, dial_db))
        )
    else:
        return OpList(
            Op.QuexAssertNoPassage()
        )
