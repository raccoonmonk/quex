/* -*- C++ -*-  vim: set syntax=cpp:
 * (C) 2007-2008 Frank-Rene Schaefer  */
#ifndef  QUEX_INCLUDE_GUARD__QUEX__CONVERTER__ICONV__CONVERTER_ICONV_I
#define  QUEX_INCLUDE_GUARD__QUEX__CONVERTER__ICONV__CONVERTER_ICONV_I

$$<Cpp>--------------------------------------------------------------------------
#include <cerrno>
#define BASE (*me)
$$-----------------------------------------------------------------------------
$$<C>--------------------------------------------------------------------------
#include <errno.h>
#define BASE me->base
$$-----------------------------------------------------------------------------

$$INC: quex/asserts$$
$$INC: quex/converter/iconv/Converter_IConv$$
$$INC: quex/MemoryManager$$


QUEX_NAMESPACE_QUEX_OPEN

extern bool
QUEX_NAME_LIB(Converter_IConv_construct)(QUEX_GNAME_LIB(Converter_IConv)* me, 
                                         size_t LexatomSize_bit, 
                                         const char* FromEncoding, const char* ToEncoding);
extern bool
QUEX_NAME_LIB(Converter_IConv_construct_from_BOM)(QUEX_GNAME_LIB(Converter_IConv)* me, 
                                                  size_t LexatomSize_bit, E_ByteOrderMark BomId);

extern bool 
QUEX_NAME_LIB(Converter_IConv_initialize)(QUEX_GNAME_LIB(Converter_IConv)* me,
                                          const char* FromEncoding, 
                                          const char* ToEncoding);

extern const char*
QUEX_NAME_LIB(Converter_IConv_BomToEncodingName)(E_ByteOrderMark BomId);

extern size_t
QUEX_NAME_LIB(Converter_IConv_EncodingToCodeUnitSize)(const char*  Encoding);

extern E_LoadResult 
QUEX_NAME_LIB(Converter_IConv_convert)(QUEX_GNAME_LIB(Converter)* me, 
                                   uint8_t**             source, 
                                   const uint8_t*        SourceEnd,
                                   void**                drain,  
                                   const void*           DrainEnd);
extern void 
QUEX_NAME_LIB(Converter_IConv_destruct)(QUEX_GNAME_LIB(Converter)* me);

extern ptrdiff_t 
QUEX_NAME_LIB(Converter_IConv_stomach_byte_n)(QUEX_GNAME_LIB(Converter)* me);

extern void 
QUEX_NAME_LIB(Converter_IConv_stomach_clear)(QUEX_GNAME_LIB(Converter)* me);

extern void 
QUEX_NAME_LIB(Converter_IConv_print_this)(QUEX_GNAME_LIB(Converter)* me);

$$<Cpp>------------------------------------------------------------------------
QUEX_NAME_LIB(Converter_IConv)::QUEX_NAME_LIB(Converter_IConv)(size_t LexatomSize_bit,
                                                               const char* FromEncoding, 
                                                               const char* ToEncoding)
{
    QUEX_NAME_LIB(Converter_IConv_construct)(this, LexatomSize_bit, FromEncoding, ToEncoding);
}
QUEX_NAME_LIB(Converter_IConv)::QUEX_NAME_LIB(Converter_IConv)(size_t LexatomSize_bit, E_ByteOrderMark BomId)
{
    QUEX_NAME_LIB(Converter_IConv_construct_from_BOM)(this, LexatomSize_bit, BomId);
}
$$-----------------------------------------------------------------------------

QUEX_GNAME_LIB(Converter)*
QUEX_NAME_LIB(Converter_IConv_new)(size_t LexatomSize_bit, const char* FromEncoding, const char* ToEncoding)
{
    QUEX_NAME_LIB(Converter_IConv)*  me = \
       (QUEX_NAME_LIB(Converter_IConv)*)
       QUEX_GNAME_LIB(MemoryManager_allocate)(sizeof(QUEX_NAME_LIB(Converter_IConv)),
                                              E_MemoryObjectType_CONVERTER);
    if( ! me ) {
        return (QUEX_GNAME_LIB(Converter)*)0;
    }
    else if( ! QUEX_NAME_LIB(Converter_IConv_construct)(me, LexatomSize_bit, FromEncoding, ToEncoding) ) {
        QUEX_NAME_LIB(MemoryManager_free)((void*)&QUEX_BASE, E_MemoryObjectType_CONVERTER);
        return (QUEX_GNAME_LIB(Converter)*)0;
    }
    return &QUEX_BASE;
}

QUEX_GNAME_LIB(Converter)*
QUEX_NAME_LIB(Converter_IConv_new_from_BOM)(size_t LexatomSize_bit, E_ByteOrderMark BomId)
{
    QUEX_NAME_LIB(Converter_IConv)*  me = \
       (QUEX_NAME_LIB(Converter_IConv)*)
       QUEX_GNAME_LIB(MemoryManager_allocate)(sizeof(QUEX_NAME_LIB(Converter_IConv)),
                                              E_MemoryObjectType_CONVERTER);
    if( ! me ) {
        return (QUEX_GNAME_LIB(Converter)*)0;
    }
    else if( ! QUEX_NAME_LIB(Converter_IConv_construct_from_BOM)(me, LexatomSize_bit, BomId) ) {
        QUEX_NAME_LIB(MemoryManager_free)((void*)&QUEX_BASE, E_MemoryObjectType_CONVERTER);
        return (QUEX_GNAME_LIB(Converter)*)0;
    }

    return &QUEX_BASE;
}

bool
QUEX_NAME_LIB(Converter_IConv_construct)(QUEX_GNAME_LIB(Converter_IConv)* me, 
                                         size_t LexatomSize_bit, const char* FromEncoding, const char* ToEncoding)
{
    me->handle = (iconv_t)-1;
    if( ! QUEX_NAME_LIB(Converter_construct)((QUEX_GNAME_LIB(Converter)*)me,
                                             LexatomSize_bit,
                                             QUEX_NAME_LIB(Converter_IConv_EncodingToCodeUnitSize)(FromEncoding),
                                             QUEX_NAME_LIB(Converter_IConv_convert),
                                             QUEX_NAME_LIB(Converter_IConv_destruct),
                                             QUEX_NAME_LIB(Converter_IConv_stomach_byte_n),
                                             QUEX_NAME_LIB(Converter_IConv_stomach_clear),
                                             QUEX_NAME_LIB(Converter_IConv_print_this)) ) {
        QUEX_GNAME_LIB(MemoryManager_free)((void*)&QUEX_BASE, E_MemoryObjectType_CONVERTER);
        return false;
    }
    else if( !  QUEX_NAME_LIB(Converter_IConv_initialize)(me, FromEncoding, ToEncoding) ) {
        QUEX_GNAME_LIB(MemoryManager_free)((void*)&QUEX_BASE, E_MemoryObjectType_CONVERTER);
        return false;
    }
    else {
        return true;
    }
}

bool
QUEX_NAME_LIB(Converter_IConv_construct_from_BOM)(QUEX_GNAME_LIB(Converter_IConv)* me, 
                                                  size_t LexatomSize_bit, E_ByteOrderMark BomId)
{
    return QUEX_NAME_LIB(Converter_IConv_construct)(me, LexatomSize_bit, 
                                                    QUEX_NAME_LIB(Converter_IConv_BomToEncodingName)(BomId), NULL);
}

bool 
QUEX_NAME_LIB(Converter_IConv_initialize)(QUEX_GNAME_LIB(Converter_IConv)* me,
                                          const char* FromEncoding, 
                                          const char* ToEncoding)
/* Initializes the converter, or in case that 'FromEncoding == 0', it marks
 * the object as 'not-initialized'. 'Converter_IConv_initialize_by_bom_id()'
 * will act upon that information.  
 *
 * RETURNS: true, if success. false, else.                                    */
{
    const bool                      little_endian_f = QUEX_GNAME_LIB(system_is_little_endian)();

    if( ! FromEncoding ) {
        me->handle = (iconv_t)-1;               /* mark 'not-initialized'.    */
        return true;                            /* still, nothing went wrong. */
    }

    /* Setup conversion handle */
    if( ! ToEncoding ) {
        switch( BASE.lexatom_size_bit ) {
        case 32: ToEncoding = little_endian_f ? "UCS-4LE" : "UCS-4BE"; break;
        case 16: ToEncoding = little_endian_f ? "UCS-2LE" : "UCS-2BE"; break;
        case 8:  ToEncoding = "ASCII"; break;
        default:  __quex_assert(false); return false;
        }
    } 
    me->handle = iconv_open(ToEncoding, FromEncoding);
    if( me->handle == (iconv_t)-1 ) return false;
    
    /* ByteN / Character:
     * IConv does not provide something like 'isFixedWidth()'. So, the 
     * safe assumption "byte_n/lexatom != const" is made, except for some
     * well-known examples.                                              */
    BASE.byte_n_per_lexatom = -1;
    if(    QUEX_GSTD(strcmp)(FromEncoding, "UCS-4LE") == 0 
        || QUEX_GSTD(strcmp)(FromEncoding, "UCS-4BE")  == 0) {
        BASE.byte_n_per_lexatom   = 4;
        BASE.input_code_unit_size = 4;
    }
    else if(   QUEX_GSTD(strcmp)(FromEncoding, "UCS-2LE") == 0 
            || QUEX_GSTD(strcmp)(FromEncoding, "UCS-2BE")  == 0) {
        BASE.byte_n_per_lexatom   = 2;
        BASE.input_code_unit_size = 2;
    }
    else if( QUEX_GSTD(strcmp)(FromEncoding, "UTF16") == 0 ) {
        BASE.byte_n_per_lexatom   = -1;
        BASE.input_code_unit_size = 2;
    }
    else if( QUEX_GSTD(strcmp)(FromEncoding, "UTF8") == 0 ) {
        BASE.byte_n_per_lexatom   = -1;
        BASE.input_code_unit_size = 1;
    }

    return true;
}

size_t
QUEX_NAME_LIB(Converter_IConv_EncodingToCodeUnitSize)(const char*  Encoding)
{

    if     ( 0 == strcmp(Encoding, "UTF-8") )    return 1;                      
    else if( 0 == strcmp(Encoding, "UTF-1") )    return 1;                      
    else if( 0 == strcmp(Encoding, "GB18030") )  return 1;                
    else if( 0 == strcmp(Encoding, "UTF-7") )    return 1;                      
    else if( 0 == strcmp(Encoding, "UTF-16") )   return 2;                                  
    else if( 0 == strcmp(Encoding, "UTF-16LE") ) return 2;              
    else if( 0 == strcmp(Encoding, "UTF-16BE") ) return 2;              
    else if( 0 == strcmp(Encoding, "UTF-32") )   return 4;                    
    else if( 0 == strcmp(Encoding, "UTF-32LE") ) return 4;              
    else if( 0 == strcmp(Encoding, "UTF-32BE") ) return 4;              
    else                                         return (size_t)-1;
}

const char*
QUEX_NAME_LIB(Converter_IConv_BomToEncodingName)(E_ByteOrderMark BomId)
{
    switch( BomId ) {
    case QUEX_BOM_UTF_8:           return "UTF-8";                      
    case QUEX_BOM_UTF_1:           return "UTF-1";                      
    case QUEX_BOM_GB_18030:        return "GB18030";                
    case QUEX_BOM_UTF_7:           return "UTF-7";                      
    case QUEX_BOM_UTF_16:          return "UTF-16";                                  
    case QUEX_BOM_UTF_16_LE:       return "UTF-16LE";              
    case QUEX_BOM_UTF_16_BE:       return "UTF-16BE";              
    case QUEX_BOM_UTF_32:          return "UTF-32";                    
    case QUEX_BOM_UTF_32_LE:       return "UTF-32LE";              
    case QUEX_BOM_UTF_32_BE:       return "UTF-32BE";              

    default:
    case QUEX_BOM_UTF_EBCDIC:      /* return "UTF_EBCDIC"; */
    case QUEX_BOM_BOCU_1:          /* return "BOCU_1";     */
    case QUEX_BOM_SCSU:            /* not supported. */
    case QUEX_BOM_SCSU_TO_UCS:     /* not supported. */
    case QUEX_BOM_SCSU_W0_TO_FE80: /* not supported. */
    case QUEX_BOM_SCSU_W1_TO_FE80: /* not supported. */
    case QUEX_BOM_SCSU_W2_TO_FE80: /* not supported. */
    case QUEX_BOM_SCSU_W3_TO_FE80: /* not supported. */
    case QUEX_BOM_SCSU_W4_TO_FE80: /* not supported. */
    case QUEX_BOM_SCSU_W5_TO_FE80: /* not supported. */
    case QUEX_BOM_SCSU_W6_TO_FE80: /* not supported. */
    case QUEX_BOM_SCSU_W7_TO_FE80: /* not supported. */
    case QUEX_BOM_NONE:            return "<unsupported>";
    }
}

#ifndef QUEX_ADAPTER_ICONV_2ND_ARG_DEFINITION_DONE
#define QUEX_ADAPTER_ICONV_2ND_ARG_DEFINITION_DONE
$$<Cpp>------------------------------------------------------------------------
/* NOTE: At the time of this writing 'iconv' is delivered on different 
 *       systems with different definitions for the second argument. The 
 *       following 'hack' by Howard Jeng does the adaption automatically. */
struct QUEX_ADAPTER_ICONV_2ND_ARG {
    QUEX_ADAPTER_ICONV_2ND_ARG(uint8_t ** in) : data(in) {}
    uint8_t ** data;
    operator const char **(void) const { return (const char **)(data); }
    operator       char **(void) const { return (      char **)(data); }
}; 
$$-----------------------------------------------------------------------------

$$<C>--------------------------------------------------------------------------
#if defined(QUEX_OPTION_ICONV_2ND_ARG_CONST_CHARPP_EXT)
#    define QUEX_ADAPTER_ICONV_2ND_ARG(ARG)  ((const char**)(ARG))
#else
#    define QUEX_ADAPTER_ICONV_2ND_ARG(ARG)  ((char**)(ARG))
#endif
$$-----------------------------------------------------------------------------
#endif

E_LoadResult 
QUEX_NAME_LIB(Converter_IConv_convert)(QUEX_GNAME_LIB(Converter)* alter_ego, 
                                       uint8_t**             source, 
                                       const uint8_t*        SourceEnd,
                                       void**                drain,  
                                       const void*           DrainEnd)
/* RETURNS:  true  --> User buffer is filled as much as possible with 
 *                     converted lexatoms.
 *           false --> More raw bytes are needed to fill the user buffer.           
 *
 *  <fschaef@users.sourceforge.net>.                                          */
{
    QUEX_NAME_LIB(Converter_IConv)* me              = (QUEX_NAME_LIB(Converter_IConv)*)alter_ego;
    size_t                      source_bytes_left_n = (size_t)(SourceEnd - *source);
    size_t                      drain_bytes_left_n  = (size_t)((const uint8_t*)DrainEnd - (const uint8_t*)*drain);
    size_t                      report;
    
    /* Compilation error for second argument in some versions of IConv?
     * => define "QUEX_OPTION_ICONV_2ND_ARG_CONST_CHARPP_EXT"                */
    report = iconv(me->handle, 
                   QUEX_ADAPTER_ICONV_2ND_ARG(source), &source_bytes_left_n,
                   (char**)drain,                      &drain_bytes_left_n);
    /* Avoid strange error reports from 'iconv' in case that the source 
     * buffer is empty.                                                      */

    if( report != (size_t)-1 ) { 
        /* No Error => Raw buffer COMPLETELY converted.                      */
        __quex_assert(! source_bytes_left_n);
        return drain_bytes_left_n ? E_LoadResult_INCOMPLETE 
                                  : E_LoadResult_COMPLETE;
    }

    switch( errno ) {
    default:
        return E_LoadResult_ENCODING_ERROR;

    case EILSEQ:
        return E_LoadResult_ENCODING_ERROR;

    case EINVAL:
        /* Incomplete byte sequence for lexatom conversion.
         * => '*source' points to the beginning of the incomplete sequence.
         * => If drain is not filled, then new source content must be 
         *    provided.                                                      */
        return drain_bytes_left_n ? E_LoadResult_INCOMPLETE 
                                  : E_LoadResult_COMPLETE;

    case E2BIG:
        /* The input buffer was not able to hold the number of converted 
         * lexatoms. => Drain is filled to the limit.                        */
        return E_LoadResult_COMPLETE;
    }
}

ptrdiff_t 
QUEX_NAME_LIB(Converter_IConv_stomach_byte_n)(QUEX_GNAME_LIB(Converter)* me)
{ (void)me; return 0; }

void 
QUEX_NAME_LIB(Converter_IConv_stomach_clear)(QUEX_GNAME_LIB(Converter)* me)
{ (void)me; }

void 
QUEX_NAME_LIB(Converter_IConv_destruct)(QUEX_GNAME_LIB(Converter)* alter_ego)
{
    QUEX_NAME_LIB(Converter_IConv)* me = (QUEX_NAME_LIB(Converter_IConv)*)alter_ego;

    iconv_close(me->handle); 
}

void 
QUEX_NAME_LIB(Converter_IConv_print_this)(QUEX_GNAME_LIB(Converter)* alter_ego)
{
    QUEX_NAME_LIB(Converter_IConv)* me = (QUEX_NAME_LIB(Converter_IConv)*)alter_ego;

    QUEX_DEBUG_PRINT("        type:                 IConv, GNU;\n");
    QUEX_DEBUG_PRINT1("        handle:               ((%p));\n", (const void*)(me->handle));
}

QUEX_NAMESPACE_QUEX_CLOSE


#endif /*  QUEX_INCLUDE_GUARD__QUEX__CONVERTER__ICONV__CONVERTER_ICONV_I */
