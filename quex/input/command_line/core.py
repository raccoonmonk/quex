# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
import sys
import os
from functools import reduce
sys.path.insert(0, os.environ["QUEX_PATH"])

from   quex.blackboard                         import setup
from   quex.input.command_line.GetPot          import GetPot
import quex.input.command_line.code_generation as     code_generation
import quex.input.command_line.query           as     query     
from   quex.input.code.base                    import SourceRef
from   quex.input.setup                        import SETUP_INFO,               \
                                                      SetupParTypes,            \
                                                      NotificationDB
from   quex.engine.misc.tools                  import flatten
import quex.engine.misc.error                  as     error
from   quex.engine.misc.file_operations        import open_file_or_die
from   quex.engine.misc.file_in                import get_integer_parameter_value
                                                 
def do(argv):
    """RETURNS: True,  if CODE GENERATION needs to happen.
                False, if NOTHING remains to be done.
    """        
    global setup
    location_list = __extra_option_extend_argv(argv)

    query_f, command_line = argv_interpret(argv)

    # Debug: restrict call stack size
    if setup._debug_limit_recursion:
        sys.setrecursionlimit(setup._debug_limit_recursion)

    if command_line is None: 
        return False
    elif not query_f:        
        code_generation.prepare(command_line, argv)
    else:                    
        query.run(command_line, argv)

    __extra_option_message(location_list)
    return not query_f

def __extra_option_extend_argv(argv):
    """Checks for source files mentioned in the command line. Some may
    contain sections that extend the command line. If so, the command line
    options are parsed and added to 'argv'.

    Details in '__extra_option_extract_from_file()'.
    """
    extra_location_list = []
    try:    
        idx = argv.index("--token-class-file")
        if idx + 1 < len(argv): idx += 1
        else:                   idx  = None
    except: 
        idx = None 

    if idx is None:
        # No file with extra command line options.
        return

    extra_argv, extra_location_list = __extra_option_extract_from_file(argv[idx])
    if extra_argv is None: 
        # No extra option in file. 
        return

    argv.extend(extra_argv)
    return extra_location_list

def __extra_option_extract_from_file(FileName):
    """Extract an option section from a given file. The quex command line 
       options may be given in a section surrounded by '<<<QUEX-OPTIONS>>>'
       markers. For example:

           <<<QUEX-OPTIONS>>>
              --token-class-file      Common-token
              --token-class           Common::Token
              --token-id-type         uint32_t
              --buffer-element-type   uint8_t
              --lexeme-null-object    ::Common::LexemeNullObject
              --foreign-token-id-file Common-token_ids
           <<<QUEX-OPTIONS>>>

       This function extracts those options and builds a new 'argv' array, i.e.
       an array of strings are if they would come from the command line.
    """
    MARKER = "<<<QUEX-OPTIONS>>>"
    fh     = open_file_or_die(FileName)

    while 1 + 1 == 2:
        line = fh.readline()
        if line == "":
            return None, [] # Simply no starting marker has been found
        elif line.find(MARKER) != -1: 
            pos = fh.tell()
            break

    result = []
    location_list = []

    line_n = 0
    while 1 + 1 == 2:
        line_n += 1
        line    = fh.readline()
        if line == "":
            fh.seek(pos)
            error.log("Missing terminating '%s'." % MARKER, fh)

        if line.find(MARKER) != -1: 
            break
        
        idx = line.find("-")
        if idx == -1: continue
        options = line[idx:].split()

        location_list.append((SourceRef(True, FileName, line_n), options))
        result.extend(options)

    if not result: return None, location_list

    return result, location_list

def __extra_option_message(ExtraLocationList):
    if ExtraLocationList is None:
        return
    elif NotificationDB.message_on_extra_options in setup.suppressed_notification_list:
        return
    elif len(ExtraLocationList) == 0:
        return

    sr = ExtraLocationList[0][0]
    error.log("Command line arguments from inside files:", sr, NoteF=True)
    for sr, option in ExtraLocationList:
        if len(option) < 2: option_str = option[0]
        else:               option_str = reduce(lambda x, y: "%s %s" % (x.strip(), y.strip()), option)
        error.log("%s" % option_str, sr, NoteF=True)
    error.log("", sr, NoteF=True, SuppressCode=NotificationDB.message_on_extra_options)

def argv_interpret(argv):
    """RETURNS:
         QueryF -- True, if quex is run in query mode.
                   False, if it is run in code generation mode.
         Setup  -- information about the command line.
    """
    # Filter: Parameters which are not to be set on command line.
    parameter_list = [ 
        # variable_name, flag_list, argument type
        (variable_name, info[0], info[1])
        for variable_name, info in SETUP_INFO.items() 
        if type(info) == list  
    ]

    # Filter: Parameters which are not found on given command line.
    parameter_list = [
        (variable_name, flag_list, arg_type)
        for variable_name, flag_list, arg_type in parameter_list
        if any(flag in argv for flag in flag_list) 
    ]

    command_line = GetPot(argv, SectionsEnabledF=False)
    query_f = __is_query(command_line, parameter_list)
    command_line.disable_loop()
    for variable_name, flag_list, arg_type in parameter_list:
        command_line.reset_cursor()
        value = get_argument_value(command_line, flag_list, arg_type)
        setup.set(variable_name, arg_type, value)

    # Handle unidentified command line options.
    argv_ufo_detections(command_line)

    return query_f, command_line

def get_argument_value(command_line, flag_list, arg_type):
    if   arg_type == SetupParTypes.FLAG:
        return True
    elif arg_type == SetupParTypes.NEGATED_FLAG:
        return False
    elif arg_type == SetupParTypes.OPTIONAL_STRING:
        return argv_catch_string(command_line, flag_list, arg_type)
    elif arg_type == SetupParTypes.INT_LIST:
        return argv_catch_int_list(command_line, flag_list)
    elif arg_type == SetupParTypes.LIST:
        return argv_catch_list(command_line, flag_list)
    elif isinstance(arg_type, int):
        return argv_catch_int(command_line, flag_list, arg_type)
    else:
        return argv_catch_string(command_line, flag_list, arg_type)

def __is_query(command_line, parameter_list):
    query_f = any(variable_name.startswith("query_") 
                  for variable_name, flag_list, arg_type in parameter_list)
    not_query_f = any(not variable_name.startswith("query_") 
                      for variable_name, flag_list, arg_type in parameter_list)
    if query_f and not query_f:
        if command_line.search(SETUP_INFO["_debug_exception_f"][0]): return query_f

        error.log("Mixed options: query and code generation mode.\n"
                  "The option(s) '%s' cannot be combined with preceeding options." \
                  % str(SETUP_INFO[Name][0])[1:-1].replace("'",""))
    return query_f

def argv_catch_int(Cl, Option, Default):
    """RETURNS: Integer for the given variable name.
    """
    miss = "<\0>"
    setting = Cl.follow(miss, Option)
    if setting == miss:
        setting = Default
    else: 
        return get_integer_parameter_value(str(Option)[1:-1], setting)

def argv_catch_int_list(Cl, Option):
    """RETURNS: list of integers built from the list of no-minus followers of 
    the given option.
    """
    return [
        get_integer_parameter_value(str(Option)[1:-1], x)
        for x in argv_catch_list(Cl, Option)
    ]

def argv_catch_list(Cl, Option):
    """Catch the list of no-minus followers of the given option. Multiple
    occurrencies of Option are considered.

    RETURNS: list of no-minus followers.
    """
    result = []
    while 1 + 1 == 2:
        if not Cl.search(Option):
            break

        the_list = Cl.nominus_followers(Option)
        if not the_list:
            error.log("Option %s\nnot followed by anything." % str(Option)[1:-1])

        for x in the_list:
            if x not in result: result.append(x)
    return result

def argv_catch_string(Cl, Option, Type):
    Cl.reset_cursor()
    value = Cl.follow("##EMPTY##", Option)
    if value == "##EMPTY##":
        if Type == SetupParTypes.OPTIONAL_STRING:
            value = ""
        else:
            error.log("Option %s\nnot followed by anything." % str(Option)[1:-1])
    return value

def argv_ufo_detections(Cl):
    """Detects unidentified command line options.
    """
    known_option_list = []
    for info in SETUP_INFO.values():
        if type(info) != list: continue
        known_option_list.extend(info[0])

    ufo_list = Cl.unidentified_options(known_option_list)
    if not ufo_list: return

    pre_filter_flag_info = [ 
        info for info in SETUP_INFO.values() if info 
    ]
    all_flag_list = flatten(
        flag_list for flag_list, dummy in pre_filter_flag_info
    )
    ufo = ufo_list[0]

    error.log_similar(ufo, all_flag_list, "Unknown command line option '%s'" % ufo)
