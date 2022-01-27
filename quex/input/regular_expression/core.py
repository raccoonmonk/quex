# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
import quex.engine.misc.error                   as     error
from   quex.engine.misc.unistream               import UniStream
from   quex.engine.misc.file_in                 import EndOfStreamException, \
                                                       check_end_of_file
from   quex.engine.state_machine.core           import DFA 
from   quex.input.regular_expression.exception  import RegularExpressionException
import quex.blackboard                          as     blackboard
import quex.input.regular_expression.engine     as     regex

def parse(Txt_or_File, Terminator=None, Name=None, 
          AllowAcceptanceOnNothingF=False, AllowPreContextF=True, 
          AllowPostContextF=True, AllowEmptyF=False):
    sh  = UniStream(Txt_or_File)
    pos = sh.tell()

    pattern, dummy = __parse(sh, AllowAcceptanceOnNothingF=AllowAcceptanceOnNothingF, 
                             Terminator=Terminator, Name=Name, AllowEmptyF=AllowEmptyF)

    return __check(pattern, AllowPreContextF, AllowPostContextF, sh, pos, Name)

def parse_multiple_result(fh): 
    return __core(fh, AllowNothingIsNecessaryF=False, 
                  Terminator=None, AllowLogicOrAfterPostContextF=True) 

def parse_character_set(Txt_or_File, Terminator=None):
    return __parse(Txt_or_File, DFA.get_number_set, "character set", Terminator)

def __parse(Txt_or_File, ExtractFunction=None, Name=None, Terminator=None, 
            AllowAcceptanceOnNothingF=False, AllowEmptyF=False):

    sh = UniStream(Txt_or_File)
    start_position = sh.tell()

    # (*) Parse the pattern => A Pattern object
    pattern = __core(sh, AllowNothingIsNecessaryF=AllowAcceptanceOnNothingF, Terminator=Terminator, AllowEmptyF=AllowEmptyF)

    # (*) Extract the object as required 
    if ExtractFunction is not None:
        result = ExtractFunction(pattern.get_cloned_sm())

        if pattern.has_pre_or_post_context() or result is None:
            sh.seek(start_position)
            pattern_str = pattern.pattern_string().strip()
            txt = "Regular expression '%s' cannot be interpreted as plain %s." % (pattern_str, Name) 
            if len(pattern_str) != 0 and pattern_str[-1] == Terminator:
                txt += "\nMissing delimiting whitespace ' ' between the regular expression and '%s'.\n" % Terminator
            error.log(txt, sh)
    else:
        result = None

    return pattern, result

def __core(sh, AllowNothingIsNecessaryF, Terminator, AllowLogicOrAfterPostContextF=False, AllowEmptyF=False):
    """RETURNS: pattern list, if AllowLogicOrAfterPostContextF = True,
                pattern,      else.
    """
    start_position = sh.tell()
    try:
        result = regex.do(sh, blackboard.shorthand_db, 
                          AllowNothingIsNecessaryF = AllowNothingIsNecessaryF,
                          SpecialTerminator        = Terminator,
                          AllowLogicOrAfterPostContextF = AllowLogicOrAfterPostContextF,
                          AllowEmptyF = AllowEmptyF)
        if result is None:
            if check_end_of_file(sh):
                raise EndOfStreamException()
            sh.seek(start_position)
            error.log("Expression does not result in regular expression.", sh)

    except RegularExpressionException as x:
        sh.seek(start_position)
        error.log("Regular expression parsing:\n" + x.message, sh)

    return result

def __check(pattern, AllowPreContextF, AllowPostContextF, sh, pos, Name):
    if pattern is not None:
        if     pattern.pre_context_trivial_begin_of_line_f \
           and len(blackboard.setup.buffer_encoding.do_single(ord('\n'))) != 1:
            error.log("Pre-context 'begin-of-line' cannot be implemented with given encoding.\n"
                      "Number of code units for character 'newline' must be exactly 1.", 
                      sh)

        elif not AllowPreContextF and pattern.has_pre_context():
            sh.seek(pos)
            error.log("Patterns in '%s' cannot contain pre-context." % Name, sh)

        elif not AllowPostContextF and pattern.has_post_context():
            sh.seek(pos)
            error.log("Patterns in '%s' cannot contain post-context." % Name, sh)
    return pattern
