Struct
--------------------------------------------------------------------------

This directory contains files concerned with:

    * construction: The setup of a lexical analyzer object so that
             the engine is ready to start analyzing a specific input.

    * reset: The release of the current input and its related data
             structures. Then, the analyzer is setup to start with 
             a new, or the same, input. The state of the previous
             input is completely dropped.

    * inclusion: The setup of the current input is stored on a stack as
             a 'nesting input'. Then, the analyzer is setup to start from 
             a new input. Inputs may nest recursively other inputs. Once
             an input terminates, the lexical analyzer state is reset
             to its state before the inclusion.

To handle these cases, an important assumption must be made:

 .----------------------------------------------------------------------------.
 |  The OWNERSHIP of the objects passed to these procedures is passed to the  |
 |  analyzer objects! That means, the the user is not responsible for         |
 |  destruction and freeing of associated memory!                             |
 '----------------------------------------------------------------------------'

All of these deal with the setup of a lexical analyzer object. The API for the
related operations was designed to follow a homogeneous scheme. It should allow
easy handling for the standard case. The level of required detail knowledge
increases with the deviation from what is considered the most expected use
case. 

A lexical analyzer runs on a content presented in a chunk of memory. This way
it can be accessed quickly. If the engine's codec differs from the codec of the
input stream it must be converted. The general concept of buffer filling
performs this task. Depending on the platform, files or streams are accessed in
different manners. To cope with different operating systems and platforms, the
byte loading is abstracted through a byte loader class. Figure one depicts
the entities related to buffer filling.

   file, stream,      .------------.      .--------------.     .--------.
   message, or   <--->| QUEX_GNAME_LIB(ByteLoader )|<---->| LexatomLoader |---->| Buffer |
   signal, etc.       '------------'      '--------------'     '--------'
                        <File API>          <Conversion>       <Analysis>

               Figure 1: Filling the engine's buffer.

The lexical analyzer's engine is generated and its output is determined by the
user defined reaction to matching patterns. What remains to be discussed is the
control over the input.  The specification of the engine's input happens at
construction time, when a file or stream is 'included', or upon reset. The
sections below show the homogeneous design for dealing with these three
scenarios.

Construction
============

The most common way to identify an input is considered to be the name of a
file.  Thus, there should be a way to construct a lexical analyzer from a file
name.  Additionally, a conversion codec may be specified which defines a
character conversion before parsing. Internally, the most expected file handle
type ``FILE`` is used to access the file with the given name. The abstracted
loader interface is therefore ``QUEX_GNAME_LIB(ByteLoader_FILE)`` nesting the opened file
handle.  Together with the conversion codec's name a
``LexatomLoader_Conversion`` or a ``LexatomLoader_Plain`` can be constructed.
This object is then used to fill the buffer. 

                       
                  .-------------------. (1)
   input name --->| handle associated |
   handle type -->| with input        |
                  '-------------------'
                          | input handle
                          |
                  .-----------------.   (2)
                  |   Byte loader   |
                  |   object        |
                  '-----------------'
                          | byte loader
                          |
                  .-----------------.   (3)
    conversion -->|  Buffer Filler  |                 memory
    codec         '-----------------'              specification
                          |                             |
                          |                             |
                  .------------------.  (4)   .---------------------. (5)
                  | filling approach |        |  pointing approach  |
                  '------------------'        '---------------------'
                          |                             |
                          '-----------.   .-------------'
                                    remaining           
                                   construction


         Figure 2: Constructor interfaces depending on the required
                   level of detail knowledge.

The constructor in C++ for level (1) is 

            X(FileName, CodecName);

If a specific input handle is to be used, for which a byte loader already exists
it may be used and the construction process may be entered at level (2). The
constructors for that are

           X(FILE*, CodecName);               // Standard C Library
           X(int, CodecName);                 // POSIX File Handles
           X(std::istream*, CodecName);       // Standard C++ Library
           X(std::wistream*, CodecName);      // Standard C++ Library   

In case, there is no byte loader class that fits the user's environment,
byte loader may be derived from 'QUEX_GNAME_LIB(ByteLoader)'. An object of this type
may then be passed to the constructor of level (3).

           X(QUEX_GNAME_LIB(ByteLoader)*, CodecName);

Examples for dedicated QUEX_GNAME_LIB(ByteLoaders), i.e. derived classes from it may be
observed in the definitions of 'QUEX_NAME(QUEX_GNAME_LIB(ByteLoader_FILE))', 'ByteLoader_stream',
'QUEX_NAME(QUEX_GNAME_LIB(ByteLoader_POSIX))', or 'ByteLoader_FreeRTOS'. A customized byte loader
derived from 'QUEX_GNAME_LIB(ByteLoader)' may then be used as input to the
aforementioned constructor.

Depending on the conversion codec name, a LexatomLoader object is constructed.
If the CodecName = 0, no conversion is applied and the 'LexatomLoader_Plain'
is used. Else, the default conversion library is used to construct a 
'LexatomLoader_Converter'. If a dedicated LexatomLoader is required, for example,
if the raw buffer size needs to be manually configured, then the constructor
for level (4) needs to be called with an object derived from 'LexatomLoader'.

    X(LexatomLoader*);

A dedicated buffer filler can be constructed by

    QUEX_INLINE X_LexatomLoader*
    X_LexatomLoader_new(byte_loader, 
                       QUEX_GNAME_LIB(Converter)* (*converters_new)(void),
                       CodecName,
                       TranslationBufferSize,
                       ByteOrderReversionF)

Where 'converters_new' may either point to the allocator for an ICU or Iconv
converter, or a customized converter. Converters must be derived from
'Converter'.  The implementations of 'Converter_ICU' and 'Converter_IConv' may
serve as a template for customized solutions. Also, with the above allocator
the size of the translation buffer may be chosen independently from
QUEX_SETTING_LEXATOM_LOADER_CONVERTER_BUFFER_SIZE.

Quex allows also analyzers running on memory where the user points to. 
In that case, it is assumed that the user takes care of all filling. The
LexatomLoader remains a pointer to ``NULL``. The constructor to be used
is 

    X(MemoryBegin, MemorySize, EndOfContentP); 

The construction of additional content happens below the constructors of 
level (4) and (5). For completeness let the constructors of each level
also be mentioned for the 'C' implementation. The level (1)
constructor is

    X_from_file_name)(me, FileName, CodecName)

The level (2) interfaces are

    X_from_FILE(me, FILE*, CodecName);             // Standard C Library
    X_from_POSIX(me, int, CodecName);              // POSIX File Handles

The level (3) interface is

    X_from_QUEX_GNAME_LIB(ByteLoader)(byte_loader, CodecName)

The level (4) interface is

    X_from_LexatomLoader(me, buffer_filler)

The level (5) interface is 

    X_from_memory(me, Memory, MemorySize, EndOfFileP)

Reset
=====

A reset terminates the treatment of on input in favor of another, or the same
input from the beginning. C++ Interfaces are:

    x.reset(FileName, CodecName)                          // Level (1)
                                                           
    x.reset(FILE*, CodecName);                            // Level (2)
    x.reset(int, CodecName);                               
    x.reset(std::istream*, CodecName);                     
    x.reset(std::wistream*, CodecName);                    
                                                           
    x.reset(QUEX_GNAME_LIB(ByteLoader)*, CodecName);                      // Level (3)
                                                           
    x.reset(LexatomLoader*)                                // Level (4)

    x.reset(MemoryBegin, MemorySize, EndOfContentP);      // Level (5)

The according 'C' functions are 

    X_reset_file_name(me, FileName, CodecName)     // Level (1)
                                                            
    X_reset_FILE(me, FILE*, CodecName);            // Level (2)
    X_reset_POSIX(me, int, CodecName);                                    
                                                            
    X_reset_QUEX_GNAME_LIB(ByteLoader)(me, QUEX_GNAME_LIB(ByteLoader)*);           // Level (3)
                                                            
    X_reset_LexatomLoader(me, LexatomLoader*);       // Level (4)

    X_reset_memory(me, MemoryBegin, MemorySize,    // Level (5)
                   EndOfContentP); 


Inclusion
=========

Inclusion is understood as the process of redirecting the analyzer to another
input source triggered by something in the input stream. In 'C/C++' the
inclusion happens by means of the '#include' directive. When the new input is
considered, the state of the analyzer is stored in a memento structure.  When
the included content is treated, it returns to the original file and the
analyzer's state is restored from the memento. The specification of the
included content follows the same 5-level scheme as for construction.
Thus, on level (1) a file may be included by

    x.include_push(FileName, CodecName)

On level (2), an input specified by other input handles may included by

    x.include_push(FILE*, CodecName);               // Standard C Library
    x.include_push(int, CodecName);                 // POSIX File Handles
    x.include_push(std::istream*, CodecName);       // Standard C++ Library
    x.include_push(std::wistream*, CodecName);      // Standard C++ Library   

A dedicated QUEX_GNAME_LIB(ByteLoader )can be specified on level (3) by

    x.include_push(QUEX_GNAME_LIB(ByteLoader)*, CodecName)

A dedicated LexatomLoader can be passed to the level (4) function

    x.include_push(LexatomLoader*)

Some external memory that is to be used as included input may be specified
by the level (5) function

    x.include_push(MemoryBegin, MemorySize, EndOfContentP); 

The according 'C' functions are 

    X_include_push_file_name(me, FileName, CodecName)     // Level (1)
                                                            
    X_include_push_FILE(me, FILE*, CodecName);            // Level (2)
    X_include_push_POSIX(me, int, CodecName);                                    
                                                            
    X_include_push_QUEX_GNAME_LIB(ByteLoader)(me, QUEX_GNAME_LIB(ByteLoader)*);           // Level (3)
                                                            
    X_include_push_LexatomLoader(me, LexatomLoader*);       // Level (4)

    X_include_push_memory(me, MemoryBegin, MemorySize,    // Level (5)
                          EndOfContentP); 

