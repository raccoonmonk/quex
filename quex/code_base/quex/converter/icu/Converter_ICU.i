/* -*- C++ -*-  vim: set syntax=cpp:
 * (C) 2007-2008 Frank-Rene Schaefer  */
#ifndef  QUEX_INCLUDE_GUARD__QUEX__CONVERTER__ICU__CONVERTER_ICU_I
#define  QUEX_INCLUDE_GUARD__QUEX__CONVERTER__ICU__CONVERTER_ICU_I

$$INC: quex/asserts$$
$$INC: quex/converter/icu/Converter_ICU$$
$$INC: quex/types.h$$
$$INC: quex/MemoryManager$$

$$<Cpp>--------------------------------------------------------------------------
#define BASE (*me)
$$-----------------------------------------------------------------------------
$$<C>--------------------------------------------------------------------------
#define BASE me->base
$$-----------------------------------------------------------------------------

QUEX_NAMESPACE_QUEX_OPEN

extern bool
QUEX_NAME_LIB(Converter_ICU_construct)(QUEX_GNAME_LIB(Converter_ICU)* me, 
                                         size_t LexatomSize_bit, 
                                         const char* FromEncoding, const char* ToEncoding);
extern bool
QUEX_NAME_LIB(Converter_ICU_construct_from_BOM)(QUEX_GNAME_LIB(Converter_ICU)* me, 
                                                size_t LexatomSize_bit, E_ByteOrderMark BomId);

extern const char*
QUEX_NAME_LIB(Converter_ICU_BomToEncodingName)(E_ByteOrderMark BomId);

extern size_t
QUEX_NAME_LIB(Converter_ICU_EncodingToCodeUnitSize)(const char*  Encoding);

extern bool
QUEX_NAME_LIB(Converter_ICU_initialize)(QUEX_GNAME_LIB(Converter_ICU)* me, 
                                        const char*                    FromEncoding, 
                                        const char*                    ToEncoding);

extern E_LoadResult
QUEX_NAME_LIB(Converter_ICU_convert)(QUEX_GNAME_LIB(Converter)*     me, 
                                     uint8_t**       source, 
                                     const uint8_t*  SourceEnd, 
                                     void**          drain,  
                                     const void*     DrainEnd);
extern void
QUEX_NAME_LIB(Converter_ICU_destruct)(QUEX_GNAME_LIB(Converter)* me);

extern ptrdiff_t 
QUEX_NAME_LIB(Converter_ICU_stomach_byte_n)(QUEX_GNAME_LIB(Converter)* me);

extern void 
QUEX_NAME_LIB(Converter_ICU_stomach_clear)(QUEX_GNAME_LIB(Converter)* me);

extern void 
QUEX_NAME_LIB(Converter_ICU_print_this)(QUEX_GNAME_LIB(Converter)* me);

$$<Cpp>------------------------------------------------------------------------
QUEX_NAME_LIB(Converter_ICU)::QUEX_NAME_LIB(Converter_ICU)(size_t LexatomSize_bit,
                                                           const char* FromEncoding, 
                                                           const char* ToEncoding)
{
    QUEX_NAME_LIB(Converter_ICU_construct)(this, LexatomSize_bit, FromEncoding, ToEncoding);
}
QUEX_NAME_LIB(Converter_ICU)::QUEX_NAME_LIB(Converter_ICU)(size_t LexatomSize_bit, E_ByteOrderMark BomId)
{
    QUEX_NAME_LIB(Converter_ICU_construct_from_BOM)(this, LexatomSize_bit, BomId);
}
$$-----------------------------------------------------------------------------

QUEX_GNAME_LIB(Converter)*
QUEX_NAME_LIB(Converter_ICU_new)(size_t LexatomSize_bit, const char* FromEncoding, const char* ToEncoding)
{
    QUEX_NAME_LIB(Converter_ICU)*  me = \
         (QUEX_NAME_LIB(Converter_ICU)*)QUEX_GNAME_LIB(MemoryManager_allocate)(sizeof(QUEX_NAME_LIB(Converter_ICU)),
                                                                   E_MemoryObjectType_CONVERTER);

    if( ! QUEX_NAME_LIB(Converter_ICU_construct)(me, LexatomSize_bit, FromEncoding, ToEncoding) ) {
        return (QUEX_GNAME_LIB(Converter)*)0;
    }
    $$<Cpp>return me;$$
    $$<C>return &me->base;$$
    
}

QUEX_GNAME_LIB(Converter)*
QUEX_NAME_LIB(Converter_ICU_new_from_BOM)(size_t LexatomSize_bit, E_ByteOrderMark BomId)
{
    QUEX_NAME_LIB(Converter_ICU)*  me = \
       (QUEX_NAME_LIB(Converter_ICU)*)
       QUEX_GNAME_LIB(MemoryManager_allocate)(sizeof(QUEX_NAME_LIB(Converter_ICU)),
                                              E_MemoryObjectType_CONVERTER);
    if( ! me ) {
        return (QUEX_GNAME_LIB(Converter)*)0;
    }
    else if( ! QUEX_NAME_LIB(Converter_ICU_construct_from_BOM)(me, LexatomSize_bit, BomId) ) {
        QUEX_NAME_LIB(MemoryManager_free)((void*)&QUEX_BASE, E_MemoryObjectType_CONVERTER);
        return (QUEX_GNAME_LIB(Converter)*)0;
    }

    return &QUEX_BASE;
}

bool
QUEX_NAME_LIB(Converter_ICU_construct)(QUEX_GNAME_LIB(Converter_ICU)* me, 
                                       size_t LexatomSize_bit, const char* FromEncoding, const char* ToEncoding)
{
    me->to_handle   = 0x0;
    me->from_handle = 0x0;
    me->status      = U_ZERO_ERROR;
    /* Setup the pivot buffer                                            */
    me->pivot.source = &me->pivot.buffer[0];
    me->pivot.target = &me->pivot.buffer[0];
    me->reset_upon_next_conversion_f = TRUE;

    if( ! QUEX_NAME_LIB(Converter_construct)(&BASE,
                                             LexatomSize_bit, 
                                             QUEX_NAME_LIB(Converter_ICU_EncodingToCodeUnitSize)(FromEncoding),
                                             QUEX_NAME_LIB(Converter_ICU_convert),
                                             QUEX_NAME_LIB(Converter_ICU_destruct),
                                             QUEX_NAME_LIB(Converter_ICU_stomach_byte_n),
                                             QUEX_NAME_LIB(Converter_ICU_stomach_clear),
                                             QUEX_NAME_LIB(Converter_ICU_print_this)) ) {
        QUEX_GNAME_LIB(MemoryManager_free)((void*)&QUEX_BASE, E_MemoryObjectType_CONVERTER);
        return false;
    }
    else if( !  QUEX_NAME_LIB(Converter_ICU_initialize)(me, FromEncoding, ToEncoding) ) {
        QUEX_GNAME_LIB(MemoryManager_free)((void*)&QUEX_BASE, E_MemoryObjectType_CONVERTER);
        return false;
    }
    else {
        return true;
    }
}
bool
QUEX_NAME_LIB(Converter_ICU_construct_from_BOM)(QUEX_GNAME_LIB(Converter_ICU)* me, 
                                                size_t LexatomSize_bit, E_ByteOrderMark BomId)
{
    return QUEX_NAME_LIB(Converter_ICU_construct)(me, LexatomSize_bit, 
                                                  QUEX_NAME_LIB(Converter_ICU_BomToEncodingName)(BomId), NULL);
}

bool
QUEX_NAME_LIB(Converter_ICU_initialize)(QUEX_GNAME_LIB(Converter_ICU)* me, 
                                        const char*                    FromEncoding, 
                                        const char*                    ToEncoding)
/* Initializes the converter, or in case that 'FromEncoding == 0', it marks
 * the object as 'not-initialized'. 'Converter_ICU_initialize_by_bom_id()'
 * will act upon that information.  
 *
 * RETURNS: true, if success. false, else.                                    */
{
    const bool                little_endian_f = QUEX_GNAME_LIB(system_is_little_endian)();
    const void*               oldContext;
    UConverterFromUCallback   oldFromAction;
    UConverterToUCallback     oldToAction;

    me->from_handle = 0x0;
    me->to_handle   = 0x0; 
    if( ! FromEncoding ) {
        /* me->from_handle = 0; mark as 'not-initialized'.                    */
        return true;                            /* still, nothing went wrong. */
    }

    __quex_assert(me);

    /* Default: assume input encoding to have dynamic lexatom sizes.          */
    if( ucnv_compareNames(FromEncoding, "UTF32") == 0 ) {
        FromEncoding = "UTF32_PlatformEndian";
    }
    else if( ucnv_compareNames(FromEncoding, "UTF16") == 0 ) {
        FromEncoding = "UTF16_PlatformEndian";
    }

    /* Open conversion handles                                                */
    me->status      = U_ZERO_ERROR;
    me->from_handle = ucnv_open(FromEncoding, &me->status);
    if( me->from_handle == NULL || ! U_SUCCESS(me->status) ) {
        goto ERROR;
    }
    /* ByteN / Character:                                               */
    else if( ucnv_isFixedWidth(me->from_handle, &me->status) && U_SUCCESS(me->status) ) {
        BASE.byte_n_per_lexatom = ucnv_getMaxCharSize(me->from_handle);
    }
    else {
        BASE.byte_n_per_lexatom = -1;
    }
    if( QUEX_GSTD(strcmp)(FromEncoding, "UTF16") == 0 ) {
        BASE.input_code_unit_size = 2;
    }
    else if( QUEX_GSTD(strcmp)(FromEncoding, "UTF8") == 0 ) {
        BASE.input_code_unit_size = 1;
    }

    if( ! ToEncoding ) {
         /* From the ICU Documentation: "ICU does not use UCS-2. UCS-2 is a
          * subset of UTF-16. UCS-2 does not support surrogates, and UTF-16
          * does support surrogates. This means that UCS-2 only supports
          * UTF-16's Base Multilingual Plane (BMP). The notion of UCS-2 is
          * deprecated and dead. Unicode 2.0 in 1996 changed its default
          * encoding to UTF-16." (userguide.icu-project.org/icufaq)           */
        switch( BASE.lexatom_size_bit ) {
        case 32:  ToEncoding = little_endian_f ? "UTF32-LE" : "UTF32-LE"; break;
        case 16:  ToEncoding = little_endian_f ? "UTF16-LE" : "UTF16-LE"; break;
        case 8:   ToEncoding = "ISO-8859-1"; break;
        default:  __quex_assert(false); goto ERROR_1;
        }
    } 

    me->status = U_ZERO_ERROR;
    me->to_handle = ucnv_open(ToEncoding, &me->status);
    if( me->to_handle == NULL || ! U_SUCCESS(me->status) ) goto ERROR_1;

    /* Setup the pivot buffer                                                 */
    //me->pivot.source = &me->pivot.buffer[0];
    //me->pivot.target = &me->pivot.buffer[0];         
    me->reset_upon_next_conversion_f = TRUE;

    /* Ensure that converter stops upon encoding error.                       
     * (from_handle: to unicode; to_handle: from unicode; => strange calls)   */
    ucnv_setFromUCallBack(me->to_handle, UCNV_FROM_U_CALLBACK_STOP,
                          NULL, &oldFromAction, &oldContext, &me->status);
    if( ! U_SUCCESS(me->status) ) goto ERROR_2;
    ucnv_setToUCallBack(me->from_handle, UCNV_TO_U_CALLBACK_STOP,
                        NULL, &oldToAction, &oldContext, &me->status);
    if( ! U_SUCCESS(me->status) ) goto ERROR_2;
    return true;

ERROR_2:
    ucnv_close(me->to_handle);
ERROR_1:
    ucnv_close(me->from_handle);
ERROR:
    return false;
}

size_t
QUEX_NAME_LIB(Converter_ICU_EncodingToCodeUnitSize)(const char*  Encoding)
{

    if     ( 0 == strcmp(Encoding, "UTF-8") )    return 1;                      
    else if( 0 == strcmp(Encoding, "UTF-1") )    return 1;                      
    else if( 0 == strcmp(Encoding, "UTF-7") )    return 1;                      
    else if( 0 == strcmp(Encoding, "UTF-16") )   return 2;                                  
    else if( 0 == strcmp(Encoding, "UTF-16LE") ) return 2;              
    else if( 0 == strcmp(Encoding, "UTF-16BE") ) return 2;              
    else if( 0 == strcmp(Encoding, "UTF-32") )   return 4;                    
    else if( 0 == strcmp(Encoding, "UTF-32LE") ) return 4;              
    else if( 0 == strcmp(Encoding, "UTF-32BE") ) return 4;              
    else if( 0 == strcmp(Encoding, "gb18030") )  return 1;                
    else if( 0 == strcmp(Encoding, "BOCU-1") )   return 1;                    
    else if( 0 == strcmp(Encoding, "SCSU") )     return 1;                        
    else                                         return (size_t)-1;
}

const char*
QUEX_NAME_LIB(Converter_ICU_BomToEncodingName)(E_ByteOrderMark BomId)
{
    switch( BomId ) {
    case QUEX_BOM_UTF_8:            return "UTF-8";                      
    case QUEX_BOM_UTF_1:            return "UTF-1";                      
    case QUEX_BOM_BOCU_1:           return "BOCU-1";                    
    case QUEX_BOM_GB_18030:         return "gb18030";                
    case QUEX_BOM_UTF_7:            return "UTF-7";                      
    case QUEX_BOM_UTF_16:           return "UTF-16";                                  
    case QUEX_BOM_UTF_16_LE:        return "UTF-16LE";              
    case QUEX_BOM_UTF_16_BE:        return "UTF-16BE";              
    case QUEX_BOM_UTF_32:           return "UTF-32";                    
    case QUEX_BOM_UTF_32_LE:        return "UTF-32LE";              
    case QUEX_BOM_UTF_32_BE:        return "UTF-32BE";              
    case QUEX_BOM_SCSU:             return "SCSU";                        
    default:
    case QUEX_BOM_UTF_EBCDIC:       /* return "UTF_EBCDIC"; */
    case QUEX_BOM_SCSU_TO_UCS:      /* not supported. */
    case QUEX_BOM_SCSU_W0_TO_FE80:  /* not supported. */
    case QUEX_BOM_SCSU_W1_TO_FE80:  /* not supported. */
    case QUEX_BOM_SCSU_W2_TO_FE80:  /* not supported. */
    case QUEX_BOM_SCSU_W3_TO_FE80:  /* not supported. */
    case QUEX_BOM_SCSU_W4_TO_FE80:  /* not supported. */
    case QUEX_BOM_SCSU_W5_TO_FE80:  /* not supported. */
    case QUEX_BOM_SCSU_W6_TO_FE80:  /* not supported. */
    case QUEX_BOM_SCSU_W7_TO_FE80:  /* not supported. */
    case QUEX_BOM_NONE:             return "<unsupported>";
    }
}

E_LoadResult
QUEX_NAME_LIB(Converter_ICU_convert)(QUEX_GNAME_LIB(Converter)*  alter_ego, 
                                 uint8_t**              source, 
                                 const uint8_t*         SourceEnd, 
                                 void**                 drain,  
                                 const void*            DrainEnd)
/* RETURNS: 'true'  if the drain was completely filled.
 *          'false' if the drain could not be filled completely and 
 *                  more source bytes are required.                      */
{
    QUEX_NAME_LIB(Converter_ICU)* me          = (QUEX_NAME_LIB(Converter_ICU)*)alter_ego;
    uint8_t*                  SourceBegin = *source;
    (void)SourceBegin;

    __quex_assert(me);
    __quex_assert(me->to_handle);
    __quex_assert(me->from_handle);
    __quex_assert(SourceEnd >= *source);
    __quex_assert(DrainEnd >= *drain);
    __quex_assert(&me->pivot.buffer[0] <= me->pivot.source);
    __quex_assert(me->pivot.source     <= me->pivot.target);
    __quex_assert(me->pivot.target     <= &me->pivot.buffer[QUEX_SETTING_ICU_PIVOT_BUFFER_SIZE]);

    me->status = U_ZERO_ERROR;

    ucnv_convertEx(me->to_handle, me->from_handle,
                   (char**)drain,        (const char*)DrainEnd,
                   (const char**)source, (const char*)SourceEnd,
                   &me->pivot.buffer[0], &me->pivot.source, &me->pivot.target, &me->pivot.buffer[QUEX_SETTING_ICU_PIVOT_BUFFER_SIZE],
                   /* reset = */me->reset_upon_next_conversion_f ? TRUE : FALSE, 
                   /* flush = */FALSE,
                   &me->status);
    me->reset_upon_next_conversion_f = FALSE;
    
    if( me->status == U_INVALID_CHAR_FOUND || me->status == U_ILLEGAL_CHAR_FOUND ) {
        me->status = U_ZERO_ERROR;
        return E_LoadResult_ENCODING_ERROR;
    }
    me->status = U_ZERO_ERROR;

    __quex_assert(*source >= SourceBegin);

    return *drain == DrainEnd ? E_LoadResult_COMPLETE 
                              : E_LoadResult_INCOMPLETE;
}

ptrdiff_t 
QUEX_NAME_LIB(Converter_ICU_stomach_byte_n)(QUEX_GNAME_LIB(Converter)* alter_ego)
/* To compute the source bytes which have not been converted during the last
 * conversion the 3-buffer setup must be considered. First, ICU converts the
 * source data into a pivot buffer encoded in UTF16. The the content of the
 * pivot buffer is converted into the user's drain. 
 * 
 *  source buffer  [x.x.x|y.y|z|a.a.a|b.b.b|c.c. ]    'c's are not complete
 *  (e.g. UTF8)    :   .-'   : '---. '-.   '---.      => pending = 2
 *                 :   :     '-.   :   '---.   :      
 *  pivot buffer   [X.X|Y.Y|Y.Y|Z.Z|A.A|A.A|B.B| ...  pivot.source--> 'A's
 *  (fix UTF16)    :   :   .---'   :                  pivot.target--> after 'B's
 *                 :   :   :   .---'                  
 *  drain buffer   [ X | Y | Z ]                      Drain filled to limit
 *  (some UCS)                                        'A' and 'B' cannot be 
 *                                                    converted.
 * 
 * => Source bytes NOT translated in the last conversion:
 * 
 *    (1) The 'c's that where incomplete: 'ucnv_toUCountPending()'
 *    (2) Source bytes that produced the 'A's and 'B's in the pivot buffer.  
 *
 * However, what if the conversion contained a 0xFFFD, i.e. a conversion error.
 * At the current time, I know of no reliable way to get the stomach byte
 * number <fschaef 2015y10m24d>
 * => Only report, if nothing left in pivot buffer.                          */
{
    QUEX_NAME_LIB(Converter_ICU)* me = (QUEX_NAME_LIB(Converter_ICU)*)alter_ego;

#   if 0
    /* If things go really bad; set the above to '#if 1'; Then the ICU never
     * claims to know how many bytes are in the stomach.                     */
    return (ptrdiff_t)-1;
#   endif 

    if( me->pivot.source != me->pivot.target ) {
        return (ptrdiff_t)-1;                      /* Unable to tell. Sorry. */
    }
    return ucnv_toUCountPending(me->from_handle, &me->status);
}

void 
QUEX_NAME_LIB(Converter_ICU_stomach_clear)(QUEX_GNAME_LIB(Converter)* alter_ego)
{
    QUEX_NAME_LIB(Converter_ICU)* me = (QUEX_NAME_LIB(Converter_ICU)*)alter_ego;

    // if( me->from_handle ) ucnv_reset(me->from_handle);
    // if( me->to_handle )   ucnv_reset(me->to_handle);

    /* Reset the pivot buffer iterators */
    //me->pivot.source = &me->pivot.buffer[0];
    //me->pivot.target = &me->pivot.buffer[0];
    me->reset_upon_next_conversion_f = TRUE;

    me->status = U_ZERO_ERROR;
}

void
QUEX_NAME_LIB(Converter_ICU_destruct)(QUEX_GNAME_LIB(Converter)* alter_ego)
{
    QUEX_NAME_LIB(Converter_ICU)* me = (QUEX_NAME_LIB(Converter_ICU)*)alter_ego;

    if( me->from_handle ) ucnv_close(me->from_handle);
    if( me->to_handle )   ucnv_close(me->to_handle);

    /* There should be a way to call 'ucnv_flushCache()' as soon as all converters
     * are freed automatically.                                                       */
    u_cleanup();
}

void 
QUEX_NAME_LIB(Converter_ICU_print_this)(QUEX_GNAME_LIB(Converter)* alter_ego)
{
    QUEX_NAME_LIB(Converter_ICU)* me = (QUEX_NAME_LIB(Converter_ICU)*)alter_ego;
    const void*  PivotBegin = (const void*)&me->pivot.buffer[0];
    const void*  PivotEnd   = (const void*)&me->pivot.buffer[QUEX_SETTING_ICU_PIVOT_BUFFER_SIZE];

    QUEX_DEBUG_PRINT("        type:                         ICU, IBM (tm);\n");
    QUEX_DEBUG_PRINT1("        from_handle:                  ((%p));\n", (void*)me->from_handle);
    QUEX_DEBUG_PRINT1("        to_handle:                    ((%p));\n", (void*)me->to_handle);
    QUEX_DEBUG_PRINT1("        status:                       %s;\n",     u_errorName(me->status));
    QUEX_DEBUG_PRINT1("        reset_upon_next_conversion_f: %s;\n",
                      E_Boolean_NAME(me->reset_upon_next_conversion_f));

    QUEX_DEBUG_PRINT("        pivot: {\n");
    QUEX_DEBUG_PRINT3("           buffer: { begin: ((%p)) end: ((%p)) size: %i; }\n",
                      PivotBegin, PivotEnd, (int)QUEX_SETTING_ICU_PIVOT_BUFFER_SIZE);
    QUEX_DEBUG_PRINT("           source: ");
    QUEX_GNAME_LIB(print_relative_positions)(PivotBegin, PivotEnd, sizeof(UChar),
                                     (void*)me->pivot.source);
    QUEX_DEBUG_PRINT("\n");
    QUEX_DEBUG_PRINT("           target: ");
    QUEX_GNAME_LIB(print_relative_positions)(PivotBegin, PivotEnd, sizeof(UChar),
                                     me->pivot.target);
    QUEX_DEBUG_PRINT("\n");
    QUEX_DEBUG_PRINT("        }\n");
}

QUEX_NAMESPACE_QUEX_CLOSE

#endif /* QUEX_INCLUDE_GUARD__QUEX__CONVERTER__ICU__CONVERTER_ICU_I */
