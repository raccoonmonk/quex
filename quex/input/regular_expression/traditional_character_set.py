# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
import quex.input.regular_expression.snap_backslashed_character as     snap_backslashed_character
from   quex.engine.misc.interval_handling                       import Interval, \
                                                                       NumberSet

from   quex.engine.misc.tools                  import quex_chr
from   quex.input.regular_expression.exception import RegularExpressionException
from   quex.blackboard                         import setup as Setup

class Tracker:
    def __init__(self):
        self.match_set  = NumberSet()
        self.negation_f = False
 
    def consider_interval(self, Begin, End):
        if Begin > End:
            raise RegularExpressionException("Character range: '-' requires character with 'lower code' to preceed\n" + \
                                             "found range '%s-%s' which corresponds to %i-%i as unicode code points." % \
                                             (quex_chr(Begin), quex_chr(End), Begin, End))

        self.match_set.add_interval(Interval(Begin, End))

    def consider_letter(self, CharCode):
        self.consider_interval(CharCode, CharCode+1)
 
class DoubleQuoteChecker:
    def __init__(self):
        self.quote_n = 0

    def do(self, CharacterCode):
        if CharacterCode != ord("\""): return
        self.quote_n += 1
        if self.quote_n != 2: return
        raise RegularExpressionException(
                "Character '\"' appears twice in character range [ ... ] expression.\n"
                "You cannot exempt characters this way. Please, use backslash or\n"
                "split the character range expression.")

def do(sh):
    """Transforms an expression of the form [a-z0-9A-Z] into a NumberSet of
       code points that corresponds to the characters and character ranges mentioned.
    """
    def __check_letter(stream, letter):
        position = stream.tell()
        if stream.read(1) == letter: return True
        else:                        stream.seek(position); return False

    # check, if the set is thought to be inverse (preceeded by '^')
    tracker = Tracker()

    if __check_letter(sh, "^"): tracker.negation_f = True

    char_code     = None
    quote_checker = DoubleQuoteChecker() # Checks for " appearing twice. Some users did use
    #                                    # constructs such as "-" and ended up in confusing behavior.
    while 1 + 1 == 2:
        char_code = ord(sh.read(1))

        quote_checker.do(char_code)
        
        if char_code == ord("-"):
            raise RegularExpressionException("Character range operator '-' requires a preceding character as in 'a-z'.")
        elif char_code is None: 
            raise RegularExpressionException("Missing closing ']' in character range expression.")
        elif char_code == ord("]"):
            break
        elif char_code == ord("\\"):
            char_code = snap_backslashed_character.do(sh)

        if not __check_letter(sh, "-"): 
            # (*) Normal character
            tracker.consider_letter(char_code)
        else:
            # (*) Character range:  'character0' '-' 'character1'
            char_code_2 = ord(sh.read(1))
            quote_checker.do(char_code_2)
            if char_code_2 in [None, ord(']')]: 
                raise RegularExpressionException("Character range: '-' requires a character following '-'.")
            elif char_code == ord("-"):
                raise RegularExpressionException("Character range operator '-' followed by '-'.")
            elif char_code_2 == ord("\\"): 
                char_code_2 = snap_backslashed_character.do(sh)  

            # value denotes 'end', i.e first character outside the interval => add 1
            if char_code == char_code_2:
                raise RegularExpressionException("Character range [%s-%s] has only one element.\n" \
                                                 % (quex_chr(char_code), quex_chr(char_code)) + \
                                                 "In this case avoid range expression for clarity.")
            tracker.consider_interval(char_code, char_code_2 + 1)

        if char_code is None: break

    if tracker.negation_f: 
        return tracker.match_set.get_complement(Setup.buffer_encoding.source_set)
    else:                  
        return tracker.match_set


