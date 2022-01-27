/* -*- C++ -*- vim: set syntax=cpp: */
#ifndef  QUEX_INCLUDE_GUARD__BUFFER__LEXATOMS__LEXATOM_LOADER_I
#define  QUEX_INCLUDE_GUARD__BUFFER__LEXATOMS__LEXATOM_LOADER_I

$$INC: definitions$$
$$INC: buffer/Buffer$$
$$INC: buffer/lexatoms/LexatomLoader$$
$$INC: buffer/Buffer_print$$
$$INC: quex/MemoryManager$$

QUEX_NAMESPACE_MAIN_OPEN

QUEX_INLINE bool       QUEX_NAME(LexatomLoader_lexatom_index_seek)(QUEX_NAME(LexatomLoader)*         me, 
                                                                   const QUEX_TYPE_STREAM_POSITION  LexatomIndex);
QUEX_INLINE ptrdiff_t  QUEX_NAME(LexatomLoader_load)(QUEX_NAME(LexatomLoader)*  me, 
                                                     QUEX_TYPE_LEXATOM*         RegionBeginP, 
                                                     const ptrdiff_t            Size,
                                                     QUEX_TYPE_STREAM_POSITION  CharacterIndexBegin,
                                                     bool*                      end_of_stream_f,
                                                     bool*                      encoding_error_f);
QUEX_INLINE bool       QUEX_NAME(LexatomLoader_lexatom_index_step_to)(QUEX_NAME(LexatomLoader)*        me,
                                                                      const QUEX_TYPE_STREAM_POSITION TargetCI);
QUEX_INLINE void       QUEX_NAME(LexatomLoader_reverse_byte_order)(QUEX_TYPE_LEXATOM*       Begin, 
                                                                  const QUEX_TYPE_LEXATOM* End);
QUEX_INLINE void       QUEX_NAME(LexatomLoader_destruct)(QUEX_NAME(LexatomLoader)*); 
QUEX_INLINE bool       QUEX_NAME(LexatomLoader_ByteLoader_Converter_consistency)(QUEX_GNAME_LIB(ByteLoader)*  byte_loader, 
                                                                                 QUEX_GNAME_LIB(Converter)*   converter);


                       
QUEX_INLINE QUEX_NAME(LexatomLoader)*
QUEX_NAME(LexatomLoader_new)(QUEX_GNAME_LIB(ByteLoader)*  byte_loader, 
                             QUEX_GNAME_LIB(Converter)*   converter)
{
    QUEX_NAME(LexatomLoader)* filler;

    /* byte_loader = 0; possible if memory is filled manually.               */
    if( converter ) {
        if( ! QUEX_NAME(LexatomLoader_ByteLoader_Converter_consistency)(byte_loader, converter) ) {
            return (QUEX_NAME(LexatomLoader)*)0;
        }
        filler = QUEX_NAME(LexatomLoader_Converter_new)(byte_loader, converter);
    }
    else {
        filler = QUEX_NAME(LexatomLoader_Plain_new)(byte_loader); 
    }
    
    return filler;
}

QUEX_INLINE bool
QUEX_NAME(LexatomLoader_ByteLoader_Converter_consistency)(QUEX_GNAME_LIB(ByteLoader)*  byte_loader, 
                                                          QUEX_GNAME_LIB(Converter)*   converter)
{
    if( ! byte_loader ) {
        return true;
    }
    else if( converter->input_code_unit_size == (size_t)-1 ) {
        return true;
    }
    else if( converter->input_code_unit_size >= (size_t)byte_loader->chunk_size_in_bytes ) {
        return true;
    }
    else {
        QUEX_DEBUG_PRINT1("Error: The specified byte loader provides elements of size %i.\n", 
                          (int)byte_loader->chunk_size_in_bytes);
        QUEX_DEBUG_PRINT1("Error: The converter requires input elements of size <= %i.\n", 
                          (int)converter->input_code_unit_size);
        QUEX_DEBUG_PRINT("Error: This happens, for example, when using 'wistream' input\n"
                         "Error: without considering 'sizeof(wchar_t)' with respect to\n"
                         "Error: the encodings code unit's size. (UTF8=1byte, UTF16=2byte, etc.)\n");
        return false;
    }
}

QUEX_INLINE void       
QUEX_NAME(LexatomLoader_destruct)(QUEX_NAME(LexatomLoader)* me)
{ 
    if( ! me ) return;

    if( me->byte_loader ) {
        QUEX_GNAME_LIB(ByteLoader_delete)(&me->byte_loader);
    }

    /* destruct_self: Free resources occupied by 'me' BUT NOT 'myself'.
     * delete_self:   Free resources occupied by 'me' AND 'myself'.           */
    if( me->derived.destruct ) {
        me->derived.destruct(me);
    }
}

QUEX_INLINE void    
QUEX_NAME(LexatomLoader_setup)(QUEX_NAME(LexatomLoader)*   me,
                               size_t       (*derived_load_lexatoms)(QUEX_NAME(LexatomLoader)*,
                                                                     QUEX_TYPE_LEXATOM*, 
                                                                     const size_t, 
                                                                     bool*, bool*),
                               ptrdiff_t    (*stomach_byte_n)(QUEX_NAME(LexatomLoader)*),
                               void         (*stomach_clear)(QUEX_NAME(LexatomLoader)*),
                               void         (*derived_destruct)(QUEX_NAME(LexatomLoader)*),
                               void         (*derived_fill_prepare)(QUEX_NAME(LexatomLoader)*  me,
                                                                    QUEX_NAME(Buffer)*         buffer,
                                                                    void**                     begin_p,
                                                                    const void**               end_p),
                               ptrdiff_t    (*derived_fill_finish)(QUEX_NAME(LexatomLoader)* me,
                                                                   QUEX_TYPE_LEXATOM*        BeginP,
                                                                   const QUEX_TYPE_LEXATOM*  EndP,
                                                                   const void*               FilledEndP),
                               void         (*derived_get_fill_boundaries)(QUEX_NAME(LexatomLoader)*  alter_ego,
                                                                           QUEX_NAME(Buffer)*         buffer,
                                                                           void**                     begin_p, 
                                                                           const void**               end_p),
                               void         (*derived_print_this)(QUEX_NAME(LexatomLoader)*  alter_ego),
                               QUEX_GNAME_LIB(ByteLoader)*  byte_loader,
                               ptrdiff_t    ByteNPerCharacter)
{
    __quex_assert(0 != me);
    __quex_assert(0 != derived_load_lexatoms);
    __quex_assert(0 != derived_destruct);

    /* Support for buffer filling without user interaction                   */
    me->stomach_byte_n        = stomach_byte_n;
    me->stomach_clear         = stomach_clear;
    me->load                  = QUEX_NAME(LexatomLoader_load);
    me->derived.load_lexatoms = derived_load_lexatoms;
    me->derived.destruct      = derived_destruct;
    me->derived.print_this    = derived_print_this;
    me->destruct              = QUEX_NAME(LexatomLoader_destruct);

    /* Support for manual buffer filling.                                    */
    me->derived.fill_prepare        = derived_fill_prepare;
    me->derived.fill_finish         = derived_fill_finish;
    me->derived.get_fill_boundaries = derived_get_fill_boundaries;

    me->byte_loader                 = byte_loader;

    me->_byte_order_reversion_active_f = false;
    me->lexatom_index_next_to_fill   = 0;
    me->byte_n_per_lexatom           = ByteNPerCharacter;
}

QUEX_INLINE ptrdiff_t       
QUEX_NAME(LexatomLoader_load)(QUEX_NAME(LexatomLoader)*  me, 
                              QUEX_TYPE_LEXATOM*         LoadP, 
                              const ptrdiff_t            LoadN,
                              QUEX_TYPE_STREAM_POSITION  StartLexatomIndex,
                              bool*                      end_of_stream_f,
                              bool*                      encoding_error_f)
/* Seeks the input position StartLexatomIndex and loads 'LoadN' 
 * lexatoms into the engine's buffer starting from 'LoadP'.
 *
 * RETURNS: Number of loaded lexatoms.                                       */
{
    ptrdiff_t                loaded_n;

    /* (1) Seek to the position where loading shall start.                       
     *                                                                       */
    if( ! QUEX_NAME(LexatomLoader_lexatom_index_seek)(me, StartLexatomIndex) ) {
        return 0;
    }
    __quex_assert(me->lexatom_index_next_to_fill == StartLexatomIndex);

    /* (2) Load content into the given region.                                   
     *                                                                       */
    loaded_n = (ptrdiff_t)me->derived.load_lexatoms(me, LoadP, (size_t)LoadN,
                                                    end_of_stream_f, encoding_error_f);
#   ifdef QUEX_OPTION_ASSERTS
    {
        const QUEX_TYPE_LEXATOM* p;
        /* The buffer limit code is not to appear inside the loaded content. */
        for(p=LoadP; p != &LoadP[loaded_n]; ++p) {
            __quex_assert(*p != QUEX_SETTING_BUFFER_LEXATOM_BUFFER_BORDER);
        }
    }
#   endif

    __quex_assert(loaded_n <= LoadN);
    me->lexatom_index_next_to_fill += loaded_n;

    /* (3) Optionally reverse the byte order.                                    
     *                                                                       */
    if( me->_byte_order_reversion_active_f ) {
        QUEX_NAME(LexatomLoader_reverse_byte_order)(LoadP, &LoadP[loaded_n]);
    }

    return loaded_n;
}

QUEX_INLINE void
QUEX_NAME(LexatomLoader_reverse_byte_order)(QUEX_TYPE_LEXATOM*       Begin, 
                                           const QUEX_TYPE_LEXATOM* End)
{
    uint8_t              tmp = 0xFF;
    QUEX_TYPE_LEXATOM* iterator = 0x0;

    switch( sizeof(QUEX_TYPE_LEXATOM) ) {
    default:
        __quex_assert(false);
        break;
    case 1:
        /* Nothing to be done */
        break;
    case 2:
        for(iterator=Begin; iterator != End; ++iterator) {
            tmp = *(((uint8_t*)iterator) + 0);
            *(((uint8_t*)iterator) + 0) = *(((uint8_t*)iterator) + 1);
            *(((uint8_t*)iterator) + 1) = tmp;
        }
        break;
    case 4:
        for(iterator=Begin; iterator != End; ++iterator) {
            tmp = *(((uint8_t*)iterator) + 0);
            *(((uint8_t*)iterator) + 0) = *(((uint8_t*)iterator) + 3);
            *(((uint8_t*)iterator) + 3) = tmp;
            tmp = *(((uint8_t*)iterator) + 1);
            *(((uint8_t*)iterator) + 1) = *(((uint8_t*)iterator) + 2);
            *(((uint8_t*)iterator) + 2) = tmp;
        }
        break;
    }
}

QUEX_INLINE void       
QUEX_NAME(LexatomLoader_print_this)(QUEX_NAME(LexatomLoader)* me)
{
    QUEX_DEBUG_PRINT("    filler: {\n");
    if( ! me ) {
        QUEX_DEBUG_PRINT("      type: <none>\n");
    }
    else {
        QUEX_DEBUG_PRINT1("      lexatom_index_next_to_fill:     %i;\n", 
                          (int)me->lexatom_index_next_to_fill);
        QUEX_DEBUG_PRINT1("      byte_n_per_lexatom:             %i;\n", 
                          (int)me->byte_n_per_lexatom);
        QUEX_DEBUG_PRINT1("      _byte_order_reversion_active_f: %s;\n", 
                          E_Boolean_NAME(me->_byte_order_reversion_active_f)); 
        /* me->byte_loader->print_this(me->byte_loader); */
        if( me->derived.print_this ) me->derived.print_this(me);
        if( ! me->byte_loader ) {
            QUEX_DEBUG_PRINT("      byte_loader: <none>\n");
        }
        else {
            if( me->byte_loader->print_this ) me->byte_loader->print_this(me->byte_loader); 
        }
    }
    QUEX_DEBUG_PRINT("    }\n");
}

QUEX_NAMESPACE_MAIN_CLOSE

$$INC: buffer/Buffer.i$$
$$INC: buffer/lexatoms/LexatomLoader_navigation.i$$
$$INC: buffer/lexatoms/LexatomLoader_Converter.i$$
$$INC: buffer/lexatoms/LexatomLoader_Plain.i$$

#endif /* QUEX_INCLUDE_GUARD__BUFFER__BUFFERFILLER_I */

