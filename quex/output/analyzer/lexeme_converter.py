# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
"""PURPOSE: Converters: Lexemes towards encodings UTF8/UTF16/UTF32.

During exical analysis matches delivers lexemes in the encoding of the buffer.
The functions develops converters of those lexemes to standard encodings, so 
that they can easily be reflected.

Let 'Character' be a character in the buffer's encoding, 'Unicode' its 
correspondance in UCS, and 'Code Sequence' be 'Unicode'-s representation
in the target encoding (be it UTF8, UTF16, or UTF32). Then the process
of conversion of a 'Character' to the target encoding can be described 
by two steps

        (1) Unicode = Character +/- offset.
        (2) Code Sequence = f(Unicode)

Where the range of 'Character' is split into contigous regions where 'offset'
and the 'f(Unicode)' is the same. Thus, the character conversion is preceeded
by a search of the range in which it belong.

(C) 2006-2017 Frank-Rene Schaefer
"""
import os
import sys
sys.path.append(os.environ["QUEX_PATH"])
from   quex.engine.misc.string_handling                     import blue_print
from   quex.engine.misc.interval_handling                   import Interval
from   quex.engine.misc.tools                               import typed
import quex.engine.misc.error                               as     error
from   quex.engine.state_machine.transformation.state_split import EncodingTrafoBySplit
import quex.output.core.state.transition_map.core           as     transition_map

from   quex.blackboard import setup as Setup, \
                              Lng
from   quex.constants  import INTEGER_MAX

from   operator import attrgetter
from   copy     import copy

def do():
    """RETURNS: list of (content, file_name)

       where 'content' is the content to be written into 'file_name'.
    """
    if not Setup.converter_only_f:
        source_name = "lexeme"
    else:
        if Setup.converter_source_name: source_name = Setup.converter_source_name
        else:                           source_name = Setup.buffer_encoding.name

    header_txt         = Lng.template_converter_header()
    implementation_txt = blue_print(Lng.template_converter_implementation(), [
                                    ("$$CONVERTER_HEADER$$",     Lng.file_name_converter_header(source_name)),
                                    ("$$CHARACTER_CONVERTERS$$", _character_converters()),
                                    ("$$STRING_CONVERTERS$$",    _string_converters())])

    if Setup.converter_only_f:
        implementation_txt = implementation_txt.replace("QUEX_TYPE_LEXATOM", 
                                                        Setup.lexatom.type)
        implementation_txt = implementation_txt.replace("QUEX_INLINE",
                                                        Lng.INLINE)
        implementation_txt = Lng.Match_QUEX_NAME_lexeme.sub("QUEX_NAME(%s_" % source_name, 
                                                            implementation_txt)
        header_txt         = header_txt.replace("QUEX_TYPE_LEXATOM", 
                                                Setup.lexatom.type)
        header_txt         = header_txt.replace("QUEX_INLINE",
                                                Lng.INLINE)
        header_txt         = Lng.Match_QUEX_NAME_lexeme.sub("QUEX_NAME(%s_" % source_name, 
                                                            header_txt)

    return [
        (header_txt,         Lng.file_name_converter_header(source_name)), 
        (implementation_txt, Lng.file_name_converter_implementation(source_name)),
    ] 

def _character_converters():
    if isinstance(Setup.buffer_encoding, EncodingTrafoBySplit):
        encoding_name = Lng.SAFE_IDENTIFIER(Setup.adapted_encoding_name())
        return Lng.template_converter_character_functions_standard(encoding_name)
    else:
        return _table_character_converters(Setup.buffer_encoding)

def _string_converters():
    drain_encoding_list = [
        ("utf8",  "uint8_t",  4),
        ("utf16", "uint16_t", 2),
        ("utf32", "uint32_t", 1),
        ("char",        "char",  4),
        ("pretty_char", "char",  4),
        ("wchar_t",     "wchar_t",  4)
    ]

    string_template = Lng.template_converter_string_functions()

    def prepare(template, name, code_unit_type, max_code_unit_n):
        result = blue_print(string_template, [
            ["$$DRAIN_ENCODING$$",                 name],
            ["$$DRAIN_CODE_UNIT_TYPE$$",           code_unit_type],
            ["$$DRAIN_ENCODING_MAX_CODE_UNIT_N$$", str(max_code_unit_n)],
        ])
        if name == "wchar_t":
            result = "\n".join([
                "#if ! defined(QUEX_OPTION_WCHAR_T_DISABLED_EXT)",
                result,
                "#endif"
            ])
        return result

    txt = [
        prepare(string_template, name, code_unit_type, max_code_unit_n)
        for name, code_unit_type, max_code_unit_n in drain_encoding_list
    ]

    return "\n".join(txt)

def _table_character_converters(unicode_trafo_info):
    """
    PURPOSE: Writes converters for conversion towards UTF8/UTF16/UCS2/UCS4.

    UnicodeTrafoInfo:

       Provides the information about the relation of character codes in a particular 
       coding to unicode character codes:

               # Codec Values                 Unicode Values
               [ 
                 (Source0_Begin, Source0_End, TargetInterval0_Begin), 
                 (Source1_Begin, Source1_End, TargetInterval1_Begin),
                 (Source2_Begin, Source2_End, TargetInterval2_Begin), 
                 ... 
               ]

    """
    encoding_name = Lng.SAFE_IDENTIFIER(unicode_trafo_info.name)
    if encoding_name in ("utf32", "unicode"):
        source_interval_begin = 0
        lexatom_size_in_byte  = Setup.lexatom.size_in_byte
        if lexatom_size_in_byte == -1: lexatom_size_in_byte = 4
        source_interval_end   = min(256**lexatom_size_in_byte, 0x200000)
        target_interval_begin = 0
        unicode_trafo_info    = [
            (source_interval_begin, source_interval_end, target_interval_begin)
        ]

    utf8_function_body  = ConverterWriterUTF8().do(unicode_trafo_info)
    utf16_function_body = ConverterWriterUTF16().do(unicode_trafo_info)
    utf32_function_body = ConverterWriterUTF32().do(unicode_trafo_info)

    return blue_print(Lng.template_converter_character_functions(), [
                        ["$$BODY_UTF8$$",  utf8_function_body],
                        ["$$BODY_UTF16$$", utf16_function_body],
                        ["$$BODY_UTF32$$", utf32_function_body]])

class ConversionInfo:
    """A given interval in the character encoding corresponds to a certain byte 
       formatting range in the target encoding, where all bytes are formatted 
       the same way.
         
         -- The codec interval is determined by:      
              .codec_interval_begin
              .codec_interval_size
         
         -- The byte formatting range is determined by its index.
              .code_unit_n

         -- In order to know where to start, the unicode offset that corresponds 
            to the codec interval must be specified:
              .codec_interval_begin_unicode

       Figure:

              Source Codec
                              ci_begin       
                              |
              ................[xxxxxxxxxxxxxxx]................
                              |--- ci_size -->|


              belongs to


              Unicode    |<----          byte formatting range         ---->|
                                                                             
                         |                           |--- ci_size-->|       |
              ...........[+++++++++++++++++++++++++++|xxxxxxxxxxxxxx|++++++][
                                                     |
                                                     ci_begin_unicode
                                                      

       The codec interval always lies inside a single utf8 range.
    """
    def __init__(self, CodeUnitN, CI_Begin_in_Unicode, CI_Begin, CI_Size=-1):
        self.code_unit_n                  = CodeUnitN
        self.codec_interval_begin         = CI_Begin
        self.codec_interval_size          = CI_Size
        self.codec_interval_begin_unicode = CI_Begin_in_Unicode

    def __repr__(self):
        return "[%i] at %08X: Codec Interval [%X,%X)" % \
               (self.code_unit_n,
                self.codec_interval_begin_unicode,
                self.codec_interval_begin,
                self.codec_interval_begin + self.codec_interval_size)

class ConverterWriter:
    def __init__(self):
        self.code_unit_n_occurrence_set = set([])

    def do(self, UnicodeTrafoInfo, ProvidedConversionInfoF=False):
        """Creates code for a conversion to target encoding according to the conversion_table.
        """
        # 'ProvidedConversionTableF' is only to be used for Unit Tests
        if ProvidedConversionInfoF: conversion_table = UnicodeTrafoInfo
        else:                       conversion_table = self.get_conversion_table(UnicodeTrafoInfo)

        assert all(isinstance(entry, ConversionInfo) for entry in conversion_table)

        # Make sure that the conversion table is sorted
        conversion_table.sort(key=attrgetter("codec_interval_begin"))

        def action(ci):
            return "{ %s %s }" % \
                   (self.get_offset_code(ci),
                    self.jump_to_output_formatter(ci.code_unit_n))

        if len(conversion_table) == 1:
            ci = conversion_table[0]
            txt = [ "    %s" % self.get_offset_code(ci) ]
            txt.extend(self.unicode_to_output(ci.code_unit_n))
                      
        else:
            tm = [
                (Interval(ci.codec_interval_begin, ci.codec_interval_begin + ci.codec_interval_size),
                 action(ci))
                for ci in conversion_table
            ]
            txt = []
            transition_map.do(txt, tm, AssertBorderF=False)
            txt.append(self.unicode_to_output_all_ranges())

        return "\n".join(txt) 

    @typed(Info=ConversionInfo)
    def get_offset_code(self, Info):
        """RETURNS: Code to implement code conversion to UNICODE by adding or
                    subtracting an offset.
        """
        offset = Info.codec_interval_begin_unicode - Info.codec_interval_begin
        return "%s" % Lng.ASSIGN("offset", "(int32_t)(%s)" % offset)

    def get_conversion_table(self, UnicodeTrafoInfo):
        """The UnicodeTrafoInfo tells what ranges in the codec are mapped to 
        what ranges in unicode. The codec (e.g. UTF8/UTF16) has ranges of 
        different byte formatting. 

        This function identifies ranges in the codec that:

              (1) map linearly to unicode
              (2) belong to the same byte format range.

        The result is a list of objects that identify those ranges in the codec
        and their relation to unicode. See definition of class ConversionInfo
        for a detailed description and a nice picture.
        """
        trafo_info  = copy(UnicodeTrafoInfo)
        border_list = self.get_byte_format_range_border_list()
        L           = len(border_list)

        # Sort transform info database according to target range
        result = []
        trafo_info.sort(key=lambda a: a[2])

        # Unicode Transformation Info -- A list of the following:
        for source_interval_begin, source_interval_end, target_interval_begin in trafo_info:

            # How does the target interval has to be split according to utf8-ranges?
            begin_i = 0
            while source_interval_begin >= border_list[begin_i]: 
                begin_i += 1
            begin_i -= 1

            # 'i' now stands on the first utf8_range that touches the source interval
            info = ConversionInfo(begin_i+1, source_interval_begin, target_interval_begin)

            # NOTE: size of target interval = size of source interval
            remaining_size = source_interval_end - source_interval_begin

            for i in range(begin_i, L-1):
                remaining_utf8_range_size = border_list[i+1] - source_interval_begin
                if remaining_utf8_range_size <= 0: break

                info.codec_interval_size  = min(remaining_utf8_range_size, remaining_size)
                ## print i, "%X: %x, %x" % (border_list[i+1], remaining_utf8_range_size, remaining_size)
                result.append(info)

                source_interval_begin  = border_list[i+1] 
                target_interval_begin += info.codec_interval_size
                remaining_size        -= info.codec_interval_size
                i += 1

                if remaining_size <= 0: break
                info = ConversionInfo(i+1, source_interval_begin, target_interval_begin)

            if remaining_size != 0:
                info.codec_interval_size = remaining_size
                result.append(info)

        result.sort(key=attrgetter("codec_interval_begin"))

        return result

    def jump_to_output_formatter(self, CodeUnitN):
        assert CodeUnitN >= 1
        assert CodeUnitN <= 4
        self.code_unit_n_occurrence_set.add(CodeUnitN)
        return Lng.GOTO_STRING("code_unit_n_%i" % CodeUnitN)

    def unicode_to_output_all_ranges(self):
        if max(self.code_unit_n_occurrence_set) > self.max_code_unit_n():
            error.note("The lexer's functionality and robustness IS NOT affected by the following:\n"
                       "Optionally provided helper functions for conversion of lexemes towards\n"
                       "UTF8, UTF16 and UTF32 malfunction in case of usage beyond unicode.\n")

        txt = []
        for code_unit_n in sorted(self.code_unit_n_occurrence_set):
            txt.append(Lng.LABEL_PLAIN("code_unit_n_%i" % code_unit_n))
            txt.extend(self.unicode_to_output(code_unit_n))
        return "\n".join(txt)

    def unicode_to_output(self, CodeUnitN):
        txt = [ Lng.ASSIGN("unicode", "(uint32_t)(%s)" % Lng.OP("(int32_t)input", "+", "offset")) ]
        txt.extend(self.get_output_formatter(CodeUnitN))
        txt.append(Lng.PURE_RETURN)
        return [ "    %s" % line for line in txt ]

class ConverterWriterUTF8(ConverterWriter):

    def max_code_unit_n(self):
        return 4

    def get_output_formatter(self, CodeUnitN):
        last_but_two = Lng.OP("0x80", "|", 
                              "(%s)" % Lng.OP("(%s)" % Lng.OP("unicode", "&", "(uint32_t)0x3FFFF"), 
                                              ">>", "12"))
        last_but_one = Lng.OP("0x80", "|", 
                              "(%s)" % Lng.OP("(%s)" % Lng.OP("unicode", "&", "(uint32_t)0xFFF"), 
                                              ">>", "6"))
        last         = Lng.OP("0x80", "|", 
                              "(%s)" % Lng.OP("unicode", "&", "(uint32_t)0x3F"))

        rvalue_list = {
            1: [
                "unicode",
            ],
            2: [
                Lng.OP("0xC0", "|", "(%s)" % Lng.OP("unicode", ">>", "6")),
                last,
            ],
            3: [
                Lng.OP("0xE0", "|", "(%s)" % Lng.OP("unicode", ">>", "12")),
                last_but_one,
                last,
            ],
            4: [
                Lng.OP("0xF0", "|", "(%s)" % Lng.OP("unicode", ">>", "18")),
                last_but_two,
                last_but_one,
                last,
            ]
        }[CodeUnitN]

        return [ 
            "%s" %  Lng.INCREMENT_ITERATOR_THEN_ASSIGN("*output_pp", "(uint8_t)(%s)" % rvalue) 
            for rvalue in rvalue_list 
        ]

    def get_byte_format_range_border_list(self):
        """UTF8 covers the following regions with the corresponding numbers of bytes:
        
             0x00000000 - 0x0000007F: 1 byte  - 0xxxxxxx
             0x00000080 - 0x000007FF: 2 bytes - 110xxxxx 10xxxxxx
             0x00000800 - 0x0000FFFF: 3 bytes - 1110xxxx 10xxxxxx 10xxxxxx
             0x00010000 - 0x001FFFFF: 4 bytes - 11110xxx 10xxxxxx 10xxxxxx 10xxxxxx
             0x00200000 - 0x03FFFFFF: 5 bytes ... (not for unicode)
             0x04000000 - 0x7FFFFFFF: 

            The range borders are, therefore, as mentioned in the return value.
        """
        return [ 0x0, 0x00000080, 0x00000800, 0x00010000, 0x00200000, 0x04000000, 0x80000000, INTEGER_MAX] 

class ConverterWriterUTF16(ConverterWriter):
    def max_code_unit_n(self):
        return 2

    def get_output_formatter(self, CodeUnitN):
        UnicodeMinus0x10000 = "(%s)" % Lng.OP("unicode", "-", "0x10000")
        Offset_10bit_high = "(uint16_t)(%s)" % Lng.OP(UnicodeMinus0x10000, ">>", 10)
        Offset_10bit_low  = "(uint16_t)(%s)" % Lng.OP(UnicodeMinus0x10000, "&", "0x3FF")
        return {
            1: [
                Lng.INCREMENT_ITERATOR_THEN_ASSIGN("*output_pp", "(uint16_t)(unicode)"),
            ],
            2: [
                Lng.INCREMENT_ITERATOR_THEN_ASSIGN("*output_pp", 
                    "(uint16_t)(%s)" % Lng.OP("0xD800", "|" , Offset_10bit_high)),
                Lng.INCREMENT_ITERATOR_THEN_ASSIGN("*output_pp", 
                    "(uint16_t)(%s)" % Lng.OP("0xDC00", "|" , Offset_10bit_low)),
            ]
        }[CodeUnitN]

    def get_byte_format_range_border_list(self):
        """UCS4 covers the whole range of unicode (extend 0x10FFFF to INTEGER_MAX to be nice)."""
        return [ 0x0, 0x10000, INTEGER_MAX] 
    
class ConverterWriterUTF32(ConverterWriter):
    def max_code_unit_n(self):
        return 1

    def get_output_formatter(self, CodeUnitN):
        return {
            1: [ Lng.INCREMENT_ITERATOR_THEN_ASSIGN("*output_pp", "unicode") ]
        }[CodeUnitN]

    def get_byte_format_range_border_list(self):
        """UCS4 covers the whole range of unicode (extend 0x10FFFF to INTEGER_MAX to be nice)."""
        return [ 0x0, INTEGER_MAX] 

