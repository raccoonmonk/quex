# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.engine.misc.string_handling  import blue_print
from   quex.blackboard                   import Lng, \
                                                required_support_indentation_count, \
                                                E_IncidenceIDs

def do(Mode, ModeNameList):
    assert required_support_indentation_count()
    assert Mode.indentation_handling_f()

    on_indent_str         = Lng.event_handler(Mode, E_IncidenceIDs.INDENTATION_INDENT)
    on_nodent_str         = Lng.event_handler(Mode, E_IncidenceIDs.INDENTATION_NODENT)
    on_dedent_str         = Lng.event_handler(Mode, E_IncidenceIDs.INDENTATION_DEDENT)
    on_indentation_misfit = Lng.event_handler(Mode, E_IncidenceIDs.INDENTATION_MISFIT) 
    on_indentation_bad    = Lng.event_handler(Mode, E_IncidenceIDs.INDENTATION_BAD) 

    define_str, undefine_str = _get_definition_strings(Lng, ModeNameList)

    return blue_print(on_indentation_str, [
        ["$$DEFINITIONS$$",                         define_str],
        ["$$UNDEFINITIONS$$",                       undefine_str],
        ["$$INDENT-PROCEDURE$$",                    on_indent_str],
        ["$$NODENT-PROCEDURE$$",                    on_nodent_str],
        ["$$N-DEDENT-PROCEDURE$$",                  on_dedent_str],
        ["$$EVENT_HANDLER-on_indentation_misfit$$", on_indentation_misfit],
        ["$$EVENT_HANDLER-on_indentation_bad$$",    on_indentation_bad]
    ])



def _get_definition_strings(Lng, ModeNameList):
    # Note: 'on_indentation_bad' is applied in code generation for 
    #       indentation counter in 'indentation_counter.py'.
    counter_define_str, counter_undefine_str = Lng.DEFINE_COUNTER_VARIABLES()

    define_str = "\n".join([    
        Lng.DEFINE_SELF("me"),
        Lng.DEFINE_LEXEME_VARIABLES(),
        counter_define_str,
        Lng.MODE_DEFINITION(ModeNameList),
    ])
    undefine_str = "\n".join([
        Lng.UNDEFINE_SELF(),
        Lng.UNDEFINE_LEXEME_VARIABLES(),
        counter_undefine_str,
        Lng.MODE_UNDEFINITION(ModeNameList)
    ])

    return define_str, undefine_str


on_indentation_str = """
void
$on_indentation(QUEX_TYPE_ANALYZER*    me, 
                QUEX_TYPE_INDENTATION  Indentation, 
                QUEX_TYPE_LEXATOM*     Begin) 
{
$$DEFINITIONS$$

    (void)me;
    (void)Indentation;
    (void)Begin;

    QUEX_NAME(IndentationStack)*  stack = &me->counter._indentation_stack;
    QUEX_TYPE_INDENTATION*        start = 0x0;
    ptrdiff_t                     N = (ptrdiff_t)-1;
    size_t                        IndentationStackSize;
    QUEX_TYPE_INDENTATION*        IndentationStack = &stack->front[0];
    QUEX_TYPE_INDENTATION         IndentationUpper;
    QUEX_TYPE_INDENTATION         IndentationLower;
    (void)start;

    __quex_assert((long)Indentation >= 0);

    if( Indentation > *(stack->back) ) {
        ++(stack->back);
        if( stack->back == stack->memory_end ) {
            QUEX_NAME(MF_error_code_set_if_first)(me, E_Error_Indentation_StackOverflow);
            return;
        }
        *(stack->back) = Indentation;
$$INDENT-PROCEDURE$$
        return;
    }
    else if( Indentation == *(stack->back) ) {
$$NODENT-PROCEDURE$$
    }
    else  {
        start = stack->back;
        --(stack->back);
        while( Indentation < *(stack->back) ) {
            --(stack->back);
        }

        N = (ptrdiff_t)(start - stack->back);
        (void)N;
        if( Indentation == *(stack->back) ) { 
            /* 'Landing' must happen on indentation border. */
$$N-DEDENT-PROCEDURE$$
        } else { 
            IndentationStackSize = ((size_t)(1 + start - stack->front));
            IndentationUpper     = stack->back[0];
            IndentationLower     = ((stack->back == stack->front) ? *(stack->front) : *(stack->back - 1));
            (void)IndentationLower;
            (void)IndentationUpper;
            (void)IndentationStack;
            (void)IndentationStackSize;
$$EVENT_HANDLER-on_indentation_misfit$$
            return;
        }
    }

$$UNDEFINITIONS$$
}

void
$on_bad_indentation(QUEX_TYPE_ANALYZER* me) 
{
$$DEFINITIONS$$
#define BadCharacter  (me->buffer._read_p[-1])

(void)me;

$$EVENT_HANDLER-on_indentation_bad$$

#undef  BadCharacter
$$UNDEFINITIONS$$
}
"""

