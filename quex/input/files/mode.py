# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________

import quex.input.regular_expression.core as     regular_expression
import quex.input.files.mode_option       as     mode_option
import quex.input.files.code_fragment     as     code_fragment
from   quex.input.files.specifier.mode    import ModeParsed
from   quex.input.code.core               import CodeUser
from   quex.input.code.base               import SourceRef
                                          
import quex.engine.misc.error             as     error
import quex.engine.misc.similarity        as     similarity
from   quex.engine.misc.file_in           import EndOfStreamException, \
                                                 check, \
                                                 check_or_die, \
                                                 check_end_of_file, \
                                                 read_identifier, \
                                                 read_until_letter, \
                                                 read_until_whitespace, \
                                                 is_identifier, \
                                                 skip_whitespace, \
                                                 optional_flags
from   quex.output.token.id_generator     import token_id_db_enter

import quex.blackboard as     blackboard
from   quex.blackboard import setup as Setup, \
                              Lng, \
                              standard_incidence_db

from   collections import namedtuple

def parse(fh, mode_parsed_db):
    # NOTE: Catching of EOF happens in caller: parse_section(...)
    skip_whitespace(fh)
    position  = fh.tell()
    mode_name = read_identifier(fh, OnMissingStr="Missing identifier at beginning of mode definition.")
    error.insight("Mode '%s'" % mode_name)

    # NOTE: constructor does register this mode in the mode_db
    new_mode = ModeParsed(mode_name, SourceRef.from_FileHandle(fh))
    if new_mode.name in mode_parsed_db:
        error.log("Mode '%s' has been defined twice.\n" % new_mode.name,
                  new_mode.sr, DontExitF=True)
        error.log("Earlier definition here.",
                  mode_parsed_db[new_mode.name].sr)

    mode_parsed_db[new_mode.name] = new_mode

    # (*) inherited modes / option_db
    skip_whitespace(fh)
    dummy = fh.read(1)
    if dummy not in [":", "{"]:
        error.log("missing ':' or '{' after mode '%s'" % mode_name, fh)

    if dummy == ":":
        new_mode.direct_base_mode_name_list = _parse_base_mode_list(fh)
        _parse_option_list(fh, new_mode)

    # (*) read in pattern-action pairs and events
    while not check(fh, "}"): 
        if check_end_of_file(fh):
            error.log("End of file reached while parsing mode '%s'." % mode_name, fh, position)
        _parse_pattern_action_pair(new_mode, fh)

def _parse_base_mode_list(fh):
    """RETURNS: List of names of direct base modes.

    Deeper base modes need to be determined from reflecting a mode
    hierarchie.
    """
    skip_whitespace(fh)
    result_list      = []
    trailing_comma_f = False
    while 1 + 1 == 2:
        pos = fh.tell()
        if   check(fh, "{"): fh.seek(pos); break
        elif check(fh, "<"): fh.seek(pos); break

        skip_whitespace(fh)
        identifier = read_identifier(fh)
        if not identifier: break

        result_list.append(identifier)
        trailing_comma_f = False
        if not check(fh, ","): break
        trailing_comma_f = True

    if trailing_comma_f:
        error.warning("Trailing ',' after base mode '%s'." % result_list[-1], fh) 
        
    _check_against_old_syntax_of_base_mode_definitions(fh, result_list)
    return result_list

def _parse_option_list(fh, new_mode):
    while 1 + 1 == 2:
        sr = SourceRef.from_FileHandle(fh)
        identifier, setting = mode_option.parse(fh, new_mode)
        if identifier is None: break
        new_mode.option_db.enter(identifier, setting, sr, new_mode.name)

def _parse_pattern_action_pair(new_mode, fh):
    skip_whitespace(fh)
    if   __parse_keyword_list_and_action(new_mode, fh): 
        return
    elif __parse_brief_and_action(new_mode, fh):        
        return
    elif __parse_event_and_action(new_mode, fh):              
        return 
    else: 
       __parse_pattern_and_action(new_mode, fh)

def __parse_pattern_and_action(new_mode, fh):
    pattern_list = regular_expression.parse_multiple_result(fh)
    for pattern in pattern_list:
        sr = SourceRef.from_FileHandle(fh, new_mode.name)
        pattern.set_source_reference(sr)
    __parse_action(new_mode, fh, pattern_list)

def __parse_action(new_mode, fh, pattern_list):
    position = fh.tell()
    try:
        skip_whitespace(fh)
        position = fh.tell()
            
        code = code_fragment.parse(fh, "regular expression", ErrorOnFailureF=False) 
        if code is not None:
            assert isinstance(code, CodeUser), "Found: %s" % code.__class__
            for pattern in pattern_list:
                new_mode.add_pattern_action_pair(pattern, code, fh)
            return

        fh.seek(position)
        word, dummy, position_before_marker = read_until_letter(fh, [";"], Verbose=True)
        if   word == "PRIORITY-MARK":
            error.log("PRIORITY-MARK is has been renamed to 'DEMOTION'.", fh)
        elif word == "DEMOTION":
            # This mark 'lowers' the priority of a pattern to the priority of the current
            # pattern index (important for inherited patterns, that have higher precedence).
            # The parser already constructed a state machine for the pattern that is to
            # be assigned a new priority. Since, this machine is not used, let us just
            # use its id.
            fh.seek(position_before_marker)
            check_or_die(fh, ";")
            for pattern in pattern_list:
                new_mode.add_match_priority(pattern, fh)

        elif word == "DELETION":
            # This mark deletes any pattern that was inherited with the same 'name'
            fh.seek(position_before_marker)
            check_or_die(fh, ";", ". Since quex version 0.33.5 this is required.")
            for pattern in pattern_list:
                new_mode.add_match_deletion(pattern, fh)
            
        else:
            error.log("Missing token '=>', '{', 'DEMOTION', or 'DELETION' after '%s'.\n" % pattern_list[0].pattern_string() + \
                      "found: '%s'. Note, that since quex version 0.33.5 it is required to add a ';'\n" % word + \
                      "to the commands DEMOTION and DELETION.", fh)

    except EndOfStreamException:
        error.error_eof("pattern action", fh, position)

def __parse_event_and_action(new_mode, fh):
    pos  = fh.tell()
    word = read_until_whitespace(fh)

    # Allow '<<EOF>>' and '<<FAIL>>' out of respect for classical tools like 'lex'
    if   word == "<<EOF>>":                  word = "on_end_of_stream"
    elif word == "<<FAIL>>":                 word = "on_failure"
    elif word in blackboard.all_section_title_list:
        error.log("Pattern '%s' is a quex section title. Has the closing '}' of mode %s \n" % (word, new_mode.name) \
                  + "been forgotten? Else use quotes, i.e. \"%s\"." % word, fh)
    elif len(word) < 3 or word[:3] != "on_": fh.seek(pos); return False

    if word == "on_indentation":
        fh.seek(pos)
        error.log("Definition of 'on_indentation' is no longer supported since version 0.51.1.\n"
                  "Please, use 'on_indent' for the event of an opening indentation, 'on_dedent'\n"
                  "for closing indentation, and 'on_nodent' for no change in indentation.\n"
                  "If you want to match 'on_indentation' as a string, use quotes.", fh) 

    comment = "Unknown event handler '%s'. \n" % word + \
              "Note, that any pattern starting with 'on_' is considered an event handler.\n" + \
              "use double quotes to bracket patterns that start with 'on_'."

    error.verify_word_in_list(word, list(standard_incidence_db.keys()) + ["keyword_list"], comment, 
                              fh)

    code         = code_fragment.parse(fh, "%s::%s event handler" % (new_mode.name, word))
    incidence_id = standard_incidence_db[word][0]
    if Lng.suspicious_RETURN_in_event_handler(incidence_id, code.get_text()):
        error.warning("Suspicious 'FLUSH' in event handler '%s'.\n" % incidence_id \
                      + "This statement will trigger 'on_after_match' handler.\n" \
                      + "May be, use plain return instead.", code.sr)

    new_mode.incidence_db[word] = code

    return True

def __parse_brief_and_action(new_mode, fh):
    """ADAPTS: new_mode.pattern_action_list where new pattern action pairs 
                                            are entered.
    RETURNS: True, in case of success.
    EXITS:   in case of syntax errors.
    """
    position   = fh.tell()
    identifier = read_identifier(fh)
    if identifier != "brief":
        if similarity.get(identifier, ["brief", "briefing", "briefly"]) != -1:
            error.warning("'%s' is similar to keyword 'brief'.\n"
                          "For clarity, use quotes." % identifier, fh)
        fh.seek(position)
        return False

    flags = optional_flags(fh, "brief pattern action pair list", "", 
                           {"N": "pass LexemeNull to token contructor.",
                            "L": "pass Lexeme to token constructor.",
                            "i": "implicit token identifier definition."},
                            BadCombinationList=["NL"])

    skip_whitespace(fh)
    prefix = read_identifier(fh)
    skip_whitespace(fh)

    lexeme_null_f  = "N" in flags
    lexeme_f       = "L" in flags
    implicit_tid_f = "i" in flags

    check_or_die(fh, "{", "Opening bracket required after 'brief'.")
    while not check(fh, "}"):
        skip_whitespace(fh)

        pattern = regular_expression.parse(fh)
        skip_whitespace(fh)
        
        position   = fh.tell()
        identifier = read_identifier(fh)
        if not identifier: 
            error.log("Missing identifier after regular expression.", fh)

        identifier = "%s%s" % (prefix, identifier)
        
        check_or_die(fh, ";", 
                     "Semincolon required after brief token identifier '%s'." % identifier)

        if implicit_tid_f: token_id_db_enter(fh, identifier)

        code = code_fragment.get_CodeUser_for_token_sending(fh, identifier, position,
                                                            LexemeNullF = lexeme_null_f,
                                                            LexemeF     = lexeme_f)
        new_mode.add_pattern_action_pair(pattern, code, fh)

    return True

def __parse_keyword_list_and_action(new_mode, fh):
    """ADAPTS: new_mode.pattern_action_list where new pattern action pairs 
                                            are entered.
    RETURNS: True, in case of success.
    EXITS:   in case of syntax errors.
    """
    position   = fh.tell()
    identifier = read_identifier(fh)
    if identifier != "keyword_list":
        if similarity.get(identifier, ["keyword_list", "key words"]) != -1:
            error.warning("'%s' is similar to keyword 'keyword_list'.\n"
                          "For clarity, use quotes." % identifier, fh)
        fh.seek(position)
        return False

    def to_identifier(PatternCarryingIdentifier, fh):
        """RETURNS: Path in 'PatternCarryingIdentifier' given as string if 
                         there is single path on single characters that comply 
                         the requirements to be part of an identifier.
                    None, else.
        """
        sm = PatternCarryingIdentifier.borrow_sm()
        if not sm: return None
        code_point_sequence = sm.get_sequence()
        if not code_point_sequence: return None

        candidate = "".join(eval("u'\\U%08X'" % x) for x in code_point_sequence)

        if not is_identifier(candidate): return None
        else:                            return candidate

    def error_exit(fh, position):
        current_position = fh.tell()
        fh.seek(position)
        text = fh.read(current_position - position)
        for suspicious in ";.:,|":
            if suspicious in text:
                error.log("keywords in 'keyword_list' are must be white space separated. Found '%s'." % suspicious, fh)
        else:
            error.log("Cannot convert regular expression into identifier.", fh)


    flags = optional_flags(fh, "keyword_list", "u", 
                           {"u": "(default) make correspondent token identifiers uppercase.",
                            "l": "make correspondent token identifiers lowercase.",
                            "N": "(default) pass LexemeNull to token contructor.",
                            "L": "pass Lexeme to token constructor.",
                            "i": "implicit token identifier definition."},
                           BadCombinationList=["ul", "NL"])

    lexeme_null_f  = "N" in flags
    lexeme_f       = "L" in flags
    implicit_tid_f = "i" in flags
    lowercase_f    = "l" in flags
    uppercase_f    = "u" in flags

    skip_whitespace(fh)
    prefix = read_identifier(fh)
    skip_whitespace(fh)

    check_or_die(fh, "{", "Opening bracket required after 'keyword_list'.")
    while not check(fh, "}"):
        skip_whitespace(fh)
        position   = fh.tell()
        pattern    = regular_expression.parse(fh)
        identifier = to_identifier(pattern, fh)
        if   identifier is None: error_exit(fh, position)
        elif uppercase_f:        identifier = identifier.upper()
        elif lowercase_f:        identifier = identifier.lower()

        identifier = "%s%s" % (prefix, identifier)

        if implicit_tid_f: token_id_db_enter(fh, identifier)

        code    = code_fragment.get_CodeUser_for_token_sending(fh, identifier, position,
                                                               LexemeNullF = lexeme_null_f,
                                                               LexemeF     = lexeme_f)
        new_mode.add_pattern_action_pair(pattern, code, fh)
    return True

def _check_against_old_syntax_of_base_mode_definitions(fh, direct_base_mode_name_list):
    if not direct_base_mode_name_list: return

    pos = fh.tell()
    skip_whitespace(fh)
    dummy_identifier = read_identifier(fh)
    if dummy_identifier:
        error.log("Missing separating ',' between base modes '%s' and '%s'.\n" \
                  % (direct_base_mode_name_list[-1], dummy_identifier) + \
                  "(The comma separator is mandatory since quex 0.53.1)", fh)
    fh.seek(pos)

