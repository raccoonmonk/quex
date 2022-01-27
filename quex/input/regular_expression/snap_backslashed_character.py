# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from quex.input.regular_expression.exception import RegularExpressionException

backslashed_character_db = { 
        # inside string "..." and outside 
        'a': ord('\a'),   'b': ord('\b'), 'f': ord('\f'),   'n': ord('\n'),
        'r': ord('\r'),   't': ord('\t'), 'v': ord('\v'),   '\\': ord('\\'), '"': ord('"'),
        # only outside of string
        '+': ord('+'), '*': ord('*'), '?': ord('?'), '/': ord('/'), ":": ord(":"),
        '|': ord('|'), '$': ord('$'), '^': ord('^'), '-': ord('-'), '.': ord('.'), 
        '[': ord('['), ']': ord(']'),    
        '(': ord('('), ')': ord(')'),  
        '{': ord('{'), '}': ord('}'), 
}
        
def do(sh, ReducedSetOfBackslashedCharactersF=False, ExceptionOnNoMatchF=True, HexNumbersF=True):
    """All backslashed characters shall enter this function. In particular 
       backslashed characters appear in:
        
             "$50"     -- quoted strings
             [a-zA-Z]  -- character sets
             for       -- lonestanding characters 
    
       x = string containing characters after 'the backslash'
       i = position of the backslash in the given string

       ReducedSetOfBackslashedCharactersF indicates whether we are outside of a quoted
       string (lonestanding characters, sets, etc.) or inside a string. Inside a quoted
       string there are different rules, because not all control characters need to be
       considered.

       RETURNS: UCS code of the interpreted character,
                index of first element after the treated characters in the string
    """
    assert type(ReducedSetOfBackslashedCharactersF) == bool 

    if ReducedSetOfBackslashedCharactersF:
        backslashed_character_list = [ 'a', 'b', 'f', 'n', 'r', 't', 'v', '\\', '"' ]
    else:
        backslashed_character_list = list(backslashed_character_db.keys())

    pos = sh.tell()
    tmp = sh.read(1)
    if not tmp:
        raise RegularExpressionException("End of file while parsing backslash sequence.")

    elif tmp in backslashed_character_list: 
        return backslashed_character_db[tmp]
    elif tmp.isdigit():                     
        sh.seek(pos) 
        return __parse_octal_number(sh, 5)
    elif HexNumbersF:
        if   tmp == 'x': return __parse_hex_number(sh, 2)
        elif tmp == 'X': return __parse_hex_number(sh, 4)
        elif tmp == 'U': return __parse_hex_number(sh, 6)

    if ExceptionOnNoMatchF:
        raise RegularExpressionException("Backslashed '%s' is unknown to quex." % tmp)
    sh.seek(pos)
    return None

def __parse_octal_number(sh, MaxL):
    return __parse_base_number(sh, MaxL, 
                               DigitSet   = "01234567",
                               Base       = 8,
                               NumberName = "octal")

def __parse_hex_number(sh, MaxL):
    return __parse_base_number(sh, MaxL, 
                               DigitSet   = "0123456789abcdefABCDEF",
                               Base       = 16,
                               NumberName = "hexadecimal")

def __parse_base_number(sh, MaxL, DigitSet, Base, NumberName):
    """MaxL = Maximum length of number to be parsed.
    """
    number_str = ""
    pos        = sh.tell()
    tmp        = sh.read(1)
    while tmp and tmp in DigitSet:
        number_str += tmp
        if len(number_str) == MaxL: break
        pos = sh.tell()
        tmp = sh.read(1)
    else:
        if tmp: sh.seek(pos)
        
    if not number_str: 
        raise RegularExpressionException("Missing %s number." % NumberName)

    return int(number_str, Base)
