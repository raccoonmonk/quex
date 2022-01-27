#ifndef QUEX_INCLUDE_GUARD__QUEX__TINY_STDLIB_I
#define QUEX_INCLUDE_GUARD__QUEX__TINY_STDLIB_I

QUEX_NAMESPACE_QUEX_STDLIB_OPEN

static QUEX_STD(MemoryBlock)* QUEX_STD(malloc_region_get_predecessor)(QUEX_STD(MemoryBlock)* it);

void QUEX_STD(memcpy)(void* destination, const void* source, size_t size)
/* Default memory copy, if standard library is not available. There is no
 * claim that this is an optimal solution of any kind.                        */
{
    const char* read_it  = (const char*)source;
    char*       write_it = (char*)destination;
    const char* End      = &read_it[size];
    for(; read_it != End ; ++read_it, ++write_it) {
        *write_it = *read_it;
    }
}

void* QUEX_STD(memset)(void *memory, int c, size_t size)
{
    char*       it  = (char*)memory;
    const char* End = &it[size];
    for(; it != End ; ++it) *it = (char)c;
    return memory;
}

int QUEX_STD(memcmp)(const void *s1, const void *s2, size_t size)
{
    const char* it1 = (const char*)s1;
    const char* it2 = (const char*)s2;
    const char* End = &it1[size];
    while( it1 != End && *it1 == *it2 ) {
        ++it1; ++it2;
    }
    return *it1 - *it2;
}

int QUEX_STD(strcmp)(const char *s1, const char *s2)
{
    const char* it1 = (const char*)s1;
    const char* it2 = (const char*)s2;
    while( *it1 && *it1 == *it2 ) {
        ++it1; ++it2;
    }
    return *it1 - *it2;
}

char* QUEX_STD(strcpy)(char *destination, const char *source)
{
    const char* read_it = (const char*)source;
    char*       write_it = (char*)destination;
    for(; *read_it ; ++read_it, ++write_it) {
        *write_it = *read_it;
    };
    *write_it = *read_it;
    return destination;
}

size_t QUEX_STD(strlen)(const char *s)
{
    const char* it;
    for(it = s; *it ; ++it);
    return (size_t)(it - s);
}

void QUEX_STD(memmove)(void* destination, const void* source, size_t size)
/* Default memory copy where regions may overlap, if standard library is 
 * not available. There is no claim that this is an optimal solution.         */
{
    const char* read_it        = (const char*)source;
    char*       write_it       = (char*)destination;
    const char* SourceBefore   = &read_it[-1];
    const char* SourceEnd      = &read_it[size];
    char*       DestinationEnd = &write_it[size];

    if( destination < source ) {
        /* Copy from front to back */
        for(; read_it != SourceEnd; ++read_it, ++write_it) {
            *write_it = *read_it;
        }
    }
    else if( destination != source ) {
        /* Copy from back to front */
        read_it  = SourceEnd;
        write_it = DestinationEnd;
        --read_it; --write_it; 
        while( read_it != SourceBefore ) {
            *write_it = *read_it;
            --read_it; --write_it; 
        } 
    }
}

typedef struct {
    QUEX_STD(MemoryBlock)*  begin_p;
    QUEX_STD(MemoryBlock)*  end_p;
    struct {
        QUEX_STD(MallocStatistic_calls) calls;
        struct {
            size_t free_n;
            size_t allocated_n;
            size_t allocated_n_watermark;
        } chunks;
    } statistics;
} self_MemPool;

static char self_MemPool_object[sizeof(self_MemPool)];

/* Initialization is detected by 'self_pool != 0'                             */
static self_MemPool* self_pool = (self_MemPool*)0;

#define self_MemGranularity      sizeof(QUEX_STD(MemoryBlock))
#define self_MemByteNToBlockN(N) (((N) % self_MemGranularity == 0) ? (N) / self_MemGranularity \
                                                                   : (N) / self_MemGranularity + 1)
#define self_foreach_region(it)  for((it) = self_pool->begin_p; (it) != self_pool->end_p ; (it) += (it)->dnext) 


void
QUEX_STD(stdlib_init)(void* memory, size_t ByteN)
/* Initializes the static memory pool manager. This function needs to be called
 * implicitly. Any OS-independent singleton implementation would potentially
 * inhibit problems with racing conditions at program start-up.               */
{
    QUEX_STD(MemoryBlock)*  array   = (QUEX_STD(MemoryBlock)*)memory;
    const ptrdiff_t block_n = ByteN / self_MemGranularity;

    self_pool = block_n ? (self_MemPool*)&self_MemPool_object : (self_MemPool*)0;

    self_pool->begin_p = &array[0];
    self_pool->end_p   = &array[block_n];
    self_pool->begin_p[0].dnext  = self_pool->end_p - self_pool->begin_p;
    self_pool->begin_p[0].free_f = true;
    self_pool->statistics.calls.malloc_n = (size_t)0;
    self_pool->statistics.calls.malloc_failure_n = (size_t)0;
    self_pool->statistics.calls.malloc_search_step_n_total = (size_t)0;
    self_pool->statistics.calls.malloc_search_step_n_watermark = (size_t)0;
    self_pool->statistics.calls.free_n = (size_t)0;
    self_pool->statistics.calls.realloc_n = (size_t)0;
    self_pool->statistics.calls.realloc_failure_n = (size_t)0;
    self_pool->statistics.chunks.free_n = (size_t)0;
    self_pool->statistics.chunks.allocated_n = (size_t)0;
    self_pool->statistics.chunks.allocated_n_watermark = (size_t)0;
}

static void  self_MemPool_statistic_add(ptrdiff_t AddedBlockN, size_t SearchStepN);

void * QUEX_STD(malloc)(size_t size)
/* Allocates 'size' bytes of memory and returns a pointer pointing to the first 
 * byte. The returned pointer may later be passed to 'free()' when it is no 
 * longer needed.
 *
 * RETURNS: Pointer to allocated memory, in case of success.
 *          NULL, if 'size=0' or in case of failure.
 *
 * Further, in case of failure 'errno' (thread-safe) is set to ENOMEM.       */
{
    QUEX_STD(MemoryBlock)*  it     = NULL;
    QUEX_STD(MemoryBlock)*  result = NULL;
    const ptrdiff_t BlockN = self_MemByteNToBlockN(size);
    size_t          search_step_n = 0;

    if( size == 0 ) return (void*)NULL;

    ++(self_pool->statistics.calls.malloc_n);
                                  
    /* Find a region that is large enough to deliver 'BlockN'.                */
    self_foreach_region(it) {
        ++search_step_n;

        if( ! it->free_f ) continue;
        else if( it->dnext - 1 < BlockN ) continue;

        /* Assumption: Requested size is much greater than the free size.
         * => Take the smaller end, so that the huge part remains in front.
         * => Requests are fulfilled immediately.                             */
        result = &it[it->dnext-BlockN-1];
        result->free_f = false;
        if( result != it ) {
            result->dnext  = BlockN + 1;
            it->dnext     -= BlockN + 1;
        }
        self_MemPool_statistic_add((ptrdiff_t)BlockN, search_step_n);
        return (void*)&result[1];
    }

    ++(self_pool->statistics.calls.malloc_failure_n);
    self_MemPool_statistic_add((ptrdiff_t)0, search_step_n);
    errno = ENOMEM;
    return (void*)NULL;
}

void * QUEX_STD(calloc)(size_t size)
/* Allocates memory as 'malloc()' does but initializes it to zero. 
 *
 * RETURNS: Pointer to allocated memory, in case of success.
 *          NULL, if 'size=0' or in case of failure.
 *
 * Further, in case of failure 'errno' (thread-safe) is set to ENOMEM.       */
{
    void* result = QUEX_STD(malloc)(size);
    if( ! result ) return (void*)0; /* 'malloc()' has set 'errno' */
    QUEX_STD(memset)(result, 0, size);
    return result;
}

void QUEX_STD(free)(void *p)
/* Frees the memory pointed to by 'p'. When a null pointer is passed, no
 * operation is performed.  The memory must have been allocated by 'malloc()',
 * 'calloc()', or 'realloc()' of this library. According the standard, if
 * undefined behavior may occur, if a pointer is passed twice, or if it is
 * not allocated as required. This implemention checks, if the pointer comes
 * from the memory chunk that is managed and returns undone, if it is alien.  */
 {
    QUEX_STD(MemoryBlock)* it     = &((QUEX_STD(MemoryBlock)*)p)[-1];
    QUEX_STD(MemoryBlock)* previous;

    ++(self_pool->statistics.calls.free_n);

    if(    ! p 
        || (QUEX_STD(MemoryBlock)*)p < self_pool->begin_p 
        || (QUEX_STD(MemoryBlock)*)p >= self_pool->end_p ) {
        return;
    }

    self_MemPool_statistic_add((ptrdiff_t)(- (it->dnext - 1)), (size_t)0);

    it->free_f = true;

    previous = QUEX_STD(malloc_region_get_predecessor)(it);

    /* Combine with previous and next region if they are free                 */
    if( &it[it->dnext] != self_pool->end_p && it[it->dnext].free_f ) {
        it->dnext += it[it->dnext].dnext;
    }
    if( previous && previous->free_f ) {
        previous->dnext += it->dnext;
    }
}

void* QUEX_STD(realloc)(void *p, size_t size)
/* Changes the size of the memory pointed to by 'p' to size bytes.  The contents
 * of the original region remain unchanged, as far as the new size allows for it.
 * New memory is not initialized.  If 'p' is NULL, then the call is equivalent to
 * malloc(size), except for size=0. If size=0, and 'p' unequal to NULL, then the 
 * call is equivalent  to free('p').   A 'p' different from NULL must have been 
 * produced by either 'malloc()' or 'calloc()'. 
 * 
 * If a region is extended to a lower region, memory is only moved and the new
 * pointer is returned.  Only if a completely new region is found, a call to
 * 'free()', 'malloc()', and 'memcpy()' is done. 
 * 
 * RETURNS: Pointer to memory of given size with old content.
 *          NULL, else.                                                       */
{
    const ptrdiff_t         BlockN   = self_MemByteNToBlockN(size);
    QUEX_STD(MemoryBlock)*  it       = &((QUEX_STD(MemoryBlock)*)p)[-1];
    QUEX_STD(MemoryBlock)*  previous = (QUEX_STD(MemoryBlock)*)0;
    void*                   new_p    = (void*)0;
    ptrdiff_t               combined_size;
    ptrdiff_t               addition = BlockN + 1 - it->dnext;

    ++(self_pool->statistics.calls.realloc_n);

    if( ! p ) {
        return QUEX_STD(malloc)(size);
    }
    else if( (QUEX_STD(MemoryBlock)*)p < self_pool->begin_p || (QUEX_STD(MemoryBlock)*)p >= self_pool->end_p ) {
        errno = ENOMEM;
        return (void*)0;
    }
    else if( it->dnext - 1 == BlockN ) {
        return p;
    }
    else if(    &it[it->dnext]                      != self_pool->end_p 
             && it[it->dnext].free_f                == true
             && it->dnext + it[it->dnext].dnext - 1 >=  BlockN ) {
        /* Cut memory from the immediately following region                   */
        combined_size = it->dnext + it[it->dnext].dnext;
    }
    else {
        previous = QUEX_STD(malloc_region_get_predecessor)(it);
        if( previous && previous->free_f && previous->dnext + it->dnext - 1 >= BlockN ) {
            combined_size = previous->dnext + it->dnext;
            QUEX_STD(memmove)(&it[1], &previous[1], it->dnext);
            it = previous;
        }
        else { 
            ++(self_pool->statistics.calls.realloc_failure_n);
            new_p = ((QUEX_STD(MemoryBlock)*)QUEX_STD(malloc)(BlockN*QUEX_STD(MemoryGranularity)));
            if( ! new_p ) return (void*)0; /* 'malloc' has set 'errno' already. */
            QUEX_STD(memcpy)(new_p, p, BlockN*QUEX_STD(MemoryGranularity));
            QUEX_STD(free)(p);
            return new_p;
        }
    }
    if( BlockN == combined_size - 1) {
        it->dnext = combined_size;
    }
    else {
        it->dnext            = (BlockN + 1);
        it[it->dnext].dnext  = combined_size - it->dnext;
        it[it->dnext].free_f = true;
    }
    it->free_f = false;
    self_MemPool_statistic_add(addition, (size_t)0);
    return (void*)&it[1];
}

void QUEX_STD(MallocStatistic_get)(QUEX_STD(MallocStatistic)* s)
{
    QUEX_STD(MemoryBlock)*             it;
    QUEX_STD(MallocStatistic_regions)* region;
    size_t                             size;
    size_t                             G = self_MemGranularity;

    s->calls = self_pool->statistics.calls;

    s->granularity_in_byte        = G;
    s->allocated_byte_n           = G * self_pool->statistics.chunks.allocated_n;
    s->allocated_byte_n_watermark = G * self_pool->statistics.chunks.allocated_n_watermark;
    s->free_byte_n                = 0;

    s->free_regions.n = 0;
    s->free_regions.largest_size_in_byte = 0;
    s->free_regions.smallest_size_in_byte = SIZE_MAX;
    s->allocated_regions.n = 0;
    s->allocated_regions.largest_size_in_byte = 0;
    s->allocated_regions.smallest_size_in_byte = SIZE_MAX;

    self_foreach_region(it) {
        size = (size_t)(it->dnext - 1) * G;

        if( it->free_f ) { 
            ++s->free_regions.n;      
            s->free_byte_n += size;
            region = &s->free_regions; 
        }
        else { 
            ++s->allocated_regions.n; 
            region = &s->allocated_regions; 
        }
        
        if( size > region->largest_size_in_byte )  region->largest_size_in_byte = size;
        if( size < region->smallest_size_in_byte ) region->smallest_size_in_byte = size;
    }

    if( s->free_regions.smallest_size_in_byte == SIZE_MAX ) {
        s->free_regions.smallest_size_in_byte = 0;
    }
    if( s->allocated_regions.smallest_size_in_byte == SIZE_MAX ) {
        s->allocated_regions.smallest_size_in_byte = 0;
    }
}

static void 
self_MemPool_statistic_add(ptrdiff_t AddedBlockN, size_t SearchStepN)
{
    QUEX_STD(MallocStatistic_calls)*  calls  = &self_pool->statistics.calls;

    self_pool->statistics.chunks.allocated_n += AddedBlockN;
    if( self_pool->statistics.chunks.allocated_n > self_pool->statistics.chunks.allocated_n_watermark ) {
        self_pool->statistics.chunks.allocated_n_watermark = self_pool->statistics.chunks.allocated_n;
    }
    if( SearchStepN ) {
        calls->malloc_search_step_n_total += SearchStepN;
        if( SearchStepN > calls->malloc_search_step_n_watermark ) {
            calls->malloc_search_step_n_watermark = SearchStepN;
        }
    }
}

static QUEX_STD(MemoryBlock)* 
QUEX_STD(malloc_region_get_predecessor)(QUEX_STD(MemoryBlock)* it) 
{
    QUEX_STD(MemoryBlock)* previous;
    if( it == self_pool->begin_p ) {
        previous = NULL;
    }
    else {
        for(previous = self_pool->begin_p; previous + previous->dnext != it; previous += previous->dnext ) {
            if(previous + previous->dnext > it) {
                return NULL; /* error */
            }
        }
    }
    return previous;
}

#ifdef QUEXLIB_OPTION_PRINT_POOL_EXT
#include<stdio.h>
void
QUEX_STD(MallocStatistic_print_pool)(void)
{
    QUEX_STD(MemoryBlock)* it;
    ptrdiff_t              i;
    ptrdiff_t              size;
    int                    region_i = 0;
    printf("|");
    self_foreach_region(it) {
        size = (size_t)(it->dnext - 1);
        printf("%i:", region_i); 
        for(i=1;i<size;++i) printf("%c.", it->free_f ? ' ' : 'x');
        if( size ) {
            printf("%c%c", 
                   it->free_f ? ' ' : 'x',
                   &it[it->dnext] == self_pool->end_p ? '|' : ':');
        }
        ++region_i;
    }
}
#endif /* QUEXLIB_OPTION_PRINT_POOL_EXT */

#ifdef QUEXLIB_OPTION_ERRNO_EXT
#define ENOMEM  12
#if ! defined(GCC) && defined(GCC_VERSION)
int errno;
#else
__thread int errno;
#endif
#endif

QUEX_NAMESPACE_QUEX_STDLIB_CLOSE


#endif /* QUEX_INCLUDE_GUARD__QUEX__TINY_STDLIB_I */
