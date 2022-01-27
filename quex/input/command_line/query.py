# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
import sys

import quex.engine.misc.error                   as     error
from   quex.engine.misc.unistream               import UniStream
from   quex.engine.misc.tools                   import quex_chr
from   quex.engine.misc.interval_handling       import NumberSet, Interval
from   quex.engine.codec_db.unicode.parser      import ucs_property_db

from   quex.input.regular_expression.exception  import RegularExpressionException

import quex.input.regular_expression.core       as     regular_expression
from   quex.DEFINITIONS                         import QUEX_VERSION 
import quex.engine.codec_db.core                as     codec_db

from   quex.blackboard import setup as Setup

OPTION_DB = {
        "--encoding-info":         ["Information about supported characters of a codec."],
        "--encoding-file-info":    ["Information about supported characters of a codec file."],
        "--encoding-for-language": ["Lists possible codecs for a given language."],
        "--property":           ["Querying properties"],
        "--set-by-property":    ["Determining character set by property"],
        "--set-by-expression":  ["Determining character set by property"],
        "--property-match":     ["Find property values that match wildcards"],
        "--numeric":            ["Display sets numerically",  ["--set-by-property", "--set-by-expression"]],
        "--intervals":          ["Display sets by intervals", ["--set-by-property", "--set-by-expression"]],
        "--names":              ["Display unicode names",     ["--set-by-property", "--set-by-expression"]],
}

def run(cl, Argv):

    if   Setup.query_version_f:       print_version(); return
    elif Setup.query_help_f:          print_help(); return

    # Regular Expressions extract the BufferLimitCode and the PathTerminatorCode
    # from the sets. So let us define them outside the normal range.
    backup_buffer_limit_code = Setup.buffer_limit_code
    backup_path_limit_code   = Setup.path_limit_code
    Setup.buffer_limit_code = -1
    Setup.path_limit_code   = -1

    try: 
        if   Setup.query_encoding:             __handle_codec(cl)
        elif Setup.query_encoding_list:        __handle_codec_list(cl)
        elif Setup.query_encoding_file:        __handle_codec_file(cl)
        elif Setup.query_encoding_language:    __handle_codec_for_language(cl)
        elif Setup.query_property is not None: __handle_property(cl)
        elif Setup.query_set_by_property:      __handle_set_by_property(cl)
        elif Setup.query_set_by_expression:    __handle_set_by_expression(cl)
        elif Setup.query_property_match:       __handle_property_match(cl)
        else:
            assert False # No query option(s) !
    except RegularExpressionException as x:
        error.log(x.message)

    Setup.buffer_limit_code = backup_buffer_limit_code
    Setup.path_limit_code   = backup_path_limit_code
    return 

def get_supported_command_line_option_description():
    txt = ""
    for key, description in list(OPTION_DB.items()):
        txt += "    " + key
        if len(description) >= 2: 
            txt += " (only with "
            txt += repr(description[1])[1:-1]
            txt += ")"
        txt += "\n"
    return txt

def __handle_codec(cl):
    codec_name = Setup.query_encoding

    character_set = codec_db.get_supported_unicode_character_set(CodecAlias=codec_name)
    __display_set(character_set, cl)

    print()
    print("Codec is designed for:")
    print(repr(codec_db.get_supported_language_list(codec_name))[1:-1])

def __handle_codec_list(cl):
    codec_list = codec_db.get_complete_supported_codec_list()
    txt = ["  "]
    length = 2
    Last = len(codec_list) - 1
    for i, name in enumerate(codec_list):
        if not name: continue
        L = len(name)
        if length + L > 80: 
            txt.append("\n  ")
            length = 2
        txt.append(name)
        length += L
        if i != Last:       
            txt.append(", ")
            length += 2
    txt.append(".\n")

    print("List of supported engine encodings:\n")
    print("".join(txt))

def __handle_codec_file(cl):
    file_name = cl.follow("", "--encoding-file-info")
    character_set = codec_db.get_supported_unicode_character_set(FileName=file_name)
    __display_set(character_set, cl)

def __handle_codec_for_language(cl):
    language_name = cl.follow("", "--encoding-for-language")

    supported_language_list = codec_db.get_supported_language_list()

    if language_name == "":
        txt      = "Missing argument after '--encoding-for-language'. Supported languages are:\n\n"
        line_txt = ""
        for name in supported_language_list:
            line_txt += name + ", "
            if len(line_txt) > 50: txt += line_txt + "\n"; line_txt = ""
        txt += line_txt
        txt = txt[:-2] + "."
        error.log(txt)

    print("Possible Codecs: " + repr(codec_db.get_codecs_for_language(language_name))[1:-1])

def __handle_property(cl):
    if Setup.query_property == "": # NOT 'is None'
        # no specific property => display all properties in the database
        sys.stderr.write("(please, wait for database parsing to complete)\n")
        ucs_property_db.init_db()
        print(ucs_property_db.get_property_descriptions())

    else:
        # specific property => display information about it
        sys.stderr.write("(please, wait for database parsing to complete)\n")
        property = __get_property(Setup.query_property)
        if property is None: return 
        print(property)

def __handle_property_match(cl):
    property_follower = Setup.query_property_match
    if not property_follower: return

    sys.stderr.write("(please, wait for database parsing to complete)\n")

    fields = [x.strip() for x in property_follower.split("=")]
    if len(fields) != 2:
        error.log("Wrong property setting '%s'." % property_follower)

    # -- determine name and value
    name                 = fields[0]
    wild_card_expression = fields[1]

    # -- get the property from the database
    property = __get_property(name)
    if property is None: 
        return True

    # -- find the character set for the given expression
    if property.type == "Binary":
        error.log("Binary property '%s' is not subject to value wild card matching.\n" % property.name)

    for value in property.get_wildcard_value_matches(wild_card_expression):
        print(value)

def __handle_set_by_property(cl):
    result = Setup.query_set_by_property

    # expect: 'property-name = value'
    if not result:
        return 

    sys.stderr.write("(please, wait for database parsing to complete)\n")
    fields = [x.strip() for x in result.split("=")]
    if len(fields) not in [1, 2]:
        error.log("Wrong property setting '%s'." % result)

    # -- determine name and value
    name = fields[0]
    if len(fields) == 2: value = fields[1]
    else:                value = None

    # -- get the property from the database
    property = __get_property(name)
    if property is None: 
        return True

    # -- find the character set for the given expression
    if property.type == "Binary" and value is not None:
        error.log("Binary property '%s' cannot have a value assigned to it.\n" % property.name + \
                  "Setting ignored. Printing set of characters with the given property.")

    character_set = property.get_character_set(value)
    if character_set.__class__.__name__ != "NumberSet":
        error.log(character_set)

    __display_set(character_set, cl)

def __handle_set_by_expression(cl):
    pattern_str = Setup.query_set_by_expression
    if not pattern_str : return
    stream = UniStream("[:" + pattern_str + ":]", "<command line>")
    dummy, character_set = regular_expression.parse_character_set(stream)
    __display_set(character_set, cl)

def __display_set(CharSet, cl):
    if Setup.query_numeric_f: display = "hex"
    else:                     display = "utf8"

    CharSet.intersect_with(NumberSet(Interval(0, 0x110000)))

    print("Characters:\n")
    if CharSet.is_empty(): 
        print("    <empty>")
    elif Setup.query_interval_f:
        __print_set_in_intervals(CharSet, display, 80)
    elif Setup.query_unicode_names_f:
        __print_set_character_names(CharSet, display, 80)
    else:
        __print_set_single_characters(CharSet, display, 80)

    print() 
   
def __get_property(Name_or_Alias):
    
    ucs_property_db.init_db()
    property = ucs_property_db[Name_or_Alias]
    if property.__class__.__name__ != "PropertyInfo":
        print(property)
        if Name_or_Alias.find("=") != -1: 
            print("Use command line option `--set-by-property` to investigate property settings.")
        if Name_or_Alias.find("(") != -1:
            print("Use command line option `--set-by-expression` to investigate character set operations.")
        return None
    
    property.init_code_point_db()
    return property

def __print_set_in_intervals(CharSet, Display, ScreenWidth):
    assert Display in ["hex", "utf8"]

    interval_list = CharSet.get_intervals(PromiseToTreatWellF=True)

    txt = ""
    line_size = 0
    for interval in interval_list:
        interval_string        = interval.get_string(Display, "-") + ", "
        interval_string_length = len(interval_string)

        if line_size + interval_string_length > ScreenWidth:
            txt += "\n"
            line_size = 0
        else:
            line_size += interval_string_length
        txt += interval_string

    print(txt)

def __print_set_character_names(CharSet, Display, ScreenWidth):
    for interval in CharSet.get_intervals(PromiseToTreatWellF=True):
        for code_point in range(interval.begin, interval.end):
            print("%06X: %s" % (code_point, ucs_property_db.map_code_point_to_character_name(code_point)))

class CharacterList:
    def __init__(self, CharacterSet):
        interval_list = CharacterSet.get_intervals(PromiseToTreatWellF=True)
        interval_list.sort(key=lambda x: x.begin)


        self.__interval_list      = interval_list
        self.__interval_list_size = len(interval_list)

        if self.__interval_list_size == 0:
            self.__current_character  = None
            self.__current_interval_i = -1
        else:
            # No character below 0 --> take first interval with .end > 0
            for i in range(self.__interval_list_size):
                if self.__interval_list[i].end >= 0: break

            self.__current_character  = max(0, self.__interval_list[i].begin)
            self.__current_interval_i = i

    def is_empty(self):
        return self.__interval_list_size == 0

    def __next__(self):
        tmp = self.__current_character

        if tmp is None: return None

        # Prepare the character for the next call
        self.__current_character += 1
        if self.__current_character == self.__interval_list[self.__current_interval_i].end:
            self.__current_interval_i += 1
            if self.__current_interval_i == self.__interval_list_size:
                self.__current_character = None # End reached
            else:
                self.__current_character = self.__interval_list[self.__current_interval_i].begin

        # Return the character that is still now to treat
        return tmp

def __print_set_single_characters(CharSet, Display, ScreenWidth):
    assert Display in ["hex", "utf8"]

    if Display == "hex":
        CharactersPerLine = 8
        ColumnWidth       = 6
    else:
        CharactersPerLine = 32
        ColumnWidth       = 2

    # just to make sure ...

    character_list = CharacterList(CharSet)
    if character_list.is_empty():
        sys.stdout.write("<Result = Empty Character Set>\n")
        return

    # Avoid memory overflow for very large sets: get character by character 
    last_start_character_of_line = -1
    last_horizontal_offset       = 0
    while 1 + 1 == 2:
        character_code = next(character_list)
        if character_code is None: break

        start_character_of_line = character_code - character_code % CharactersPerLine
        horizontal_offset       = character_code - start_character_of_line

        if start_character_of_line > last_start_character_of_line + CharactersPerLine: 
            sys.stdout.write("\n...")
        if start_character_of_line != last_start_character_of_line:
            sys.stdout.write("\n%05X: " % start_character_of_line)
            last_horizontal_offset = 0

        sys.stdout.write(" " * ColumnWidth * (horizontal_offset - last_horizontal_offset - 1))

        if Display == "hex":
            sys.stdout.write("%05X " % character_code)
        else:
            if character_code >= 0x20:
                sys.stdout.write("%s " % quex_chr(character_code, SpaceIsSpaceF=True))
            else:
                sys.stdout.write("? ")

        last_start_character_of_line = start_character_of_line
        last_horizontal_offset       = horizontal_offset
        
def print_version():
    print("Quex - Fast Universe Lexical FSM Generator")
    print("Version " + QUEX_VERSION)
    print("(C) Frank-Rene Schaefer")
    print("ABSOLUTELY NO WARRANTY")

help_txt = \
"""
USAGE: quex -i INPUT-FILE-LIST -o NAME [OPTION ...]"
       quex [QUERY MODE] [OPTION ...]"

Quex's main purpose is to generate lexical analyzer engines. However, it may
also be used to query for results of regular expressions, in particular unicode
properties. When the '-i' option is passed to quex it is assumed that there are
input files for which a lexical analyzer engine with name 'NAME' needs to be
generated. Output file names (source files, header files) are directly derived
from 'NAME'. For full documentation of command line options, please, consult
the documentation or the man page.

QUERY MODE (selected options):

  --help, -h            Brief help.
  --version, -v         Version information.
  --encoding-info, 
  --ci                  Display Unicode characters of codec. 
  --encoding-list, 
  --cl                  Display all fixed size character encodings that can be 
                        implemented in a state machine without a converter.
                        (Additionally, 'utf8' and 'utf16' are supported)
  --encoding-for-language, 
  --cil                 Lists Unicode codecs supported human language. If no
                        language is specified, all available languages are 
                        listed.
  --property, 
  --pr                  Information on Unicode property or property alias. If no
                        is not specified, brief information on all available 
                        Unicode properties is listed.
  --set-by-property, 
  --sbpr                Display Unicode characters of property setting. Binary
                        property require soley the property name.  Otherwise, 
                        "name=value" is required.
  --property-match, 
  --prm                 Displays property settings that match the given wildcard 
                        expression. Helps to find correct identifiers in Unicode 
                        settings. For example, wildcard-expression "Name=*LATIN*" 
                        gives all settings of property Name that contain the 
                        string LATIN.
  --set-by-expression, 
  --sbe                 Show characters matching the given regular expression. 

  --numeric, --num      Numeric representation of characters.
  --intervals, --itv    Display larger regions of adjacent characters as 
                        intervals.
  --names               Display characters by their name.

GENERATOR MODE (selected options):

  -i                      The following '.qx' files are the basis for lexical 
                          analyzer generation.
  -o, 
  --analyzer-class        Specifies the name of the generated analyzer class 
                          and the file stem of the output files.
  --template-compression, 
  --path-compression      Use template/path compression to reduce code size.
  --no-count-lines, 
  --no-count-columns      Disable line/column counting.
  --language, -l [C|C++|dot]  
                          Language for which code is to be generated. 'dot' 
                          generates 'graphviz' state machine graphs.
  --output-directory, 
  --odir                  Output directory.
  --source-package, --sp  Generate a source package independent of quex 
                          installation.

Please, report bugs at http://quex.sourceforge.net.
"""
def print_help():
    print(help_txt)





