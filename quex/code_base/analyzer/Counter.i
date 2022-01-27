#ifndef QUEX_INCLUDE_GUARD__ANALYZER__COUNTER_I
#define QUEX_INCLUDE_GUARD__ANALYZER__COUNTER_I

$$INC: definitions$$
$$INC: analyzer/asserts$$
$$INC: analyzer/Counter$$

QUEX_NAMESPACE_MAIN_OPEN

QUEX_INLINE bool
QUEX_NAME(Counter_construct)(QUEX_NAME(Counter)* me)
{
    $$<count-line>   me->_line_number_at_begin   = (size_t)1;$$
    $$<count-line>   me->_line_number_at_end     = (size_t)1;$$
    $$<count-column> me->_column_number_at_begin = (size_t)1;$$
    $$<count-column> me->_column_number_at_end   = (size_t)1;$$

    $$<indentation>  QUEX_NAME(IndentationStack_init)(&me->_indentation_stack);$$
    return true;
}

QUEX_INLINE void
QUEX_NAME(Counter_resources_absent_mark)(QUEX_NAME(Counter)* me)
{
    $$<count-line> me->_line_number_at_begin               = (size_t)0;$$
    $$<count-line> me->_line_number_at_end                 = (size_t)0;$$
    $$<count-column> me->_column_number_at_begin           = (size_t)0;$$
    $$<count-column> me->_column_number_at_end             = (size_t)0;$$
    $$<indentation> me->_indentation_stack.back       = (QUEX_TYPE_INDENTATION*)0;$$
    $$<indentation> me->_indentation_stack.memory_end = (QUEX_TYPE_INDENTATION*)0;$$
}

QUEX_INLINE bool
QUEX_NAME(Counter_resources_absent)(QUEX_NAME(Counter)* me)
{
    $$<count-line> if( me->_line_number_at_begin               != (size_t)0) return false;$$
    $$<count-line> if( me->_line_number_at_end                 != (size_t)0) return false;$$
    $$<count-column> if( me->_column_number_at_begin           != (size_t)0) return false;$$
    $$<count-column> if( me->_column_number_at_end             != (size_t)0) return false;$$
    $$<indentation> if( me->_indentation_stack.back       != (QUEX_TYPE_INDENTATION*)0) return false;$$
    $$<indentation> if( me->_indentation_stack.memory_end != (QUEX_TYPE_INDENTATION*)0) return false;$$
    return true;
}


QUEX_INLINE void 
QUEX_NAME(Counter_print_this)(QUEX_NAME(Counter)* me)
{
    $$<indentation> QUEX_TYPE_INDENTATION* it = 0x0;$$

    QUEX_DEBUG_PRINT("  counter: ");
    if( QUEX_NAME(Counter_resources_absent)(me) ) {
        QUEX_DEBUG_PRINT("<unitialized>\n");
        return;
    }
    QUEX_DEBUG_PRINT("{\n");

$$<count-line>-----------------------------------------------------------------
    QUEX_DEBUG_PRINT1("    _line_number_at_begin:   %i;\n", (int)me->_line_number_at_begin);
    QUEX_DEBUG_PRINT1("    _line_number_at_end:     %i;\n", (int)me->_line_number_at_end);
$$-----------------------------------------------------------------------------
$$<count-column>---------------------------------------------------------------
    QUEX_DEBUG_PRINT1("    _column_number_at_begin: %i;\n", (int)me->_column_number_at_begin);
    QUEX_DEBUG_PRINT1("    _column_number_at_end:   %i;\n", (int)me->_column_number_at_end);
$$-----------------------------------------------------------------------------
$$<indentation>----------------------------------------------------------------
    QUEX_DEBUG_PRINT("    _indentation_stack: [");
    for(it  = me->_indentation_stack.front; 
           it != &me->_indentation_stack.back[1] 
        && it != &me->_indentation_stack.front[QUEX_SETTING_INDENTATION_STACK_SIZE]; 
        ++it) {
        QUEX_DEBUG_PRINT1("%i, ", (int)*it);
    }
    QUEX_DEBUG_PRINT("]\n");
$$-----------------------------------------------------------------------------
    QUEX_DEBUG_PRINT("  }\n");
}


$$<indentation>----------------------------------------------------------------
QUEX_INLINE void
QUEX_NAME(IndentationStack_init)(QUEX_NAME(IndentationStack)* me)
{
    *(me->front)   = 1;          /* first indentation at column = 1 */
    me->back       = me->front;
    me->memory_end = &me->front[QUEX_SETTING_INDENTATION_STACK_SIZE];
}
$$-----------------------------------------------------------------------------

#ifdef QUEX_OPTION_ASSERTS
QUEX_INLINE void
QUEX_NAME(Counter_assert_consistency)(QUEX_NAME(Counter)* me)
{
$$<count-line && count-column>-------------------------------------------------
    /* The line number can never decrease.                                   */ 
    __quex_assert(me->_line_number_at_begin <= me->_line_number_at_end);            
    /* Line number remained the same => column number *must* have increased. */ 
    /* There is not pattern of a length less than 1                          */ 
    if(me->_line_number_at_begin == me->_line_number_at_end ) {                     
        __quex_assert(me->_column_number_at_begin < me->_column_number_at_end);     
    }                                                                                   
$$-----------------------------------------------------------------------------
$$<count-line && not-count-column>---------------------------------------------
    __quex_assert(me->_line_number_at_begin   <= me->_line_number_at_end);         
$$-----------------------------------------------------------------------------
    /* If only column numbers are counted, then no assumptions can be made 
     * about increase or decrease. If a newline appears, for example, the 
     * column number may decrease.                                            */
}
#endif

QUEX_NAMESPACE_MAIN_CLOSE

#endif /* QUEX_INCLUDE_GUARD__ANALYZER__COUNTER_I */

