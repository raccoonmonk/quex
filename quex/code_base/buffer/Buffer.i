/* vim:set ft=c: -*- C++ -*- */
#ifndef QUEX_INCLUDE_GUARD__BUFFER__BUFFER_I
#define QUEX_INCLUDE_GUARD__BUFFER__BUFFER_I

$$INC: buffer/asserts$$
$$INC: definitions$$
$$INC: buffer/Buffer$$
$$INC: buffer/Buffer_print.i$$
$$INC: buffer/lexatoms/LexatomLoader$$
$$INC: quex/asserts$$
$$INC: quex/MemoryManager$$

QUEX_NAMESPACE_MAIN_OPEN

QUEX_INLINE void      QUEX_NAME(Buffer_init_content)(QUEX_NAME(Buffer)* me, 
                                                     QUEX_TYPE_LEXATOM* EndOfFileP);
QUEX_INLINE void      QUEX_NAME(Buffer_init_content_core)(QUEX_NAME(Buffer)*        me, 
                                                          QUEX_TYPE_STREAM_POSITION LI_Begin,
                                                          QUEX_TYPE_STREAM_POSITION LI_EndOfStream,
                                                          QUEX_TYPE_LEXATOM*        EndOfFileP);
QUEX_INLINE void      QUEX_NAME(Buffer_init_analyzis)(QUEX_NAME(Buffer)*   me);
QUEX_INLINE void      QUEX_NAME(Buffer_init_analyzis_core)(QUEX_NAME(Buffer)*        me,
                                                           QUEX_TYPE_LEXATOM*        ReadP,
                                                           QUEX_TYPE_LEXATOM*        LexatomStartP,
                                                           QUEX_TYPE_LEXATOM         LexatomAtLexemeStart,
                                                           QUEX_TYPE_LEXATOM         LexatomBeforeLexemeStart,
                                                           QUEX_TYPE_STREAM_POSITION BackupLexatomIndexOfReadP);

QUEX_INLINE void      QUEX_NAME(Buffer_on_overflow_DEFAULT)(void*              aux, 
                                                            QUEX_NAME(Buffer)* buffer, 
                                                            bool               ForwardF);
QUEX_INLINE void      QUEX_NAME(Buffer_on_before_buffer_change_DEFAULT)(void*  aux,
                                                                        const  QUEX_TYPE_LEXATOM*, 
                                                                        const  QUEX_TYPE_LEXATOM*);
QUEX_INLINE void      QUEX_NAME(Buffer_member_functions_assign)(QUEX_NAME(Buffer)* me);
#ifdef QUEX_OPTION_DEBUG_SHOW_EXT
QUEX_INLINE void      QUEX_NAME(Buffer_brief_trace_output)(const QUEX_NAME(Buffer)*  me,
                                                           QUEX_TYPE_LEXATOM**       position_register, 
                                                           const size_t              PositionRegisterN);
#endif

QUEX_INLINE void
QUEX_NAME(Buffer_construct)(QUEX_NAME(Buffer)*        me, 
                            QUEX_NAME(LexatomLoader)* filler,
                            QUEX_TYPE_LEXATOM*        memory,
                            const size_t              MemorySize,
                            QUEX_TYPE_LEXATOM*        EndOfFileP,
                            const ptrdiff_t           FallbackN,
                            E_Ownership               Ownership,
                            QUEX_NAME(Buffer)*        IncludingBuffer)
{
    __quex_assert(QUEX_SETTING_BUFFER_SIZE_MIN <= QUEX_SETTING_BUFFER_SIZE);

    /* Ownership of InputMemory is passed to 'me->_memory'.                  */
    QUEX_NAME(BufferMemory_construct)(&me->_memory, memory, MemorySize, 
                                      Ownership, IncludingBuffer); 
    
    me->filler = filler;
    QUEX_NAME(Buffer_member_functions_assign)(me);

    /* Event handlers.                                                       */
    QUEX_NAME(Buffer_callbacks_set)(me, (void (*)(void*))0, (void (*)(void*))0, (void*)0);

    /* Initialize.                                                           */
    QUEX_NAME(Buffer_init)(me, EndOfFileP);
    me->_fallback_n = FallbackN;

    QUEX_NAME(Buffer_assert_consistency)(me);
}

QUEX_INLINE void
QUEX_NAME(Buffer_member_functions_assign)(QUEX_NAME(Buffer)* me)
{
    me->fill                = QUEX_NAME(Buffer_fill);
    me->fill_prepare        = QUEX_NAME(Buffer_fill_prepare);
    me->fill_finish         = QUEX_NAME(Buffer_fill_finish);

    me->begin               = QUEX_NAME(Buffer_memory_begin);
    me->end                 = QUEX_NAME(Buffer_memory_end);
    me->size                = QUEX_NAME(Buffer_memory_size);

    me->content_space_end   = QUEX_NAME(Buffer_memory_content_space_end);
    me->content_space_size  = QUEX_NAME(Buffer_memory_content_space_size);

    me->content_begin       = QUEX_NAME(Buffer_memory_content_begin);
    me->content_end         = QUEX_NAME(Buffer_memory_content_end);
    me->content_size        = QUEX_NAME(Buffer_memory_content_size);

#   if defined(QUEX_OPTION_DEBUG_SHOW_EXT)
    me->brief_trace_output   = QUEX_NAME(Buffer_brief_trace_output);
#   endif
}

QUEX_INLINE QUEX_TYPE_LEXATOM*   QUEX_NAME(Buffer_memory_begin)(const QUEX_NAME(Buffer)* me) { return me->_memory._front; }
QUEX_INLINE QUEX_TYPE_LEXATOM*   QUEX_NAME(Buffer_memory_end)(const QUEX_NAME(Buffer)* me)   { return &me->_memory._back[1]; }
QUEX_INLINE ptrdiff_t            QUEX_NAME(Buffer_memory_size)(const QUEX_NAME(Buffer)* me)  { return &me->_memory._back[1] - me->_memory._front; }

QUEX_INLINE QUEX_TYPE_LEXATOM*   QUEX_NAME(Buffer_memory_content_space_end)(const QUEX_NAME(Buffer)* me)   { return me->_memory._back; }
QUEX_INLINE ptrdiff_t            QUEX_NAME(Buffer_memory_content_space_size)(const QUEX_NAME(Buffer)* me)  { return me->_memory._back - &me->_memory._front[1]; }

QUEX_INLINE QUEX_TYPE_LEXATOM*   QUEX_NAME(Buffer_memory_content_begin)(const QUEX_NAME(Buffer)* me) { return &me->_memory._front[1]; }
QUEX_INLINE QUEX_TYPE_LEXATOM*   QUEX_NAME(Buffer_memory_content_end)(const QUEX_NAME(Buffer)* me)   { return me->input.end_p; }
QUEX_INLINE ptrdiff_t            QUEX_NAME(Buffer_memory_content_size)(const QUEX_NAME(Buffer)* me)  { return me->input.end_p - &me->_memory._front[1]; }

QUEX_INLINE void
QUEX_NAME(Buffer_init)(QUEX_NAME(Buffer)* me, QUEX_TYPE_LEXATOM* EndOfFileP)
{
    QUEX_NAME(Buffer_init_content)(me, EndOfFileP);
    QUEX_NAME(Buffer_init_analyzis)(me); 
}

QUEX_INLINE void
QUEX_NAME(Buffer_destruct)(QUEX_NAME(Buffer)* me)
/* Destruct 'me' and mark all resources as absent.                            */
{
    if( QUEX_NAME(Buffer_resources_absent)(me) ) {
        return;
    }
    QUEX_NAME(Buffer_callbacks_on_buffer_before_change)(me);

    if( me->filler ) {
        me->filler->destruct(me->filler); 
        QUEX_GNAME_LIB(MemoryManager_free)((void*)me->filler, E_MemoryObjectType_BUFFER_FILLER);
    }
    QUEX_NAME(BufferMemory_destruct)(&me->_memory);
    QUEX_NAME(Buffer_resources_absent_mark)(me);
}

QUEX_INLINE void
QUEX_NAME(Buffer_shallow_copy)(QUEX_NAME(Buffer)* drain, const QUEX_NAME(Buffer)* source)
/*    ,.
 *   /  \   DANGER: Do not use this function, except that you totally 
 *  /    \                understand its implications!
 *  '----'
 * Copy indices and references *as is*. The purpose of this function is solely
 * to copy the setup of a buffer to a safe place and restore it. 
 *
 *           NOT TO BE USED AS A REPLACEMENT FOR COPYING/CLONING!
 *
 * At the time of this writing, the only propper application is when a backup 
 * is generated in a memento. When it is restored in the 'real' buffer object 
 * the pointers point to the right places and the ownership is handled propperly.
 *
 * The caller of this function MUST determine whether 'drain' or 'source'
 * maintains ownership.                                                       */
{
    QUEX_NAME(Buffer_assert_consistency)(source);
    *drain = *source;
}

QUEX_INLINE bool 
QUEX_NAME(Buffer_has_intersection)(QUEX_NAME(Buffer)*       me,
                                   const QUEX_TYPE_LEXATOM* Begin,
                                   ptrdiff_t                Size)
/* RETURNS: 'true' if buffer's memory intersects with the region given
 *                 by 'Begin' and 'Size'.
 *          'false', else.                                                    */
{
    const QUEX_TYPE_LEXATOM* End      = &Begin[Size];
    QUEX_NAME(Buffer)*       root     = QUEX_NAME(Buffer_nested_find_root)(me);
    const QUEX_TYPE_LEXATOM* my_begin = root->begin(root);
    const QUEX_TYPE_LEXATOM* my_end   = me->end(me);

    /* No intersection in two cases:
     * (1) second interval lies completely before: 'End <= my_begin'.
     * (2) second interval lies completely after:  'Begin >= my_begin'.       */
    if( Begin >= my_end || End <= my_begin ) return false;
    else                                     return true;
}

QUEX_INLINE void
QUEX_NAME(Buffer_resources_absent_mark)(QUEX_NAME(Buffer)* me)
/* This function is to be called in case that construction failed. It marks
 * all resources as absent, such that destruction can handle it safely. 
 * Nevertheless, the member functions are put in place to be be sure that the
 * object is functional.                                                      */
{
    QUEX_NAME(Buffer_member_functions_assign)(me);
    QUEX_NAME(Buffer_callbacks_set)(me, (void (*)(void*))0,
                                         (void (*)(void*))0, (void*)0);
    me->filler = (QUEX_NAME(LexatomLoader)*)0;
    QUEX_NAME(BufferMemory_resources_absent_mark)(&me->_memory);
    QUEX_NAME(Buffer_member_functions_assert)(me);
}

QUEX_INLINE bool    
QUEX_NAME(Buffer_resources_absent)(QUEX_NAME(Buffer)* me)
/* RETURNS: 'true' if all resources of buffer are absent. Then, nothing needs
 *                 to be freed.
 *          'false' else.                                                     */ 
{
    return    me->filler == (QUEX_NAME(LexatomLoader)*)0 
           && QUEX_NAME(BufferMemory_resources_absent)(&me->_memory);
}

QUEX_INLINE void     
QUEX_NAME(Buffer_dysfunctional_set)(QUEX_NAME(Buffer)*  me)
/* Set buffer into dysfunctional state, i.e. the buffer is inable to operarate.
 * Shall be applied only upon failure beyond repair.                          */
{
    QUEX_NAME(Buffer_init_analyzis_core)(me, 
    /* ReadP                          */ (QUEX_TYPE_LEXATOM*)0,
    /* LexatomStartP                  */ (QUEX_TYPE_LEXATOM*)0,
    /* LexatomAtLexemeStart           */ (QUEX_TYPE_LEXATOM)0,                                   
    /* LexatomBeforeLexemeStart       */ (QUEX_TYPE_LEXATOM)0,
    /* BackupLexatomIndexOfReadP      */ (QUEX_TYPE_STREAM_POSITION)-1);
    QUEX_NAME(Buffer_member_functions_assert)(me);
}

QUEX_INLINE bool     
QUEX_NAME(Buffer_dysfunctional)(QUEX_NAME(Buffer)*  me)
/* RETURNS: 'true' if buffer is in dysfunctional state.
 *          'false', else.                                                    */
{
    return    me->_read_p                         == (QUEX_TYPE_LEXATOM*)0
           && me->_lexeme_start_p                 == (QUEX_TYPE_LEXATOM*)0
           && me->_lexatom_at_lexeme_start        == (QUEX_TYPE_LEXATOM)0                                   
           && me->_backup_lexatom_index_of_lexeme_start_p == (QUEX_TYPE_STREAM_POSITION)-1
           $$<begin-of-line-context> && me->_lexatom_before_lexeme_start == (QUEX_TYPE_LEXATOM)0$$;
}

QUEX_INLINE void
QUEX_NAME(Buffer_init_analyzis)(QUEX_NAME(Buffer)*   me) 
/* Initialize:  _read_p                          
 *              _lexeme_start_p                 
 *              _lexatom_at_lexeme_start     
 *              _lexatom_before_lexeme_start                                  */
{
    if( ! me->_memory._front ) {
        /* No memory => FSM is put into a non-functional state.               */
        QUEX_NAME(Buffer_init_analyzis_core)(me, 
        /* ReadP                          */ (QUEX_TYPE_LEXATOM*)0,
        /* LexatomStartP                  */ (QUEX_TYPE_LEXATOM*)0,
        /* LexatomAtLexemeStart           */ (QUEX_TYPE_LEXATOM)0,                                   
        /* LexatomBeforeLexemeStart       */ (QUEX_TYPE_LEXATOM)0,
        /* BackupLexatomIndexOfReadP      */ (QUEX_TYPE_STREAM_POSITION)-1);
    }
    else {
        /* The first state in the state machine does not increment. 
         * => input pointer is set to the first position, not before.         */
        QUEX_NAME(Buffer_init_analyzis_core)(me, 
        /* ReadP                          */ me->content_begin(me),
        /* LexatomStartP                  */ me->content_begin(me),
        /* LexatomAtLexemeStart           */ (QUEX_TYPE_LEXATOM)0,
        /* LexatomBeforeLexemeStart       */ QUEX_SETTING_BUFFER_LEXATOM_NEWLINE,
        /* BackupLexatomIndexOfReadP      */ (QUEX_TYPE_STREAM_POSITION)-1);
    }
}

QUEX_INLINE void
QUEX_NAME(Buffer_init_analyzis_core)(QUEX_NAME(Buffer)*        me,
                                     QUEX_TYPE_LEXATOM*        ReadP,
                                     QUEX_TYPE_LEXATOM*        LexatomStartP,
                                     QUEX_TYPE_LEXATOM         LexatomAtLexemeStart,
                                     QUEX_TYPE_LEXATOM         LexatomBeforeLexemeStart,
                                     QUEX_TYPE_STREAM_POSITION BackupLexatomIndexOfReadP) 
{
    (void)LexatomBeforeLexemeStart;

    me->_read_p                  = ReadP;
    me->_lexeme_start_p          = LexatomStartP;
    me->_lexatom_at_lexeme_start = LexatomAtLexemeStart;                                   
    me->_fallback_n              = 0; /* To be set upon mode entry */
    $$<begin-of-line-context> me->_lexatom_before_lexeme_start    = LexatomBeforeLexemeStart;$$
    me->_backup_lexatom_index_of_lexeme_start_p = BackupLexatomIndexOfReadP;
}

QUEX_INLINE void
QUEX_NAME(Buffer_init_content)(QUEX_NAME(Buffer)* me, QUEX_TYPE_LEXATOM* EndOfFileP)
/*  Initialize: input.lexatom_index_begin
 *              input.lexatom_index_end_of_stream                         
 *              input.end_p                                                   */
{
    QUEX_TYPE_LEXATOM*        EndP             = me->content_space_end(me);
    QUEX_TYPE_STREAM_POSITION ci_begin         = (QUEX_TYPE_STREAM_POSITION)0;
    QUEX_TYPE_STREAM_POSITION ci_end_of_stream = (QUEX_TYPE_STREAM_POSITION)-1;
    QUEX_TYPE_LEXATOM*        end_p            = (QUEX_TYPE_LEXATOM*)0;
    (void)EndP;

    if( ! me->_memory._front ) {
        ci_end_of_stream = (QUEX_TYPE_STREAM_POSITION)-1;
        end_p            = (QUEX_TYPE_LEXATOM*)0;
        ci_begin         = (QUEX_TYPE_STREAM_POSITION)-1;
    }
    else if( me->filler && me->filler->byte_loader ) {
        __quex_assert(0 == EndOfFileP);

        /* Setup condition to initiate immediate load when the state machine
         * is entered: 'read pointer hits buffer limit code'.                */
        ci_begin         = (QUEX_TYPE_STREAM_POSITION)0;
        ci_end_of_stream = (QUEX_TYPE_STREAM_POSITION)-1;
        end_p            = me->content_begin(me);
    } 
    else {
        __quex_assert(0 != me->_memory._front);           /* See first condition. */
        __quex_assert(! EndOfFileP || (EndOfFileP >= me->content_begin(me) && EndOfFileP <= EndP));

        if( EndOfFileP ) {
            ci_end_of_stream = EndOfFileP - me->content_begin(me);
            end_p            = EndOfFileP;   
        }
        else {
            ci_end_of_stream = (QUEX_TYPE_STREAM_POSITION)-1;
            end_p            = me->content_begin(me);   
        }
    }

    QUEX_NAME(Buffer_init_content_core)(me, ci_begin, ci_end_of_stream, end_p);
}

QUEX_INLINE void
QUEX_NAME(Buffer_init_content_core)(QUEX_NAME(Buffer)* me, 
                                    QUEX_TYPE_STREAM_POSITION LI_Begin,
                                    QUEX_TYPE_STREAM_POSITION LI_EndOfStream,
                                    QUEX_TYPE_LEXATOM*        EndOfFileP)
{
    me->input.lexatom_index_begin         = LI_Begin;
    me->input.lexatom_index_end_of_stream = LI_EndOfStream;
    if( EndOfFileP ) {
        me->input.end_p    = EndOfFileP;
        me->input.end_p[0] = QUEX_SETTING_BUFFER_LEXATOM_BUFFER_BORDER;
        QUEX_IF_ASSERTS_poison(&me->content_end(me)[1], me->content_space_end(me));
    }
    else {
        me->input.end_p    = (QUEX_TYPE_LEXATOM*)0;
    }
}

QUEX_INLINE void
QUEX_NAME(Buffer_register_content)(QUEX_NAME(Buffer)*        me,
                                   QUEX_TYPE_LEXATOM*        EndOfInputP,
                                   QUEX_TYPE_STREAM_POSITION CharacterIndexBegin)
/* Registers information about the stream that fills the buffer and its
 * relation to the buffer. 
 *  
 *  EndOfInputP --> Position behind the last lexatom in the buffer that has
 *                  been streamed.
 *          '0' --> No change.
 *  
 *  CharacterIndexBegin --> Character index of the first lexatom in the 
 *                          buffer.
 *                 '-1' --> No change.                                       */
{
    if( EndOfInputP ) {
        __quex_assert(EndOfInputP <= me->content_space_end(me));
        __quex_assert(EndOfInputP >= me->content_begin(me));

        me->input.end_p    = EndOfInputP;
        me->input.end_p[0] = QUEX_SETTING_BUFFER_LEXATOM_BUFFER_BORDER;
    }

    if( CharacterIndexBegin != (QUEX_TYPE_STREAM_POSITION)-1 ) {
        me->input.lexatom_index_begin = CharacterIndexBegin;
    }

    QUEX_IF_ASSERTS_poison(&me->content_end(me)[1], me->content_space_end(me));
    /* NOT: assert(QUEX_NAME(Buffer_input_lexatom_index_begin)(me) >= 0);
     * This function may be called before content is setup/loaded propperly. */ 
}

QUEX_INLINE void       
QUEX_NAME(Buffer_register_eos)(QUEX_NAME(Buffer)*        me,
                               QUEX_TYPE_STREAM_POSITION CharacterIndexEndOfStream)
{
    me->input.lexatom_index_end_of_stream = CharacterIndexEndOfStream;
}

QUEX_INLINE bool
QUEX_NAME(Buffer_is_empty)(QUEX_NAME(Buffer)* me)
/* RETURNS: true, if buffer does not contain anything.
 *          false, else.                                                     */
{ 
    return    me->content_end(me) == me->content_begin(me) 
           && me->input.lexatom_index_begin == 0; 
}

QUEX_INLINE QUEX_TYPE_STREAM_POSITION  
QUEX_NAME(Buffer_input_lexatom_index_end)(QUEX_NAME(Buffer)* me)
/* RETURNS: Character index of the lexatom to which '.input.end_p' points.
 *                                                                           */
{
    __quex_assert(me->input.lexatom_index_begin >= 0);
    QUEX_NAME(Buffer_assert_pointers_in_range)(me);

    return me->input.lexatom_index_begin + me->content_size(me);
}

QUEX_INLINE bool 
QUEX_NAME(Buffer_is_end_of_stream_inside)(QUEX_NAME(Buffer)* me)
{ 
    const ptrdiff_t ContentSpaceSize = me->content_space_size(me);

    if( me->input.lexatom_index_end_of_stream == (QUEX_TYPE_STREAM_POSITION)-1 ) {
        return false;
    }
    else if( me->input.lexatom_index_end_of_stream < me->input.lexatom_index_begin ) {
        return false;
    }
    else {
        return me->input.lexatom_index_end_of_stream - me->input.lexatom_index_begin < ContentSpaceSize;
    }
}

QUEX_INLINE bool 
QUEX_NAME(Buffer_is_end_of_stream)(QUEX_NAME(Buffer)* me)
{ 
    QUEX_NAME(Buffer_assert_consistency)(me);
    if( me->input.lexatom_index_end_of_stream == (QUEX_TYPE_STREAM_POSITION)-1 ) {
        return false;
    }
    else if( me->_read_p != me->content_end(me) ) {
        return false;
    }

    return    QUEX_NAME(Buffer_input_lexatom_index_end)(me) 
           == me->input.lexatom_index_end_of_stream;
}

QUEX_INLINE bool                  
QUEX_NAME(Buffer_is_begin_of_stream)(QUEX_NAME(Buffer)* buffer)
{ 
    QUEX_NAME(Buffer_assert_consistency)(buffer);
    if     ( buffer->_lexeme_start_p != buffer->content_begin(buffer) ) return false;
    else if( QUEX_NAME(Buffer_input_lexatom_index_begin)(buffer) )      return false;
    else                                                                return true;
}

QUEX_INLINE void
QUEX_NAME(Buffer_pointers_add_offset)(QUEX_NAME(Buffer)*  me,
                                      ptrdiff_t           offset,
                                      QUEX_TYPE_LEXATOM** position_register,
                                      const size_t        PositionRegisterN)
/* Modify all buffer related pointers and lexatom indices by an offset. It is
 * assumed, that buffer content has been moved by 'offset' and that pointers
 * and offsets still related to the content before the move. 
 *
 * EXAMPLE: (lexatom index at buffer begin, read_p)
 *
 *                       0  1  2  3  4  5  6  7  8  9  10 11 12 13 14 15 
 * Stream:               [a][b][c][d][e][f][g][h][j][i][k][l][m][n][o][p]
 *
 * Buffer before move:           |[d][e][f][g][h]|
 *                                |        |
 *     lexatom_index_begin = 3 ---'        |
 *     read_p -----------------------------'
 *
 * Buffer after move, then ADD:  |[f][g][h][j][i]|
 *                                |   |
 *     lexatom_index_begin = 5 ---'   |
 *     read_p ------------------------'
 *
 * ADAPTS: _read_p, _lexeme_start_p, position registers, end_p, 
 *         input.end_lexatom_index                                            */
{ 
#   define QUEX_BUFFER_POINTER_ADD(P, BORDER, OFFSET)                \
           ((P) = (  ((P) == (QUEX_TYPE_LEXATOM*)0) ? (P)            \
                   : ((BORDER) - (P) < OFFSET)     ? (BORDER)        \
                   : (P) + (OFFSET)))
#   define QUEX_BUFFER_POINTER_SUBTRACT(P, BORDER, NEGATIVE_OFFSET)  \
           ((P) = (  ((P) == (QUEX_TYPE_LEXATOM*)0)     ? (P)        \
                   : ((BORDER) - (P) > NEGATIVE_OFFSET) ? (BORDER)   \
                   : (P) + (NEGATIVE_OFFSET)))
    QUEX_TYPE_LEXATOM*  border = (QUEX_TYPE_LEXATOM*)0;
    QUEX_TYPE_LEXATOM** pit    = (QUEX_TYPE_LEXATOM**)0x0;
    QUEX_TYPE_LEXATOM** pEnd   = &position_register[PositionRegisterN];

    QUEX_NAME(Buffer_assert_pointers_in_range)(me);

    if( offset > 0 ) {
        border = me->content_space_end(me);
        QUEX_BUFFER_POINTER_ADD(me->_read_p,         border, offset);
        QUEX_BUFFER_POINTER_ADD(me->_lexeme_start_p, border, offset);
        QUEX_BUFFER_POINTER_ADD(me->input.end_p,     border, offset);

        for(pit = position_register; pit != pEnd; ++pit) {
            QUEX_BUFFER_POINTER_ADD(*pit, border, offset); 
        }
    }
    else if( offset < 0 ) {
        border = me->content_begin(me);
        QUEX_BUFFER_POINTER_SUBTRACT(me->_read_p,         border, offset);
        QUEX_BUFFER_POINTER_SUBTRACT(me->_lexeme_start_p, border, offset);
        QUEX_BUFFER_POINTER_SUBTRACT(me->input.end_p,     border, offset);

        for(pit = position_register; pit != pEnd; ++pit) {
            QUEX_BUFFER_POINTER_SUBTRACT(*pit, border, offset); 
        }
    }
    else {
        return;
    }

    *(me->content_end(me)) = (QUEX_TYPE_LEXATOM)QUEX_SETTING_BUFFER_LEXATOM_BUFFER_BORDER;

    me->input.lexatom_index_begin -= offset;

    QUEX_NAME(Buffer_assert_pointers_in_range)(me);

#   undef QUEX_BUFFER_POINTER_ADD
#   undef QUEX_BUFFER_POINTER_SUBTRACT
}

QUEX_INLINE QUEX_TYPE_LEXATOM*
QUEX_NAME(Buffer_get_min_position_without_lexeme_start_p)(QUEX_NAME(Buffer)*  me, 
                                                          QUEX_TYPE_LEXATOM** position_register, 
                                                          const size_t        PositionRegisterN)
/* Determines the earliest position in the buffer that needs to be maintained
 * for acceptance position / post context recovery. That is,
 *
 *         IT IS ASSUMED THAT THE LEXEME DOES NOT HAVE TO BE MAINTAINED!
 *_____________________________________________________________________________
 * NOTE: POSSIBLY, THE EXACT POSITION OF ACCEPTANCES OS OPTIMIZED AWAY, SO    *
 *       THAT IT MAY NOT BE STORED. THIS FUNCTION IS NOT SAFE AGAINST THAT.   *
 *_____________________________________________________________________________
 *
 * If an input position is set, it must lie in between the lexeme start pointer
 * and the current input pointer. Only those are considered. The 'smallest' one
 * is then returned.
 *
 * This function is useful for reload procedures in cases where there is no
 * need for the lexatom itself. As a result more data may be loaded into the
 * buffer.
 *
 * RETURNS: Min position in buffer that needs to be maintained in order to 
 *          recover position of last acceptance or begining of post context.  */
{
    QUEX_TYPE_LEXATOM** pit              = (QUEX_TYPE_LEXATOM**)0x0;
    QUEX_TYPE_LEXATOM*  min_position     = (QUEX_TYPE_LEXATOM*)0x0;
    QUEX_TYPE_LEXATOM** Begin            = &position_register[0];
    QUEX_TYPE_LEXATOM** End              = &position_register[PositionRegisterN];
    QUEX_TYPE_LEXATOM*  relevant_begin_p = me->_lexeme_start_p ? me->_lexeme_start_p 
                                           : QUEX_NAME(Buffer_memory_content_begin)(me);
    QUEX_TYPE_LEXATOM*  relevant_end_p   = me->_read_p;
    QUEX_TYPE_LEXATOM*  p                = (QUEX_TYPE_LEXATOM*)0;

    QUEX_NAME(Buffer_assert_pointers_in_range)(me);

    for(pit = Begin; pit != End; ++pit) {
        p = *pit - 1;
        if( p < relevant_begin_p || p >= relevant_end_p ) continue;
        if( min_position > p ) min_position = p;
    }
    return min_position ? min_position : relevant_end_p;
}

#if defined(QUEX_OPTION_DEBUG_SHOW_EXT)
QUEX_INLINE void
QUEX_NAME(Buffer_brief_trace_output)(const QUEX_NAME(Buffer)*  me, 
                                     QUEX_TYPE_LEXATOM**       position_register, 
                                     const size_t              PositionRegisterN)
{
    /* lexatom_index --> position in the input stream
     * offset        --> offset from the buffer's first content lexatom       */
    const int buffer_lexatom_index_at_begin          = (int)(me->input.lexatom_index_begin);
    const int buffer_lexatom_index_at_end            = (int)(me->input.lexatom_index_begin + me->content_size(me));
    const int buffer_free_space_at_end_in_lexatoms   = (int)(me->content_space_size(me)    - me->content_size(me));
    const int lexeme_start_offset                    = (int)(me->_lexeme_start_p           - me->content_begin(me));
    const int lexeme_start_lexatom_index             = (int)(me->input.lexatom_index_begin + lexeme_start_offset);
    const int read_position_offset                   = (int)(me->_read_p                   - me->content_begin(me));
    const int read_position_lexatom_index            = (int)(me->input.lexatom_index_begin + read_position_offset);
    /* offset of 'end-of-stream' in buffer                                    */
    char      end_of_stream_offset[32];
    ptrdiff_t i, offset;

    if( me->input.lexatom_index_end_of_stream != -1 ) {
        __QUEX_STD_sprintf(end_of_stream_offset, "eos@%i", 
                           (int)(me->input.lexatom_index_end_of_stream - me->input.lexatom_index_begin));
    }
    else {
        __QUEX_STD_sprintf(end_of_stream_offset, "!eos");
    }

    __QUEX_STD_fprintf(QUEX_SETTING_DEBUG_OUTPUT_CHANNEL, 
                       "b[%i-%i|+%i]:%s:l%i@%i:r%i@%i", 
                       buffer_lexatom_index_at_begin,
                       buffer_lexatom_index_at_end,
                       buffer_free_space_at_end_in_lexatoms,
                       end_of_stream_offset,
                       lexeme_start_offset,
                       lexeme_start_lexatom_index,
                       read_position_offset,
                       read_position_lexatom_index);

    QUEX_DEBUG_PRINT(":"); 
    if( PositionRegisterN == 0 ) {
        QUEX_DEBUG_PRINT("-:"); 
    }
    else {
        for(i=0;i<(ptrdiff_t)PositionRegisterN;++i) { 
            if( ! position_register[i] ) {
                QUEX_DEBUG_PRINT("?:"); 
            }
            else {
                QUEX_DEBUG_PRINT(i == 0 ? "a" : "pc");
                offset = position_register[i] - me->content_begin(me); 
                __QUEX_STD_fprintf(QUEX_SETTING_DEBUG_OUTPUT_CHANNEL,
                                   "%i@%i:", 
                                   (int)(me->input.lexatom_index_begin + offset), (int)(offset));
            }
        }
    }
}
#endif

QUEX_NAMESPACE_MAIN_CLOSE

$$INC: buffer/lexatoms/LexatomLoader.i$$
$$INC: buffer/Buffer_print.i$$
$$INC: buffer/Buffer_navigation.i$$
$$INC: buffer/Buffer_fill.i$$
$$INC: buffer/Buffer_load.i$$
$$INC: buffer/Buffer_nested.i$$
$$INC: buffer/Buffer_callbacks.i$$
$$INC: buffer/Buffer_invariance.i$$
$$INC: buffer/Buffer_move.i$$
$$INC: buffer/BufferMemory.i$$

#endif /* QUEX_INCLUDE_GUARD__BUFFER__BUFFER_I */
