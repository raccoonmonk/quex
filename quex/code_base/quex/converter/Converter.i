/* -*- C++ -*-  vim: set syntax=cpp:
 * (C) 2007-2008 Frank-Rene Schaefer  */
#ifndef  QUEX_INCLUDE_GUARD__QUEX__CONVERTER__CONVERTER_I
#define  QUEX_INCLUDE_GUARD__QUEX__CONVERTER__CONVERTER_I

$$INC: quex/converter/Converter$$
$$INC: quex/MemoryManager$$

QUEX_NAMESPACE_QUEX_OPEN

bool
QUEX_NAME_LIB(Converter_construct)(QUEX_GNAME_LIB(Converter)* me,
                                   size_t       LexatomSize_bit,
                                   size_t       InputCodeUnitSize,
                                   E_LoadResult (*convert)(QUEX_GNAME_LIB(Converter)*, 
                                                           uint8_t**      source, const uint8_t* SourceEnd, 
                                                           void** drain,  const void*            DrainEnd),
                                   void         (*destruct)(QUEX_GNAME_LIB(Converter)*),
                                   ptrdiff_t    (*stomach_byte_n)(QUEX_GNAME_LIB(Converter)*),
                                   void         (*stomach_clear)(QUEX_GNAME_LIB(Converter)*),
                                   void         (*print_this)(QUEX_GNAME_LIB(Converter)*))
/* If 'FromCodec == 0': The converter is expected to adapt to a BOM (byte order
 *                      mark *later*. 'initialize' is expected to mark the 
 *                      derived class' as 'not-initialized'.
 *                      In that case, the function '.initialize_by_bom_id' must 
 *                      be called before the converter is operational. That 
 *                      function may check, whether an initialization has been
 *                      done before.
 * 
 * RETURNS: true  -- construction succesful
 *          false -- else.                                                    */
{
    __quex_assert(0 != convert);
    __quex_assert(0 != destruct);
    __quex_assert(0 != stomach_byte_n);
    __quex_assert(0 != stomach_clear);

    me->convert              = convert;
    me->stomach_byte_n       = stomach_byte_n;
    me->stomach_clear        = stomach_clear;
    me->destruct             = destruct;
    me->print_this           = print_this;

    me->virginity_f          = true;
    me->byte_n_per_lexatom   = -1;         /* No fixed ratio 'byte_n/lexatom' */
    me->lexatom_size_bit     = LexatomSize_bit;
    me->input_code_unit_size = InputCodeUnitSize; /* Unknown input code unit. */

    /* Opens internally a conversion handle for the conversion from 'FromCodec'
     * to 'ToCodec'. Pass '0x0' as 'ToCodec' in order to indicate a conversion
     * to unicode of size sizeof(QUEX_TYPE_LEXATOM). 
     *
     * It is the task of the particular implementation to provide the 'ToCodec'
     * which is appropriate for sizeof(QUEX_TYPE_LEXATOM), i.e.  ASCII, UCS2,
     * UCS4.                                                                  */
    return true;
}

void
QUEX_NAME_LIB(Converter_delete)(QUEX_GNAME_LIB(Converter)** me)
{
    if( ! *me ) {
        return;
    }
    else if( (*me)->destruct ) {
        (*me)->destruct(*me);
    }
    QUEX_NAME_LIB(MemoryManager_free)((void*)*me, E_MemoryObjectType_CONVERTER);
    (*me) = (QUEX_GNAME_LIB(Converter)*)0;
}

void
QUEX_NAME_LIB(Converter_reset)(QUEX_GNAME_LIB(Converter)* me)
{
    me->stomach_clear(me);
    me->virginity_f = true;
}

void
QUEX_NAME_LIB(Converter_print_this)(QUEX_GNAME_LIB(Converter)* me)
{
    QUEX_DEBUG_PRINT("      converter: ");
    if( ! me ) {
        QUEX_DEBUG_PRINT("<none>\n");
        return;
    }
    QUEX_DEBUG_PRINT("{\n");
    QUEX_DEBUG_PRINT1("        virginity_f:          %s;\n", E_Boolean_NAME(me->virginity_f));
    QUEX_DEBUG_PRINT1("        byte_n_per_lexatom:   %i;\n", (int)me->byte_n_per_lexatom);
    QUEX_DEBUG_PRINT1("        input_code_unit_size: %i;\n", (int)me->input_code_unit_size);
    if( me->print_this ) {
        me->print_this(me);
    }
    QUEX_DEBUG_PRINT("      }\n");
}


QUEX_NAMESPACE_QUEX_CLOSE

#endif /*  QUEX_INCLUDE_GUARD__QUEX__CONVERTER__CONVERTER_I     */
