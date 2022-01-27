# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
# IMPORTANT: This file shall be import-able by any 'normal' module of Quex.    #
#            For this, it was a designated design goal to make sure that the   #
#            imports are 'flat' and only cause environment or outer modules.   #
#_______________________________________________________________________________
from   quex.input.code.base   import CodeFragment_NULL
from   quex.input.setup       import QuexSetup, \
                                     SETUP_INFO
from   quex.constants         import E_IncidenceIDs, \
                                     E_TerminalType

import quex.engine.state_machine.transformation.core as     bc_factory


#------------------------------------------------------------------------------
# setup: All information of the user's desired setup.
#------------------------------------------------------------------------------
setup = QuexSetup(SETUP_INFO, bc_factory)

class Lng_class:
    """Provide shortcut to 'Setup.language_db'.
    ___________________________________________________________________________
    During code generation, there is an excessive reference to the language
    database, i.e. the instance which tells who to do things in the output
    language. Instead of writing 'Setup.language_db.xyz()' it shall be possible
    to write 'Lng.xyz()' which helps to keep the code clean. 

    The global object 'Lng' is an instance of this class. It references to 
    'Setup.language_db', even if the setting of '.language_db' changes.
    ___________________________________________________________________________
    """
    def __init__(self, TheSetup):
        self.__setup = TheSetup
    def __getattr__(self, Attr): 
        language_db = self.__setup.language_db
        try:             return getattr(language_db, Attr)
        except KeyError: raise AttributeError

Lng = Lng_class(setup)

#-----------------------------------------------------------------------------------------
# standard_incidence_db: Stores names of event handler functions as keys and their meaning
#                        as their associated values.
#-----------------------------------------------------------------------------------------
standard_incidence_db = {
    "on_entry":                (E_IncidenceIDs.MODE_ENTRY,          "On entry of a mode."),
    "on_exit":                 (E_IncidenceIDs.MODE_EXIT,           "On exit of a mode."),
    "on_indent":               (E_IncidenceIDs.INDENTATION_INDENT,  "On opening indentation."),
    "on_nodent":               (E_IncidenceIDs.INDENTATION_NODENT,  "On same indentation."),
    "on_dedent":               (E_IncidenceIDs.INDENTATION_DEDENT,  "On closing indentation'."),
    "on_indentation_misfit":   (E_IncidenceIDs.INDENTATION_MISFIT,   "Closing indentation on non-border."),
    "on_indentation_bad":      (E_IncidenceIDs.INDENTATION_BAD,     "On bad character in indentation."),
    "on_indentation":          (E_IncidenceIDs.INDENTATION_HANDLER, "General Indentation Handler."),
    "on_match":                (E_IncidenceIDs.MATCH,               "On each match (before pattern action)."),
#   TODO        "on_token_stamp":            "On event of token stamping.",
#   instead of: QUEX_ACTION_TOKEN_STAMP 
    "on_bad_lexatom":          (E_IncidenceIDs.BAD_LEXATOM,          "On each match (after pattern action)."),
    "on_after_match":          (E_IncidenceIDs.AFTER_MATCH,          "On each match (after pattern action)."),
    "on_failure":              (E_IncidenceIDs.MATCH_FAILURE,        "In case that no pattern matches."),
    "on_load_failure":         (E_IncidenceIDs.LOAD_FAILURE,         "Loading failed for some reason."),
    "on_buffer_before_change": (E_IncidenceIDs.BUFFER_BEFORE_CHANGE, "Buffer content is about to change."),
    "on_buffer_overflow":      (E_IncidenceIDs.BUFFER_OVERFLOW,      "Loading impossible; lexeme too long."),
    "on_skip_range_open":      (E_IncidenceIDs.SKIP_RANGE_OPEN,      "On missing skip range delimiter."),
    "on_end_of_stream":        (E_IncidenceIDs.END_OF_STREAM,        "On end of file/stream."),
}

def standard_incidence_db_get_event_handler(IncidenceId):
    for name, entry in standard_incidence_db.items():
        if entry[0] == IncidenceId: return name
    return None

def standard_incidence_db_is_mandatory(IncidenceId):
    return IncidenceId in [
        E_IncidenceIDs.MATCH_FAILURE, 
        E_IncidenceIDs.LOAD_FAILURE, 
        E_IncidenceIDs.END_OF_STREAM,
        E_IncidenceIDs.BAD_LEXATOM,      # i.e. encoding error
        E_IncidenceIDs.SKIP_RANGE_OPEN,
        E_IncidenceIDs.INDENTATION_BAD,
    ]

incidence_id_to_terminal_type_db = {
    E_IncidenceIDs.MATCH_FAILURE:   E_TerminalType.MATCH_FAILURE,
    E_IncidenceIDs.END_OF_STREAM:   E_TerminalType.END_OF_STREAM,
    E_IncidenceIDs.BAD_LEXATOM:     E_TerminalType.BAD_LEXATOM,
    E_IncidenceIDs.LOAD_FAILURE:    E_TerminalType.LOAD_FAILURE,
    E_IncidenceIDs.SKIP_RANGE_OPEN: E_TerminalType.SKIP_RANGE_OPEN,
    # Otherwise, it would try to make terminals for that in 'extract_terminal_db()'
}

def standard_incidence_db_get_terminal_type(IncidenceId):
    global incidence_id_to_terminal_type_db
    return incidence_id_to_terminal_type_db.get(IncidenceId)

#-----------------------------------------------------------------------------------------
# mode_db: storing the mode information into a dictionary:
#            key  = mode name
#            item = Mode object
#
# A Mode is a more 'fermented' container of information about a mode. It is based on
# a ModeParsed.
#-----------------------------------------------------------------------------------------
mode_db = {}

#-----------------------------------------------------------------------------------------
# initial_mode: mode in which the lexcial analyser shall start
#-----------------------------------------------------------------------------------------
initial_mode = CodeFragment_NULL

#-----------------------------------------------------------------------------------------
# footer: code fragment that is to be pasted BEFORE all class definitions.
#         basic macro definitons are available
#-----------------------------------------------------------------------------------------
header = CodeFragment_NULL

#-----------------------------------------------------------------------------------------
# footer: code fragment that is to be pasted AFTER all class definitions.
#-----------------------------------------------------------------------------------------
footer = CodeFragment_NULL

#-----------------------------------------------------------------------------------------
# class_body_extension: code fragment that is to be pasted inside the class definition
#                       of the lexical analyser class.
#-----------------------------------------------------------------------------------------
class_body_extension = CodeFragment_NULL

#-----------------------------------------------------------------------------------------
# class_constructor_extension: code fragment that is to be pasted inside the lexer class constructor
#-----------------------------------------------------------------------------------------
class_constructor_extension = CodeFragment_NULL

#-----------------------------------------------------------------------------------------
# class_destructor_extension: code fragment that is to be pasted inside the lexer class constructor
#-----------------------------------------------------------------------------------------
class_destructor_extension = CodeFragment_NULL

#-----------------------------------------------------------------------------------------
# class_print_extension: code fragment that extends the class' print function
#-----------------------------------------------------------------------------------------
class_print_extension = CodeFragment_NULL

# reset_extension: code fragment for user defined reset actions
#-----------------------------------------------------------------------------------------
reset_extension = CodeFragment_NULL

#-----------------------------------------------------------------------------------------
# memento_extension: fragment to be pasted into the memento  class's body.
#-----------------------------------------------------------------------------------------
memento_class_extension = CodeFragment_NULL

#-----------------------------------------------------------------------------------------
# memento_pack_extension: fragment to be pasted into the function that packs the
#                         lexical analyzer state in a memento.
#-----------------------------------------------------------------------------------------
memento_pack_extension = CodeFragment_NULL

#-----------------------------------------------------------------------------------------
# memento_unpack_extension: fragment to be pasted into the function that unpacks the
#                           lexical analyzer state in a memento.
#-----------------------------------------------------------------------------------------
memento_unpack_extension = CodeFragment_NULL

fragment_db = {
    "header":         "header",
    "footer":         "footer",                     # -> in 'header' after all definitions.
    "body":           "class_body_extension",
    "constructor":    "class_constructor_extension",
    "destructor":     "class_destructor_extension",
    "print":          "class_print_extension",
    "reset":          "reset_extension",
    "memento":        "memento_class_extension",
    "memento_pack":   "memento_pack_extension",
    "memento_unpack": "memento_unpack_extension",
}

all_section_title_list = ["start", "define", "token", "mode", "repeated_token", "token_type" ] + list(fragment_db.keys())

#-----------------------------------------------------------------------------------------
# shorthand_db: user defined names for regular expressions.
#-----------------------------------------------------------------------------------------
shorthand_db = {}

#-----------------------------------------------------------------------------------------
# dfa_command_executed_f: If a dfa command in a 'define' section has been evaluated
#                         no mode need to be defined.
#-----------------------------------------------------------------------------------------
dfa_command_executed_f = False

#-----------------------------------------------------------------------------------------
# signal_lexatoms: List of lexatoms that mark positions in the input stream wich are
#                  relevant only to the lexical analyzer.
#-----------------------------------------------------------------------------------------
def signal_lexatoms(TheSetup):
    result = [
        (TheSetup.buffer_limit_code, "Buffer Limit Code")
    ]
    if TheSetup.compression_path_f: 
        result.append((TheSetup.path_limit_code, "Path Limit Code"))
    return result

#-----------------------------------------------------------------------------------------
# Helper functions about required features.
#-----------------------------------------------------------------------------------------
# Determine whether the lexical analyser needs indentation counting
# support. if one mode has an indentation handler, than indentation
# support must be provided.                                         
__required_support_indentation_count = False
def required_support_indentation_count_set():
    global __required_support_indentation_count
    __required_support_indentation_count = True
def required_support_indentation_count():
    global __required_support_indentation_count
    return __required_support_indentation_count

def required_counter():
    return    setup.count_line_number_f \
           or setup.count_column_number_f \
           or required_support_indentation_count()

# If one single pattern in one mode depends on begin of line, then
# the begin of line condition must be supported. Otherwise not.
# The requirement can be only set, but no unset!
__required_support_begin_of_line = False
def required_support_begin_of_line_set():
    global __required_support_begin_of_line
    __required_support_begin_of_line = True
def required_support_begin_of_line():
    global __required_support_begin_of_line
    return __required_support_begin_of_line

def deprecated(*Args):
    """This function is solely to be used as setter/getter property, 
       of member variables that are deprecated. This way misuse
       can be detected. Example usage:

       class X(object):  # Class must be derived from 'object'
           ...
           my_old = property(deprecated, deprecated, "Alarm on 'my_old'")
    """
    assert False

class DefaultCounterFunctionDB:
    """Default counters may be used in several modes. This database
    keeps track of implementations. If an implementation is done for
    one mode, another mode may refer it it.
    """
    __db = []
    @staticmethod
    def get_mode_name(CCFactory):
        """Returns name of function which already implemented the 'CounterDb'.
        Otherwise, it returns 'None' if no such function exists.
        """
        for factory, mode_name in DefaultCounterFunctionDB.__db:
            if factory.is_equal(CCFactory): 
                return mode_name
        return None

    @classmethod
    def enter(cls, CCFactory, ModeName):
        assert not any(ModeName == mode_name for ccfactory, mode_name in cls.__db)
        DefaultCounterFunctionDB.__db.append((CCFactory, ModeName))

    @staticmethod
    def clear():
        del DefaultCounterFunctionDB.__db[:]
 

