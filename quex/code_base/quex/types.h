/* PURPOSE: Definition of basic data types (integers, bool, sizes)
 *
 * For the standard reference, please review: "The Open Group Base 
 * Specifications Issue 6, IEEE Std 1003.1, 2004 Edition".
 *
 * (C) 2008-2019  Frank-Rene Schaefer                                         */           
#ifndef QUEX_INCLUDE_GUARD__QUEX__TYPES_H
#define QUEX_INCLUDE_GUARD__QUEX__TYPES_H

/* Boolean Values ("stdbool.h") ________________________________________________
 *                                                                            */
$$<C && std-lib >---------------------------------------------------------------
#if    (defined(__STDC_VERSION__) && __STDC_VERSION__ < 199901L) \
    || (defined(_MSC_VER)         && _MSC_VER < 1800) 

   /* Helper definition for the case that the compiler distribution does not
    * provide 'stdbool.h'.                                                    */
#  if ! defined(__bool_true_false_are_defined)
      typedef int _Bool;
#     define bool  _Bool
#     define true  ((_Bool)1)
#     define false ((_Bool)0)
#     define __bool_true_false_are_defined ((int)(1))
#  endif

#else
   /* Include fails => compiler distribution does not provide 'stdbool.h'.
    * Use helper definitions above (and report problem, so that special
    * case can be included in later versions of Quex).                        */
#  include <stdbool.h>
#endif
$$-----------------------------------------------------------------------------
$$<C && not-std-lib >----------------------------------------------------------
#  if ! defined(__bool_true_false_are_defined)
      typedef int _Bool;
#     define bool  _Bool
#     define true  ((_Bool)1)
#     define false ((_Bool)0)
#     define __bool_true_false_are_defined ((int)(1))
#  endif
$$-----------------------------------------------------------------------------

/* Integer Types ("stdint.h"/"inttypes.h") ____________________________________
 *                                                                           */
$$<Cpp> extern "C" {$$
#if defined (_MSC_VER)
$$INC:<std-lib> quex/compatibility/msc_stdint.h$$
#elif defined(__BORLANDC__)
$$INC:<std-lib> quex/compatibility/borland_stdint.h$$
#elif defined(__sun) && defined(__sparc)
$$<std-lib>---------------------------------------------------------------------
#   include <inttypes.h>  
$$------------------------------------------------------------------------------
#else
$$<std-lib>---------------------------------------------------------------------
#   include <stdint.h>
$$------------------------------------------------------------------------------
#endif
$$<Cpp> }$$

$$<not-std-lib>-----------------------------------------------------------------
/* The following definitions are guesses. Since the standard headers are not
 * available (--no-std-lib), all size types need to be defined manually.      
 *
 * Use compile options of the form '-DQUEXLIB_uint32_t=someU8' to customize
 * the definition of integer types.                                           */
#ifndef   QUEXLIB_uint8_t
#  define QUEXLIB_uint8_t   unsigned char
#endif
#ifndef   QUEXLIB_int8_t
#  define QUEXLIB_int8_t    signed char
#endif
#ifndef   QUEXLIB_uint16_t
#  define QUEXLIB_uint16_t  unsigned short
#endif
#ifndef   QUEXLIB_int16_t
#  define QUEXLIB_int16_t   signed short
#endif
#ifndef   QUEXLIB_uint32_t
#  define QUEXLIB_uint32_t  unsigned int
#endif
#ifndef   QUEXLIB_int32_t
#  define QUEXLIB_int32_t   signed int
#endif
#ifndef   QUEXLIB_uint64_t
#  define QUEXLIB_uint64_t  unsigned long
#endif
#ifndef   QUEXLIB_int64_t
#  define QUEXLIB_int64_t   signed long
#endif
#ifndef   QUEXLIB_intmax_t
#  define QUEXLIB_intmax_t  int64_t
#endif
typedef QUEXLIB_uint8_t     uint8_t;
typedef QUEXLIB_int8_t      int8_t;
typedef QUEXLIB_uint16_t    uint16_t;
typedef QUEXLIB_int16_t     int16_t;
typedef QUEXLIB_uint32_t    uint32_t;
typedef QUEXLIB_int32_t     int32_t;
typedef QUEXLIB_uint64_t    uint64_t;
typedef QUEXLIB_int64_t     int64_t;
typedef QUEXLIB_intmax_t    intmax_t;
$$-----------------------------------------------------------------------------

$$<Cpp && std-lib>-------------------------------------------------------------
#   include <cstddef>
$$-----------------------------------------------------------------------------
$$<C && std-lib>---------------------------------------------------------------
#   include <stddef.h>
$$-----------------------------------------------------------------------------
$$<not-std-lib>----------------------------------------------------------------
#ifndef   QUEXLIB_ptrdiff_t
#  define QUEXLIB_ptrdiff_t signed long
#endif
#ifndef   QUEXLIB_size_t
#  define QUEXLIB_size_t    signed long
#endif
typedef QUEXLIB_ptrdiff_t   ptrdiff_t;
typedef QUEXLIB_size_t      size_t;
#define   PTRDIFF_MAX       (((size_t)1) << (sizeof(ptrdiff_t) - 1))
#define   SIZE_MAX          (((size_t)1) << sizeof(size_t))
$$-----------------------------------------------------------------------------

$$<   not-std-lib> typedef intmax_t       QUEX_TYPE_STREAM_POSITION;$$
$$<   not-std-lib> typedef intmax_t       QUEX_TYPE_STREAM_OFFSET;$$
$$<C   && std-lib> typedef long           QUEX_TYPE_STREAM_POSITION;$$
$$<C   && std-lib> typedef long           QUEX_TYPE_STREAM_OFFSET;$$
$$<Cpp && std-lib> #include <iostream>$$
$$<Cpp && std-lib> typedef std::streampos QUEX_TYPE_STREAM_POSITION;$$
$$<Cpp && std-lib> typedef std::streamoff QUEX_TYPE_STREAM_OFFSET;$$

#endif /* QUEX_INCLUDE_GUARD__QUEX__TYPES_H                                   */

