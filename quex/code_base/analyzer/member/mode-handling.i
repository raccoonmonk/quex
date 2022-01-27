/* -*- C++ -*- vim:set syntax=cpp:
 * (C) Frankt-Rene Schaefer
 * ABSOLUTELY NO WARRANTY               */
#ifndef QUEX_INCLUDE_GUARD__ANALYZER__MEMBER__MODE_HANDLING_I
#define QUEX_INCLUDE_GUARD__ANALYZER__MEMBER__MODE_HANDLING_I

$$INC: definitions$$
$$INC: analyzer/Mode$$

QUEX_NAMESPACE_MAIN_OPEN

QUEX_INLINE const QUEX_NAME(Mode)*
QUEX_NAME(MF_mode)(QUEX_TYPE_ANALYZER* me) 
{ return me->__current_mode_p; }

QUEX_INLINE void 
QUEX_NAME(MF_set_mode_brutally)(QUEX_TYPE_ANALYZER* me, const QUEX_NAME(Mode)* ModeP) 
/* Core of all mode setting functions. 
 *
 * ADAPTS: -- current mode pointer.
 *         -- current analyzer function pointer
 *         -- setting the buffer's handlers for 'on_buffer_overflow' and 
 *            'on_buffer_before_change'                                   */
{ 
    __quex_debug_show_mode_transition(me, ModeP);

    me->__current_mode_p          = ModeP;
    me->current_analyzer_function = ModeP->analyzer_function; 

    QUEX_NAME(Buffer_callbacks_set)(&me->buffer, 
                                    me->__current_mode_p->buffer_callbacks.on_buffer_before_change,
                                    me->__current_mode_p->buffer_callbacks.on_buffer_overflow,
                                    (void*)me);
}

QUEX_INLINE void    
QUEX_NAME(MF_enter_mode)(QUEX_TYPE_ANALYZER* me, const QUEX_NAME(Mode)* TargetMode) 
{
$$<mode-on-entry-handler>------------------------------------------------------
    const QUEX_NAME(Mode)* SourceMode = me->__current_mode_p;
$$-----------------------------------------------------------------------------

$$<mode-on-exit-handler>-------------------------------------------------------
    me->__current_mode_p->on_exit(me, TargetMode);
$$-----------------------------------------------------------------------------

#   ifdef QUEX_OPTION_ASSERTS
    if( ! me->__current_mode_p->has_exit_to(TargetMode) ) {
        QUEX_DEBUG_PRINT2("Mode '%s' has no exit to '%s'.\n", 
                          me->__current_mode_p->name,
                          TargetMode->name);
        QUEX_NAME(MF_error_code_set_if_first)(me, E_Error_ModeInadmissibleTransition);
    }
    if( ! TargetMode->has_entry_from(me->__current_mode_p) ) {
        QUEX_DEBUG_PRINT2("Mode '%s' has no entry from '%s'.\n", 
                          TargetMode->name,
                          me->__current_mode_p->name);
        QUEX_NAME(MF_error_code_set_if_first)(me, E_Error_ModeInadmissibleTransition);
    }
#   endif

    QUEX_NAME(MF_set_mode_brutally)(me, TargetMode);

$$<mode-on-entry-handler>------------------------------------------------------
    TargetMode->on_entry(me, SourceMode);         
$$-----------------------------------------------------------------------------
}

QUEX_INLINE void 
QUEX_NAME(MF_pop_mode)(QUEX_TYPE_ANALYZER* me) 
{ 
    if( me->_mode_stack.end == me->_mode_stack.begin ) {
        QUEX_NAME(MF_error_code_set_if_first)(me, E_Error_ModeStack_PopOnTopLevel);
    }
    else {
        --(me->_mode_stack.end);
        QUEX_NAME(MF_enter_mode)(me, *me->_mode_stack.end); 
    }
}

QUEX_INLINE void
QUEX_NAME(MF_pop_drop_mode)(QUEX_TYPE_ANALYZER* me) 
{ 
    if( me->_mode_stack.end == me->_mode_stack.begin ) {
        QUEX_NAME(MF_error_code_set_if_first)(me, E_Error_ModeStack_PopOnTopLevel);
    }
    else {
        --(me->_mode_stack.end);
    }
}
    
QUEX_INLINE void       
QUEX_NAME(MF_push_mode)(QUEX_TYPE_ANALYZER* me, QUEX_NAME(Mode)* new_mode) 
{ 
    if( me->_mode_stack.end == me->_mode_stack.memory_end ) {
        QUEX_NAME(MF_error_code_set_if_first)(me, E_Error_ModeStack_Overflow);
    }
    else {
        *me->_mode_stack.end = me->__current_mode_p;
        ++(me->_mode_stack.end);
        QUEX_NAME(MF_enter_mode)(me, new_mode); 
    }
}

QUEX_NAMESPACE_MAIN_CLOSE

#endif /* QUEX_INCLUDE_GUARD__ANALYZER__MEMBER__MODE_HANDLING_I */
