# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.engine.misc.tools                   import quex_chr
import quex.engine.misc.error                   as     error
from   quex.engine.misc.file_operations         import open_file_or_die
from   quex.engine.misc.file_in                 import optional_flags, \
                                                       read_until_whitespace, \
                                                       read_until_character, \
                                                       check, \
                                                       read_identifier, \
                                                       skip_whitespace, \
                                                       EndOfStreamException
import quex.input.regular_expression.core       as     regular_expression
from   quex.input.regular_expression.macro      import PatternShorthand, \
                                                       MacroCall
from   quex.input.code.base                     import SourceRef
import quex.blackboard                          as     blackboard
from   quex.constants                           import DEFINE_SECTION_COMMAND_SET
from   quex.output.syntax_elements              import Signature
import quex.output.transform_to_encoding        as     transform_to_encoding

def parse(fh):
    """Parses pattern definitions of the form:
   
          WHITESPACE  [ \t\n]
          IDENTIFIER  [a-zA-Z0-9]+
          OP_PLUS     "+"

          \macro SOMETHING(sm = X, set = Y, number = N):
          
       That means: 'name' whitespace 'regular expression' whitespace newline.
       Comments can only be '//' nothing else and they have to appear at the
       beginning of the line.

       One regular expression can have more than one name, but one name can 
       only have one regular expression.
    """
    command_db = {
        "\\macro":   _parse_macro,
        "\\plot":    _parse_plot,
        "\\run":     _parse_run,
        "\\lexemes": _parse_lexemes
    }
    assert set(command_db.keys()) == DEFINE_SECTION_COMMAND_SET

    if not check(fh, "{"):
        error.log("define region must start with opening '{'.", fh)

    while 1 + 1 == 2:
        if check(fh, "}"): 
            return
        
        skip_whitespace(fh)
        # Get the name of the pattern
        for command, parse_function in command_db.items():
            if check(fh, command):
                name, value = parse_function(fh)
                blackboard.dfa_command_executed_f = True
                break
        else:
            name, value = _parse_shorthand(fh)

        if name is None: continue

        blackboard.shorthand_db[name] = value

def _parse_plot(fh):
    PatternDict = blackboard.shorthand_db

    sr = SourceRef.from_FileHandle(fh)

    flags = optional_flags(fh, "brief pattern action pair list", "h", 
                           {"h": "(default) hexadecimal values",
                            "d": "decimal values",
                            "c": "unicode characters",
                            "t": "text to console representation (not graphviz-dot format to file)",
                            "q": "suppress display of location (file name, line number)",
                            "s": "(default) print shortcut to file with same name + \".dot\"",
                            "f": "plot expression to file (name to follow)",
                           },
                           BadCombinationList=["hdc", "sf", "tf"])

    skip_whitespace(fh)
    if "f" in flags:
        pos = fh.tell()
        file_name = read_until_whitespace(fh)

        if not file_name:
            error.log("Missing file name after '\plot' (option 'f' for filename).", sr)

    if "t" in flags or "f" in flags:
        skip_whitespace(fh)
        pattern = regular_expression.parse(fh, 
                                           Name="\\plot",
                                           AllowAcceptanceOnNothingF = True,
                                           AllowEmptyF=True,
                                           AllowPreContextF=False,
                                           AllowPostContextF=False) 
        if not pattern: 
            dfa        = None
            dfa_string = None
        else:           
            dfa        = pattern.extract_sm()
            dfa_string = pattern.pattern_string()

    else:
        identifier = read_identifier(fh)
        if not identifier:
            error.log("Missing identifier following '\\plot'.", sr)
        file_name  = "%s.dot" % identifier

        reference = PatternDict.get(identifier)
        if not reference:
            error.log("Dfa '%s' has not been defined yet." % identifier, sr)
        dfa = reference.get_DFA()
        dfa_string = "Macro '%s'" % identifier

    if dfa is None:
        fh.seek(pos)
        error.log("Expression did not result in DFA.", fh)

    locaction_display_f = "q" not in flags

    dfa = transform_to_encoding.do(dfa)
    if "t" in flags:
        error.note("plot (%s) '%s'" % (flags, dfa_string), sr, PrefixF=locaction_display_f)
        txt = dfa.get_string(NormalizeF = True, 
                             Option     = _flag_to_character_display(flags))
        error.note("    " + txt.strip().replace("\n", "\n    "), sr, PrefixF=locaction_display_f)
        error.note("plot <terminated>", sr, PrefixF=locaction_display_f)
    else:
        txt = dfa.get_graphviz_string(NormalizeF = True, 
                                      Option     = _flag_to_character_display(flags))

        fh = open_file_or_die(file_name, "w", Encoding="utf-8")
        fh.write(txt)
        fh.close()
        error.note("plot (%s) to file '%s'." % (flags, file_name), sr, PrefixF=locaction_display_f)

    return None, None

def _flag_to_character_display(flags):
    if   "h" in flags: return "hex"
    elif "d" in flags: return "dec"
    else:              return "utf8"

def _parse_macro(fh):
    signature_str = read_until_character(fh, ":").strip()
    if not signature_str: 
        error.log("Missing signature for macro definition.\n"
                  "(Possibly misplaced ':').", fh)
   
    signature = Signature.from_String(signature_str)
    for arg in signature.argument_list:
        if not arg.name:
            error.log("Missing argument name in macro defitions.", fh)

    pos = fh.tell()
    reference_sr = SourceRef.from_FileHandle(fh)
    try:
        skip_whitespace(fh) #, ExceptNewlineF=True)
        # The function body remains a string until it is parsed at expansion time.
        function_body = read_until_character(fh, "\n").strip()
        name          = signature.function_name
        value         = MacroCall(signature.argument_list,
                                  function_body, 
                                  reference_sr)
    except EndOfStreamException:
        fh.seek(pos)
        error.log("End of stream reached while parsing '%s' in 'define' section.",
                  fh)

    return name, PatternShorthand(name, value, SourceRef.from_FileHandle(fh), 
                                  signature.function_name)

def _parse_run(fh):
    sr = SourceRef.from_FileHandle(fh)
    skip_whitespace(fh)
    pattern = regular_expression.parse(fh, 
                                       Name="\\run",
                                       AllowAcceptanceOnNothingF = True,
                                       AllowPreContextF=False,
                                       AllowPostContextF=False) 
    if not pattern: 
        error.log("\\run command: first argument missing: the DFA (1st argument)", sr)

    dfa        = pattern.extract_sm()
    dfa_string = pattern.pattern_string()

    # Let the sequences list be given by a DFA
    skip_whitespace(fh)
    pattern = regular_expression.parse(fh, 
                                       Name="\\run",
                                       AllowAcceptanceOnNothingF = True,
                                       AllowPreContextF=False,
                                       AllowPostContextF=False) 

    if not pattern: 
        error.log("\\run command: missing test sequence description (2nd argument).", sr)

    tsql_dfa = pattern.extract_sm()
    if tsql_dfa.has_cycles(): 
        error.error("DFA to describe test sequence list contains loop.\n"
                    "This would result in an infinite number of test sequences.",
                    fh)

    test_sequence_list = tsql_dfa.iterable_lexemes() 

    error.note("run on '%s'" % dfa_string, sr)
    error.note(" ", sr)
    for test_sequence in sorted(test_sequence_list):
        _perform_run(dfa, test_sequence, sr)
    error.note(" ", sr)
    error.note("run <terminated>", sr)
    return None, None

def _parse_lexemes(fh):
    sr = SourceRef.from_FileHandle(fh)

    flags = optional_flags(fh, "lexemes for a given DFA", "1c", 
                           {"1": "(default) max. 1 loop re-entries",
                            "2": "max. 2 loop re-entries",
                            "3": "max. 2 loop re-entries",
                            "4": "max. 2 loop re-entries",
                            "5": "max. 2 loop re-entries",
                            "h": "hexadecimal values",
                            "q": "suppress display of location (file name, line number)",
                            "d": "decimal values",
                            "c": "(default) unicode characters",
                            "s": "print sets instead of single characters",
                           },
                           BadCombinationList=["hdc", "12345"])

    loop_n = 1
    for i, value in enumerate("12345"):
        if value in flags: loop_n = i
    locaction_display_f = "q" not in flags

    skip_whitespace(fh)
    pattern = regular_expression.parse(fh, 
                                       Name="\\lexemes",
                                       AllowAcceptanceOnNothingF = True,
                                       AllowEmptyF               = True,
                                       AllowPreContextF=False,
                                       AllowPostContextF=False) 
    if not pattern: 
        error.log("\\lexemes command: first argument missing: the DFA (1st argument)", sr)

    dfa        = pattern.extract_sm()
    dfa_string = pattern.pattern_string()

    error.note("lexemes for '%s' (max loops=%i, sets=%s)" % (dfa_string, loop_n, "s" in flags), sr, PrefixF=locaction_display_f)
    error.note(" ", sr, PrefixF=locaction_display_f)
    if "s" in flags:
        option = _flag_to_character_display(flags)
        for number_set_sequence in dfa.iterable_NumberSetSequences(loop_n):
            txt = [ "{%s}" % step.get_string(option).strip() for step in number_set_sequence ]
            error.note(", ".join(txt), sr, PrefixF=locaction_display_f)
    else:
        if   "h" in flags: char_function = lambda x: "%04X" % x
        elif "d" in flags: char_function = lambda x: "%d" % x
        elif "c" in flags: char_function = quex_chr
        else:              char_function = quex_chr

        for number_sequence in dfa.iterable_lexemes(loop_n):
            txt = [ char_function(step) for step in number_sequence ]
            error.note(", ".join(txt), sr, PrefixF=locaction_display_f)

    error.note(" ", sr, PrefixF=locaction_display_f)
    error.note("lexemes <terminated>", sr, PrefixF=locaction_display_f)
    return None, None

def _perform_run(dfa, TestSeq, sr):
    """Print test sequence, step along and show where acceptance
       happened, and where the analysis stopped.
    """
    if not TestSeq: 
       error.note("  <empty test sequence>", sr)
       return

    state = dfa.get_init_state()
    last_acceptance_step_i = -1
    if state.is_acceptance(): 
        last_acceptance_step_i = 0
    for i, x in enumerate(TestSeq, start=1):
        next_si = state.target_map.get_resulting_target_state_index(x)
        if not next_si: break
        state = dfa.states[next_si]
        if state.is_acceptance(): 
            last_acceptance_step_i = i

    def marker(k):
        if k == last_acceptance_step_i: return "A"
        elif k == i:                    return "^"
        else:                           return " "

    test_sequence_txt = "".join(eval("u'\\U%08X'" % c) for c in TestSeq)
    error.note("  " + "|" + "|".join(x for x in test_sequence_txt) + "|", sr)
    error.note("  " + " ".join("%s" % marker(k) for k in range(len(test_sequence_txt)+1)), sr)

def _parse_shorthand(fh):
    skip_whitespace(fh)
    name = read_identifier(fh, 
                           OnMissingStr="Missing identifier in 'define' section.")

    if name in blackboard.shorthand_db:
        error.log("Second definition of pattern '%s'.\n" % name + \
                  "Pattern names must be unique.", fh)

    pos = fh.tell()
    try:
        if check(fh, "}", SkipWhitespaceExceptNewlineF=True): 
            error.log("Missing regular expression for pattern definition '%s'." % \
                      name, fh)

        skip_whitespace(fh)
        pattern = regular_expression.parse(fh, 
                                           Name="define",
                                           AllowAcceptanceOnNothingF = True,
                                           AllowPreContextF=False,
                                           AllowPostContextF=False) 

    except EndOfStreamException:
        fh.seek(pos)
        error.log("End of stream reached while parsing '%s' in 'define' section.",
                  fh)

    state_machine = pattern.extract_sm()

    value = PatternShorthand(name, state_machine, SourceRef.from_FileHandle(fh), 
                             pattern.pattern_string())

    return name, value


