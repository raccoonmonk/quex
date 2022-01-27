# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.input.code.base                                      import SourceRef_VOID, \
                                                                        SourceRef
from   quex.engine.state_machine.core                            import DFA
from   quex.engine.state_machine.character_counter               import SmLineColumnCountInfo
import quex.engine.state_machine.construction.setup_post_context as     setup_post_context
import quex.engine.state_machine.construction.setup_pre_context  as     setup_pre_context
import quex.engine.state_machine.algorithm.beautifier            as     beautifier
import quex.engine.misc.error                                    as     error
from   quex.engine.misc.tools                                    import typed, print_callstack

from   quex.engine.pattern import Pattern

from   quex.blackboard  import setup as Setup

class Pattern_Prep(object):
    __slots__ = ("__sr", # Source Reference (filename, line_n)
                 "__sm", 
                 "__post_context_f", 
                 "__post_context_sm",
                 "__pre_context_sm_to_be_reversed", 
                 "__pre_context_begin_of_line_f", 
                 "__pre_context_begin_of_stream_f", 
                 "__post_context_end_of_line_f", 
                 "__post_context_end_of_stream_f", 
                 "__pattern_string",
                 "__finalized_f")
    @typed(CoreSM=DFA, BeginOfLineF=bool, BeginOfStreamF=bool,
           EndOfLineF=bool, EndOfStreamF=bool,
           AllowNothingIsNecessaryF=bool, Sr=SourceRef)
    def __init__(self, CoreSM, PreContextSM=None, PostContextSM=None, 
                 BeginOfLineF=False, BeginOfStreamF=False, 
                 EndOfLineF=False, EndOfStreamF=False, Sr=SourceRef_VOID, 
                 PatternString="",
                 AllowNothingIsNecessaryF=False, AllowEmptyF=False):
        def assert_sm(sm):
            if sm is None: return
            assert isinstance(sm, DFA)
            assert sm.is_DFA_compliant()
            assert not sm.has_specific_acceptance_id()

        assert CoreSM is not None
        assert_sm(CoreSM)
        assert_sm(PreContextSM)
        assert_sm(PostContextSM)

        self.check_initial(CoreSM, 
                           BeginOfLineF, PreContextSM, 
                           EndOfLineF, PostContextSM, 
                           Sr, AllowNothingIsNecessaryF, AllowEmptyF)

        if PatternString is None: self.__pattern_string = ""
        else:                     self.__pattern_string = PatternString
        if Sr is None:            self.__sr             = SourceRef_VOID
        else:                     self.__sr             = Sr


        # (*) Setup the whole pattern
        self.__sm                           = CoreSM
        self.__post_context_sm              = PostContextSM
        self.__post_context_end_of_line_f   = EndOfLineF
        # EndOfLine shall encompass EndOfStreamF
        self.__post_context_end_of_stream_f = EndOfStreamF 

        # -- [optional] pre contexts
        #
        #    Same as for backward input position detection holds for pre-contexts.
        self.__pre_context_sm_to_be_reversed = PreContextSM

        # Detect the trivial pre-context
        self.__pre_context_begin_of_line_f   = BeginOfLineF
        self.__pre_context_begin_of_stream_f = BeginOfStreamF
        
        self.__validate(Sr, AllowEmptyF)
        self.__finalized_f = False

        # Equip state machines with source reference
        if self.__sm:                            self.__sm.sr                            = self.__sr
        if self.__post_context_sm:               self.__post_context_sm.sr               = self.__sr
        if self.__pre_context_sm_to_be_reversed: self.__pre_context_sm_to_be_reversed.sr = self.__sr

    @staticmethod
    def Empty():
        return Pattern_Prep(DFA.Empty(), AllowEmptyF=True)

    def clone(self):
        def cloney(X):
            if X is None:         return None
            elif type(X) == bool: return X
            else:                 return X.clone()

        return Pattern_Prep(cloney(self.__sm),
                            PreContextSM             = cloney(self.__pre_context_sm_to_be_reversed),
                            PostContextSM            = cloney(self.__post_context_sm),
                            BeginOfLineF             = cloney(self.__pre_context_begin_of_line_f),
                            BeginOfStreamF           = cloney(self.__pre_context_begin_of_stream_f),
                            EndOfLineF               = cloney(self.__post_context_end_of_line_f),
                            EndOfStreamF             = cloney(self.__post_context_end_of_stream_f),
                            Sr                       = self.__sr,
                            PatternString            = self.__pattern_string,
                            AllowNothingIsNecessaryF = True,
                            AllowEmptyF              = True)

    @property
    def sr(self):             return self.__sr

    @typed(Sr=SourceRef)
    def set_source_reference(self, Sr):
        self.__sr = Sr

    def pattern_string(self): return self.__pattern_string

    def set_pattern_string(self, Value): self.__pattern_string = Value

    def incidence_id(self):   return self.__sm.get_id()

    def set_incidence_id(self, Id):
        self.__sm.set_id(Id)

    def extract_sm(self): 
        """Extract the state machine from the pattern. The pattern may then no
        longer be used! It is considered further 'finalized'.

        A pattern's state machine can only be extracted ONCE!
        """
        tmp_sm = self.__sm
        self.__mark_dysfunctional()
        return tmp_sm

    def get_cloned_sm(self, StateMachineId=None): 
        """Get a clone of the pattern's state machine. That is, the caller may
        do with the state machine anything, but the pattern is not affected.
        """
        if self.__sm is None: return None
        return self.__sm.clone(StateMachineId=StateMachineId)

    def borrow_sm(self):
        """Exposes the core state machine to the user, assuming that he does not
        modify it.
        """
        return self.__sm

    @property
    def pre_context_sm_to_be_reversed(self):       return self.__pre_context_sm_to_be_reversed

    @property
    def pre_context_trivial_begin_of_line_f(self): 
        if self.__pre_context_sm_to_be_reversed is not None:
            return False
        return self.__pre_context_begin_of_line_f

    def has_pre_context(self): 
        return    self.__pre_context_begin_of_line_f \
               or self.__pre_context_begin_of_stream_f \
               or self.__pre_context_sm_to_be_reversed is not None

    def has_post_context(self):   
        return    self.__post_context_sm is not None \
               or self.__post_context_end_of_line_f  \
               or self.__post_context_end_of_stream_f

    def has_pre_or_post_context(self):
        return self.has_pre_context() or self.has_post_context()

    def __validate(self, Sr, AllowEmptyF):
        # Acceptance states shall not store the input position when they are 'normally'
        # post-conditioned. Post-conditioning via the backward search is a different 
        # ball-game.
        assert not any(state.input_position_store_f() and state.is_acceptance()
                       for state in list(self.__sm.states.values()))

        if not self.__sm.has_acceptance_state() and not AllowEmptyF:
            error.log("Pattern has no acceptance state and can never match.\n" + \
                      "Aborting generation process.", Sr)

        self.assert_consistency()

    def __repr__(self):
        return self.get_string(self)

    def get_string(self, NormalizeF=False, Option="utf8"):
        assert Option in ["utf8", "hex"]

        msg = self.__sm.get_string(NormalizeF, Option)
            
        if self.__pre_context_sm_to_be_reversed is not None:
            msg += "pre-context to be inverted = "
            msg += self.__pre_context_sm_to_be_reversed.get_string(NormalizeF, Option)           

        return msg

    def assert_consistency(self):
        def check(SM):
            if SM is None: return
            assert SM.is_DFA_compliant()
            assert not SM.has_orphaned_states()

        check(self.__sm)
        check(self.__pre_context_sm_to_be_reversed)
        check(self.__post_context_sm)

    @staticmethod
    def check_initial(core_sm, 
                      begin_of_line_f, pre_context, 
                      end_of_line_f,   post_context, 
                      Sr, 
                      AllowNothingIsNecessaryF, AllowEmptyF):

        def check(Name, Sm, Sr):
            if Sm is None: 
                return

            elif Sm.has_orphaned_states(): 
                error.log("Orphaned state(s) detected in %spattern (optimization lack).\n" % Name + \
                          "Please, log a defect at the projects website quex.sourceforge.net.\n"    + \
                          "Orphan state(s) = " + repr(Sm.get_orphaned_state_index_list()), 
                          Sr, DontExitF=True)
            elif Sm.is_Empty() and not AllowEmptyF:
                error.log("Empty %spattern." % Name, Sr)

            elif not AllowNothingIsNecessaryF:
                # 'Nothing is necessary' cannot be accepted. 
                # See the discussion in the module "quex.output.core.engine".
                Pattern_Prep.detect_path_of_nothing_is_necessary(Sm,  Name.strip(),  post_context_f, Sr)

        post_context_f = (post_context is not None)
        for name, sm in [("pre-context ", pre_context), ("", core_sm), ("post-context ", post_context)]:
            check(name, sm, Sr)

    @staticmethod
    def detect_path_of_nothing_is_necessary(sm, Name, PostContextPresentF, Sr):
        assert Name in ["", "pre-context", "post-context"]
        if sm is None: 
            return
        elif not sm.get_init_state().is_acceptance(): 
            return
        else:
            if not Name: name_str = "core pattern"
            else:        name_str = Name

        msg = "The %s contains in a 'nothing is necessary' path in the state machine.\n"   \
              % name_str                                                                     + \
              "This means, that without reading a character the analyzer drops into\n"   + \
              "an acceptance state. "

        msg += { 
            "":
                "The analyzer would then stall.",

            "pre-context":
                "E.g., pattern 'x*/y/' means that zero or more 'x' are a pre-\n"             + \
                "condition for 'y'. If zero appearances of 'x' are enough, then obviously\n" + \
                "there is no pre-context for 'y'! Most likely the author intended 'x+/y/'.",

            "post-context":
                "A post context where nothing is necessary is superfluous.",
        }[Name]

        if Name != "post-context" and PostContextPresentF:
            msg += "\n"                                                          \
                   "Note: A post context does not change anything to that fact." 

        error.log(msg, Sr)

    def finalize(self, CaMap):
        """Prepares for further processing:

            * Determines line column counting information (lcci)
            * Mounts pre and post context state machines

        RETURNS: 'Pattern' object.

        NOTE: After the call to this function 'self' is dysfunctional (empty).
        """
        assert not self.__finalized_f
        assert self.__sm is not None

        self.__finalized_f = True

        # Count information must be determined BEFORE transformation!
        if CaMap is not None:
            lcci = SmLineColumnCountInfo(CaMap, self.__sm, 
                                         self.pre_context_trivial_begin_of_line_f, 
                                         Setup.buffer_encoding)
        else: 
            lcci = None

        original_incidence_id = self.__sm.get_id()

        # (*) Pre-contexts and BIPD can only be mounted, after the transformation.
        sm_main,                      \
        sm_bipd_to_be_reversed        = _finalize_mount_post_context_sm(self.__sm, 
                                                                        self.__post_context_sm, 
                                                                        self.__post_context_end_of_line_f, 
                                                                        self.__post_context_end_of_stream_f, 
                                                                        self.__sr)

        if sm_main.is_Empty():
            sm_pre_context_to_be_reversed = None
        else:
            sm_pre_context_to_be_reversed = setup_pre_context.do(sm_main, 
                                                                 self.__pre_context_sm_to_be_reversed, 
                                                                 self.__pre_context_begin_of_line_f, 
                                                                 self.__pre_context_begin_of_stream_f)

        sm_main = sm_main.clone()
        sm_main.set_id(original_incidence_id)

        self.__mark_dysfunctional()

        return Pattern(sm_main, 
                       sm_pre_context_to_be_reversed, 
                       sm_bipd_to_be_reversed,
                       lcci, 
                       PatternString = self.__pattern_string, 
                       Sr            = self.__sr)

    def __mark_dysfunctional(self):
        # Set: self = Dysfunctional! (No one shall work or finalize this self)
        self.__sm                            = None
        self.__post_context_sm               = None
        self.__post_context_end_of_line_f    = None
        self.__post_context_f                = None
        self.__pre_context_sm_to_be_reversed = None
        self.__pre_context_begin_of_line_f   = None
        self.__pre_context_begin_of_stream_f = None
        self.__finalized_f                   = True

def _finalize_mount_post_context_sm(Sm, SmPostContext, PostEOL_f, PostEOS_f, Sr):
    # In case of a 'trailing post context' a 'bipd_sm' may be provided
    # to detect the input position after match in backward direction.
    # BIPD = backward input position detection.
    if Sm.is_Empty():
        return Sm, None

    sm,                    \
    bipd_sm_to_be_reversed = setup_post_context.do(Sm, SmPostContext, 
                                                   PostEOL_f, PostEOS_f, Sr)

    if bipd_sm_to_be_reversed is None: 
        return sm, None

    elif not bipd_sm_to_be_reversed.is_DFA_compliant(): 
        bipd_sm_to_be_reversed = beautifier.do(bipd_sm_to_be_reversed)

    return sm, bipd_sm_to_be_reversed

