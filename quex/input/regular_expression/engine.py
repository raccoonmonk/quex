# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
# The 'grammar' of quex's regular expressions:
#
#  complete expression: expression
#                       expression / expression              = post conditioned expression
#                       expression / expression /            = pre conditioned expression
#                       expression / expression / expression = pre and post conditioned expression
# 
#  expression: term
#              term | expression
#  
#  term:  primary
#         primary term
#  
#  primary:  " non_double_quote *  "              = character string
#            [ non_rect_bracket_close ]           = set of characters
#            { identifier }                       = pattern replacement
#            ( expression )
#            non_control_character+               = lonely characters
#            primary repetition_cmd
#  
#  non_double_quote: 'anything but an unbackslashed double quote, i.e. \" is ok, 
#                     but " is not.'      
#  non_rect_bracket_close: 'anything but an unbackslashed rectangular bracket, i.e.
#                           \] is ok, but ] is not.'               
#  non_control_character: 'anything but (, ", [, or {'
#       
#  repetition_cmd: 'a repetition command such as +, *, {2}, {,2}, {2,5}'        
#
#########################################################################################       
import quex.engine.codec_db.core                                as codec_db
from   quex.engine.state_machine.core                           import DFA
import quex.engine.state_machine.algorithm.beautifier           as beautifier
import quex.engine.state_machine.algorithm.nfa_to_dfa           as nfa_to_dfa
import quex.engine.state_machine.algebra.sanitizer              as sanitizer
import quex.engine.state_machine.algebra.complement             as complement
import quex.engine.state_machine.algebra.complement_variants    as complement_variants
import quex.engine.state_machine.algebra.reverse                as reverse
import quex.engine.state_machine.algebra.intersection           as intersection
import quex.engine.state_machine.algebra.difference             as difference
import quex.engine.state_machine.algebra.symmetric_difference   as symmetric_difference
import quex.engine.state_machine.algebra.union                  as union
import quex.engine.state_machine.cut.operations_on_sets         as derived
import quex.engine.state_machine.cut.stem_and_branches          as stem_and_branches
import quex.engine.state_machine.cut.operations_on_lexemes      as cut
from   quex.input.code.base                                     import SourceRef

import quex.input.regular_expression.traditional_character_set  as     traditional_character_set
from   quex.input.regular_expression.macro                      import PatternShorthand
import quex.input.regular_expression.property                   as     unicode_property
from   quex.input.regular_expression.pattern                    import Pattern_Prep
import quex.input.regular_expression.snap_backslashed_character as     snap_backslashed_character
from   quex.input.regular_expression.snap_backslashed_character import __parse_hex_number
from   quex.input.regular_expression.debug                      import __debug_entry, \
                                                                       __debug_exit, \
                                                                       __debug_print, \
                                                                       __debug_print_stream

import quex.engine.state_machine.construction.sequentialize    as sequentialize
import quex.engine.state_machine.construction.parallelize      as parallelize
import quex.engine.state_machine.construction.repeat           as repeat
import quex.engine.state_machine.edit_distance.core            as edit_distance
import quex.engine.state_machine.edit_distance.transposition   as transposition
import quex.engine.state_machine.edit_distance.levenshtein     as levenshtein
import quex.engine.state_machine.edit_distance.pseudo_damerau  as pseudo_damerau
import quex.engine.codec_db.unicode.case_fold_parser           as ucs_case_fold

from   quex.engine.misc.interval_handling  import Interval, NumberSet, NumberSet_All
from   quex.engine.misc.tools              import quex_chr, typed
import quex.engine.misc.error              as     error
from   quex.engine.misc.unistream          import UniStream
from   quex.engine.misc.file_operations    import read_between_positions
from   quex.engine.misc.file_in            import check, \
                                                  check_whitespace, \
                                                  snap_until, \
                                                  read_integer, \
                                                  skip_whitespace, \
                                                  read_identifier, \
                                                  optional_flags
from   quex.output.syntax_elements         import Argument

from   quex.blackboard import setup as Setup
from   quex.constants  import INTEGER_MAX, \
                              DEFINE_SECTION_COMMAND_SET
from   quex.input.regular_expression.exception import RegularExpressionException

CONTROL_CHARACTERS = [ "+", "*", "\"", "/", "(", ")", "{", "}", "|", "[", "]", "$"] 
SPECIAL_TERMINATOR = None

def do(UTF8_String_or_Stream, PatternDict, 
       AllowNothingIsNecessaryF = False, 
       SpecialTerminator = None,
       AllowLogicOrAfterPostContextF = False,
       AllowEmptyF = False):
    global SPECIAL_TERMINATOR 
    assert type(AllowNothingIsNecessaryF) == bool
    assert type(PatternDict) == dict

    # SPECIAL_TERMINATOR --> if string is not only to be terminated by ' '
    SPECIAL_TERMINATOR = SpecialTerminator

    def __ensure_whitespace_follows(InitialPos, stream):
        pos = stream.tell()
        tmp = stream.read(1)
        if tmp == "" or tmp.isspace() or tmp == SPECIAL_TERMINATOR:
            stream.seek(pos)
        else:
            stream.seek(pos)
            pattern_str = read_between_positions(stream, InitialPos, stream.tell())
            error.log("Pattern definition '%s' not followed by whitespace.\n" % pattern_str + \
                      "Found subsequent character '%s'." % tmp, 
                      stream)

    stream = UniStream(UTF8_String_or_Stream)

    if PatternDict is None: PatternDict = {}

    initial_position = stream.tell()

    # -- check for the begin of line condition (BOL)
    begin_of_line_f   = check(stream, '^')
    begin_of_stream_f = check(stream, '<<BOS>>')
    if Setup.pre_context_begin_of_line_implies_begin_of_stream_f and begin_of_line_f: 
        begin_of_stream_f = True
    
    if begin_of_stream_f: skip_whitespace(stream)

    # -- MAIN: transform the pattern into a state machine
    sr = SourceRef.from_FileHandle(stream)
    pre, core, post = snap_conditional_expression(stream, PatternDict)

    if core is None: 
        stream.seek(initial_position)
        return None

    # -- check for end of line condition (EOL) 
    # -- check for terminating whitespace
    end_of_line_f   = check(stream, "$")
    end_of_stream_f = check(stream, "<<EOS>>")

    if Setup.post_context_end_of_line_implies_end_of_stream_f and end_of_line_f: 
        end_of_stream_f = True

    __error_check(begin_of_line_f, begin_of_stream_f, pre, stream, "pre-context")
    __error_check(end_of_line_f, end_of_stream_f, post, stream, "post-context")

    __ensure_whitespace_follows(initial_position, stream)
    
    if end_of_stream_f and end_of_line_f:
        if not AllowLogicOrAfterPostContextF:
            error.log("Post contexts 'end-of-line' and 'end-of-stream' may only appear together\n"
                      "in environments where logical disjunction of post contexts is admissible.\n", 
                      stream)
        if pre is None: pre_clone = None
        else:           pre_clone = pre.clone()
        pattern_0 = Pattern_Prep(CoreSM         = core.clone(), 
                                 BeginOfLineF   = begin_of_line_f,
                                 BeginOfStreamF = begin_of_stream_f,
                                 PreContextSM   = pre_clone,
                                 EndOfLineF     = end_of_line_f,
                                 EndOfStreamF   = False,
                                 PostContextSM  = post,
                                 Sr             = sr,
                                 PatternString  = read_pattern_string(stream, initial_position),
                                 AllowNothingIsNecessaryF = AllowNothingIsNecessaryF, 
                                 AllowEmptyF              = AllowEmptyF)
        pattern_1 = Pattern_Prep(CoreSM         = core, 
                                 BeginOfLineF   = begin_of_line_f,
                                 BeginOfStreamF = begin_of_stream_f,
                                 PreContextSM   = pre,
                                 EndOfLineF     = False,
                                 EndOfStreamF   = True,
                                 PostContextSM  = None,
                                 Sr             = sr,
                                 PatternString  = read_pattern_string(stream, initial_position),
                                 AllowNothingIsNecessaryF = AllowNothingIsNecessaryF,
                                 AllowEmptyF              = AllowEmptyF)
        result = [ pattern_0, pattern_1 ]
    else:
        result = [
             Pattern_Prep(CoreSM         = core, 
                          BeginOfLineF   = begin_of_line_f,
                          BeginOfStreamF = begin_of_stream_f,
                          PreContextSM   = pre,
                          EndOfLineF     = end_of_line_f,
                          EndOfStreamF   = end_of_stream_f,
                          PostContextSM  = post,
                          Sr             = sr,
                          PatternString  = read_pattern_string(stream, initial_position),
                          AllowNothingIsNecessaryF = AllowNothingIsNecessaryF,
                          AllowEmptyF              = AllowEmptyF)
        ]
    
    if AllowLogicOrAfterPostContextF:
        return result
    else: 
        assert len(result) == 1
        return result[0]

def read_pattern_string(fh, StartPos):
    """Reads the regular expression string which was interpreted to build the 
    pattern. 
    """
    end_position = fh.tell()
    fh.seek(StartPos)
    result = []
    while fh.tell() != end_position:
        result.append(fh.read(1))
    return "".join(result)

def snap_conditional_expression(stream, PatternDict):
    """conditional expression: expression
                               expression / expression                 = post conditioned expression
                               expression / expression /               = pre conditioned expression
                               expression / expression / expression    = pre and post conditioned expression
       TODO: <- ($8592) for pre-context
             -> ($8594) for post-context

        RETURNS: pre_context, core_pattern, post_context
    """                     
    __debug_entry("conditional expression", stream)    

    # -- expression
    pattern_0 = __core(stream, PatternDict) 
    if pattern_0 is None: 
        return None, None, None
    
    # -- '/'
    if not check(stream, '/'): 
        # (1) expression without pre and post condition
        #     pattern_0 is already beautified by '__core()'
        return None, pattern_0, None
        
    # -- expression
    pattern_1 = __core(stream, PatternDict) 
    if pattern_1 is None: 
        return None, pattern_0, None
    
    # -- '/'
    if not check(stream, '/'): 
        # (2) expression with only a post condition
        #     NOTE: setup_post_context() marks state origins!
        return None, pattern_0, pattern_1

    # -- expression
    pattern_2 = __core(stream, PatternDict) 
    if pattern_2 is None: 
        # (3) expression with only a pre condition
        #     NOTE: setup_pre_context() marks the state origins!
        return pattern_0, pattern_1, None
    else:
        # (4) expression with post and pre-context
        return pattern_0, pattern_1, pattern_2

def __core(stream, PatternDict):
    result = snap_expression(stream, PatternDict)
    if result is None: return None
    else:              return beautifier.do(result)

def snap_expression(stream, PatternDict):
    """expression:  term
                    term | expression
    """              
    __debug_entry("expression", stream)    
    # -- term
    result = snap_term(stream, PatternDict) 
    if result is None: 
        return __debug_exit(None, stream)

    # -- optional '|'
    if not check(stream, '|'): 
        return __debug_exit(result, stream)
    
    position_1 = stream.tell()
    __debug_print("'|' (in expression)")

    # -- expression
    result_2 = snap_expression(stream, PatternDict) 
    __debug_print("expression(in expression):",  result_2)
    if result_2 is None:
        stream.seek(position_1) 
        return __debug_exit(result, stream)

    result = parallelize.do([result, result_2])
    return __debug_exit(nfa_to_dfa.do(result), stream)

def snap_term(stream, PatternDict):
    """term:  primary
              primary term 
    """
    __debug_entry("term", stream)    

    # -- primary
    result = snap_primary(stream, PatternDict) 
    __debug_print("##primary(in term):", result)
    if result is None: return __debug_exit(None, stream)
    position_1 = stream.tell()

    # -- optional 'term' 
    result_2 = snap_term(stream, PatternDict) 
    __debug_print("##term(in term):",  result_2)
    if result_2 is None: 
        stream.seek(position_1)
        return __debug_exit(result, stream)
    
    result = sequentialize.do([result, result_2], 
                              MountToFirstStateMachineF=True, 
                              CloneRemainingStateMachinesF=False)    

    return __debug_exit(result, stream)
        
def snap_primary(stream, PatternDict):
    """primary:  " non_double_quote *  "              = character string
                 [ non_rect_bracket_close ]           = set of characters
                 { identifier }                       = pattern replacement
                 ( expression )
                 non_control_character+               = lonely characters
                 primary repetition_cmd
    """
    global SPECIAL_TERMINATOR 

    __debug_entry("primary", stream)    
    pos = stream.tell()
    x   = stream.read(1)
    if not x: 
        stream.seek(pos); 
        return __debug_exit(None, stream)
    elif   x == "\"": 
        result = DFA.from_sequence(snap_character_code_iterable(stream))
    elif x == "[":  
        stream.seek(pos); 
        result = snap_character_set_expression(stream, PatternDict)
    elif x == "{":  result = _snap_expansion(stream, PatternDict)
    elif x == ".":  result = create_ALL_BUT_NEWLINE_state_machine(stream)
    elif x == "(":  result = snap_bracketed_expression(stream, PatternDict)

    elif x.isspace():
        # a lonestanding space ends the regular expression
        stream.seek(pos)
        return __debug_exit(None, stream)

    elif x in ["*", "+", "?"]:
        raise RegularExpressionException("lonely operator '%s' without expression proceeding." % x) 

    elif x == "\\":
        result = snap_command(stream, pos, PatternDict)

    elif x not in CONTROL_CHARACTERS and x != SPECIAL_TERMINATOR:
        # NOTE: The '\' is not inside the control characters---for a reason.
        #       It is used to define for example character codes using '\x' etc.
        stream.seek(pos)
        result = snap_non_control_character(stream, PatternDict)

    else:
        # NOTE: This includes the '$' sign which means 'end of line'
        #       because the '$' sign is in CONTROL_CHARACTERS, but is not checked
        #       against. Thus, it it good to leave here on '$' because the
        #       '$' sign is handled on the very top level.
        # this is not a valid primary
        stream.seek(pos)
        return __debug_exit(None, stream)

    # -- optional repetition command? 
    if result is not None:
        result_repeated = __snap_repetition_range(result, stream) 
        if result_repeated is not None: result = result_repeated

    return __debug_exit(result, stream)

def snap_case_folded_pattern(sh, PatternDict, NumberSetF=False):
    """Parse a case fold expression of the form \C(..){ R } or \C{ R }.
       Assume that '\C' has been snapped already from the stream.

       See function ucs_case_fold_parser.get_fold_set() for details
       about case folding.
    """
    def __add_intermediate_states(sm, character_list, start_state_idx, target_state_idx):
        next_idx = start_state_idx
        for letter in character_list[:-1]:
            next_idx = sm.add_transition(next_idx, letter)
        sm.add_transition(next_idx, character_list[-1], target_state_idx)

    def __add_case_fold(sm, Flags, trigger_set, start_state_idx, target_state_idx):
        for interval in trigger_set.get_intervals(PromiseToTreatWellF=True):
            for fold in ucs_case_fold.get_fold_set_for_interval(interval, Flags):
                if len(fold) > 1:
                    __add_intermediate_states(sm, fold, start_state_idx, target_state_idx)
                else:
                    trigger_set.add_interval(Interval(fold[0]))


    pos = sh.tell()
    skip_whitespace(sh)
    # -- parse the optional options in '(' ')' brackets
    if NumberSetF: default_flag_txt = "s"
    else:          default_flag_txt = "sm"

    flag_txt = optional_flags(sh, "case fold",
                              default_flag_txt,
                              { "s": "simple case fold",
                                "m": "multi character sequence case fold",
                                "t": "special turkish case fold rules", },
                              [])

    if NumberSetF and "m" in flag_txt:
        sh.seek(pos)
        error.log("Option 'm' not permitted as case fold option in set expression.\n" + \
                  "Set expressions cannot absorb multi character sequences.", sh)

    skip_whitespace(sh)

    result = snap_curly_bracketed_expression(sh, PatternDict, "case fold operator", "C")[0]

    if NumberSetF:
        trigger_set = result.get_number_set()
        if trigger_set is None or trigger_set.is_empty():
            error.log("Expression in case fold does not result in character set.\n" + 
                      "The content in '\\C{content}' may start with '[' or '[:'.", sh)

        # -- perform the case fold for Sets!
        for interval in trigger_set.get_intervals(PromiseToTreatWellF=True):
            for fold in ucs_case_fold.get_fold_set_for_interval(interval, flag_txt):
                trigger_set.add_interval(Interval(fold[0]))

        result = trigger_set

    else:
        # -- perform the case fold for DFAs!
        for state_idx, state in list(result.states.items()):
            for target_state_idx, trigger_set in list(state.target_map.get_map().items()):
                __add_case_fold(result, flag_txt, trigger_set, state_idx, target_state_idx)

    return result

def snap_command(stream, positionOfBackslash, PatternDict):
    global CommandDB
    pos       = stream.tell()
    char_code = snap_backslashed_character.do(stream, ExceptionOnNoMatchF=False, 
                                              HexNumbersF=False)
    if char_code is not None:
        return DFA.from_character_set(NumberSet.from_integer(char_code))

    stream.seek(pos)
    identifier = read_identifier(stream)
    if not identifier: stream.seek(pos); return None

    entry = CommandDB.get(identifier)
    if entry:
        position_required_f, snap_func = entry
        if position_required_f:
            return snap_func(stream, positionOfBackslash, PatternDict)
        else:
            return snap_func(stream, PatternDict)

    if any(identifier.startswith(letter) for letter in ("x", "X", "U")):
        stream.seek(pos + 1)
        position_required_f, snap_func = CommandDB[identifier[0]]
        return snap_func(stream, PatternDict)

    if "\\%s" % identifier in DEFINE_SECTION_COMMAND_SET:
        error.log("Found command '\\%s' in regular expression.\n" % identifier \
                  + "Are there missing closing brackets?", stream)
    error.verify_word_in_list(identifier, [x for x in CommandDB],
                              "Unidentified command '\\%s'." % identifier,
                              stream)
    
def snap_non_control_character(stream, PatternDict):
    __debug_entry("non-control characters", stream)

    # (*) read first character
    char_code = ord(stream.read(1))
    if char_code is None:
        error.log("Character could not be interpreted as UTF8 code or End of File reached prematurely.", 
                  stream)
    result = DFA.from_character_set(char_code)
    return __debug_exit(result, stream)
    
@typed(the_state_machine=DFA)
def __snap_repetition_range(the_state_machine, stream):    
    """Snaps a string that represents a repetition range. The following 
       syntaxes are supported:
           '?'      one or none repetition
           '+'      one or arbitrary repetition
           '*'      arbitrary repetition (even zero)
           '{n}'    exactly 'n' repetitions
           '{m,n}'  from 'm' to 'n' repetitions
           '{n,}'   arbitrary, but at least 'n' repetitions
    """       
    position_0 = stream.tell()
    x = stream.read(1)
    if   x == "+": result = repeat.do(the_state_machine, 1)
    elif x == "*": result = repeat.do(the_state_machine)
    elif x == "?": result = repeat.do(the_state_machine, 0, 1)
    elif x == "{":
        repetition_range_str = snap_until(stream, "}")
        if len(repetition_range_str) and not repetition_range_str[0].isdigit():
            # no repetition range, so everything remains as it is
            stream.seek(position_0)
            return the_state_machine
            
        try:
            if repetition_range_str.find(",") == -1:
                # no ',' thus "match exactly a certain number": 
                # e.g. {4} = match exactly four repetitions
                number = int(repetition_range_str)
                result = repeat.do(the_state_machine, number, number)
                return result
            # a range of numbers is given       
            fields = repetition_range_str.split(",")
            fields = [field.strip() for field in fields]

            number_1 = int(fields[0].strip())
            if fields[1] == "": number_2 = -1                      # e.g. {2,}
            else:               number_2 = int(fields[1].strip())  # e.g. {2,5}  
            # produce repeated state machine 
            result = repeat.do(the_state_machine, number_1, number_2)
            return result
        except:
            raise RegularExpressionException("error while parsing repetition range expression '%s'" \
                                             % repetition_range_str)
    else:
        # no repetition range, so everything remains as it is
        stream.seek(position_0)
        return the_state_machine
    
    return result

def create_ALL_BUT_NEWLINE_state_machine(stream):
    global Setup
    result = DFA()
    # NOTE: Buffer control characters are supposed to be filtered out by the code
    #       generator.
    trigger_set = NumberSet(Interval(ord("\n"))).get_complement(Setup.buffer_encoding.source_set)
    if trigger_set.is_empty():
        error.log("The set of admissible characters contains only newline.\n"
                  "The '.' for 'all but newline' is an empty set.",
                  SourceRef.from_FileHandle(stream))

    result.add_transition(result.init_state_index, trigger_set, AcceptanceF=True) 
    return result
    
def snap_bracketed_expression(stream, PatternDict):
    position = stream.tell()
    result = snap_expression(stream, PatternDict)
    if not check(stream, ")"): 
        stream.seek(position)
        remainder_txt = stream.readline().replace("\n", "").replace("\r", "")
        raise RegularExpressionException("Missing closing ')' after expression; found '%s'.\n" % remainder_txt \
                                         + "Note, that patterns end with the first non-quoted whitespace.\n" \
                                         + "Also, closing brackets in quotes do not close a syntax block.")

    if result is None:
        length = stream.tell() - position
        stream.seek(position)
        raise RegularExpressionException("expression in brackets has invalid syntax '%s'" % \
                                         stream.read(length))
    return result

def snap_nothing(stream, PatternDict):
    return DFA.Nothing()

def snap_any(stream, PatternDict):
    return DFA.Any()

def snap_universal(stream, PatternDict):
    return DFA.Universe()

def snap_empty(stream, PatternDict):
    return DFA.Empty()

def snap_reverse(stream, PatternDict):
    result = snap_curly_bracketed_expression(stream, PatternDict, "reverse operator", "R")[0]
    return reverse.do(result, EnsureDFA_f=False)

def snap_sanitizer(stream, PatternDict):
    result = snap_curly_bracketed_expression(stream, PatternDict, "sanatizer operator", "A")[0]
    return sanitizer.do(result)

def snap_stem(stream, PatternDict):
    result = snap_curly_bracketed_expression(stream, PatternDict, "\\Stem", "A")[0]
    return stem_and_branches.stem(result)

def snap_crown(stream, PatternDict):
    result = snap_curly_bracketed_expression(stream, PatternDict, "\\Crown", "A")[0]
    return stem_and_branches.crown(result)
def snap_sanitized_complement(stream, PatternDict):
    result = snap_curly_bracketed_expression(stream, PatternDict, "anti-pattern operator", "A")[0]
    return sanitizer.do(complement.do(result))

def snap_complement(stream, PatternDict):
    pattern_list = snap_curly_bracketed_expression(stream, PatternDict, "complement operator", "Not")
    if len(pattern_list) == 1: tmp = pattern_list[0]
    else:                      tmp = union.do(pattern_list)
    return complement.do(tmp)

def snap_union(stream, PatternDict):
    pattern_list = snap_curly_bracketed_expression(stream, PatternDict, "union operator", "Union", 
                                                   MinN=2, MaxN=INTEGER_MAX)
    return union.do(pattern_list)

def snap_intersection(stream, PatternDict):
    pattern_list = snap_curly_bracketed_expression(stream, PatternDict, "intersection operator", "Intersection", 
                                                   MinN=2, MaxN=INTEGER_MAX)
    return intersection.do(pattern_list)

def snap_two_or_union_of_more_state_machines(Func, stream, PatternDict, Name, Cmd):
    sm_list = snap_curly_bracketed_expression(stream, PatternDict, Name, Cmd, 
                                              MinN=2, MaxN=INTEGER_MAX)
    sm0 = sm_list[0]
    if len(sm_list) == 2: sm1 = sm_list[1]
    else:                 sm1 = union.do(sm_list[1:])

    return Func(sm0, sm1)

def snap_first(stream, PatternDict):
    pattern_list = snap_curly_bracketed_expression(stream, PatternDict, "complement operator", "Not")
    return cut.first(pattern_list)

def snap_not_first(stream, PatternDict):
    pattern_list = snap_curly_bracketed_expression(stream, PatternDict, "complement operator", "Not")
    return cut.first_complement(pattern_list, Setup.buffer_encoding.source_set)

def snap_cut_begin(stream, PatternDict):
    return snap_two_or_union_of_more_state_machines(cut.cut_begin,
                                                    stream, PatternDict,
                                                    "cut-begin", "CutBegin")

def snap_cut_end(stream, PatternDict):
    return snap_two_or_union_of_more_state_machines(cut.cut_end,
                                                    stream, PatternDict,
                                                    "cut-end", "CutEnd")

def snap_leave_begin(stream, PatternDict):
    return snap_two_or_union_of_more_state_machines(cut.leave_begin,
                                                    stream, PatternDict,
                                                    "leave-begin", "LeaveBegin")

def snap_leave_end(stream, PatternDict):
    return snap_two_or_union_of_more_state_machines(cut.leave_end,
                                                    stream, PatternDict,
                                                    "leave-end", "LeaveEnd")

def snap_infimum_deviant(stream, PatternDict):
    pattern_list = snap_curly_bracketed_expression(stream, PatternDict, "infimum deviant", "InfDev")
    if len(pattern_list) == 1: tmp = pattern_list[0]
    else:                      tmp = union.do(pattern_list)
    return complement_variants.infimum_deviant(tmp)

def snap_acceptance_flush(stream, PatternDict):
    pattern_list = snap_curly_bracketed_expression(stream, PatternDict, "acceptance flush", "AccFlush")
    if len(pattern_list) == 1: tmp = pattern_list[0]
    else:                      tmp = union.do(pattern_list)
    return complement_variants.acceptance_flush(tmp)

def snap_acceptance_inversion(stream, PatternDict):
    pattern_list = snap_curly_bracketed_expression(stream, PatternDict, "acceptance inversion", "AccInv")
    if len(pattern_list) == 1: tmp = pattern_list[0]
    else:                      tmp = union.do(pattern_list)
    return complement_variants.acceptance_inversion(tmp)

def snap_begin(stream, PatternDict):
    return snap_two_or_union_of_more_state_machines(derived.is_begin, 
                                                    stream, PatternDict, 
                                                    "begin operator", "Begin") 

def snap_end(stream, PatternDict):
    return snap_two_or_union_of_more_state_machines(derived.is_end, 
                                                    stream, PatternDict, 
                                                    "end operator", "End") 

def snap_in(stream, PatternDict):
    return snap_two_or_union_of_more_state_machines(derived.is_in, 
                                                    stream, PatternDict, 
                                                    "in operator", "In") 

def snap_not_begin(stream, PatternDict):
    return snap_two_or_union_of_more_state_machines(derived.not_begin, 
                                                    stream, PatternDict, 
                                                    "not-begin operator", "NotBegin") 

def snap_not_end(stream, PatternDict):
    return snap_two_or_union_of_more_state_machines(derived.not_end, 
                                                    stream, PatternDict, 
                                                    "not-end operator", "NotEnd") 

def snap_not_in(stream, PatternDict):
    return snap_two_or_union_of_more_state_machines(derived.not_in, 
                                                    stream, PatternDict, 
                                                    "not-in operator", "NotIn") 

def snap_difference(stream, PatternDict):
    sm_list = snap_curly_bracketed_expression(stream, PatternDict, "difference operator", "Diff",
                                              MinN=2, MaxN=2)
    return difference.do(sm_list[0], sm_list[1])

def snap_symmetric_difference(stream, PatternDict):
    sm_list = snap_curly_bracketed_expression(stream, PatternDict, "intersection operator", "Intersection", 
                                              MinN=2, MaxN=2)
    return symmetric_difference.do(sm_list)

def snap_curly_bracketed_expression(stream, PatternDict, Name, TriggerChar, MinN=1, MaxN=1):
    """Snaps a list of RE's in '{' and '}'. The separator between the patterns 
    is whitespace. 'MinN' and 'MaxN' determine the number of expected patterns.
    Set 'MaxN=INTEGER_MAX' for an arbitrary number of patterns.

    RETURNS: result = list of patterns, if MinN <= len(result) <= MaxN 
             else, the function sys.exit()-s.
    """
    assert MinN <= MaxN
    assert MinN > 0

    skip_whitespace(stream)

    # Read over the trigger character 
    if not check(stream, "{"):
        error.log("Missing opening '{' after %s %s." % (Name, TriggerChar), stream)

    result = []
    while 1 + 1 == 2:
        pattern = snap_expression(stream, PatternDict) 
        if pattern is not None:
            result.append(pattern)

        if check(stream, "}"):
            break
        elif check_whitespace(stream):
            continue
        elif check(stream, "/") or check(stream, "$"):
            error.log("Pre- or post contexts are not allowed in %s \\%s{...} expressions." % (Name, TriggerChar), stream)
        else:
            error.log("Missing closing '}' %s in \\%s{...}." % (Name, TriggerChar), stream)

    if MinN != MaxN:
        if len(result) < MinN:
            error.log("At minimum %i pattern%s required between '{' and '}'" \
                      % (MinN, "" if MinN == 1 else "s"), stream)
        if len(result) > MaxN:
            error.log("At maximum %i pattern%s required between '{' and '}'" \
                      % (MaxN, "" if MaxN == 1 else "s"), stream)
    else:
        if len(result) != MinN:
            error.log("Exactly %i pattern%s required between '{' and '}'" \
                      % (MinN, "" if MinN == 1 else "s"), stream)

    def ensure_dfa(sm):
        if not sm.is_DFA_compliant(): return nfa_to_dfa.do(sm)
        else:                         return sm

    return [ensure_dfa(sm) for sm in result]

def _edit_distance_check_cycles(Dfa, OpName, stream):
    if not Dfa.has_cycles(): return
    error.warning("DFA contains loop.\n"
                  "Edit distance operation '%s' might match more than expected." % OpName,
                  stream)

def _snap_call_ed_function(stream, Name, func, VariableList, PatternDict):
    if not check(stream, "{"):
        error.log("Missing opening '{' after %s." % Name, stream)

    VariableList.insert(0, Argument("dfa",     "dfa",              None)) 
    argument_db = _macro_parse_argument_setting(stream, VariableList, Name, PatternDict)
    dfa         = argument_db["dfa"]
    _edit_distance_check_cycles(dfa, Name, stream)

    # x[1] = variable name
    arg = [argument_db[x[1]] for x in VariableList]
    return func(*arg)

def snap_ed_insertion(stream, PatternDict):
    return _snap_call_ed_function(stream, "EdInsert", edit_distance.insert_upto, 
                                  [Argument("integer", "insertion_number",    0), 
                                   Argument("set",     "concerned_cs",     NumberSet_All())], PatternDict)

def snap_ed_insertion_n(stream, PatternDict):
    return _snap_call_ed_function(stream, "EdInsertN", edit_distance.insert, 
                                  [Argument("integer", "insertion_number",    0), 
                                   Argument("set",     "concerned_cs",        NumberSet_All())], PatternDict)
    
def snap_ed_deletion(stream, PatternDict):
    return _snap_call_ed_function(stream, "EdDelete", edit_distance.delete_upto, 
                                  [Argument("integer", "deletion_number",     0), 
                                   Argument("set",     "concerned_cs",        NumberSet_All())], PatternDict)

def snap_ed_deletion_n(stream, PatternDict):
    return _snap_call_ed_function(stream, "EdDeleteN", edit_distance.delete, 
                                  [Argument("integer", "deletion_number",     0), 
                                   Argument("set",     "concerned_cs",        NumberSet_All())], PatternDict)

def snap_ed_substitution(stream, PatternDict):
    return _snap_call_ed_function(stream, "EdSubstitute", edit_distance.substitute_upto, 
                                  [Argument("integer", "substitution_number", 0), 
                                   Argument("set",     "concerned_cs",        NumberSet_All()),
                                   Argument("set",     "substitute_set",      NumberSet_All())], PatternDict)

def snap_ed_substitution_n(stream, PatternDict):
    return _snap_call_ed_function(stream, "EdSubstituteN", edit_distance.substitute, 
                                  [Argument("integer", "substitution_number", 0), 
                                   Argument("set",     "concerned_cs",        NumberSet_All()),
                                   Argument("set",     "substitute_set",      NumberSet_All())], PatternDict)

def snap_ed_transposition(stream, PatternDict):
    return _snap_call_ed_function(stream, "EdTransposition", transposition.do_upto, 
                                  [Argument("integer", "transposition_number", 0), 
                                   Argument("set",     "concerned_cs",        NumberSet_All())], PatternDict)

def snap_ed_transposition_n(stream, PatternDict):
    return _snap_call_ed_function(stream, "EdTranspositionN", transposition.do, 
                                  [Argument("integer", "transposition_number", 0), 
                                   Argument("set",     "concerned_cs",         NumberSet_All())], PatternDict)

def snap_ed_levenshtein(stream, PatternDict):
    variable_list = [ 
        Argument("integer", "levenshtein_distance", 0), 
        Argument("set",     "insertable_cs",        NumberSet_All()),
        Argument("set",     "deletable_cs",         NumberSet_All()),
        Argument("set",     "substitutable_cs",     NumberSet_All()),
        Argument("set",     "substitute_cs",        NumberSet_All())
    ]
    return _snap_call_ed_function(stream, "EdLevenshtein", levenshtein.do, 
                                  variable_list, PatternDict)

def snap_ed_pseudo_damerau(stream, PatternDict):
    variable_list = [ 
        Argument("integer", "levenshtein_distance", 0), 
        Argument("set",     "insertable_cs",        NumberSet_All()),
        Argument("set",     "deletable_cs",         NumberSet_All()),
        Argument("set",     "substitutable_cs",     NumberSet_All()),
        Argument("set",     "substitute_cs",        NumberSet_All()),
        Argument("set",     "transposable_cs",      NumberSet_All())
    ]
    return _snap_call_ed_function(stream, "EdPseudoDamerau", pseudo_damerau.do, 
                                  variable_list, PatternDict)

def snap_unicode_property_P(stream, position, PatternDict=None, DfaRequiredF=True):
    stream.seek(position)
    result = unicode_property.do(stream)
    if DfaRequiredF: return DFA.from_character_set(result)
    else:            return result

def snap_unicode_property_N(stream, position, PatternDict=None, DfaRequiredF=True):
    stream.seek(position)
    result = unicode_property.do_shortcut(stream, "N", "na") # UCS Property: Name
    if DfaRequiredF: return DFA.from_character_set(result)
    else:            return result

def snap_unicode_property_G(stream, position, PatternDict=None, DfaRequiredF=True):
    stream.seek(position)
    result = unicode_property.do_shortcut(stream, "G", "gc") # UCS Property: General_Category
    if DfaRequiredF: return DFA.from_character_set(result)
    else:            return result

def snap_unicode_property_E(stream, PatternDict=None, DfaRequiredF=True):
    skip_whitespace(stream)
    if check(stream, "{") == False:
        error.log("Missing '{' after '\\E'.", stream)
    encoding_name = snap_until(stream, "}").strip()
    result = codec_db.get_supported_unicode_character_set(encoding_name)
    if result is None:
        error.log("Error occured at this place.", stream)

    if DfaRequiredF: return DFA.from_character_set(result)
    else:            return result

__DNA_replacement_db = {
    ord("R"):   NumberSet.from_integer_list([ord(x) for x in "GA"]),
    ord("Y"):   NumberSet.from_integer_list([ord(x) for x in "TC"]),
    ord("M"):   NumberSet.from_integer_list([ord(x) for x in "AC"]),
    ord("K"):   NumberSet.from_integer_list([ord(x) for x in "GT"]),
    ord("S"):   NumberSet.from_integer_list([ord(x) for x in "GC"]),
    ord("W"):   NumberSet.from_integer_list([ord(x) for x in "AT"]),
    ord("H"):   NumberSet.from_integer_list([ord(x) for x in "ACT"]),
    ord("B"):   NumberSet.from_integer_list([ord(x) for x in "GTC"]),
    ord("V"):   NumberSet.from_integer_list([ord(x) for x in "GCA"]),
    ord("D"):   NumberSet.from_integer_list([ord(x) for x in "GTA"]),
    ord("N"):   NumberSet.from_integer_list([ord(x) for x in "GTAC"]), 
}
__DNA_nucleotide = NumberSet.from_integer_list(list(__DNA_replacement_db.keys()) + [ord(x) for x in "GATC"])
__RNA_replacement_db = {
    ord("R"):   NumberSet.from_integer_list([ord(x) for x in "GA"]),
    ord("Y"):   NumberSet.from_integer_list([ord(x) for x in "UC"]),
    ord("M"):   NumberSet.from_integer_list([ord(x) for x in "AC"]),
    ord("K"):   NumberSet.from_integer_list([ord(x) for x in "GU"]),
    ord("S"):   NumberSet.from_integer_list([ord(x) for x in "GC"]),
    ord("W"):   NumberSet.from_integer_list([ord(x) for x in "AU"]),
    ord("H"):   NumberSet.from_integer_list([ord(x) for x in "ACU"]),
    ord("B"):   NumberSet.from_integer_list([ord(x) for x in "GUC"]),
    ord("V"):   NumberSet.from_integer_list([ord(x) for x in "GCA"]),
    ord("D"):   NumberSet.from_integer_list([ord(x) for x in "GUA"]),
    ord("N"):   NumberSet.from_integer_list([ord(x) for x in "GUAC"]), 
}
__RNA_nucleotide = NumberSet.from_integer_list(list(__RNA_replacement_db.keys()) + [ord(x) for x in "GAUC"])

def __snap_nucleotide_expresssion(stream, PatternDict, Name, NucleotideSet, NucleotidDb):
    dfa = snap_curly_bracketed_expression(stream, PatternDict, "%s expression" % Name, Name)[0]
    all_set = dfa.get_union_of_number_sets()

    if not NucleotideSet.is_superset(all_set):
        error.log("DNA pattern contains nucletoide bases beyond the admissible range.\n"
                  "Use only: '%s'." % ", ".join(quex_chr(x) for x in NucleotideSet.get_number_list()),
                  stream)
    dfa.replace_triggers(NucleotidDb)
    return dfa

def snap_DNA(stream, PatternDict, DfaRequiredF=True):
    """Parse a DNA expression and interpret the nucleotide as alternatives.
       DNA has 'T' (thymin) but no 'U' (uracil).
    """
    return __snap_nucleotide_expresssion(stream, PatternDict, "DNA",
                                         __DNA_nucleotide, __DNA_replacement_db)

def snap_RNA(stream, PatternDict, DfaRequiredF=True):
    """Parse a RNA expression and interpret the nucleotide as alternatives.
       DNA has no 'T' (thymin) but has 'U' (uracil).
    """
    return __snap_nucleotide_expresssion(stream, PatternDict, "RNA",
                                         __RNA_nucleotide, __RNA_replacement_db)

def snap_hex_number_2(stream, PatternDict=None, DfaRequiredF=True):
    number = __parse_hex_number(stream, 2)
    return DFA.from_character_set(NumberSet.from_integer(number))

def snap_hex_number_4(stream, PatternDict=None, DfaRequiredF=True):
    number = __parse_hex_number(stream, 4)
    return DFA.from_character_set(NumberSet.from_integer(number))

def snap_hex_number_6(stream, PatternDict=None, DfaRequiredF=True):
    number = __parse_hex_number(stream, 6)
    return DFA.from_character_set(NumberSet.from_integer(number))

# MUST BE SORTED WITH LONGEST PATTERN FIRST!
CommandDB = {
   "Any":          (False, snap_any),
   # Note, that there are backlashed elements that may appear also in strings.
   # \a, \r, ... those are not treated here. They are treated in 
   # 'snap_backslashed_character()'.
   "x":            (False, snap_hex_number_2),
   "X":            (False, snap_hex_number_4),
   "U":            (False, snap_hex_number_6),
   # Case folding, Reversion
   "C":            (False, snap_case_folded_pattern),
   # Unicode Property Sets
   "P":            (True, snap_unicode_property_P),
   "N":            (True, snap_unicode_property_N),
   "G":            (True, snap_unicode_property_G),
   "E":            (False, snap_unicode_property_E),
   # DNA/RNA
   "DNA":          (False, snap_DNA),
   "RNA":          (False, snap_RNA),
   # DFA Algebra
   "Intersection": (False, snap_intersection),
   "Union":        (False, snap_union),
   "Not":          (False, snap_complement),
   "Diff":         (False, snap_difference),
   "SymDiff":      (False, snap_symmetric_difference),
   # Singular DFAs
   "Universe":    (False, snap_universal),
   "Empty":        (False, snap_empty),
   "Nothing":      (False, snap_nothing),
   #
   "Sanitize":     (False, snap_sanitizer),
   #
   "Begin":        (False, snap_begin),
   "End":          (False, snap_end),
   "In":           (False, snap_in),
   "NotBegin":     (False, snap_not_begin),
   "NotEnd":       (False, snap_not_end),
   "NotIn":        (False, snap_not_in),
   #
   "First":        (False, snap_first),
   "NotFirst":     (False, snap_not_first),
   #
   "CutBegin":     (False, snap_cut_begin),
   "CutEnd":       (False, snap_cut_end),
   "LeaveBegin":   (False, snap_leave_begin),
   "LeaveEnd":     (False, snap_leave_end),
   #
   "A":            (False, snap_sanitized_complement),
   "R":            (False, snap_reverse),
   "Stem":         (False, snap_stem),
   "Crown":        (False, snap_crown),
   "InfDev":       (False, snap_infimum_deviant),
   "AccFlush":     (False, snap_acceptance_flush),
   "AccInv":       (False, snap_acceptance_inversion),
   #
   # Edit Distance / Levenstein Distance
   "EdInsert":        (False, snap_ed_insertion),
   "EdInsertN":       (False, snap_ed_insertion_n),
   "EdDelete":        (False, snap_ed_deletion),
   "EdDeleteN":       (False, snap_ed_deletion_n),
   "EdSubstitute":    (False, snap_ed_substitution),
   "EdSubstituteN":   (False, snap_ed_substitution_n),
   "EdTranspose":     (False, snap_ed_transposition),
   "EdTransposeN":    (False, snap_ed_transposition_n),
   "EdLevenshtein":   (False, snap_ed_levenshtein),
   "EdPseudoDamerau": (False, snap_ed_pseudo_damerau),
}

special_character_set_db = {
    # The closing ']' is to trigger the end of the traditional character set
    "alnum":  "a-zA-Z0-9]",
    "alpha":  "a-zA-Z]",
    "blank":  " \\t]",
    "cntrl":  "\\x00-\\x1F\\x7F]", 
    "digit":  "0-9]",
    "graph":  "\\x21-\\x7E]",
    "lower":  "a-z]",
    "print":  "\\x20-\\x7E]", 
    "punct":  "!\"#$%&'()*+,-./:;?@[\\]_`{|}~\\\\]",
    "space":  " \\t\\r\\n]",
    "upper":  "A-Z]",
    "xdigit": "a-fA-F0-9]",
}

def snap_character_set_expression(stream, PatternDict):
    # GRAMMAR:
    #
    # set_expression: 
    #                 [: set_term :]
    #                 traditional character set
    #                 \P '{' propperty string '}'
    #                 '{' identifier '}'
    #
    # set_term:
    #                 "alnum" 
    #                 "alpha" 
    #                 "blank" 
    #                 "cntrl" 
    #                 "digit" 
    #                 "graph" 
    #                 "lower" 
    #                 "print" 
    #                 "punct" 
    #                 "space" 
    #                 "upper" 
    #                 "xdigit"
    #                 "union"        '(' set_term [ ',' set_term ]+ ')'
    #                 "intersection" '(' set_term [ ',' set_term ]+ ')'
    #                 "difference"   '(' set_term [ ',' set_term ]+ ')'
    #                 "complement"   '(' set_term ')'
    #                 set_expression
    # 
    trigger_set = snap_set_expression(stream, PatternDict)

    if trigger_set is None: 
        error.log("Regular Expression: snap_character_set_expression called for something\n" + \
                  "that does not start with '[:', '[' or '\\P'", stream)
    elif trigger_set.is_empty():
        error.warning("Regular Expression: Character set expression results in empty set.", stream)

    return __debug_exit(DFA.from_character_set(trigger_set), stream)

def snap_set_expression(stream, PatternDict):
    __debug_entry("set_expression", stream)

    result = snap_property_set(stream)
    if result is not None: return __debug_exit(result, stream)

    first  = stream.read(1)
    pos1   = stream.tell()
    second = stream.read(1)
    x = first + second
    if   x == "\\C":
        result = snap_case_folded_pattern(stream, PatternDict, NumberSetF=True)

    elif x == "[:":
        result = snap_set_term(stream, PatternDict)
        skip_whitespace(stream)
        x = stream.read(2)
        if x != ":]":
            raise RegularExpressionException("Missing closing ':]' for character set expression.\n" + \
                                             "found: '%s'" % x)
    elif x[0] == "[":
        stream.seek(pos1)
        result = traditional_character_set.do(stream)   

    elif x[0] == "{":
        stream.seek(pos1)
        result = _snap_expansion(stream, PatternDict, StateMachineF=False)   

    else:
        result = None

    return __debug_exit(result, stream)

def snap_property_set(stream):
    position = stream.tell()
    x = stream.read(2)
    if x == "\\E": 
       return snap_unicode_property_E(stream, DfaRequiredF=False)
    elif x == "\\P": return snap_unicode_property_P(stream, position, DfaRequiredF=False)
    elif x == "\\N": return snap_unicode_property_N(stream, position, DfaRequiredF=False)
    elif x == "\\G": return snap_unicode_property_G(stream, position, DfaRequiredF=False)
    else:
        stream.seek(position)
        return None

def snap_set_term(stream, PatternDict):
    global special_character_set_db

    __debug_entry("set_term", stream)    

    operation_list     = [ 
        "union", "intersection", "difference", "complement",
        "inverse"  # => Detect deprecated "inverse" instead of "complement".
    ]
    character_set_list = list(special_character_set_db.keys())

    skip_whitespace(stream)
    position = stream.tell()

    # if there is no following '(', then enter the 'snap_expression' block below
    word = read_identifier(stream)

    if word in operation_list: 
        set_list = snap_set_list(stream, word, PatternDict)
        # if an error occurs during set_list parsing, an exception is thrown about syntax error

        L      = len(set_list)
        result = set_list[0]

        if word == "inverse":
            error.log("Usage of 'inverse' instead of 'complement'", stream)

        elif word == "complement":
            # The inverse of multiple sets, is to be the inverse of the union of these sets.
            if L > 1:
                for character_set in set_list[1:]:
                    result.unite_with(character_set)
            return __debug_exit(result.get_complement(Setup.buffer_encoding.source_set), stream)

        elif L < 2:
            error.log("Regular Expression: A %s operation needs at least\n" % word + \
                      "two sets to operate on them.",
                      stream)
            
        elif word == "union":
            for sub_set in set_list[1:]:
                result.unite_with(sub_set)
        elif word == "intersection":
            for sub_set in set_list[1:]:
                result.intersect_with(sub_set)
        elif word == "difference":
            for sub_set in set_list[1:]:
                result.subtract(sub_set)

    elif word in character_set_list:
        reg_expr = special_character_set_db[word]
        result   = traditional_character_set.do(UniStream(reg_expr))

    elif word:
        error.verify_word_in_list(word, character_set_list + operation_list, 
                                  "Unknown keyword '%s'." % word, stream)
    else:
        stream.seek(position)
        result = snap_set_expression(stream, PatternDict)

    return __debug_exit(result, stream)

def snap_set_list(stream, set_operation_name, PatternDict):
    __debug_entry("set_list", stream)

    skip_whitespace(stream)
    if stream.read(1) != "(": 
        error.log("Missing opening bracket '%s' operation." % set_operation_name,
                  stream)

    set_list = []
    while 1 + 1 == 2:
        skip_whitespace(stream)
        result = snap_set_term(stream, PatternDict)
        if result is None: 
            error.log("Missing set expression list after %s operation." % set_operation_name,
                      stream)
        set_list.append(result)
        skip_whitespace(stream)
        pos = stream.tell()
        tmp = stream.read(1)
        if tmp != ",": 
            if tmp != ")":
                stream.seek(pos)
                error.log("Missing closing ')' or argument seperator ',' in %s operation." % set_operation_name,
                          stream)
            return __debug_exit(set_list, stream)

def _snap_expansion(stream, PatternDict, StateMachineF=True, IntegerF=False):
    """Snaps a predefined pattern from the input string and returns the resulting
       state machine.
    """ 
    skip_whitespace(stream)
    pattern_name = read_identifier(stream)  
    if not pattern_name:
        raise RegularExpressionException("Pattern replacement expression misses identifier after '{'.")

    ## print "#PatternDict:", id(PatternDict), PatternDict
    error.verify_word_in_list(pattern_name, list(PatternDict.keys()),
                             "Specifier '%s' not found in any preceeding 'define { ... }' section." % pattern_name, 
                             stream)

    reference = PatternDict[pattern_name]
    assert isinstance(reference, PatternShorthand)

    def _notify_if_error(result, TypeName):
        if result is not None: return
        error.log("Expansion of '%s' does not result in a object of type '%s'.\n" % (pattern_name, TypeName),
                  stream)

    macro = reference.get_MacroCall()
    if macro is not None:
        argument_setting_db = _macro_parse_argument_setting(stream, 
                                                            macro.argument_list, 
                                                            pattern_name, 
                                                            PatternDict)
        result = _macro_evaluate(macro, argument_setting_db, PatternDict)

    elif not check(stream, "}", SkipWhitespaceExceptNewlineF=True):
        error.log("Missing closing '}' for shorthand expansion '%s'." % pattern_name,
                  stream)

    elif IntegerF:
        result = reference.get_integer()
        _notify_if_error(result, "integer")

    elif StateMachineF:
        result = reference.get_DFA()
        _notify_if_error(result, "dfa")
        assert not result.has_specific_acceptance_id()
    else:
        result = reference.get_NumberSet()
        _notify_if_error(result, "set")
        if result.is_empty():
            error.warning("Referenced character set '%s' is empty." % pattern_name, stream)

    return result

def _macro_evaluate(macro, ArgumentSettingDb, PatternDict):
    # backup variables that are overwritten by local parameters
    backup_dict = dict(
        (name, setting)
        for name, setting in PatternDict.items()
        if name in ArgumentSettingDb
    )

    PatternDict.update(
        (name, PatternShorthand(name, setting))
        for name, setting in ArgumentSettingDb.items())

    # Parse the regular expression
    string_handle              = UniStream(macro.source_txt)
    string_handle.reference_sr = macro.sr

    result = __core(string_handle, PatternDict=PatternDict)

    # reset variables that have been temporarily overwritten
    for name in ArgumentSettingDb:
        del PatternDict[name]
    PatternDict.update(backup_dict)

    return result

def _macro_parse_argument_setting(stream, VariableList, PatterName, PatternDict):
    """VariableList: 
        
    list of tuples

          (argment type, argument name, argument default value)
    
    RETURN: 
          argument name --> (argument type, argument value)

    If argument has not been specified, then the default value is taken.
    """
    def _report_in_case_of_error(stream, result, ArgN, ArgName, ArgType):
        if result is not None: return result
        error.log("Missing %s for parameter %s '%s'." % (ArgType, ArgN, ArgName), stream)

    def _parse(stream, ArgN, ArgName, ArgType, PatternDict):
        if ArgType == "integer":
            result = read_integer(stream)
            if result is None and check(stream, "{"):
                result = _snap_expansion(stream, PatternDict, StateMachineF=False, IntegerF=True)
        elif ArgType == "dfa":
            result = __core(stream, PatternDict=PatternDict)
        elif ArgType == "set":
            result = __core(stream, PatternDict=PatternDict)
            if result is not None:
                result = result.get_number_set()
        else:
            assert False
        return _report_in_case_of_error(stream, result, ArgN, ArgName, ArgType)

    result = {}
    i      = -1
    for i, arg in enumerate(VariableList):
        skip_whitespace(stream)
        if check(stream, "}"): i -= 1; break

        arg_value = _parse(stream, i+1, arg.name, arg.type, PatternDict)
        result[arg.name] = arg_value
    else:
        skip_whitespace(stream)
        if not check(stream, "}"): 
            error.log("Too many arguments in macro expansion '%s'." % PatterName, stream)

    result.update(
        (arg.name, arg.default) for arg in VariableList[i+1:]
    )

    return result
    
def __error_check(ConditionLine, ConditionStream, Sm, stream, Name):
    condition_n = 0
    if   ConditionLine:   condition_n += 1
    elif ConditionStream: condition_n += 1
    elif Sm is not None:  condition_n += 1

    if condition_n > 1:
        error.log("More than one %s." % Name, stream)
        # mention only to prevent 'unused'
        __debug_print_stream("<none>", stream)

charCode_backslash = ord("\\")
charCode_quote     = ord("\"")
def snap_character_code_iterable(sh):
    """Converts a uni-code string into a state machine that parses 
       its letters sequentially. Each state in the sequence correponds
       to the sucessful triggering of a letter. Only the last state, though,
       is an acceptance state. Any bailing out before is 'not accepted'. 
       Example:

       "hey" is translated into the state machine:

           (0)-- 'h' -->(1)-- 'e' -->(2)-- 'y' --> ACCEPTANCE
            |            |            |
           FAIL         FAIL         FAIL
    
      Note: The state indices are globally unique. But, they are not necessarily
            0, 1, 2, ... 
    """
    while 1 + 1 == 2:
        # Only \" is a special character '"', any other backslashed character
        # remains as the sequence 'backslash' + character
        char = sh.read(1)
        if not char: 
            raise RegularExpressionException("End of file reached while parsing quoted string.")
        char_code = ord(char)
        if char_code == charCode_backslash:
            char_code = snap_backslashed_character.do(sh)
            if char_code is None: 
                raise RegularExpressionException("Unidentified backslash-sequence in quoted string.")
        elif char_code == charCode_quote:
            return
        yield char_code


