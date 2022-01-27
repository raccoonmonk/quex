# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.engine.misc.tools      import typed
import quex.engine.misc.similarity as     similarity
from   quex.engine.misc.unistream  import UniStreamBase
from   quex.input.code.base        import SourceRef, SourceRef_VOID

from   io import StringIO, TextIOWrapper 

import time
import sys
import os

__reference_to_setup = None
def specify_setup_object(TheSetup):
    global __reference_to_setup 
    __reference_to_setup = TheSetup

@typed(Fh_or_Sr=(int, SourceRef, TextIOWrapper, StringIO, UniStreamBase), Prefix=str)
def warning(ErrMsg, Fh_or_Sr=-1, Prefix="", SuppressCode=None):
    log(ErrMsg, Fh_or_Sr, DontExitF=True, WarningF=True, NoteF=False, SuppressCode=SuppressCode)

@typed(Fh_or_Sr=(int, SourceRef, TextIOWrapper, StringIO, UniStreamBase), DontExitF=bool)
def log(ErrMsg, Fh_or_Sr=-1, DontExitF=False, Prefix="", WarningF=False, NoteF=False, SuppressCode=None):
    # Fh_or_Sr  = filehandle [1] or filename [2]
    # LineN     = line_number of error
    # DontExitF = True then no exit from program
    #           = False then total exit from program
    # WarningF  = Asked only if DontExitF is set. 
    #
    # count line numbers (this is a kind of 'dirty' solution for not
    # counting line numbers on the fly. it does not harm at all and
    # is much more direct to be programmed.)
    global __reference_to_setup

    PlainMessageF = Fh_or_Sr is None

    if     __reference_to_setup is not None \
       and SuppressCode in __reference_to_setup.suppressed_notification_list:
        return

    if NoteF: DontExitF = True

    if Fh_or_Sr == -1:
        sr = SourceRef_VOID
    elif isinstance(Fh_or_Sr, SourceRef):
        sr = Fh_or_Sr
    elif hasattr(Fh_or_Sr, "reference_sr"):
        sr = SourceRef.from_FileHandle_and_Reference(Fh_or_Sr)
    elif isinstance(Fh_or_Sr, (TextIOWrapper, UniStreamBase)):
        sr = SourceRef.from_FileHandle(Fh_or_Sr)
    elif isinstance(Fh_or_Sr, (StringIO)):
        sr = SourceRef.from_CommandLine()
    else:
        assert False

    if Fh_or_Sr == -1:
        if Prefix == "": prefix = "command line"
        else:            prefix = Prefix
    elif PlainMessageF:  prefix = "message"
    elif NoteF:          prefix = "%s:%i:note"    % (sr.file_name, sr.line_n)   
    elif WarningF:       prefix = "%s:%i:warning" % (sr.file_name, sr.line_n)   
    else:                prefix = "%s:%i:error"   % (sr.file_name, sr.line_n)   
        
    if ErrMsg:
        for line in ErrMsg.splitlines():
            print(prefix + ": %s" % line)

    if SuppressCode is not None:
        print(prefix + ": ('--suppress %s' to avoid this message)" % SuppressCode)

    if not DontExitF: sys.exit(-1)  # Here, sys.exit(-1) is accepted

def note(Text, Sr, MorePrefix="", PrefixF=True):
    if PrefixF: prefix = __SourceRef_to_string(Sr)
    else:       prefix = ""
    for line in Text.splitlines():
        print(prefix + "%s %s" % (MorePrefix, line))

def __SourceRef_to_string(Sr, Prefix=None):
    if Sr == -1:
        if not Prefix: return "command line"
        else:          return Prefix
    else:              return "%s:%i:" % (Sr.file_name, Sr.line_n)   


def error_eof(title, fh, position=None):
    if position is not None: fh.seek(position)
    log("End of file reached while parsing '%s' section." % title, fh)

def log_consistency_issue(This, That, ThisComment, ThatComment="", EndComment="", ExitF=True, SuppressCode=None):
    log("The pattern '%s' %s" % (This.pattern_string(), ThisComment), 
        This.sr, DontExitF=True, WarningF=not ExitF)

    if ThatComment: space = " "
    else:           space = ""
    msg = "pattern '%s'%s%s." % (That.pattern_string(), space, ThatComment)

    if not EndComment:
        log(msg, That.sr, DontExitF=not ExitF, WarningF=not ExitF, 
            SuppressCode=SuppressCode)
    else:
        log(msg,        That.sr, DontExitF=True,      WarningF=not ExitF)
        log(EndComment, That.sr, DontExitF=not ExitF, WarningF=not ExitF, 
            SuppressCode=SuppressCode)

def log_file_not_found(FileName, Comment="", FH=-1):
    """FH and LineN follow format of 'log(...)'"""
    directory = os.path.dirname(FileName)
    if directory == "": directory = os.path.normpath("./"); suffix = "."
    else:               suffix = " in directory\n'%s'." % directory
    comment = ""
    if Comment != "": comment = "(%s) " % Comment
    try:
        ext = os.path.splitext(FileName)[1]

        files_in_directory = [
            file for file in os.listdir(directory) 
            if file.rfind(ext) == len(file) - len(ext)
        ]
    except:
        log("File '%s' (%s) not found." % (FileName, comment), FH)

    verify_word_in_list(FileName, files_in_directory, 
                        "File '%s' %snot found%s" % (FileName, comment, suffix), FH)
    
@typed(Fh_or_Sr=(int, SourceRef, TextIOWrapper, UniStreamBase, StringIO), WordList=(dict, list, tuple, set))
def verify_word_in_list(Word, WordList, Comment, Fh_or_Sr=-1, ExitF=True, SuppressCode=None):
    """FH, and LineN work exactly the same as for error.log(...)"""

    if     __reference_to_setup is not None \
       and SuppressCode in __reference_to_setup.suppressed_notification_list:
        return

    if not WordList:
        log(Comment + "\n'%s' is not addmissible here." % Word, Fh_or_Sr, DontExitF=False, 
            SuppressCode=SuppressCode)
        return

    if type(WordList) == set: WordList = sorted(WordList)

    position_known_f = False
    if type(WordList) == dict:
        word_list = list(WordList.keys())
    elif WordList[0].__class__.__name__ == "UserCodeFragment":
        word_list        = [x.get_code() for x in WordList]
        position_known_f = True
    else:
        word_list        = WordList

    # Word is there. All korrect.
    if Word in word_list: return True

    log_similar(Word, word_list, Comment, Fh_or_Sr=Fh_or_Sr, ExitF=ExitF, 
                SuppressCode=SuppressCode, PositionKnownF=position_known_f)
    return False

def log_similar(Word, WordList, Comment, Fh_or_Sr=-1, ExitF=True, SuppressCode=None, PositionKnownF=True):
    similar_index = similarity.get(Word, WordList)

    if similar_index == -1:
        txt = "Acceptable: "
        length = len(txt)
        for word in sorted(WordList):
            L = len(word)
            if length + L > 80: 
                txt += "\n"; length = 0
            txt += word + ", "
            length += L

        if txt != "": txt = txt[:-2] + "."
        log(Comment + "\n" + txt, Fh_or_Sr, DontExitF=False,
            SuppressCode=SuppressCode)

    else:
        similar_word = WordList[similar_index]
        if PositionKnownF:
            log(Comment, Fh_or_Sr, DontExitF=True)
            if hasattr(WordList[similar_index], "sr"): source_ref = WordList[similar_index].sr
            else:                                      source_ref = -1
            log("Did you mean '%s'?" % similar_word, source_ref, DontExitF=not ExitF, 
                SuppressCode=SuppressCode)
        else:
            log(Comment + "\n" + "Did you mean '%s'?" % similar_word,
                Fh_or_Sr, DontExitF=not ExitF, 
                SuppressCode=SuppressCode)

__insight_ref_str    = ""
__insight_time_begin = None

def insight(Msg):
    # TODO: Is this function supposed to to something?
    global __reference_to_setup
    global __insight_ref_str
    global __insight_time_begin 

    if __insight_time_begin is None: __insight_time_begin = time.time()

    if not __reference_to_setup.insight_f: return

    #time_sec = time.time() - __insight_time_begin
    #memory = 4711 # psutils.memory_usage()

