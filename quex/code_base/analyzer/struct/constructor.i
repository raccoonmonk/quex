/* -*- C++ -*- vim:set syntax=cpp:
 *
 * CONSTRUCTION: Setup a lexical analyzer.
 *
 *   -- Construction may fail, but it never throws an exception!
 *      Failure is notified by the '.error_code' flag.
 *   -- '.receive()' may always be called, but that function might return
 *      immediately if '.error_code' is not 'NONE'.
 *   -- The destructor can be called safely for any object that has been 
 *      'constructed'--even if the construction failed.
 *
 * FAILURE => Current lexer: all resources marked absent 
 *                           -> dysfunctional but destruct-able.
 *            Overtaken objects are destructed and freed!
 *
 *  .error_code == 'NONE': All resources have been allocated. Lexical 
 *                         analysis may start.
 *
 *  .error_code != 'NONE': Error during resource allocation.
 *                         Lexical analysis will immediately send 
 *                         'TERMINATION' token.
 *                         The lexer must (and can) be destructed.
 *
 * DESTRUCTION:
 *
 *   -- never fails, never throws exceptions.
 *
 * (C) 2005-2017 Frank-Rene Schaefer
 * ABSOLUTELY NO WARRANTY                                                     */
#ifndef  QUEX_INCLUDE_GUARD__ANALYZER__STRUCT__CONSTRUCTOR_I
#define  QUEX_INCLUDE_GUARD__ANALYZER__STRUCT__CONSTRUCTOR_I

$$INC: buffer/Buffer.i$$
$$INC: buffer/lexatoms/LexatomLoader.i$$
$$INC: analyzer/struct/include-stack$$

QUEX_NAMESPACE_MAIN_OPEN
                    
QUEX_INLINE void   QUEX_NAME(Asserts_user_memory)(QUEX_TYPE_ANALYZER*  me,
                                                  QUEX_TYPE_LEXATOM*   BufferMemoryBegin, 
                                                  size_t               BufferMemorySize,
                                                  QUEX_TYPE_LEXATOM*   BufferEndOfContentP /* = 0 */);
QUEX_INLINE void   QUEX_NAME(Asserts_construct)();

$$<std-lib>--------------------------------------------------------------------
QUEX_INLINE void
QUEX_NAME(from_file_name)(QUEX_TYPE_ANALYZER*         me,
                          const char*                 FileName, 
                          QUEX_GNAME_LIB(Converter)*  converter /* = 0 */)
{
    QUEX_GNAME_LIB(ByteLoader)*   new_byte_loader;

    QUEX_NAME(MF_error_code_clear)(me);

    new_byte_loader = QUEX_GNAME_LIB(ByteLoader_FILE_new_from_file_name)(FileName);

    if( ! new_byte_loader ) {
        QUEX_NAME(MF_error_code_set_if_first)(me, E_Error_File_OpenFailed);
        goto ERROR_2;
    }
    QUEX_NAME(from_ByteLoader)(me, new_byte_loader, converter); 

    if( me->error_code != E_Error_None ) {
        goto ERROR_1;
    }
    else if( ! QUEX_NAME(MF_input_name_set)(me, FileName) ) {
        QUEX_NAME(MF_error_code_set_if_first)(me, E_Error_InputName_Set_Failed);
        goto ERROR_0;
    }

    return;

    /* ERROR CASES: Free Resources ___________________________________________*/
ERROR_2:
    QUEX_GNAME_LIB(Converter_delete)(&converter);
    QUEX_NAME(MF_resources_absent_mark)(me);
ERROR_1:
    /* from_ByteLoader(): destructed and marked all resources absent.         */
    return;
ERROR_0:
    __quex_assert(me->__input_name == (char*)0); /* see constructor core      */
    QUEX_NAME(destruct)(me);
}
$$-----------------------------------------------------------------------------

/* USE: byte_loader = QUEX_GNAME_LIB(ByteLoader_FILE_new)(fh, BinaryModeF);
 *      byte_loader = QUEX_GNAME_LIB(ByteLoader_stream_new)(istream_p, BinaryModeF);
 *      byte_loader = QUEX_GNAME_LIB(ByteLoader_wstream_new)(wistream_p, BinaryModeF);
 *      ...
 *      Unit Test's StrangeStreams:
 *      byte_loader = QUEX_GNAME_LIB(ByteLoader_stream_new)(strangestr_p, false);  */

QUEX_INLINE void
QUEX_NAME(from_ByteLoader)(QUEX_TYPE_ANALYZER*          me,
                           QUEX_GNAME_LIB(ByteLoader)*  byte_loader,
                           QUEX_GNAME_LIB(Converter)*   converter /* = 0 */)
{
    QUEX_NAME(LexatomLoader)* new_filler;
    QUEX_TYPE_LEXATOM*        new_memory;

    QUEX_NAME(MF_error_code_clear)(me);

    /* NEW: Filler.                                                           */
    new_filler = QUEX_NAME(LexatomLoader_new)(byte_loader, converter);

    if( ! new_filler ) {
        QUEX_NAME(MF_error_code_set_if_first)(me, E_Error_Allocation_LexatomLoader_Failed);
        goto ERROR_0;
    }

    /* NEW: Memory.                                                           */
    new_memory = (QUEX_TYPE_LEXATOM*)QUEX_GNAME_LIB(MemoryManager_allocate)(
                       QUEX_SETTING_BUFFER_SIZE * sizeof(QUEX_TYPE_LEXATOM), 
                       E_MemoryObjectType_BUFFER_MEMORY);
    if( ! new_memory ) {
        QUEX_NAME(MF_error_code_set_if_first)(me, E_Error_Allocation_BufferMemory_Failed);
        goto ERROR_1;
    }

    QUEX_NAME(Buffer_construct)(&me->buffer, new_filler,
                                new_memory, QUEX_SETTING_BUFFER_SIZE, 
                                (QUEX_TYPE_LEXATOM*)0,
                                QUEX_SETTING_BUFFER_FALLBACK_N,
                                E_Ownership_LEXER,
                                (QUEX_NAME(Buffer)*)0);

    QUEX_NAME(construct_all_but_buffer)(me, true);
    if( me->error_code != E_Error_None ) {
        goto ERROR_2;
    }
    return;

    /* ERROR CASES: Free Resources __________________________________________*/
ERROR_2:
    QUEX_NAME(Buffer_destruct)(&me->buffer);
    QUEX_NAME(MF_resources_absent_mark)(me);
    return;
ERROR_1:
    if( new_filler ) {
        new_filler->destruct(new_filler); 
        QUEX_GNAME_LIB(MemoryManager_free)((void*)new_filler, E_MemoryObjectType_BUFFER_FILLER);
    }
    QUEX_NAME(MF_resources_absent_mark)(me);
    return;
ERROR_0:
    QUEX_GNAME_LIB(ByteLoader_delete)(&byte_loader);
    QUEX_GNAME_LIB(Converter_delete)(&converter);
    QUEX_NAME(MF_resources_absent_mark)(me);
    return;
}

QUEX_INLINE void
QUEX_NAME(from_memory)(QUEX_TYPE_ANALYZER* me,
                       QUEX_TYPE_LEXATOM*  Memory,
                       const size_t        MemorySize,
                       QUEX_TYPE_LEXATOM*  EndOfFileP)

/* When memory is provided from extern, the 'external entity' is responsible
 * for filling it. There is no 'file/stream handle', no 'ByteLoader', and no
 * 'LexatomLoader'.                                                           */
{
    QUEX_NAME(MF_error_code_clear)(me);

    if( ! QUEX_NAME(BufferMemory_check_chunk)(Memory, MemorySize, EndOfFileP) ) {
        QUEX_NAME(MF_error_code_set_if_first)(me, E_Error_ProvidedExternal_Memory_Corrupt);
        goto ERROR_0;
    }

    QUEX_NAME(Buffer_construct)(&me->buffer, 
                                (QUEX_NAME(LexatomLoader)*)0,
                                Memory, MemorySize, EndOfFileP,
                                QUEX_SETTING_BUFFER_FALLBACK_N,
                                E_Ownership_EXTERNAL,
                                (QUEX_NAME(Buffer)*)0);

    if( ! QUEX_NAME(construct_all_but_buffer)(me, true) ) {
        goto ERROR_1;
    }
    return;

    /* ERROR CASES: Free Resources ___________________________________________*/
ERROR_1:
    QUEX_NAME(Buffer_destruct)(&me->buffer); 
ERROR_0:
    QUEX_NAME(MF_resources_absent_mark)(me);
}

QUEX_INLINE bool
QUEX_NAME(construct_all_but_buffer)(QUEX_TYPE_ANALYZER* me, 
                                    bool                CallUserConstructorF)
/* Constructs anything but 'LexatomLoader' and 'Buffer'.
 * 
 * RETURNS: true, for success.
 *          false, for failure.                                               */
{
    QUEX_NAME(Asserts_construct)();

    $$<C> QUEX_NAME(member_functions_assign)(me);$$

    me->__input_name = (char*)0;
    me->_parent_memento = (QUEX_TYPE_MEMENTO*)0;

    if( ! QUEX_NAME(TokenQueue_construct)(&me->_token_queue, me,
                                          QUEX_SETTING_TOKEN_QUEUE_SIZE) ) {
        goto ERROR_0;
    }
    else if( ! QUEX_NAME(ModeStack_construct)(&me->_mode_stack, 
                                              QUEX_SETTING_MODE_STACK_SIZE) ) {
        goto ERROR_1;
    }
    $$<count>----------------------------------------------------------------------
    else if( ! QUEX_NAME(Counter_construct)(&me->counter) ) {
        QUEX_NAME(MF_error_code_set_if_first)(me, E_Error_Constructor_Counter_Failed);
        goto ERROR_2;
    }
    $$-----------------------------------------------------------------------------

    /* A user's mode change callbacks may be called as a consequence of the 
     * call to 'set_mode_brutally_by_id()'. The current mode must be set to '0'
     * so that the user may detect whether this is the first mode transition.*/
    me->__current_mode_p = (QUEX_NAME(Mode)*)0;
    QUEX_NAME(MF_set_mode_brutally)(me, QUEX_SETTING_MODE_INITIAL_P);

    if( CallUserConstructorF && ! QUEX_NAME(user_constructor)(me) ) {
        QUEX_NAME(MF_error_code_set_if_first)(me, E_Error_UserConstructor_Failed);
        goto ERROR_3;
    }

    QUEX_NAME(MF_error_code_clear)(me);
    return true;

    /* ERROR CASES: Free Resources ___________________________________________*/
ERROR_3:
    /* NO ALLOCATED RESOURCES IN: 'me->counter'                               */
$$<count>----------------------------------------------------------------------
ERROR_2:
$$-----------------------------------------------------------------------------
    QUEX_NAME(ModeStack_destruct)(&me->_mode_stack);
ERROR_1:
    QUEX_NAME(TokenQueue_destruct)(&me->_token_queue);
ERROR_0:
    QUEX_NAME(all_but_buffer_resources_absent_mark)(me);
    return false;
}

QUEX_INLINE void
QUEX_NAME(destruct)(QUEX_TYPE_ANALYZER* me)
{
    QUEX_NAME(destruct_all_but_buffer)(me);

    QUEX_NAME(Buffer_destruct)(&me->buffer);

    QUEX_NAME(user_destructor)(me);

    /* Protect against double destruction.                                    */
    QUEX_NAME(MF_resources_absent_mark)(me);
}

QUEX_INLINE void
QUEX_NAME(destruct_all_but_buffer)(QUEX_TYPE_ANALYZER* me)
{
    QUEX_NAME(MF_include_stack_delete)(me);
    /*
     *              DESTRUCT ANYTHING ONLY AFTER INCLUDE STACK                
     *
     * During destruction the all previously pushed analyzer states are 
     * popped and destructed, until only the outest state remains. This
     * is then the state that is destructed here.                             */
    QUEX_NAME(TokenQueue_destruct)(&me->_token_queue);
    QUEX_NAME(ModeStack_destruct)(&me->_mode_stack);

    if( me->__input_name ) {
        QUEX_GNAME_LIB(MemoryManager_free)(me->__input_name, E_MemoryObjectType_BUFFER_MEMORY);
    }

    QUEX_NAME(all_but_buffer_resources_absent_mark)(me);
}

QUEX_INLINE void
QUEX_NAME(MF_resources_absent_mark)(QUEX_TYPE_ANALYZER* me)
/* Resouces = 'absent' => Destructor knows that it must not be freed. 
 * 
 * This function is essential to set the lexical analyzer into a state
 * where it is safe to be destructed, even if some resources were missing.    
 *
 * IMPORTANT: The '.error_code' remains intact!
 *______________________________________________________________________________
 * WARNING: This function is NOT to be called, if not all resources are 
 *          disattached (destructed/freed) from the lexical analyzer. 
 *          Otherwise: unreferenced trailing objects; memory leaks.
 *____________________________________________________________________________*/
{
    /* NOTE: 'memset()' would destroy the v-table in case that the analyzer 
     *       is a c++ class object.                                           */
    QUEX_NAME(TokenQueue_resources_absent_mark)(&me->_token_queue);

    $$<C> QUEX_NAME(member_functions_assign)(me);$$

    $$<count> QUEX_NAME(Counter_resources_absent_mark)(&me->counter);$$

    QUEX_NAME(Buffer_resources_absent_mark)(&me->buffer);

    me->current_analyzer_function = (QUEX_NAME(AnalyzerFunctionP))0;
    me->__current_mode_p          = (QUEX_NAME(Mode)*)0; 

    QUEX_NAME(ModeStack_resources_absent_mark)(&me->_mode_stack);
    me->_parent_memento = (QUEX_TYPE_MEMENTO*)0;
    me->__input_name = (char*)0;
}

QUEX_INLINE void
QUEX_NAME(all_but_buffer_resources_absent_mark)(QUEX_TYPE_ANALYZER* me)
{
    uint8_t backup[sizeof(QUEX_NAME(Buffer))];

    /* Plain copy suffices (backup holds pointers safely).                    */
    QUEX_GSTD(memcpy)((void*)&backup[0], (void*)&me->buffer, sizeof(QUEX_NAME(Buffer)));

    QUEX_NAME(MF_resources_absent_mark)(me);

    /* Plain copy suffices (backup resets pointers safely).                   */
    QUEX_GSTD(memcpy)((void*)&me->buffer, (void*)&backup[0], sizeof(QUEX_NAME(Buffer)));
}

QUEX_INLINE bool
QUEX_NAME(MF_resources_absent)(QUEX_TYPE_ANALYZER* me)
/* RETURNS: 'true' if all resources are marked absent.
 *          'false' if at least one is not marked absent.                     */
{
    if( ! QUEX_NAME(TokenQueue_resources_absent)(&me->_token_queue) ) {
        return false;
    }
    else if( me->_parent_memento != (QUEX_TYPE_MEMENTO*)0 ) {
        return false;
    }
    else if( ! QUEX_NAME(Buffer_resources_absent)(&me->buffer) ) {
        return false;
    }
    else if( ! QUEX_NAME(ModeStack_resources_absent)(&me->_mode_stack) ) {
        return false;
    }
    else if(    me->current_analyzer_function != (QUEX_NAME(AnalyzerFunctionP))0
             || me->__current_mode_p          != (QUEX_NAME(Mode)*)0
             || me->__input_name              != (char*)0 ) {
        return false;
    }
    else {
        return true;
    }
}


QUEX_INLINE void
QUEX_NAME(Asserts_user_memory)(QUEX_TYPE_ANALYZER* me,
                               QUEX_TYPE_LEXATOM*  BufferMemoryBegin, 
                               size_t              BufferMemorySize,
                               QUEX_TYPE_LEXATOM*  BufferEndOfContentP /* = 0 */)
{
#   ifdef QUEX_OPTION_ASSERTS
    size_t               memory_size = BufferMemoryBegin ? BufferMemorySize 
                                       :                   QUEX_SETTING_BUFFER_SIZE;
    QUEX_TYPE_LEXATOM*   iterator = 0x0;

    __quex_assert(memory_size == 0 || memory_size > 2);
    if( BufferMemoryBegin ) {
        /* End of File must be inside the buffer, because we assume that the 
         * buffer contains all that is required.                              */
        if(    BufferEndOfContentP < BufferMemoryBegin 
            || BufferEndOfContentP > (BufferMemoryBegin + BufferMemorySize - 1)) {
            QUEX_ERROR_EXIT("\nConstructor: Argument 'BufferEndOfContentP' must be inside the provided memory\n"
                            "Constructor: buffer (speficied by 'BufferMemoryBegin' and 'BufferMemorySize').\n"
                            "Constructor: Note, that the last element of the buffer is to be filled with\n"
                            "Constructor: the buffer limit code character.\n");
        }
    }
    if( BufferEndOfContentP ) {
        __quex_assert(BufferEndOfContentP >  BufferMemoryBegin);
        __quex_assert(BufferEndOfContentP <= BufferMemoryBegin + memory_size - 1);

        /* The memory provided must be initialized. If it is not, then that's wrong.
         * Try to detect me by searching for BLC and PTC.                         */
        for(iterator = BufferMemoryBegin + 1; iterator != BufferEndOfContentP; ++iterator) {
            if(    *iterator == QUEX_SETTING_BUFFER_LEXATOM_BUFFER_BORDER 
                || *iterator == QUEX_SETTING_BUFFER_LEXATOM_PATH_TERMINATION ) {
                QUEX_ERROR_EXIT("\nConstructor: Buffer limit code and/or path termination code appeared in buffer\n"
                                "Constructor: when pointed to user memory. Note, that the memory pointed to must\n"
                                "Constructor: be initialized! You might redefine QUEX_SETTING_BUFFER_LEXATOM_PATH_TERMINATION\n"
                                "Constructor: and/or QUEX_SETTING_BUFFER_LEXATOM_PATH_TERMINATION; or use command line arguments\n"
                                "Constructor: '--buffer-limit' and '--path-termination'.");
            }
        }
    }
#   endif

    /* NOT: before ifdef, otherwise c90 issue: mixed declarations and code   */
    (void)me; (void)BufferMemoryBegin; (void)BufferMemorySize; (void)BufferEndOfContentP;
}

/* AUXILIARY FUNCTIONS FOR CONSTRUCTION _______________________________________                                     
 *                                                                           */

QUEX_INLINE void
QUEX_NAME(Asserts_construct)()
{
$$<not-std-lib>----------------------------------------------------------------
    /* If one of the following fails or causes compilation errors, 
     * then define '-DQUEXLIB_type=replacement'. For example,
     *
     *             -DQUEXLIB_uint32_t='unsigned long' 
     * 
     * defines 'unsigned long' as uint32_t'.                                 */
    char dummy0, dummy1;
    ptrdiff_t p = &dummy0 - &dummy1; /* ptrdiff_t must hold a pointer diff   */
    size_t    q = sizeof(p);         /* size_t must hold result of 'sizeof'  */
    (void)p; (void)q; (void)dummy0; (void)dummy1;
    __quex_assert(sizeof(uint8_t) == 1);
    __quex_assert(sizeof(int8_t) == 1);
    __quex_assert(sizeof(uint16_t) == 2);
    __quex_assert(sizeof(int16_t) == 2);
    __quex_assert(sizeof(uint32_t) == 4);
    __quex_assert(sizeof(int32_t) == 4);
    __quex_assert(sizeof(uint64_t) == 8);
    __quex_assert(sizeof(int64_t) == 8);
$$-----------------------------------------------------------------------------
#   if      defined(QUEX_OPTION_ASSERTS) \
       && ! defined(QUEX_OPTION_ASSERTS_WARNING_MESSAGE_DISABLED_EXT)
    QUEX_DEBUG_PRINT(__QUEX_MESSAGE_ASSERTS_INFO);
#   endif

#   if defined(QUEX_OPTION_ASSERTS) 
    if( QUEX_SETTING_BUFFER_LEXATOM_BUFFER_BORDER == QUEX_SETTING_BUFFER_LEXATOM_PATH_TERMINATION ) {
        QUEX_ERROR_EXIT("Path termination code (PTC) and buffer limit code (BLC) must be different.\n");
    }
#   endif
}

QUEX_INLINE void
QUEX_NAME(MF_collect_user_memory)(QUEX_TYPE_ANALYZER* me, 
                                  QUEX_TYPE_LEXATOM** user_buffer_memory)
{
    *user_buffer_memory = me->buffer._memory.ownership == E_Ownership_LEXER ?
                            (QUEX_TYPE_LEXATOM*)0 
                          : me->buffer.begin(&me->buffer);
}

QUEX_NAMESPACE_MAIN_CLOSE

#endif /*  QUEX_INCLUDE_GUARD__ANALYZER__STRUCT__CONSTRUCTOR_I */
