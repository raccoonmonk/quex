# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
"""PURPOSE: 

   Walk along a state machine and display the lexeme and input stream.

   (C) Frank-Rene Schaefer
"""

class Step:
    def __init__(self, StateIndex, Lexatom, Command):
        self.state_index = StateIndex
        self.lexatom     = Lexatom
        self.command     = Command

def do(Dfa, Lexeme):
    """'Lexeme' can be list of characters (string) or list of numbers.
    """
    __print(__get_step_list(Dfa, Lexeme))
    
def __print(StepList, InputPosition):
    cell_size           = __get_cell_size(StepList) 

    si_string           = __get_state_index_string(StepList, cell_size)
    upper_border_string = __get_border_string(StepList, cell_size, UpperF=True)
    lexatom_string      = __get_lexatom_string(StepList, cell_size, InputPosition)
    lower_border_string = __get_border_string(StepList, cell_size, UpperF=False)

    print(si_string)
    print(upper_border_string)
    print(lexatom_string)
    print(lower_border_string)

def __get_state_index_string(StepList, CellSize):
    def prepare(Si, CellSize):
        si_str = "%s " % Si
        space  = " " * (CellSize - len(si_str))
        return "%s%s" % (si_str, space)

    return "".join(prepare(step.state_index, CellSize) 
                   for step in StepList)

def __get_border_string(StepList, CellSize, UpperF):
    def prepare(position, InputPosition):
        if position == InputPosition: marker = ":"
        else:                         marker = "-"
        if UpperF: border_str = "%s." % (marker * (CellSize - 1)); first = "."
        else:      border_str = "%s'" % (marker * (CellSize - 1)); first = "'"
    return first + "".join(prepare(i, InputPosition) for i in range(len(StepList)))

def __get_lexatom_string(StepList, CellSize, InputPosition):
    def prepare(Si, CellSize, WeAreHereF):
        si_str = "%s" % Si
        space  = " " * (CellSize - 1 - len(si_str))
        return "%s%s|" % (si_str, space)

    print("#StepList:", StepList)
    return "|" + "".join(prepare(step.lexatom, CellSize, position==InputPosition) 
                         for position, step in enumerate(StepList))

def __get_cell_size(StepList):
    si_string_list       = ["%s" % step.state_index for step in StepList ]
    lexatom_string_list  = ["%s" % step.lexatom     for step in StepList ]
    command_string_list  = ["%s" % step.command     for step in StepList ]

    si_string_max_L      = max(len(s)+1 for s in si_string_list)
    lexatom_string_max_L = max(len(s)+1 for s in lexatom_string_list)
    command_string_max_L = max(len(s)+1 for s in command_string_list)

    si_cell_size      = si_string_max_L 
    lexatom_cell_size = lexatom_string_max_L 
    command_cell_size = command_string_max_L

    return max(si_cell_size, lexatom_cell_size, command_cell_size)

def __get_step_list(Dfa, Lexeme):
    result = []
    si = Dfa.init_state_index
    for input_position, lexatom in enumerate(Lexeme):
        state = Dfa.states[si]
        result.append(Step(si, lexatom, "%s" % state.entry))
        si = state.target_map().get_resulting_target_state_index()
        if si is None: break
    else:
        result.append(Step(si, -1, "<passed>"))

    return result
        
    
if "__main__" == __name__:
    step_list = [ (1, 100, "A"), (2, 101, "B"), (3, 102, "C") ]
    step_list = [ Step(x, y, z) for x, y, z in step_list ]
    __print(step_list, InputPosition=len(step_list))
