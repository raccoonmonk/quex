# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.engine.state_machine.core import DFA
import quex.engine.state_machine.index as index

def line(sm, *StateIndexSequence):
    prev_si = int(StateIndexSequence[0])
    for info in StateIndexSequence[1:]:
        if type(info) != tuple:
            si = int(info)
            if unique_transition_f():
                sm.add_transition(prev_si, unique(), si)
            else:
                sm.add_transition(prev_si, 66, si)
        elif info[0] is None:
            si = int(info[1])
            sm.add_epsilon_transition(prev_si, si)
        else:
            trigger, si = info
            si = int(si)
            sm.add_transition(prev_si, trigger, si)
        prev_si = si
    return sm, len(StateIndexSequence)

def get_linear(sm):
    """Build a linear state machine, so that the predecessor states
    are simply all states with lower indices.
    """
    pic = """
                  (0)--->(1)---> .... (StateN-1)
    """
    line(sm, 0, 1, 2, 3, 4, 5, 6)
    return sm, 7, pic

def get_butterfly(sm):
    pic = """           
                          .-<--(4)--<---.
                         /              |
               (0)---->(1)---->(2)---->(3)---->(6)---->(7)
                         \              |
                          '-<--(5)--<---'
    """
    line(sm, 0, 1, 2, 3, 6, 7)
    line(sm, 3, 4, 1)
    line(sm, 3, 5, 1)
    return sm, 8, pic

def get_fork(sm):
    pic = """           
                          .->--(2)-->---.
                         /              |
               (0)---->(1)---->(3)---->(5)---->(6)
                         \              |
                          '->--(4)-->---'
    """
    def v():
        if unique_transition_f(): return unique()
        else:                     return 66
    sm.add_transition(0, v(), 1)
    sm.add_transition(1, v(), 2)
    sm.add_transition(1, v(), 3)
    sm.add_transition(1, v(), 4)
    sm.add_transition(2, v(), 5)
    sm.add_transition(3, v(), 5)
    sm.add_transition(4, v(), 5)
    sm.add_transition(5, v(), 6)
    return sm, 7, pic

def get_fork2(sm):
    pic = """           
                          .->--(1)-->---.
                         /              |
                       (0)---->(2)---->(4)---->(5)
                         \                      |
                          '->--(3)-->-----------'
    """
    line(sm, 0, 2, 4, 5)
    line(sm, 0, 3, 5)
    line(sm, 0, 1, 4)
    return sm, 6, pic

def get_fork3(sm):
    pic = """           
                          .->--(2)-->--(5)
                         /              
               (0)---->(1)---->(3)---->(6)
                         \              
                          '->--(4)-->--(7)
    """
    line(sm, 0, 1, 2, 5)
    line(sm, 1, 3, 6)
    line(sm, 1, 4, 7)
    return sm, 8, pic

def get_fork4(sm):
    pic = """           
                  .->--(1)-->--(2)-->--.
                 /                      \  
               (0)---->(3)---->(4)-->---(7)
                 \                      /
                  '->--(5)-->--(6)-->--'
    """
    line(sm, 0, 1, 2, 7)
    line(sm, 0, 3, 4, 7)
    line(sm, 0, 5, 6, 7)
    return sm, 8, pic

def get_mini_join(sm):
    pic = """
                (0)---->(1)
                 |       |
                 '--<----'
    """
    line(sm, 1, 0)
    line(sm, 0, 1)
    return sm, 2, pic

def get_DEBUG(sm):
    pic = """
                 .--------->(5)---->-----.
                 |                       |
                (0)------------>(2)---->(6)
                 |               |
                 '--<------------' 
    """
    line(sm, 0, 1, 3)
    line(sm, 1, 0)
    line(sm, 0, 2, 3)
    return sm, 7, pic

def get_long_loop(sm):
    """Build a linear state machine, so that the predecessor states
    are simply all states with lower indices.
    """
    pic = """
                 .--------->(5)---->-----.
                 |                       |
                (0)---->(1)---->(2)---->(6)
                 |               |
                 '--<---(4)-----(3)
    """
    line(sm, 0, 1, 2, 6)
    line(sm, 2, 3, 4, 0)
    line(sm, 0, 5, 6)
    return sm, 7, pic

def get_nested_loop(sm):
    pic = """           
                .--<-------(5)---<------.
                |                       |
               (0)---->(1)---->(2)---->(3)---->(4)
                        |       |   
                        '---<---'
    """
    line(sm, 0, 1, 2, 3, 4)
    line(sm, 3, 5, 0)
    line(sm, 2, 1)
    return sm, 6, pic

def get_mini_loop(sm):
    pic = """           
               (0)---->(1)---->(2)---->(3)
                        |       |   
                        '---<---'
    """
    line(sm, 0, 1, 2, 3)
    line(sm, 2, 1)
    return sm, 4, pic

def get_mini_bubble(sm):
    pic = """
                (0)---->(1)---.
                         |    |
                         '-<--'
    """
    line(sm, 0, 1, 1)
    return sm, 2, pic

def get_bubble(sm):
    pic = """
                .------>(1)
               /       /   \ 
             (0)       |   |
               \       \   /
                '------>(2)
    """
    line(sm, 0, 1, 2, 1)
    line(sm, 0, 2)
    return sm, 3, pic

def get_bubble2(sm):
    pic = """
                .------>(1)------>(3)
               /       /   \     /   \ 
             (0)       |   |     |   |
               \       \   /     \   /
                '------>(2)------>(4)
    """
    line(sm, 0, 1, 3, 4, 3)
    line(sm, 0, 2, 1, 2)
    line(sm, 2, 4)
    return sm, 5, pic

def get_bubble2b(sm):
    pic = """
                .------>(1)------>(3)
               /       /         /   \ 
             (0)      \/        \/   /\ 
               \       \         \   /
                '------>(2)------>(4)
    """
    line(sm, 0, 1, 3, 4, 3)
    line(sm, 1, 2)
    line(sm, 0, 2, 4)
    return sm, 5, pic

def get_bubble3(sm):
    pic = """
                .------>(1)------>(3)
               /       /   \     /   \ 
             (0)       |   |     |   |
               \       \   /     \   /
                '------>(2)       (4)
    """
    line(sm, 0, 1, 3, 4, 3)
    line(sm, 0, 2, 1, 2)
    return sm, 5, pic

def get_bubble4(sm):
    pic = """
                .------>(1)------>(3)
               /       /   \     /   \ 
             (0)       |   |     |   |
               \       \   /     \   /
                '------>(2)<------(4)      (4 has only entry from 3)
    """
    line(sm, 0, 1, 3, 4, 3)
    line(sm, 0, 2, 1, 2)
    line(sm, 4, 2)
    return sm, 5, pic

def get_tree(sm):
    pic = """
                                .---->(3)
                          .->--(2)
                         /      '---->(4)
               (0)---->(1)
                         \      .---->(6)        
                          '->--(5)
                                '---->(7)
    """
    line(sm, 0, 1, 2, 3)
    line(sm, 2, 4)
    line(sm, 1, 5, 6)
    line(sm, 5, 7)
    return sm, 8, pic

def get_sm_shape_names():
    return "linear, butterfly, long_loop, nested_loop, mini_loop, fork, fork2, fork3, fork4, tree, mini_bubble, bubble, bubble2, bubble2b, bubble3, bubble4, mini_join;"

def get_sm_shape_names_list():
    return get_sm_shape_names().replace(",", " ").replace(";", "").split()

def get_sm_shape_by_name_with_acceptance(Name):
    sm = get_sm_shape_by_name(Name)[0]
    acceptance_state_list_db = {
        "linear":      [6],
        "butterfly":   [7],
        "long_loop":   [6],
        "DEBUG":       [3],
        "nested_loop": [4],
        "mini_loop":   [3],
        "fork":        [6],
        "fork2":       [5],
        "fork3":       [5, 6, 7],
        "fork4":       [7],
        "mini_bubble": [1],
        "bubble":      [1, 2],
        "bubble2":     [3, 4],
        "bubble2b":    [3, 4],
        "bubble3":     [2, 3],
        "bubble4":     [3, 2],
        "tree":        [3, 4, 6, 7],
        "mini_join":   [1],
    }

    for si in acceptance_state_list_db[Name]:
        sm.states[si].set_acceptance(True)
    return sm

def get_sm_shape_by_name(Name):
    sm = DFA(InitStateIndex=0)
    if   Name == "linear":      sm, state_n, pic = get_linear(sm)
    elif Name == "butterfly":   sm, state_n, pic = get_butterfly(sm)
    elif Name == "long_loop":   sm, state_n, pic = get_long_loop(sm)
    elif Name == "nested_loop": sm, state_n, pic = get_nested_loop(sm)
    elif Name == "mini_loop":   sm, state_n, pic = get_mini_loop(sm)
    elif Name == "fork":        sm, state_n, pic = get_fork(sm)
    elif Name == "fork2":       sm, state_n, pic = get_fork2(sm)
    elif Name == "fork3":       sm, state_n, pic = get_fork3(sm)
    elif Name == "fork4":       sm, state_n, pic = get_fork4(sm)
    elif Name == "mini_bubble": sm, state_n, pic = get_mini_bubble(sm)
    elif Name == "bubble":      sm, state_n, pic = get_bubble(sm)
    elif Name == "bubble2":     sm, state_n, pic = get_bubble2(sm)
    elif Name == "bubble2b":    sm, state_n, pic = get_bubble2b(sm)
    elif Name == "bubble3":     sm, state_n, pic = get_bubble3(sm)
    elif Name == "bubble4":     sm, state_n, pic = get_bubble4(sm)
    elif Name == "mini_join":   sm, state_n, pic = get_mini_join(sm)
    elif Name == "DEBUG":       sm, state_n, pic = get_DEBUG(sm)
    else:                       sm, state_n, pic = get_tree(sm)
    return sm, state_n, pic

def get_sm_list(NoLoopsF=False):
    global __value

    set_unique_transition_f()
    result  = []
    max_state_index = -1
    for name in get_sm_shape_names_list():
        __value = 1
        sm = get_sm_shape_by_name_with_acceptance(name)
        if not NoLoopsF or not sm.has_cycles(): 
            result.append(sm)
            if max(sm.states.keys()) > max_state_index:
                max_state_index = max(sm.states.keys())

    # Make sure, that the largest state index used, is actually taken
    # by the globa state index counter.
    while index.get() < max_state_index:
        pass

    return result

__unique_transition_f = [ False ]

def set_unique_transition_f():
    global __unique_transition_f
    __unique_transition_f[0] = True

def unique_transition_f():
    return __unique_transition_f[0]

__value = 1
def unique():
    global __value
    __value += 1
    return __value

