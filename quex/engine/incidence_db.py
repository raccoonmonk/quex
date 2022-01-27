# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
from   quex.engine.misc.tools                import typed
from   quex.engine.analyzer.terminal.factory import TerminalFactory
import quex.engine.misc.error                as     error
from   quex.input.code.base                  import CodeFragment, \
                                                    SourceRef_DEFAULT
from   quex.input.setup                      import NotificationDB
from   quex.blackboard import standard_incidence_db, \
                              standard_incidence_db_is_mandatory, \
                              standard_incidence_db_get_terminal_type, \
                              E_IncidenceIDs, \
                              Lng

class IncidenceDB(dict):
    """Database of CodeFragments related to 'incidences'.
    ---------------------------------------------------------------------------

                      incidence_id --> [ CodeFragment ]

    If the 'mode_option_info_db[option_name]' mentions that there can be 
    no multiple definitions or if the options can be overwritten than the 
    list of OptionSetting-s must be of length '1' or the list does not exist.

    ---------------------------------------------------------------------------
    """
    @staticmethod
    def from_BaseModeSequence(BaseModeSequence):
        """Collects the content of the 'incidence_db' member of this mode and
        its base modes. Incidence handlers can only defined ONCE in a mode
        hierarchy.

        RETURNS:      map:    incidence_id --> [ CodeFragment ]
        """
        assert BaseModeSequence

        mode_name = BaseModeSequence[-1].name
        
        # Collect from base modes event handlers
        #
        event_handler_list_raw = [
            # info[0]: incidence id related to 'incidence_name'
            (info[0], _find_in_mode_hierarchy(BaseModeSequence, incidence_name))
            for incidence_name, info in standard_incidence_db.items()
        ]

        # Implement and prepare all event handlers
        #
        event_handler_list = [
            (incidence_id, _compose_event_handler(code, incidence_id, mode_name))
            for incidence_id, code in event_handler_list_raw
        ]

        # Provide an entry for each existing handler
        #
        return IncidenceDB.from_iterable(
            (incidence_id, code)
            for incidence_id, code in event_handler_list if code is not None
        )

    @staticmethod
    def from_iterable(iterable):
        result = IncidenceDB()
        result.update(iterable)
        return result

def _find_in_mode_hierarchy(BaseModeSequence, incidence_name):
    """Find incidence handler in the mode hierarchy. An incidence handler
    can only be defined once. If none is found 'None' is returned.
    """
    found      = None # Note on style: 'for-else' does not make sense,
    #                 # because multi-definitions need to be detected.
    found_mode = None
    for mode in BaseModeSequence:
        code_fragment = mode.incidence_db.get(incidence_name)
        if code_fragment is None:         
            continue
        elif found is not None:
            error.warning("Handler '%s' in mode '%s' overwrites previous in mode '%s'." \
                          % (incidence_name, mode.name, found_mode), code_fragment.sr,
                          SuppressCode=NotificationDB.warning_incidence_handler_overwrite)
        found      = code_fragment.clone()
        found_mode = mode.name
    return found

def _compose_event_handler(code, IncidenceId, ModeName):
    if IncidenceId == E_IncidenceIDs.INDENTATION_HANDLER:  
        return code

    # Event handler core: user defined or default
    #
    if code is not None:                                   
        event_handler_txt = code.get_code()
        sr                = code.sr
    else:
        event_handler_txt = Lng.event_handler_default_db[IncidenceId](Lng) 
        sr                = SourceRef_DEFAULT

    # Event handler prolog
    #
    event_handler_prolog_txt = Lng.event_prolog_db[IncidenceId](Lng, ModeName)

    txt =   event_handler_prolog_txt \
          + event_handler_txt

    if not txt: return None
    else:       return CodeFragment(txt, sr)

