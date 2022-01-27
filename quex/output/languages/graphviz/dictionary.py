# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.output.languages.cpp.dictionary import Language as LanguageCpp
from   quex.constants                       import E_Files

class Language(LanguageCpp):
    all_extension_db = {
        "": {
              E_Files.SOURCE:              ".dot",
              E_Files.HEADER:              None,
              E_Files.HEADER_IMPLEMTATION: None,
        }
    }
