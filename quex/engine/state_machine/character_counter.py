# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
# (C) 2012 Frank-Rene Schaefer
from   quex.engine.counter          import CountActionMap
from   quex.engine.misc.tree_walker import TreeWalker
from   quex.engine.misc.tools       import typed
from   quex.constants               import E_Count, E_R
from   quex.engine.operations.operation_list import Op

from   quex.blackboard import setup as Setup, Lng

class SmLineColumnCountInfo(object):
    """Information on character counting characteristics of lexeme that match a 
    given state machine.
    
      .line_n_increment   
        
         The number of lines that appear in the pattern.
         
         E_Count.VOID => cannot be determined from the pattern off-line.

      .line_n_increment_by_lexeme_length 

         If the line number increment is proportional to the length of the
         lexeme which is matched, then this variable contains the factor. 
         
         E_Count.VOID => lexeme length not proportional to line_n_increment.

      .column_index
      
         If the column index after match has a specific value, then this 
         member variable contains its value. 

         E_Count.VOID => No specific value for '.column_index'.

         (This makes sense for pattern that have a 'begin-of-line' pre-
         context. Or, when it contains a newline such as "\\notto".)

      .column_n_increment 
      
         The number of columns that appear in the pattern 
         
         E_Count.VOID => it cannot be determined from the pattern off-line.

      .column_n_increment_by_lexeme_length 

         If the column number increment is proportional to the length of the
         lexeme which is matched, then this variable contains the factor. 

         E_Count.VOID => if there is no relation between lexeme length and
                         column number increment.
    """
    __slots__ = (
        "column_n_increment",
        "line_n_increment",
        "column_index",
        "grid_step_n",
        "column_n_increment_by_lexeme_length",
        "line_n_increment_by_lexeme_length",
        "grid_step_size_by_lexeme_length",
        "run_time_counter_required_f"
    )
    @typed(CaMap=CountActionMap)
    def __init__(self, CaMap, SM, BeginOfLineF=False, CodecTrafoInfo=None, AllowConstTermsF=True):
        """LINE AND COLUMN NUMBER ANALYSIS ________________________________________
        
        Given a pattern as a state machine 'SM' this function analyses the 
        increments of line and column numbers. Depending on whether those 
        values can be determined from the state machine or only during run-
        time, a SmLineColumnCountInfo object is provided.
        
        NOTES _____________________________________________________________________

        DFA shall not contain pre- or post-contexts.
        
        DEPENDS ON: CaMap providing three databases:

                    .newline
                    .grid
                    .column 

        RESTRICTION _______________________________________________________________

        * The current approach does consider the column count to be void as soon  *
        * as a state is reached with two different column counts.                 *

        Disadvantage:

        Sub-optimal results for a very restricted amount of patterns.  In these
        cases, a 'count' is implemented where a plain addition or setting would be
        sufficient.

        Sub-Optimal Scenario:
        
        If there is more than one path to one node in the state machine with
        different column counts AND after that node there comes a newline from
        whereon the pattern behaves 'deterministic'.

        Reason for restriction left in place:

        To fix this, another approach would have to be implemented where the state
        machine is inverted and then the column counts starts from rear to front
        until the first newline. This tremendous computation time overhead is shied
        away from, because of the aforementioned low expected value add.

        RETURNS: 'None', if SM is empty (no transitions).
                  SmLineColumnCountInfo, else.

        ___________________________________________________________________________
        """
        Count.init(CaMap)
        result = _analyze(CaMap, SM, BeginOfLineF, CodecTrafoInfo, AllowConstTermsF)

        if result is None:
            # Do not count at all
            self.line_n_increment                    = 0
            self.line_n_increment_by_lexeme_length   = 0
            self.column_index                        = 0
            self.column_n_increment                  = 0
            self.column_n_increment_by_lexeme_length = 0
            self.grid_step_n                         = 0
            self.grid_step_size_by_lexeme_length     = 0
            self.run_time_counter_required_f         = False
        else:
            def _real(Object, ValueOfVirginity):
                if   Object.value == E_Count.VIRGIN: return ValueOfVirginity
                elif Object.value == E_Count.NONE:   return 0
                return Object.value

            self.line_n_increment                    = _real(result.line_n_increment,                   0)
            self.line_n_increment_by_lexeme_length   = _real(Count.line_n_increment_by_lexeme_length,   0)
            self.column_index                        = _real(result.column_index,                       E_Count.VOID)
            self.column_n_increment                  = _real(result.column_n_increment,                 0)
            self.column_n_increment_by_lexeme_length = _real(Count.column_n_increment_by_lexeme_length, 0)
            self.grid_step_n                         = _real(result.grid_step_n,                        0)
            self.grid_step_size_by_lexeme_length     = _real(Count.grid_step_size_by_lexeme_length,     E_Count.VOID)

            if CodecTrafoInfo is not None and CodecTrafoInfo.variable_character_sizes_f():
                self._consider_variable_character_sizes(SM, CodecTrafoInfo)

            self.run_time_counter_required_f = self.__run_time_counter_required_f()

    def __run_time_counter_required_f(self):
        if (    self.grid_step_size_by_lexeme_length != 0 \
            and self.grid_step_size_by_lexeme_length != E_Count.VOID):
            return False
        if (    self.line_n_increment_by_lexeme_length     == E_Count.VOID \
            and self.line_n_increment                      == E_Count.VOID):
            return True
        elif (    self.column_n_increment_by_lexeme_length == E_Count.VOID \
              and self.column_n_increment                  == E_Count.VOID \
              and self.column_index                        == E_Count.VOID):
            return True
        else:
            return False

    @classmethod
    def get_OpList(cls, LCCI, ModeName, InsertShiftCommandsF=True):
        """RETURN: [0] Verdict
                   [1] CounterCode

        Verdict == True  --> Run-time counter implementation required!!
                             Pattern's length cannot be determined beforehand.
                             
                   False --> No run-time counting is necessary!!
                             It was possible to determine the increments
                             based on the pattern's structure. 
                                 
        Default Character Counter is used when the increments and/or setting 
        cannot be derived from the pattern itself. 
        """
        if not (Setup.count_line_number_f or Setup.count_column_number_f):
            return False, []
        elif LCCI is None:
            return True, [ Op.PasspartoutCounterCall(ModeName, E_R.InputP) ]
        elif LCCI.run_time_counter_required_f:
            return True, [ Op.PasspartoutCounterCall(ModeName, E_R.InputP) ]

        # (*) Determine Line and Column Number Count ______________________________
        #    
        #     Both, for line and column number considerations the same rules hold.
        #     Those rules are defined in 'get_offset()' as shown below.
        #
        def get_offset(Increment, IncrementByLexemeLength):
            if IncrementByLexemeLength == 0 or Increment == 0:
                return None, None
            elif Increment != E_Count.VOID:
                return Increment, 1
            else:
                return Lng.LEXEME_LENGTH(), IncrementByLexemeLength

        # Column and line counts must be shifted (begin=end) even if only
        # columns are counted. For example, even if only columns are modified
        # the old line_number_at_begin must be adapted to the current.
        cmd_list = []
        if InsertShiftCommandsF:
            cmd_list.extend([Op.ColumnCountShift() , Op.LineCountShift()])

        # -- Line Number Count
        offset, factor = get_offset(LCCI.line_n_increment, 
                                    LCCI.line_n_increment_by_lexeme_length) 
        if offset is not None:
            cmd_list.append(Op.LineCountAdd(offset, factor))

        # -- Column Number Count
        if  LCCI.column_index != E_Count.VOID:
            cmd_list.append(Op.ColumnCountSet(LCCI.column_index + 1))

        elif LCCI.grid_step_n != 0:
            # Following assert results from entry check against 'VOID'
            assert LCCI.grid_step_size_by_lexeme_length != E_Count.VOID

            if   LCCI.grid_step_n == E_Count.VOID: grid_step_n = Lng.LEXEME_LENGTH()
            elif LCCI.grid_step_n != 0:            grid_step_n = LCCI.grid_step_n
            else:                                  grid_step_n = None

            if grid_step_n is not None:
                cmd_list.append(Op.ColumnCountGridAdd(LCCI.grid_step_size_by_lexeme_length, 
                                                      grid_step_n)) 
        else:
            offset, factor = get_offset(LCCI.column_n_increment, 
                                        LCCI.column_n_increment_by_lexeme_length) 
            if offset is not None:
                cmd_list.append(Op.ColumnCountAdd(offset, factor))

        return False, cmd_list

    def _consider_variable_character_sizes(self, SM, CodecTrafoInfo):
        """UTF8 and UTF16 counters may have different numbers of chunks that
        represent a single character. In such cases, it cannot be concluded from
        the LexemeL to the number of involved characters. In such cases, column and
        line number counter have to be done at run-time. This is signalized by

                self.column_n_increment_by_lexeme_length = E_Count.VOID
                self.grid_step_size_by_lexeme_length     = E_Count.VOID

        and respectively

               self.line_n_increment_by_lexeme_length  = E_Count.VOID

        If the number of chunks per character is the same for all involved characters,
        then the factor can be adapted by this number. For example, if all characters
        involve 2 bytes and the buffer element is 'byte', then the character number
        is equal to number of bytes divide by two, i.e.
        
                self.column_n_increment_by_lexeme_length /= 2.
        """
        lexatom_n_per_char = -1

        # If the internal engine is not running on Unicode, considerations
        # may be made about the byte number per character (e.g. UTF8).
        if    self.column_n_increment != E_Count.VOID \
           or self.column_index       != E_Count.VOID:
           # No problem in this case; increment does not depend on the lexeme length.
           pass

        elif    self.column_n_increment_by_lexeme_length != E_Count.VOID \
             or self.grid_step_size_by_lexeme_length     != E_Count.VOID:
            # In this case, the column number increment is a function of
            # the lexeme length. This is only valid if all characters in the
            # pattern actually have the same number of 'chunks' (e.g. bytes in UTF8).
            lexatom_n_per_char = CodecTrafoInfo.lexatom_n_per_character_in_state_machine(SM)
            if lexatom_n_per_char is None:
                # One cannot conclude from the number of bytes of a lexeme to 
                # the number of columns to be incremented.
                self.column_n_increment_by_lexeme_length = E_Count.VOID
                self.grid_step_size_by_lexeme_length     = E_Count.VOID
            else:
                if self.column_n_increment_by_lexeme_length  != E_Count.VOID:
                    self.column_n_increment_by_lexeme_length = float(self.column_n_increment_by_lexeme_length) / lexatom_n_per_char
                elif self.grid_step_size_by_lexeme_length    != E_Count.VOID:
                    self.grid_step_size_by_lexeme_length     = float(self.grid_step_size_by_lexeme_length) / lexatom_n_per_char

        if self.line_n_increment != E_Count.VOID:
            # No problem in this case; increment does not depend on the lexeme length.
            pass
        
        elif self.line_n_increment_by_lexeme_length != E_Count.VOID:
            if lexatom_n_per_char == -1: # If not yet determined, determine!
                lexatom_n_per_char = CodecTrafoInfo.lexatom_n_per_character_in_state_machine(SM)
            if lexatom_n_per_char is None:
                self.line_n_increment_by_lexeme_length  = E_Count.VOID
            elif self.line_n_increment_by_lexeme_length != E_Count.VOID:
                self.line_n_increment_by_lexeme_length  = float(self.line_n_increment_by_lexeme_length) / lexatom_n_per_char

    def __str__(self):
        return "line_n_increment                    = %s;\n" \
               "column_index                        = %s;\n" \
               "column_n_increment                  = %s;\n" \
               "grid_step_n                         = %s;\n" \
               "line_n_increment_by_lexeme_length   = %s;\n" \
               "column_n_increment_by_lexeme_length = %s;\n" \
               "grid_step_size_by_lexeme_length     = %s;\n" \
               % (
                  self.line_n_increment,
                  self.column_index,
                  self.column_n_increment, 
                  self.grid_step_n,
                  self.line_n_increment_by_lexeme_length, 
                  self.column_n_increment_by_lexeme_length,
                  self.grid_step_size_by_lexeme_length
               )

class UniqueValue(object):
    """A simple class to hold a value that is:

              -- VIRGIN, if it has not been assigned.
              -- VOID, if it has been assigned with different values.
              -- Some Value, if the assignment was always the same.
    """
    __slots__ = ('value')
    def __init__(self, InitValue=E_Count.VIRGIN):
        assert InitValue is not None
        if isinstance(InitValue, UniqueValue): self.value = InitValue.value
        else:                                  self.value = InitValue

    def clone(self):
        return UniqueValue(self.value)

    def __ilshift__(self, Value):
        """Use 'injection' to fulfill the task of virgin, void, coherent assignment."""
        assert not isinstance(Value, UniqueValue) 
        assert Value is not None
        if   self.value == E_Count.VIRGIN: self.value = Value
        elif Value      == E_Count.NONE:   self.value = E_Count.NONE
        elif self.value == E_Count.VOID:   pass
        elif self.value != Value:          self.value = E_Count.VOID
        else:                              pass # No change
        return self

    def __iadd__(self, Value):
        assert not isinstance(Value, UniqueValue) 
        if   self.value == E_Count.VIRGIN: self.value  = Value
        elif self.value == E_Count.VOID:   pass
        elif self.value == E_Count.NONE:   pass
        else:                              self.value += Value
        return self

    def __eq__(self, Other):
        if isinstance(Other, UniqueValue): other_value = Other.value
        else:                              other_value = Other

        if self.value == other_value: 
            return True

        # NONE == VIRGIN
        if   (self.value == E_Count.NONE   and other_value == E_Count.VIRGIN) \
          or (self.value == E_Count.VIRGIN and other_value == E_Count.NONE):
            return True
       
        return False

    def __ne__(self, Other):
        return not (self == Other)

    def __str__(self):
        return str(self.value)

    def is_number(self):
        if self.value == E_Count.VIRGIN or self.value == E_Count.VOID: 
            return False
        if isinstance(self.value, str):
            return False
        return True

class CharacterCountTracer(TreeWalker):
    """________________________________________________________________________
    
    Recursive Algorithm to count the number of newlines, characters, or spaces
    for each state in the state machine. It is done for each state, so that 
    path walking can be aborted as soon as a known state is hit.

     -- A loop makes a count either (i) void if the counted character appears, 
        or (ii) is unimportant. If (i) happens, then the counter is globally
        void. In case of (ii) no change happened so any analysis starting from
        the loop's knot point is still valid and does not have to be made 
        again.

     -- A node is met through another path. Exactly the same consideration as
        for loops holds again. The break-up here is also essential to avoid
        exponential time (The total number of paths multiplies with the number
        of branches through each knot on the path).

    ONLY PATTERNS WITHOUT PRE- AND POST-CONTEXT ARE HANDLED HERE!
    ___________________________________________________________________________
    """   
    def __init__(self, SM):  
        self.sm       = SM
        self.result   = Count(E_Count.VIRGIN, E_Count.VIRGIN, E_Count.VIRGIN, E_Count.VIRGIN)
        if SM.get_init_state().is_acceptance():
            self.result = Count(ColumnN=0, LineN=0, ColumnIndex=E_Count.VIRGIN, GridStepN=E_Count.VIRGIN)
        else:
            self.result = Count(E_Count.VIRGIN, E_Count.VIRGIN, E_Count.VIRGIN, E_Count.VIRGIN)
        self.known_db = {}  # state_index --> count
        TreeWalker.__init__(self)

    def on_enter(self, Info):  
        """Info = (state_index of what is entered, character set that triggers to it)"""
        StateIndex, CharacterSet, count = Info

        if not count.compute(CharacterSet):
            self.result.register_result(count)
            self.abort_f = True
            return None


        state = self.sm.states[StateIndex]
        known = self.known_db.get(StateIndex)
        if known is not None:
            # Set elements to 'VOID' if the previous count deviates from current count.
            # 'voidify' returns 'True' if all elements have been set to void.
            if self.result.voidify_deviants(known, count): self.abort_f = True

            # Rest of paths starting from this state has been walked along before
            subsequent = None
        else:
            known                     = count.clone()
            self.known_db[StateIndex] = known

            subsequent = [ (state_index, character_set, count.clone()) \
                           for state_index, character_set in state.target_map ]

        if state.is_acceptance():
            if not self.result.register_result(known): self.abort_f = True

        return subsequent

    def on_finished(self, node):   
        pass

class Count(object):
    """________________________________________________________________________

    Contains increment of line and column number of a pattern as soon as one
    particular state has been reached.
    ___________________________________________________________________________
    """
    __slots__ = ('column_n_increment', 'line_n_increment', 'column_index', 'grid_step_n')

    # (*) Increment per step:
    #
    #     If the increment per step is the same 'C' for any character that
    #     appears in the pattern, then the length of the pattern can be
    #     computed at run- time by a simple subtraction:
    # 
    #               length = (LexemeEnd - LexemeBegin) * C
    #
    #     provided that there is no newline in the pattern this is at the same
    #     time the column increment. Same holds for line number increments.
    column_n_increment_by_lexeme_length = None

    # Just for info, in Unicode there are the following candidates which may
    # possibly have assigned a separate line number increment: Line Feed, 0x0A;
    # Vertical Tab, 0x0B; Form Feed, 0x0C; Carriage Return, 0x0D; Next Line,
    # 0x85; Line Separator, 0x28; Paragraph Separator, 0x2029; 
    line_n_increment_by_lexeme_length   = None
    grid_step_size_by_lexeme_length     = None

    # Line/Column count information
    count_map                           = None

    @staticmethod
    @typed(CountMap=CountActionMap)
    def init(CountMap):
        """Initialize global objects in namespace 'Count'."""
        Count.column_n_increment_by_lexeme_length = UniqueValue()
        Count.line_n_increment_by_lexeme_length   = UniqueValue()
        Count.grid_step_size_by_lexeme_length     = UniqueValue()
        Count.count_map                           = CountMap

    def __init__(self, ColumnN, LineN, ColumnIndex, GridStepN=0, AllowConstTermsF=True):
        self.line_n_increment   = UniqueValue(LineN)
        self.column_n_increment = UniqueValue(ColumnN)
        self.column_index       = UniqueValue(ColumnIndex)
        self.grid_step_n        = UniqueValue(GridStepN)

        if not AllowConstTermsF:
            self.line_n_increment   <<= E_Count.VOID
            self.column_n_increment <<= E_Count.VOID
            self.column_index       <<= E_Count.VOID
            self.grid_step_n        <<= E_Count.VOID

    def clone(self):
        return Count(self.column_n_increment, 
                     self.line_n_increment, 
                     self.column_index, 
                     self.grid_step_n)

    def compute(self, CharacterSet):
        """CharacterSet -- If a given input character lies in the CharacterSet,
                           then a state transition happens. 
        
        This function determines the influence of such a state transition 
        on the line and column numbers.

        RETURNS: 
        
        True  -- If it is worth to consider subsequent transitions, because the
                 line or column numbering is still deterministic.

        False -- If all further consideration may be dropped, because line and
                 column numbering cannot be determined deterministically from 
                 the state machine.  
        """
        def void_line_count():
            Count.line_n_increment_by_lexeme_length <<= E_Count.VOID
            self.line_n_increment                   <<= E_Count.VOID

        def void_grid_steps():
            Count.grid_step_size_by_lexeme_length   <<= E_Count.VOID
            self.grid_step_n                        <<= E_Count.VOID

        def void_column_count():
            Count.column_n_increment_by_lexeme_length <<= E_Count.VOID
            self.column_n_increment                   <<= E_Count.VOID

        column, grid, line = Count.count_map.get_count_commands(CharacterSet)
        if line == -1:
            void_line_count()
        elif line is not None:
            delta = line
            # 'CharacterSet' does not contain anything beyond 'character_set'
            Count.line_n_increment_by_lexeme_length   <<= delta
            Count.column_n_increment_by_lexeme_length <<= 0
            Count.grid_step_size_by_lexeme_length     <<= 0
            self.column_n_increment                   <<= 0
            self.column_index                         = 0 # UniqueValue(E_Count.VIRGIN)
            self.grid_step_n                          = UniqueValue(E_Count.VIRGIN)
            if isinstance(delta, str): 
                void_line_count()
            else:
                self.line_n_increment  += delta

        if grid == -1:
            void_grid_steps()

        elif grid is not None:
            grid_size = grid
            # 'CharacterSet' does not contain anything beyond 'character_set'
            Count.line_n_increment_by_lexeme_length <<= 0
            Count.grid_step_size_by_lexeme_length   <<= grid_size
            if isinstance(grid_size, str): 
                void_grid_steps()
            else:
                self.grid_step_n += 1 # Remains VOID, if it is already
                if self.column_index.is_number():
                    delta = grid_size - (self.column_index.value % grid_size)

                    Count.column_n_increment_by_lexeme_length <<= delta
                    self.column_index                          += delta
                    self.column_n_increment                    += delta
                else:
                    void_column_count()

        if column == -1:
            void_column_count()
            self.column_index <<= E_Count.VOID
        elif column is not None:
            delta = column
            # 'CharacterSet' does not contain anything beyond 'character_set'
            Count.line_n_increment_by_lexeme_length   <<= 0
            Count.column_n_increment_by_lexeme_length <<= delta
            Count.grid_step_size_by_lexeme_length     <<= 0
            # Assign 'NONE' which prevents increment to it. 
            # (Assinging '0' would not prevent increment.)
            self.grid_step_n <<= E_Count.NONE

            if isinstance(delta, str): 
                void_column_count()
                self.column_index <<= E_Count.VOID
            else:
                self.column_index       += delta
                self.column_n_increment += delta

        if self.all_void(): return False # Abort if all void
        else:               return True # Do not abort, yet

    def all_void(self):
        """Determine whether all values are void. In that case the counting
        may be aborted.
        """
        return \
                   Count.column_n_increment_by_lexeme_length == E_Count.VOID \
               and Count.line_n_increment_by_lexeme_length   == E_Count.VOID \
               and Count.grid_step_size_by_lexeme_length     == E_Count.VOID \
               and self.column_index                         == E_Count.VOID \
               and self.column_n_increment                   == E_Count.VOID \
               and self.line_n_increment                     == E_Count.VOID \
               and self.grid_step_n                          == E_Count.VOID 

    def register_result(self, Result):
        """Register the counted numbers for one path to an acceptance state.
        If any parameter has not yet been set before, set it. The call to
        'voidify_deviants()' ensures that parameters which have different
        counts for different paths are set to VOID.

        RETURNS: False, if analysis should be aborted, because all has
                        been detected as being VOID.
                 True, if analysis may continue, since it may still be
                       possible that one or the other value remains.
        """
        if self.line_n_increment   == E_Count.VIRGIN: self.line_n_increment   = Result.line_n_increment.clone()
        if self.column_index       == E_Count.VIRGIN: self.column_index       = Result.column_index.clone()
        if self.column_n_increment == E_Count.VIRGIN: self.column_n_increment = Result.column_n_increment.clone()
        if self.grid_step_n        == E_Count.VIRGIN: self.grid_step_n        = Result.grid_step_n.clone()

        return not self.voidify_deviants(self, Result)

    def voidify_deviants(self, Known, New):
        """Compares elements of 'Know' with 'New' representing counts of 
           different paths through the state machine. If counts differ
           for different paths, they are 'VOID' and cannot be determined
           beforehand.

           RETURNS: 'True' if all counts are 'VOID', thus the investigation
                           can be aborted.
                    'False' else.
        """
        if Known.line_n_increment   != New.line_n_increment:   self.line_n_increment   <<= E_Count.VOID
        if Known.column_index       != New.column_index:       self.column_index       <<= E_Count.VOID
        if Known.column_n_increment != New.column_n_increment: self.column_n_increment <<= E_Count.VOID
        if Known.grid_step_n        != New.grid_step_n:        self.grid_step_n        <<= E_Count.VOID

        return     self.column_index       == E_Count.VOID \
               and self.column_n_increment == E_Count.VOID \
               and self.grid_step_n        == E_Count.VOID \
               and self.line_n_increment   == E_Count.VOID 
               #and Count.line_n_increment_by_lexeme_length   == E_Count.VOID \
               #and Count.column_n_increment_by_lexeme_length == E_Count.VOID \
               #and Count.grid_step_size_by_lexeme_length     == E_Count.VOID 

    def __str__(self):
        return "general: {\n"                                    \
               "    column_n_increment_by_lexeme_length = %s;\n" \
               "    grid_step_size_by_lexeme_length          = %s;\n" \
               "    line_n_increment_by_lexeme_length   = %s;\n" \
               "}\n"                                             \
               "column_index       = %s;\n"     \
               "column_n_increment = %s;\n"     \
               "line_n_increment   = %s;\n"     \
               % (Count.column_n_increment_by_lexeme_length,
                  Count.grid_step_size_by_lexeme_length, 
                  Count.line_n_increment_by_lexeme_length, 
                  self.column_index,
                  self.column_n_increment, 
                  self.line_n_increment)

def _analyze(CaMap, SM, BeginOfLineF, CodecTrafoInfo, AllowConstTermsF):
    assert SM.is_DFA_compliant()
    tracer     = CharacterCountTracer(SM)
    init_state = SM.get_init_state()

    init_state_target_map = init_state.target_map.get_map()
    if not init_state_target_map:
        return None # Do not count anything

    if BeginOfLineF: column_index = 0
    else:            column_index = E_Count.VOID
    count = Count(0, 0, ColumnIndex=column_index, GridStepN=E_Count.VIRGIN, 
                  AllowConstTermsF=AllowConstTermsF)
    # Next Node: [0] state index of target state
    #            [1] character set that triggers to it
    #            [2] count information (initialized to 'virgin')
    initial = [ 
        (target_state_index, character_set, count.clone()) \
        for target_state_index, character_set in init_state_target_map.items() 
    ]

    tracer.do(initial)

    # If there was an acceptance state, the result cannot be None
    assert tracer.result is not None

    # (*) Determine detailed count information
    if tracer.abort_f and Count.grid_step_size_by_lexeme_length.value == E_Count.VIRGIN:
        # If the count procedure was aborted, possibly NOT all character
        # transitions have been investigated. So the value for 'grid' must
        # determined now, independently of the 'tracer.do()'.
        Count.grid_step_size_by_lexeme_length <<= E_Count.VOID

    return tracer.result

