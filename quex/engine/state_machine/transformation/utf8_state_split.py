# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
"""
(C) 2009-2016 Frank-Rene Schaefer
"""
import os
import sys
from   copy import copy
sys.path.append(os.environ["QUEX_PATH"])

# "quex.engine.misc.utf8"
#
# CANNOT BE REPLACED, BECAUSE python's encoder cannot encode 'surrogates'!
#
from   quex.engine.misc.utf8                                import utf8_to_unicode, \
                                                                   unicode_to_utf8, \
                                                                   UTF8_MAX,        \
                                                                   UTF8_BORDERS
from   quex.engine.misc.interval_handling                   import Interval,        \
                                                                   NumberSet,       \
                                                                   NumberSet_All
from   quex.engine.state_machine.transformation.state_split import EncodingTrafoBySplit

class EncodingTrafoUTF8(EncodingTrafoBySplit):
    DEFAULT_LEXATOM_TYPE_SIZE = 1 # [Byte]

    def __init__(self):
        error_range_0 = NumberSet([
            Interval(0b00000000, 0b01111111+1), Interval(0b11000000, 0b11011111+1),
            Interval(0b11100000, 0b11101111+1), Interval(0b11110000, 0b11110111+1),
            Interval(0b11111000, 0b11111011+1), Interval(0b11111100, 0b11111101+1),
        ]).get_complement(NumberSet_All()) # Adapted later

        error_range_N = NumberSet(Interval(0b10000000, 0b10111111+1)) \
                        .get_complement(NumberSet_All()) # Adapted later

        error_range_by_code_unit_db = {
            0: error_range_0,
            1: error_range_N, 2: error_range_N, 3: error_range_N,
            4: error_range_N, 5: error_range_N, 6: error_range_N,
            7: error_range_N, 8: error_range_N
        }

        EncodingTrafoBySplit.__init__(self, "utf8", 
                                      error_range_by_code_unit_db)
        self.UnchangedRange = 0x7F

    def adapt_ranges_to_lexatom_type_range(self, LexatomTypeRange):
        self._adapt_error_ranges_to_lexatom_type_range(LexatomTypeRange)
        # UTF16 requires at least 2 byte for a 'normal code unit'. Anything else
        # requires to cut on the addmissible set of code points.
        self.source_set.mask(0, 0x110000)

        if LexatomTypeRange.end > 0x100:
            for error_range in self._error_range_by_code_unit_db.values():
                error_range.unite_with(Interval(0x100, LexatomTypeRange.end))

    def cut_forbidden_range(self, X):
        """Cuts the 'forbidden range' from the given number set.

        RETURNS: True, if number set is not empty. False, else.
        """
        return True

    def get_interval_sequences(self, Orig):
        """Orig = Unicode Trigger Set. It is transformed into a sequence of intervals
        that cover all elements of Orig in a representation as UTF8 code units.
        A transition from state '1' to state '2' on 'Orig' is then equivalent to 
        the transitions along the code unit sequence.
        """
        db = _split_by_transformed_sequence_length(Orig)
        if db is None: return []

        result = []
        for seq_length, interval in list(db.items()):
            interval_list = _get_contiguous_interval_sequences(interval, seq_length)
            result.extend(
                _get_trigger_sequence_for_contigous_byte_range_interval(interval, seq_length)
                for interval in interval_list)
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
        front_chunk_n = len(unicode_to_utf8(front))
        back_chunk_n  = len(unicode_to_utf8(back))
        if front_chunk_n != back_chunk_n: return None
        else:                             return front_chunk_n

def _split_by_transformed_sequence_length(X):
    """Split Unicode interval into intervals where all values have the same 
    utf8-byte sequence length.

    RETURNS: map: sequence length --> Unicode Sub-Interval of X.
    """
    if X.begin < 0:         X.begin = 0
    if X.end   > UTF8_MAX:  X.end   = UTF8_MAX + 1

    if X.size() == 0: return None

    db = {}
    current_begin = X.begin
    last_L        = len(unicode_to_utf8(X.end - 1))  # Length of utf8 sequence corresponding
    #                                                # the last value inside the interval.
    while 1 + 1 == 2:
        L = len(unicode_to_utf8(current_begin))   # Length of the first unicode in utf8
        # Store the interval together with the required byte sequence length (as key)
        current_end = UTF8_BORDERS[L-1]
        if L == last_L: 
            db[L] = Interval(current_begin, X.end)
            break
        db[L] = Interval(current_begin, current_end)
        current_begin = current_end

    return db

def _get_trigger_sequence_for_contigous_byte_range_interval(X, L):
    front_sequence = unicode_to_utf8(X.begin)
    back_sequence  = unicode_to_utf8(X.end - 1)
    # If the interval is contigous it must produce equal length utf8 sequences

    return [ Interval(front_sequence[i], back_sequence[i] + 1) for i in range(L) ]

def _get_contiguous_interval_sequences(X, L):
    """
    A contiguous interval in the domain is an interval where all 'N' first
    lexatoms in the range the same. The last 'N-2' lexatoms cover the whole
    range of lexatom values. The lexatoms at 'N-2' are all adjacent. 'N' may
    range from 1 to 'max. length of lexatom + 1'. In the case 'N=max. length of
    lexatom + 1' only the last by covers a range (if it does).
    
    EXAMPLE: UTF8 sequences related to the unicode interval [0x12345, 0x17653]. 
       
                                                 Sequence Description in 
          Unicode:  UTF8-byte sequence:          Contiguous Interval:

           012345    F0.92.8D.85        ----.
                     ...                    |=>  F0.92.8D.[85-BF]
           01237F    F0.92.8D.BF        ----'   
           012380    F0.92.8E.80        ----.   
                     ...                    |=>  F0.92.[8E-BF].[80-BF]
           012FFF    F0.92.BF.BF        ----'   
           013000    F0.93.80.80        ----.   
                     ...                    |=>  F0.[93-96].[8E-BF].[80-BF]
           016FFF    F0.96.BF.BF        ----'   
           017000    F0.97.80.80        ----.   
                     ...                    |=>  F0.97.[80-98].[80-BF]
           01763F    F0.97.98.BF        ----'   
           017640    F0.97.99.80        ----.   
                     ...                    |=>  F0.97.99.[80-93]
           017653    F0.97.99.93        ----'

    This function splits a given interval into such intervals. Providing such
    intervals and implementing it in state sequences avoids a complex hopcroft 
    minimization after the transformation.

    REQUIRES: The byte sequence in the given interval **must** have all the same 
              length L.

    RETURNS: List of 'contigous' intervals and the index of the first byte
             where all sequences differ.
    """
    # A byte in a utf8 sequence can only have a certain range depending
    # on its position. UTF8 sequences look like the following dependent
    # on their length:
    #
    #       Length:   Byte Masks for each byte
    #
    #       1 byte    0xxxxxxx
    #       2 bytes   110xxxxx 10xxxxxx
    #       3 bytes   1110xxxx 10xxxxxx 10xxxxxx
    #       4 bytes   11110xxx 10xxxxxx 10xxxxxx 10xxxxxx
    #       5 bytes   ...
    #
    # where 'free' bits are indicated by 'x'. 
    # Min. value of a byte = where all 'x' are zero.
    # Max. value of a byte = where all 'x' are 1.
    # 
    def min_byte_value(L, ByteIndex):
        assert L <= 6
        if ByteIndex != 0: return 0x80
        # Only first byte's range depends on length
        return { 0: 0x00, 1: 0xC0, 2: 0xE0, 3: 0xF0, 4: 0xF8, 5: 0xFC }[L]

    def max_byte_value(L, ByteIndex):
        assert L <= 6
        if ByteIndex != 0: 
            return 0b10111111
        # Only first byte's range depends on length
        return { 0: 0b01111111, 
                 1: 0b11011111, 
                 2: 0b11101111, 
                 3: 0b11110111,
                 4: 0b11111011,
                 5: 0b11111101 }[L]
       
    def find_first_diff_byte(front_sequence, back_sequence):
        # Find the first byte that is different in the front and back sequence 
        for i in range(L-1):
            if front_sequence[i] != back_sequence[i]: return i
        # At least the last byte must be different. That's why it **must** be the
        # one different if no previous byte was it.
        return L - 1

    assert X.size() != 0

    # Interval's size = 1 character      --> no split
    if X.size() == 1: return [ X ]
    # Resulting utf8 sequence length = 1 --> no split 
    elif L == 1:      return [ X ]

    # Utf8 Sequences representing first and last element in interval 'X'.
    front_sequence = unicode_to_utf8(X.begin)
    back_sequence  = unicode_to_utf8(X.end - 1)
    assert len(front_sequence) == len(back_sequence) 
    assert L == len(front_sequence)

    p      = find_first_diff_byte(front_sequence, back_sequence)
    result = []
    current_begin = X.begin
    byte_sequence = copy(front_sequence)
    byte_indices  = list(range(p + 1, L))
    for q in reversed(byte_indices):
        # There **must** be at least one overrun, even for 'q=p+1', since 'p+1' 
        # points to the first byte after the first byte that was different. If 'p' 
        # indexed that last byte this block is never entered.
        byte_sequence[q] = max_byte_value(L, q)
        current_end      = utf8_to_unicode(byte_sequence) + 1
        assert current_end <= X.end
        if current_begin != current_end:
            result.append(Interval(current_begin, current_end))
        current_begin    = current_end

    if front_sequence[p] + 1 != back_sequence[p]:
        if p == L - 1: byte_sequence[p] = back_sequence[p]
        else:          byte_sequence[p] = back_sequence[p] - 1 
        current_end      = utf8_to_unicode(byte_sequence) + 1
        assert current_end <= X.end
        if current_begin != current_end:
            result.append(Interval(current_begin, current_end))
        current_begin    = current_end

    byte_sequence[p] = back_sequence[p]
    for q in byte_indices:
        if back_sequence[q] == min_byte_value(L, q):
            byte_sequence[q] = back_sequence[q]
        else:
            if q == L - 1: byte_sequence[q] = back_sequence[q] 
            else:          byte_sequence[q] = back_sequence[q] - 1
            current_end      = utf8_to_unicode(byte_sequence) + 1
            assert current_end <= X.end
            if current_begin != current_end:
                result.append(Interval(current_begin, current_end))
            if current_begin == X.end: break
            current_begin    = current_end
            byte_sequence[q] = back_sequence[q]

    if current_begin != X.end:
        result.append(Interval(current_begin, X.end))

    return result
