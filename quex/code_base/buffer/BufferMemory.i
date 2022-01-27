/* vim:set ft=c: -*- C++ -*- */
#ifndef QUEX_INCLUDE_GUARD__BUFFER__BUFFER_MEMORY_I
#define QUEX_INCLUDE_GUARD__BUFFER__BUFFER_MEMORY_I

$$INC: quex/asserts$$
$$INC: buffer/asserts$$
$$INC: definitions$$
$$INC: buffer/Buffer$$
$$INC: buffer/Buffer_print.i$$
$$INC: buffer/lexatoms/LexatomLoader$$
$$INC: quex/MemoryManager$$

QUEX_NAMESPACE_MAIN_OPEN

QUEX_INLINE void 
QUEX_NAME(BufferMemory_construct)(QUEX_NAME(BufferMemory)*  me, 
                                  QUEX_TYPE_LEXATOM*        Memory, 
                                  const size_t              Size,
                                  E_Ownership               Ownership,
                                  QUEX_NAME(Buffer)*        IncludingBuffer) 
{
    __quex_assert(E_Ownership_is_valid(Ownership));    

    if( Memory ) {
        me->_front    = Memory;
        me->_back     = &Memory[Size-1];
        me->ownership = Ownership;
        me->_front[0] = QUEX_SETTING_BUFFER_LEXATOM_BUFFER_BORDER;
        me->_back[0]  = QUEX_SETTING_BUFFER_LEXATOM_BUFFER_BORDER;
    } else {
        me->_front    = (QUEX_TYPE_LEXATOM*)0;
        me->_back     = me->_front;
        me->ownership = Ownership;
    }
    
    if( Ownership == E_Ownership_INCLUDING_BUFFER ) { 
        __quex_assert(0 != IncludingBuffer); 
    }
    else { 
        __quex_assert(0 == IncludingBuffer); 
        __quex_assert(me != &IncludingBuffer->_memory); 
    }

    me->including_buffer = IncludingBuffer;
}

QUEX_INLINE void 
QUEX_NAME(BufferMemory_destruct)(QUEX_NAME(BufferMemory)* me) 
/* Does not set 'me->_front' to zero, if it is not deleted. Thus, the user
 * may detect wether it needs to be deleted or not.                           */
{
    if( me->_front ) {
        switch( me->ownership ) {
        case E_Ownership_LEXER:
            __quex_assert(0 == me->including_buffer);
            QUEX_GNAME_LIB(MemoryManager_free)((void*)me->_front, 
                                       E_MemoryObjectType_BUFFER_MEMORY);
            break;
        case E_Ownership_INCLUDING_BUFFER:
            __quex_assert(0 != me->including_buffer);
            __quex_assert(me->_front == me->including_buffer->end(me->including_buffer));
            me->including_buffer->_memory._back = me->_back;
        default: 
            break;
        }
    }
    QUEX_NAME(BufferMemory_resources_absent_mark)(me);
}


QUEX_INLINE void 
QUEX_NAME(BufferMemory_resources_absent_mark)(QUEX_NAME(BufferMemory)* me) 
/* Marks memory absent. If previously the ownership was 'E_Ownership_EXTERNAL'.
 * then the concerned memory is no longer referred by this buffer.            */
{
    /* 'me->_front == 0' prevents 'MemoryManager_free()'                      */
    me->_front = me->_back = (QUEX_TYPE_LEXATOM*)0;
    me->ownership        = E_Ownership_LEXER;
    me->including_buffer = (QUEX_NAME(Buffer)*)0;
}

QUEX_INLINE bool 
QUEX_NAME(BufferMemory_resources_absent)(QUEX_NAME(BufferMemory)* me) 
{
    /* Ownership is irrelevant.                                               */
    return    (me->_front == me->_back) 
           && (me->_front == (QUEX_TYPE_LEXATOM*)0)
           && (me->including_buffer == (QUEX_NAME(Buffer)*)0);
}

QUEX_INLINE size_t          
QUEX_NAME(BufferMemory_size)(QUEX_NAME(BufferMemory)* me)
{ return (size_t)(me->_back - me->_front + 1); }

QUEX_INLINE bool
QUEX_NAME(BufferMemory_check_chunk)(const QUEX_TYPE_LEXATOM* Front, 
                                    size_t                   Size, 
                                    const QUEX_TYPE_LEXATOM* EndOfFileP) 
{
    const QUEX_TYPE_LEXATOM* Back = &Front[Size-1];

    if( ! Front ) {
        return (Size == 0 && ! EndOfFileP) ? true : false; 
    }
    else if(   Size < 3  
            || ! EndOfFileP
            || EndOfFileP    <= Front 
            || EndOfFileP    >  Back  
            || Front[0]      != QUEX_SETTING_BUFFER_LEXATOM_BUFFER_BORDER    
            || Back[0]       != QUEX_SETTING_BUFFER_LEXATOM_BUFFER_BORDER 
            || EndOfFileP[0] != QUEX_SETTING_BUFFER_LEXATOM_BUFFER_BORDER ) {
        return false;
    }
    else  {
        return true;
    }
}

QUEX_INLINE void
QUEX_NAME(BufferMemory_print_this)(QUEX_NAME(BufferMemory)* me)
{
    QUEX_DEBUG_PRINT("    memory: {\n");
    QUEX_DEBUG_PRINT1("      ownership: %s;\n", E_Ownership_NAME(me->ownership));
    QUEX_DEBUG_PRINT1("      begin:     ((%p)) (== _front);\n",       (void*)me->_front);
    QUEX_DEBUG_PRINT1("      end:       begin + %i (== _back + 1);\n", (int)(me->_back + 1 - me->_front));
    QUEX_DEBUG_PRINT("    }\n");
}

QUEX_NAMESPACE_MAIN_CLOSE

#endif /*  QUEX_INCLUDE_GUARD__BUFFER__BUFFER_MEMORY_I */
