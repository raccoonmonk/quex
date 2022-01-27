# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________

file_pickled_dfas = "helper-dfas.pickled"
file_pickled_dfas = "helper-more-dfas.pickled"
day_in_sec        = 86400
now_in_sec        = time.time()

def get_dfas():
    """Get DFAs from pickled file. If the file is older than a day regenerate it."""
    global day_in_sec
    global now_in_sec
    global __dfa_list
    try:
        pickle_time, dfa_list = pickle.load(open(file_pickled_dfas, "rb"))
    except:
        generate_new_f = True

    # Error while reading, or pickle to old => regenerate pickled DFAs
    if generate_new_f or pickle_time - now_in_sec > day_in_sec:
        dfa_list = [
            DFA.Universe(),  # Matches all lexemes
            DFA.Empty(),      # Matches the lexeme of zero length
            #
            dfa('a'),
            dfa('ab'),
            dfa('a(b?)'),
            dfa('ab|abcd'),
            # "Branches" 
            dfa('12|AB'),
            dfa('x(12|AB)'),
            dfa('(12|AB)x'),
            dfa('x(12|AB)x'),
            dfa('x(1?2|A?B)x'),
            dfa('x(1?2?|A?B?)x'),
            # "Loops" 
            dfa('A+'),
            dfa('A(B*)'),
            dfa('A((BC)*)'),
            dfa('((A+)B+)C+'),
            # "BranchesLoops"
            dfa('(AB|XY)+'),
            dfa('(AB|XY)(DE|FG)*'),
            dfa('(AB|XY)+(DE|FG)+'),
            dfa('((AB|XY)(DE|FG))+'),
            # "Misc" 
            dfa('(pri|ri|n)+'),
            dfa('(p?r?i?|rin|n)+'),
        ]
        pickle.dump((now_in_sec, dfa_list), open(file_pickled_dfas, "wb"))
    __dfa_list.extend(dfa_list)

def add_more_DFAs():
    global day_in_sec
    global now_in_sec
    global __dfa_list
    try:
        pickle_time, dfa_list = pickle.load(open(file_pickled_more_dfas, "rb"))
    except:
        generate_new_f = True

    # Error while reading, or pickle to old => regenerate pickled DFAs
    if generate_new_f or pickle_time - now_in_sec > day_in_sec:
        dfa_list = [
            shapes.get_sm_shape_by_name_with_acceptance(name.strip())
            for name in shapes.get_sm_shape_names_list()
        ]
        pickle.dump((now_in_sec, dfa_list), open(file_pickled_more_dfas, "wb"))

    __dfa_list.extend(dfa_list)

get_dfas()
