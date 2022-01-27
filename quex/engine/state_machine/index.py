# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
import itertools

#     The index is chosen to be globally unique, even though, there is a constraint
#     that all target indices of a state machine must be also start indices. For connecting
#     state machines though, it is much easier to rely on a globaly unique state index.
#
#     NOTE: The index is stored in a 'long' variable. If this variable flows over, then
#           we are likely not be able to implement our state machine due to memory shortage
#           anyway.
__internal_state_index_counter = itertools.count(start=0)
def get():
    global __internal_state_index_counter
    return int(next(__internal_state_index_counter))

__internal_state_machine_id_counter = itertools.count(start=0)
def get_state_machine_id():
    global __internal_state_machine_id_counter
    return int(next(__internal_state_machine_id_counter))

def clear():
    global __internal_state_index_counter
    global __internal_state_machine_id_counter
    __internal_state_index_counter      = itertools.count(start=0)
    __internal_state_machine_id_counter = itertools.count(start=0)

