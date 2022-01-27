# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.engine.misc.interval_handling                        import NumberSet 
import quex.engine.state_machine.algorithm.nfa_to_dfa            as     nfa_to_dfa
import quex.engine.state_machine.algorithm.hopcroft_minimization as     hopcroft_minimization
import quex.engine.state_machine.index                           as     state_machine_index
from   quex.engine.state_machine.state.core                      import DFA_State
from   quex.engine.misc.tools                                    import typed
from   quex.engine.misc.interval_handling                        import NumberSet_All
from   quex.constants                                            import E_IncidenceIDs
from   quex.blackboard import setup as Setup

class EncodingTrafo:
    """Maintains information about a encoding transformation and functions that
    transform numbers and state machines from the 'pure' encoding to a target
    encoding.

        .name       = Name of the codec.
        .source_set = NumberSet of unicode code points which have a representation 
                      the given codec.
    """
    DEFAULT_LEXATOM_TYPE_SIZE = 4 # Byte

    @typed(Name=str, SourceSet=NumberSet, ErrorRangeByCodeUnitDb={int:NumberSet})
    def __init__(self, Name, SourceSet, ErrorRangeByCodeUnitDb):
        self.name       = Name
        self.source_set = SourceSet   

        # For every position in a code unit sequence, there might be a different
        # error range (see UTF8 or UTF16 for example).
        self._error_range_by_code_unit_db = ErrorRangeByCodeUnitDb

    def bad_lexatom_possible(self):
        """If there is any non-empty error range, then a lexatom may occurr
        which is outside the given encoding.
        """
        return any(not error_range.is_empty() 
                   for error_range in self._error_range_by_code_unit_db.values())

    def do_state_machine(self, sm):
        """Transforms a given state machine from 'Unicode Driven' to another
        character encoding type.

        *** THE ORIGINAL STATE INDICES REMAIN IN PLACE, IF THEY ARE NOT ***
        *** SUBJECT TO RANGE EXCEEDING.                                 ***
        
        RETURNS: 
           [0] Transformation complete (True->yes, False->not all transformed)
           [1] Transformed state machine. It may be the same as it was 
               before if there was no transformation actually.

        It is ensured that the result of this function is a DFA compliant
        state machine. 
        """
        assert Setup.lexatom.type_range is not None

        if sm is None: return True, None
        assert sm.is_DFA_compliant()

        all_complete_f = True
        if Setup.bad_lexatom_detection_f: 
            bad_lexatom_si = state_machine_index.get()
            # Generate the 'bad lexatom accepter'.
            bad_lexatom_state = DFA_State(AcceptanceF=True)
            bad_lexatom_state.mark_acceptance_id(E_IncidenceIDs.BAD_LEXATOM)
            sm.states[bad_lexatom_si] = bad_lexatom_state

        else:                    
            bad_lexatom_si = None

        # NOTE: Not 'iteritems()', for some encodings intermediate states are 
        #       generated. Those shall not be subject to transformation.
        _assert_original_state_index_set = set(sm.states.keys())
        for from_si, state in list(sm.states.items()):
            if from_si == bad_lexatom_si: continue
            target_map = state.target_map.get_map()

            for to_si, trigger_set in list(target_map.items()):
                if to_si == bad_lexatom_si: continue

                complete_f,  \
                new_state_db = self.do_transition(target_map, from_si, to_si, 
                                                  bad_lexatom_si) 
                # Assume that the 'target_map' has been adapted if changes were
                # necessary.
                if new_state_db is not None:
                    sm.states.update(new_state_db)

                all_complete_f &= complete_f

            # Transition to 'bad lexatom acceptor' on first code unit is best
            # to happen here, after all transitions have been adapted.
            self._add_transition_to_bad_lexatom_detector(target_map, bad_lexatom_si, 0)

            # If there were intermediate states being generated, the error
            # error detection must have been implemented right then.

        # Verify, that original states remained in place!
        assert _assert_original_state_index_set.issubset(list(sm.states.keys()))

        sm.delete_transitions_beyond_interval(Setup.lexatom.type_range)

        sm.delete_orphaned_states()

        # AFTER: Whatever happend, the transitions in the state machine MUST
        #        lie in the drain_set.
        if not sm.is_DFA_compliant(): 
            sm = nfa_to_dfa.do(sm, CloneF=False)
        sm = hopcroft_minimization.do(sm, CreateNewStateMachineF=False)

        return all_complete_f, sm

    @typed(Code=(int, int))
    def do_single(self, Code): 
        """Translate a single character code from unicode to the engine's
        encoding. The result is a sequence of code values.
        """
        result = self._do_single(Code)
        assert isinstance(result, (list, tuple))
        assert all(isinstance(x, int) for x in result)
        return result

    def _add_transition_to_bad_lexatom_detector(self, target_map, BadLexatomSi, CodeUnitIndex):
        # A state with an empty target map is not supposed to handle input.
        # => drop-out without bad-lexatom check.
        if   not target_map:       return
        elif BadLexatomSi is None: return
        error_range = self._error_range_by_code_unit_db[CodeUnitIndex]
        if error_range.is_empty(): return
        target_map[BadLexatomSi] = error_range

    def lexatom_n_per_character(self, CharacterSet):
        return 1     # Default behavior (e.g. UTF8 differs here)

    def lexatom_n_per_character_in_state_machine(self, SM):
        return 1     # Default behavior (e.g. UTF8 differs here)

    def variable_character_sizes_f(self): 
        return False # Default behavior (e.g. UTF8 differs here)

    def adapt_ranges_to_lexatom_type_range(self, LexatomTypeRange):
        self._adapt_error_ranges_to_lexatom_type_range(LexatomTypeRange)

    def _adapt_error_ranges_to_lexatom_type_range(self, LexatomTypeRange):
        for error_range in self._error_range_by_code_unit_db.values():
            error_range.mask_interval(LexatomTypeRange)

    def hopcroft_minimization_always_makes_sense(self): 
        # Default-wise no intermediate states are generated
        # => hopcroft minimization does not make sense.
        return False

class EncodingTrafoNone(EncodingTrafo):
    DEFAULT_LEXATOM_TYPE_SIZE = 4 # Byte

    def __init__(self):
        error_range_by_code_unit_db = { 
            0: NumberSet()  # No errors
        }
        EncodingTrafo.__init__(self, "none", NumberSet_All(), 
                               error_range_by_code_unit_db)

    def do_transition(self, from_target_map, FromSi, ToSi, BadLexatomSi):
        """Translates to transition 'FromSi' --> 'ToSi' inside the state
        machine according to 'Unicode'.

        'BadLexatomSi' is ignored. This argument is only of interest if
        intermediate states are to be generated. This it not the case for this
        type of transformation.

        RETURNS: [0] True if complete, False else.
                 [1] StateDb of newly generated states (always None, here)
        """
        # Do nothing
        return True, None

    def _do_single(self, Code):
        """No translation: character is translated to itself.
        """
        return [ Code ]

class EncodingTrafoUnicode(EncodingTrafo):
    DEFAULT_LEXATOM_TYPE_SIZE = 1 # Byte

    @typed(SourceSet=NumberSet)
    def __init__(self, SourceSet, Name="unicode"):
        # Plain 'Unicode' associates a character with a single code unit, i.e.
        # its 'code point'. 
        # => Only code unit '0' is specified and everything is allowed.
        #    ('everything allowed' is disputable, since certain ranges are
        #     disallowed.)
        assert Name in ("unicode", "utf32")
        error_range_by_code_unit_db = { 0: NumberSet() }
        EncodingTrafo.__init__(self, Name, SourceSet, 
                               error_range_by_code_unit_db)

    def do_transition(self, from_target_map, FromSi, ToSi, BadLexatomSi):
        """Translates to transition 'FromSi' --> 'ToSi' inside the state
        machine according to 'Unicode'.

        'BadLexatomSi' is ignored. This argument is only of interest if
        intermediate states are to be generated. This it not the case for this
        type of transformation.

        RETURNS: [0] True if complete, False else.
                 [1] StateDb of newly generated states (always None, here)
        """
        number_set = from_target_map[ToSi]

        if self.source_set.is_superset(number_set): 
            return True, None
        else:
            # Adapt 'number_set' in 'from_target_map' according to addmissible
            # range.
            number_set.intersect_with(self.source_set)
            return False, None

    def _do_single(self, Code): 
        """Unicode character is translated to itself.
        """
        return [ Code ]

    def adapt_ranges_to_lexatom_type_range(self, LexatomTypeRange):
        self.source_set.mask_interval(LexatomTypeRange)
        self._adapt_error_ranges_to_lexatom_type_range(LexatomTypeRange)

