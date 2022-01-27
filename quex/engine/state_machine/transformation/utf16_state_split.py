# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
# (C) 2009 Frank-Rene Schaefer
"""
ABSTRACT:

    !! UTF16 state split is similar to UTF8 state split as shown in file !!
    !! "uf8_state_split.py". Please, read the documentation there about  !!
    !! the details of the basic idea.                                    !!

    Due to the fact that utf16 conversion has only two possible byte sequence
    lengths, 2 and 4 bytes, the state split process is significantly easier
    than the utf8 state split.

    The principle idea remains: A single transition from state A to state B is
    translated (sometimes) into an intermediate state transition to reflect
    that the unicode point is represent by a value sequence.

    The special case utf16 again is easier, since, for any unicode point <=
    0xFFFF the representation value remains exactly the same, thus those
    intervals do not have to be adapted at all!
    
    Further, the identification of 'contigous' intervals where the last value
    runs repeatedly from min to max is restricted to the consideration of a
    single word. UTF16 character codes can contain at max two values (a
    'surrogate pair') coded in two 'words' (1 word = 2 bytes). The overun
    happens every 2*10 code points.  Since such intervals are pretty large and
    the probability that a range runs over multiple such ranges is low, it does
    not make sense to try to combine them. The later Hopcroft Minimization will
    not be overwhelmed by a little extra work.

(C) Frank-Rene Schaefer
"""
import os
import sys
sys.path.append(os.environ["QUEX_PATH"])

from   quex.engine.state_machine.transformation.state_split import EncodingTrafoBySplit
from   quex.engine.misc.utf16                               import utf16_to_unicode, \
                                                                   unicode_to_utf16
from   quex.engine.misc.interval_handling                   import Interval, NumberSet, \
                                                                   NumberSet_All
from   quex.constants import INTEGER_MAX


ForbiddenRange = Interval(0xD800, 0xE000) # This range is fordbidden in Unicode

class EncodingTrafoUTF16(EncodingTrafoBySplit):
    DEFAULT_LEXATOM_TYPE_SIZE = 2 # [Byte]
    UnchangedRange            = 0x10000
    def __init__(self):
        # A character in UTF16 is at maximum represented by two code units.
        # => Two error ranges.
        error_range_0 = NumberSet([
            Interval(0x0000, 0xDC00), Interval(0xE000, 0x10000)
        ]).get_complement(NumberSet_All()) # Adapted later

        error_range_1 = NumberSet([
            Interval(0xDC00, 0xE000)
        ]).get_complement(NumberSet_All()) # Adapted later

        error_range_by_code_unit_db = {
            0: error_range_0,
            1: error_range_1
        }

        EncodingTrafoBySplit.__init__(self, "utf16", 
                                      error_range_by_code_unit_db)

    def cut_forbidden_range(self, number_set):
        """Cuts the 'forbidden range' from the given number set.

        RETURNS: True, if number set is not empty. False, else.
        """
        global ForbiddenRange 
        number_set.subtract(ForbiddenRange)
        number_set.mask(0, 0x110000)
        return not number_set.is_empty()

    def get_interval_sequences(self, Orig):
        interval_1word, intervals_2word = _get_contigous_intervals(Orig)

        result = []
        if interval_1word is not None:
            result.append([interval_1word])

        if intervals_2word is not None:
            result.extend(
                _get_trigger_sequence_for_interval(interval)
                for interval in intervals_2word
            )
        return result

    def lexatom_n_per_character(self, CharacterSet):
        """If all characters in a unicode character set state machine require the
        same number of bytes to be represented this number is returned.  Otherwise,
        'None' is returned.

        RETURNS:   N > 0  number of bytes required to represent any character in the 
                          given state machine.
                   None   characters in the state machine require different numbers of
                          bytes.
        """
        assert isinstance(CharacterSet, NumberSet)

        interval_list = CharacterSet.get_intervals(PromiseToTreatWellF=True)
        front = interval_list[0].begin     # First element of number set
        back  = interval_list[-1].end - 1  # Last element of number set
        # Determine number of bytes required to represent the first and the 
        # last character of the number set. The number of bytes per character
        # increases monotonously, so only borders have to be considered.
        front_chunk_n = len(unicode_to_utf16(front))
        back_chunk_n  = len(unicode_to_utf16(back))
        if front_chunk_n != back_chunk_n: return None
        else:                             return front_chunk_n

    def adapt_ranges_to_lexatom_type_range(self, LexatomTypeRange):
        self._adapt_error_ranges_to_lexatom_type_range(LexatomTypeRange)
        # UTF16 requires at least 2 byte for a 'normal code unit'. Anything else
        # requires to cut on the addmissible set of code points.
        if LexatomTypeRange.end < 0x10000:
            self.source_set.mask(0, LexatomTypeRange.end)
        else:
            self.source_set.mask(0, 0x110000)
        if LexatomTypeRange.end > 0x10000:
            self._error_range_by_code_unit_db[0].unite_with(Interval(0x10000, LexatomTypeRange.end))
            self._error_range_by_code_unit_db[1].unite_with(Interval(0x10000, LexatomTypeRange.end))

def _get_contigous_intervals(X):
    """Split Unicode interval into intervals where all values
       have the same utf16-byte sequence length. This is fairly 
       simple in comparison with utf8-byte sequence length: There
       are only two lengths: 2 bytes and 2 x 2 bytes.

       RETURNS:  [X0, List1]  

                 X0   = the sub-interval where all values are 1 word (2 byte)
                        utf16 encoded. 
                         
                        None => No such interval
                
                List1 = list of contigous sub-intervals where coded as 2 words.

                        None => No such intervals
    """
    global ForbiddenRange
    if X.begin == -INTEGER_MAX: X.begin = 0
    if X.end   == INTEGER_MAX:  X.end   = 0x110000
    assert X.end != X.begin     # Empty intervals are nonsensical
    assert X.end <= 0x110000    # Interval must lie in unicode range
    assert not X.check_overlap(ForbiddenRange) # The 'forbidden range' is not to be covered.

    if   X.end   <= 0x10000: 
        return [X, None]
    elif X.begin >= 0x10000: 
        return [None, _split_contigous_intervals_for_surrogates(X.begin, X.end)]
    else:                    
        return [Interval(X.begin, 0x10000), _split_contigous_intervals_for_surrogates(0x10000, X.end)]

def _split_contigous_intervals_for_surrogates(Begin, End):
    """Splits the interval X into sub interval so that no interval runs over a 'surrogate'
       border of the last word. For that, it is simply checked if the End falls into the
       same 'surrogate' domain of 'front' (start value of front = Begin). If it does not
       an interval [front, end_of_domain) is split up and front is set to end of domain.
       This procedure repeats until front and End lie in the same domain.
    """
    global ForbiddenRange
    assert Begin >= 0x10000
    assert End   <= 0x110000
    assert End   > Begin

    front_seq = unicode_to_utf16(Begin)
    back_seq  = unicode_to_utf16(End - 1)

    # (*) First word is the same.
    #     Then,
    #       -- it is either a one word character.
    #       -- it is a range of two word characters, but the range 
    #          extends in one contigous range in the second surrogate.
    #     In both cases, the interval is contigous.
    if front_seq[0] == back_seq[0]:
        return [Interval(Begin, End)]

    # (*) First word is NOT the same
    # Separate into three domains:
    #
    # (1) Interval from Begin until second surrogate hits border 0xE000
    # (2) Interval where the first surrogate inreases while second 
    #     surrogate iterates over [0xDC00, 0xDFFF]
    # (3) Interval from begin of last surrogate border to End
    result = []
    end    = utf16_to_unicode([front_seq[0], ForbiddenRange.end - 1]) + 1

    
    # (1) 'Begin' until second surrogate hits border 0xE000
    #      (The following **must** hold according to entry condition about 
    #       front and back sequence.)
    assert End > end
    result.append(Interval(Begin, end))

    if front_seq[0] + 1 != back_seq[0]: 
        # (2) Second surrogate iterates over [0xDC00, 0xDFFF]
        mid_end = utf16_to_unicode([back_seq[0] - 1, ForbiddenRange.end - 1]) + 1
        #     (The following **must** hold according to entry condition about 
        #      front and back sequence.)
        assert mid_end > end
        result.append(Interval(end, mid_end)) 
        end     = mid_end
         
    # (3) Last surrogate border to End
    if End > end:
        result.append(Interval(end, End)) 

    return result
    
def _get_trigger_sequence_for_interval(X):
    # The interval either lies entirely >= 0x10000 or entirely < 0x10000
    assert X.begin >= 0x10000 or X.end < 0x10000

    # An interval below < 0x10000 remains the same
    if X.end < 0x10000: return [ X ]
    
    # In case that the interval >= 0x10000 it the value is split up into
    # two values.
    front_seq = unicode_to_utf16(X.begin)
    back_seq  = unicode_to_utf16(X.end - 1)

    return [ Interval(front_seq[0], back_seq[0] + 1), 
             Interval(front_seq[1], back_seq[1] + 1) ]

