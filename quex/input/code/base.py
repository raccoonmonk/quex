# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.engine.misc.file_operations import count_until_position_raw, \
                                               count_until_position
from   quex.engine.misc.unistream       import UniStreamBytesIO, \
                                               UniStreamStream
from   quex.engine.misc.tools           import typed, \
                                               all_isinstance, \
                                               none_isinstance

from   collections import namedtuple
from   io import StringIO

import os
import re

class SourceRef(namedtuple("SourceRef_tuple", ("file_f", "file_name", "position", "mode_name", "line_n_offset", "current_directory"))):
    """A reference into source code:
    _______________________________________________________________________________
      
        file_name = Name of the file where the code is located.
        line_n    = Number of line where code is found.
    _______________________________________________________________________________
    """
    @typed(FileF=bool, FileName=str, Position=(int, None))
    def __new__(self, FileF=False, FileName="<default>", Position=None, ModeName="", LineNOffset=0):
        self.computed_line_n = None
        return super(SourceRef, self).__new__(self, FileF, FileName, Position, ModeName, LineNOffset, os.getcwd())

    @staticmethod
    def from_CommandLine():
        return SourceRef(False, "<command line>", None)

    @staticmethod
    def from_FileHandle(Fh, ModeName="", BeginPos=None):
        if Fh == -1: return SourceRef.from_CommandLine()

        if BeginPos: position = BeginPos
        else:        position = Fh.tell()

        if isinstance(Fh, StringIO):
            file_name     = "<string>" 
            file_f        = False
            line_n_offset = count_until_position_raw(Fh, Fh.tell(), '\n') - 1
        elif    isinstance(Fh, UniStreamBytesIO) \
             or (isinstance(Fh, UniStreamStream) and Fh.string_f()):
            file_name     = Fh.name
            file_f        = False
            line_n_offset = count_until_position_raw(Fh, Fh.tell(), '\n') - 1
        else:                                  
            file_name     = Fh.name
            file_f        = True
            line_n_offset = 0

        return SourceRef(file_f, file_name, position, ModeName, line_n_offset)

    @staticmethod
    def from_FileName(FileName, LineN=0):
        return SourceRef(True, FileName, LineNOffset=LineN)

    @staticmethod
    def from_FileHandle_and_Reference(FhWithReferenceSr):
        file_name = FhWithReferenceSr.reference_sr.file_name
        return SourceRef(True, file_name, 
                         FhWithReferenceSr.tell(), 
                         LineNOffset = FhWithReferenceSr.reference_sr.line_n)

    @property
    def line_n(self):
        if not self.computed_line_n:
            if self.file_f and self.position:
                os.chdir(self.current_directory)
                self.computed_line_n = count_until_position(self.file_name, self.position, '\n') + self.line_n_offset
            else:
                self.computed_line_n = 1 + self.line_n_offset
        return self.computed_line_n

    def is_void(self):
        return     (self.file_name == "<default>") \
               and self.file_f == False \
               and not self.mode_name \
               and self.position is None

SourceRef_VOID    = SourceRef(False, "<default>", None)
SourceRef_DEFAULT = SourceRef(False, "<default>", None)

class SourceRefObject(object):
    """________________________________________________________________________
    Maintains information about an object which has been defined somewhere in
    the source code. It stores the name, the value, and the source code 
    position.

        .name  = Name of the object.
        .sr    = SourceRef of the object, i.e. where it was defined.
        .set_f()        -> Value has been 'set()' other than with constructor.
        .set(Value, sr) -> Set value of the object.
        .get()          -> Read value of the object

    ___________________________________________________________________________
    """
    def __init__(self, Name, Default, FH=-1):
        self.name    = Name
        self.__value = Default
        # Reference place, where it was set
        if FH == -1: self.sr = SourceRef_DEFAULT
        else:        self.sr = SourceRef.from_FileHandle(FH)
        if hasattr(self.__value, "sr"): self.__value.sr = self.sr
        self.__set_f = False

    @typed(sr=SourceRef)
    def set(self, Value, sr):
        self.__value    = Value
        self.sr         = sr
        if hasattr(self.__value, "sr"): self.__value.sr = self.sr
        self.__set_f    = True

    def get(self):
        return self.__value

    def set_f(self):
        return self.__set_f

class CodeFragment(SourceRefObject):
    """base class for all kinds of generated code and code which
    potentially contains text formatting instructions. Sole feature:

       .get_code() = A list of strings and text formatting instructions.

       .sr         = Reference to the source where the code fragment 
                     was taken from. 
                     
    '.sr.is_void()' tells that the code fragment was either generated
    or is a default setting.
    """
    @typed(Code=(list, str, None), SourceReference=SourceRef)
    def __init__(self, Code=None, SourceReference=SourceRef_VOID):
        assert not isinstance(Code, list) or not any(isinstance(s, list) for s in Code)

        if   Code is None:          code = []
        elif isinstance(Code, str): code = [ Code ]
        else:                       code = Code
        self.set(code, SourceReference)

    def clone(self):
        return CodeFragment(Code=copy(self.get_code()), SourceReference=self.sr)

    def __check_code(self, condition):
        return any(isinstance(s, str) and condition(s) for s in self.get_code())

    @property
    def mode_name(self):
        return self.sr.mode_name

    def set_source_reference(self, SourceReference): 
        self.sr = SourceReference

    @typed(Re=re.Pattern)
    def contains_string(self, Re):  return self.__check_code(lambda x: Re.search(x) is not None)
    def is_empty(self):             return not self.__check_code(lambda x: len(x) != 0)
    def is_whitespace(self):        return not self.__check_code(lambda x: len(x.strip()) != 0)

    def get_code(self):
        """RETURNS: List of text elements. 
        
        May contain annotations to the code made by the derived class. 
        """
        return self.get()

    def get_text(self):
        """RETURNS: Text

        May contain annotations to the code may by the derived class.
        """
        code = self.get_code()
        assert all_isinstance(code, str)
        return "".join(code)

    def requires_lexeme_begin_f(self, Lng):            
        # NOT: if self.__requires_lexeme_begin_f is None: ...
        #      The construction is too dynamic.
        return    self.requires_lexeme_terminating_zero_f(Lng) \
               or self.contains_string(Lng.Match_LexemeBegin)

    def requires_lexeme_terminating_zero_f(self, Lng): 
        # NOT: if self.__requires_lexeme_terminating_zero_f is None: ...
        #      The construction is too dynamic.
        return self.contains_string(Lng.Match_Lexeme) 

CodeFragment_NULL = CodeFragment([])

