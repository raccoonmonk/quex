# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
# (C) Frank-Rene Schaefer
from   quex.input.code.core                        import CodeFragment
from   quex.engine.state_machine.character_counter import SmLineColumnCountInfo
from   quex.engine.pattern                         import Pattern
from   quex.engine.analyzer.terminal.core          import Terminal
from   quex.engine.analyzer.door_id_address_label  import DoorID
from   quex.engine.misc.tools                      import typed

import quex.blackboard as blackboard
from   quex.blackboard import Lng, setup as Setup
from   quex.constants  import E_IncidenceIDs, \
                              E_TerminalType

def _aux_adorn_nothing(Code):
    return Code

def _aux_adorn_on_skip_range_open(Code):
    return CodeFragment([
        "%s\n" % Lng.DEFINE_NESTED_RANGE_COUNTER(), 
        Lng.SOURCE_REFERENCED(Code)
    ])

def _aux_adorn_on_bad_lexatom(Code):
    return CodeFragment([
        "%s\n" % Lng.DEFINE_BAD_LEXATOM(), 
        Lng.SOURCE_REFERENCED(Code),
        "%s\n" % Lng.UNDEFINE_BAD_LEXATOM(),
    ])

aux_db = {
    E_TerminalType.PLAIN:           (_aux_adorn_nothing, None, ""),
    E_TerminalType.MATCH_PATTERN:   (_aux_adorn_nothing, None, ""),

    E_TerminalType.MATCH_FAILURE:   (_aux_adorn_nothing, "FAILURE", ""),

    E_TerminalType.END_OF_STREAM:   
     (_aux_adorn_nothing, "END_OF_STREAM",
      "End of Stream FORCES a return from the lexical analyzer, so that no\n" \
      "tokens can be filled after the termination token.",
     ),
    E_TerminalType.BAD_LEXATOM:     
     (_aux_adorn_on_bad_lexatom, "BAD_LEXATOM",
      "Bad lexatom detection FORCES a return from the lexical analyzer, so that no\n" \
      "tokens can be filled after the termination token.",
     ),
    E_TerminalType.LOAD_FAILURE:    
     (_aux_adorn_nothing, "LOAD_FAILURE",
      "Load failure FORCES a return from the lexical analyzer, so that no\n" \
      "tokens can be filled after the termination token.",
     ),
    E_TerminalType.SKIP_RANGE_OPEN: 
     (_aux_adorn_on_skip_range_open, "SKIP_RANGE_OPEN",
      "End of Stream appeared, while scanning for end of skip-range.",
     ),
}

class CountCmdFactory(object):
    __slots__ = ("run_time_counter_f", "mode_name", "ca_map", 
                 "allow_constant_terms_f", "insert_shift_commands_f")
    @typed(ModeName=str, ExcludeConstTermsF=bool)
    def __init__(self, ModeName, CaMap, AllowConstTermsF, InsertShiftCommandsF=True):
        self.run_time_counter_f      = False
        self.mode_name               = ModeName
        self.ca_map                  = CaMap
        self.allow_constant_terms_f  = AllowConstTermsF
        self.insert_shift_commands_f = InsertShiftCommandsF

    def get(self, Dfa, InsertShiftCommandsF=True):
        if Dfa is None: return []
        lcci                = SmLineColumnCountInfo(self.ca_map, Dfa, False, 
                                                    Setup.buffer_encoding,
                                                    AllowConstTermsF=self.allow_constant_terms_f)
        run_time_counter_f, \
        cmd_list            = SmLineColumnCountInfo.get_OpList(lcci, 
                                                               ModeName=self.mode_name, 
                                                               InsertShiftCommandsF=self.insert_shift_commands_f)
        self.run_time_counter_f |= run_time_counter_f
        return cmd_list

class TerminalFactory:
    """Factory for Terminal-s
    ___________________________________________________________________________

    A TerminalStateFactory generates Terminal-s by its '.do()' member function.
    Terminal-s are created dependent on the E_TerminalTypes indicator.  The
    whole process is initiated in its constructor.

    Additionally, the factory keeps track of the necessity to count lexemes
    and the necessity of a default counter for line and column number.
    ___________________________________________________________________________
    """
    def __init__(self, ModeName, IncidenceDb, dial_db, IndentationHandlingF): 
        """Sets up the terminal factory, i.e. specifies all members required
        in the process of Terminal construction. 
        """
        self.run_time_counter_required_f = False
        self.mode_name    = ModeName
        self.dial_db      = dial_db

        if IndentationHandlingF: 
            self.txt_indentation_handler_call = Lng.INDENTATION_HANDLER_CALL(ModeName) 
        else:
            self.txt_indentation_handler_call = ""

        self.txt_store_last_character = Lng.STORE_LAST_CHARACTER(blackboard.required_support_begin_of_line())

        self.on_match = IncidenceDb.get(E_IncidenceIDs.MATCH)
        if not self.on_match: self.on_match = CodeFragment()

        self.on_after_match = IncidenceDb.get(E_IncidenceIDs.AFTER_MATCH)
        if not self.on_after_match: self.on_after_match = CodeFragment()

    @typed(Code=CodeFragment)
    def do(self, TerminalType, Code, ThePattern=None):
        """Construct a Terminal object based on the given TerminalType and 
        parameterize it with 'IncidenceId' and 'Code'.
        """
        global aux_db

        if ThePattern is not None:
            assert ThePattern.count_info() is not None

        if TerminalType in (E_TerminalType.END_OF_STREAM, 
                            E_TerminalType.BAD_LEXATOM, 
                            E_TerminalType.LOAD_FAILURE,
                            E_TerminalType.SKIP_RANGE_OPEN):

            adorn, name, comment_txt = aux_db[TerminalType]

            return self.__terminate_analysis_step(adorn(Code), name, comment_txt)
        else:
            return {
                E_TerminalType.PLAIN:           self.do_and_insert_count_code,
                E_TerminalType.MATCH_PATTERN:   self.do_match_pattern,
                # Error handlers:
                E_TerminalType.MATCH_FAILURE:   self.do_match_failure,
            }[TerminalType](Code, ThePattern)

    @typed(ThePattern=Pattern)
    def do_match_pattern(self, Code, ThePattern):
        """A pattern has matched."""
        lexeme_begin_f,     \
        terminating_zero_f, \
        adorned_code        = self.__adorn_user_code(Code, MatchF=True)

        # IMPORTANT: Terminals can be entered by any kind of 'GOTO'. In order to
        #            be on the safe side, BIPD should be started from within the
        #            terminal itself. Otherwise, it may be missed due to some 
        #            coding negligence.
        text = []
        if ThePattern.sm_bipd_to_be_reversed is not None:
            self.do_bipd_entry_and_return(text, ThePattern)

        text.extend([
            self.__counter_code(ThePattern.lcci),
            #
            adorned_code,
            #
            Lng.ON_AFTER_MATCH_THEN_RETURN # 'RETURN' since mode change may have occurred
        ])
        t = self.__terminal(text, Code, 
                            ThePattern.pattern_string(),
                            IncidenceId            = ThePattern.incidence_id,
                            LexemeBeginF           = lexeme_begin_f,
                            LexemeTerminatingZeroF = terminating_zero_f)
        assert t.incidence_id() == ThePattern.incidence_id
        return t

    def do_match_failure(self, Code, ThePattern):
        """No pattern in the mode has matched. Line and column numbers are 
        still counted. But, no 'on_match' or 'on_after_match' action is 
        executed.
        """
        lexeme_begin_f,     \
        terminating_zero_f, \
        adorned_code        = self.__adorn_user_code(Code, MatchF=False)

        text = [ 
            self.__counter_code(None),
            #
            adorned_code,
            #
            Lng.PURE_RETURN # 'RETURN' since mode change may have occurred
        ]
        return self.__terminal(text, Code, "FAILURE")

    def do_and_insert_count_code(self, Code, ThePattern, NamePrefix="", RequiredRegisterSet=None):
        """Plain source code text as generated by quex."""

        text = []
        text.extend(self.__counter_code(ThePattern.lcci))
        text.extend(Code.get_code())

        if ThePattern is None: name = "<no name>"
        else:                  name = ThePattern.pattern_string() 
        name = "%s%s" % (NamePrefix, name)

        return self.__terminal(text, Code, name, 
                               IncidenceId         = ThePattern.incidence_id, 
                               RequiredRegisterSet = RequiredRegisterSet)

    def __lexeme_flags(self, Code):
        lexeme_begin_f     =    self.on_match.requires_lexeme_begin_f(Lng)      \
                             or Code.requires_lexeme_begin_f(Lng)               \
                             or self.on_after_match.requires_lexeme_begin_f(Lng) 
        terminating_zero_f =    self.on_match.requires_lexeme_terminating_zero_f(Lng)       \
                             or Code.requires_lexeme_terminating_zero_f(Lng)                \
                             or self.on_after_match.requires_lexeme_terminating_zero_f (Lng)
        return lexeme_begin_f, terminating_zero_f

    def do_bipd_entry_and_return(self, txt, ThePattern):
        """(This is a very seldom case) After the pattern has matched, one needs 
        to determine the end of the lexeme by 'backward input position detection' 
        (bipd). Thus,

              TERMINAL 
                   '----------.
                       (goto) '---------> BIPD DFA
                                               ...
                                          (determine _read_p)
                                               |
                      (label) .----------------'
                   .----------'
                   |
              The actions on 
              pattern match.
        """
        door_id_entry  = DoorID.state_machine_entry(ThePattern.sm_bipd_to_be_reversed.get_id(), self.dial_db)
        door_id_return = DoorID.bipd_return(ThePattern.incidence_id, self.dial_db)
        txt.append("    %s\n%s\n" 
           % (Lng.GOTO(door_id_entry, self.dial_db),   # Enter BIPD
              Lng.LABEL(door_id_return)) # Return from BIPD
        )

    def __counter_code(self, LCCI):
        """Get the text of the source code required for 'counting'. This information
        has been stored along with the pattern before any transformation happened.
        No database or anything is required as this point.
        """
        run_time_counter_required_f, \
        cmd_list                     = SmLineColumnCountInfo.get_OpList(LCCI, ModeName=self.mode_name)

        self.run_time_counter_required_f |= run_time_counter_required_f
        text = Lng.COMMAND_LIST(cmd_list, self.dial_db)
        return "".join(Lng.REPLACE_INDENT(text))

    def __adorn_user_code(self, Code, MatchF):
        """Adorns user code with:
           -- storage of last character, if required for 'begin of line'
              pre-context.
           -- storage of the terminating zero, if the lexeme is required
              as a zero-terminated string.
           -- add the 'on_match' event handler in front, if match is relevant.
           -- adding source reference information.
        """
        code_user = Lng.SOURCE_REFERENCED(Code)

        lexeme_begin_f,    \
        terminating_zero_f = self.__lexeme_flags(Code)

        txt_terminating_zero = Lng.LEXEME_TERMINATING_ZERO_SET(terminating_zero_f)

        if MatchF: txt_on_match = Lng.SOURCE_REFERENCED(self.on_match)
        else:      txt_on_match = ""

        result = "".join([
            self.txt_store_last_character,
            txt_terminating_zero,
            txt_on_match,
            "{\n",
            code_user,
            "\n}\n",
        ])

        return lexeme_begin_f, terminating_zero_f, result

    def __terminate_analysis_step(self, Code, Name, Comment):
        lexeme_begin_f,     \
        terminating_zero_f, \
        adorned_code        = self.__adorn_user_code(Code, MatchF=True)
        
        text = [ 
            self.__counter_code(LCCI=None),
            # No indentation handler => Empty string.
            self.txt_indentation_handler_call,
            #
            adorned_code,
            #
            Lng.ML_COMMENT(Comment),
            Lng.PURE_RETURN # RETURN without on after match
            #__________________________________________________________________
            #
            # NOT: The following might include that something is sent after 
            #      the TERMINATION token. Also, the above code has *NOTHING'*
            #      to do with pattern match actions. It handles events.
            #
            # Lng.GOTO(DoorID.return_with_on_after_match(self.dial_db), self.dial_db)
            #
            #__________________________________________________________________
        ]
        return self.__terminal(text, Code, Name)

    def __terminal(self, Text, Code, Name,
                   IncidenceId=None,
                   LexemeTerminatingZeroF=False, LexemeBeginF=False,
                   RequiredRegisterSet=None):

        pure_code = Code.get_code()
        if not pure_code: pure_code = Text

        code = CodeFragment(Text, SourceReference = Code.sr) 

        result = Terminal(code, Name, 
                        IncidenceId                   = IncidenceId,
                        RequireLexemeTerminatingZeroF = LexemeTerminatingZeroF,
                        RequiresLexemeBeginF          = LexemeBeginF,
                        RequiredRegisterSet           = RequiredRegisterSet, 
                        dial_db                       = self.dial_db,
                        PureCode                      = pure_code)

        assert all(x==y for x, y in zip(pure_code, result.pure_code()))
        return result
