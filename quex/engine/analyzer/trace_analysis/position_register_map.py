# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from quex.constants import E_TransitionN, \
                           E_IncidenceIDs
from quex.engine.misc.quex_enum import QuexEnum


from collections import defaultdict


def do(state_brief_db):
    """
    RETURNS: 
    
    A dictionary that maps:

            post-context-id --> position register index

    where post-context-id == E_PostContextIDs.NONE means
    'last_acceptance_position'.  The position register index starts from
    0 and ends with N, where N-1 is the number of required position
    registers. It can directly be used as index into an array of
    positions.

    -----------------------------------------------------------------------
   
    Under some circumstances it is necessary to store the acceptance
    position or the position in the input stream where a post context
    begins. For this an array of positions is necessary, e.g.

        QUEX_POSITION_LABEL     positions[4];

    where the last acceptance input position or the input position of
    post contexts may be stored. The paths of a state machine, though,
    may allow to store multiple positions in one array location, because

        (1) the path from store to restore does not intersect, or

        (2) they store their positions in exactly the same states.

    A more general and conclusive condition will be derived later. Now,
    consider the following example:
                                   . b .
                                  /     \ 
                                  \     /
             .-- a -->( 1 )-- b -->( 2 )-- c -->((3))
            /            S47                       R47 
        ( 0 )
            \            S11                       R11
             '-- b -->( 4 )-- c -->( 5 )-- d -->((6))
                          \                     /
                           '-------- e --------'

    The input position needs to be stored for post context 47 in state 1 and
    for post context 11 in state 4. Since the paths of the post contexts do
    not cross it is actually not necessary to have to separate array
    registers. One register for post context 47 and 11 is enough.  Reducing
    position registers saves space, but moreover, it may spare the
    computation time to store redundant input positions.

    .-------------------------------------------------------------------------.
    | CONDITION:                                                              |
    |                                                                         |
    | Let 'A' be a state that restores the input position from register 'x'.  |
    | If 'B' be the last state on a trace to 'A' where the position is stored |
    | in 'x'. If another state 'C' stores the input position in register 'y'  |
    | and comes **AFTER** 'B' on the trace, then 'x' and 'y' cannot be the    |
    | same.                                                                   |
    '-------------------------------------------------------------------------'
    """
    cannot_db       = get_cannot_db(state_brief_db)
    combinable_list = get_combinable_candidates(cannot_db)

    return get_mapping(combinable_list)

def pseudo(SM):
    """Primitive solution: every acceptance id has its own position register.
    """
    return dict((acceptance_id, i) for i, acceptance_id in enumerate(SM.acceptance_id_set().union([E_IncidenceIDs.BAD_LEXATOM])))

def get_cannot_db(state_brief_db):
    """
    Determine for each position register (identified by acceptance_id) the set of 
    position registers. The condition for this is given at the entrance of this file.

    RETURNS:   
    
        map:  
              acceptance_id --> list of pattern_ids that it cannot be combined with.
    """
    def cannot_db_update(db, position_restore_db):
        """According to the CONDITION mentioned in the entry, it determined 
           what post contexts cannot be combined for the given trace list.
           Note, that FAILURE never needs a position register. After FAILURE, 
           the position is set to lexeme start plus one.
        """
        # FAILURE is excluded implicitly, since then 'transition_n_since_positioning'
        # is equal to 'LEXEME_START_PLUS_ONE' and not 'VOID'.
        entry_list = [
             (acceptance_id, x) for acceptance_id, x in position_restore_db.items() \
             if x.transition_n_since_positioning == E_TransitionN.VOID
        ] 

        for i, x_entry in enumerate(entry_list):
            x_acceptance_id, x = x_entry
            # Ensure, the database has at least one entry.
            if x_acceptance_id not in db: db[x_acceptance_id] = set()
            for y_acceptance_id, y in entry_list[i+1:]:
                # If the positioning state differs, and we need to restore here, 
                # then the position register cannot be shared.
                if x.storing_si_set == y.storing_si_set: continue
                # Note, that in particular if x == y, it is left out of consideration
                db[x_acceptance_id].add(y_acceptance_id)
                db[y_acceptance_id].add(x_acceptance_id)

    # Database that maps for each state with post context id with which post context id
    # it cannot be combined.
    cannot_db = defaultdict(set)

    for state_index, state_brief in state_brief_db.items():
        cannot_db_update(cannot_db, state_brief.restore.position_db)

    return cannot_db

def get_combinable_candidates(cannot_db):
    """Determine sets of combinations that are allowed."""

    all_post_context_id_list = set(cannot_db.keys())

    combinable_list = []
    done_set        = set()
    done_set        = set()
    for acceptance_id, cannot_set in sorted(cannot_db.items()):
        candidate_list = list(all_post_context_id_list.difference(cannot_set))
        assert acceptance_id in candidate_list

        # Delete all candidates that cannot be be combined with the remainder
        def _condition(candidate, acceptance_id, cannot_db, candidate_list, done_set):
            cannot_set = cannot_db[candidate] # 'candidate' cannot be combined with 'cannot_set'
            if   candidate in done_set:                 return False
            elif candidate == acceptance_id:            return True
            elif cannot_set.isdisjoint(candidate_list): return True
            else:                                       return False

        # Consider those patterns first that have the largest set of 'cannot-s'.
        candidate_list.sort(key=lambda x: (-len(cannot_db[x]), x))
        i    = 0
        size = len(candidate_list)
        while i < size:
            candidate  = candidate_list[i]
            if _condition(candidate, acceptance_id, cannot_db, candidate_list, done_set):
                 i += 1                # candidate can stay, go to next
            else:
                 del candidate_list[i] # candidate is deleted
                 size -= 1

        # MORE ELEGANT! However, 'candidate_list' changes with iteration, so that
        #               a different possibility of combinations is chosen. This 
        #               causes some unit tests to fail. Use code fragment below
        #               when all unit tests are working. (TODO)
        # Consider those patterns first that have the largest set of 'cannot-s'.
        ## for i, candidate in reversed(list(enumerate(candidate_list))):
        ##    if not _condition(candidate, acceptance_id, cannot_db, candidate_list, done_set):
        ##        del candidate_list[i] # candidate is deleted
        if candidate_list:
            combinable_list.append(set(candidate_list))
            done_set.update(candidate_list)

    return combinable_list

def get_mapping(combinable_list):
    """Determine the mapping from acceptance_id to the register id that can be used
       to index into an array.
    """
    result      = {}
    array_index = 0
    while len(combinable_list) != 0:
        # Allways, try to combine the largest combinable set first.
        k           = max(enumerate(combinable_list), key=lambda x: len(x[1]))[0]
        combination = combinable_list.pop(k)

        for acceptance_id in (x for x in combination if x not in result):
            result[acceptance_id] = array_index

        # Since: -- The combinations only contain post_context_id's that have not been
        #           mentioned before, and
        #        -- all empty combinations are deleted from the combinable_list,
        # Thus:  It is safe to assume that new entries were made for the current
        #        array index. Thus, a new array index is required for the next turn.
        array_index += 1

        # Delete combinations that have become empty
        combinable_list = [ x for x in combinable_list if len(x) ]

    return result

def print_this(TheAnalyzer):
    brief_db = TheAnalyzer.state_brief_db_for_printing
    for state_index, state_brief in sorted(iter(brief_db.items()),key=lambda x: QuexEnum.general_key(x[0])):
        print("State %i:" % state_index)
        txt = ""
        for acceptance_id, x in sorted(state_brief.restore.position_db.items(),
                                       key=lambda x: QuexEnum.general_key(x[0])): 
            if x.transition_n_since_positioning == E_TransitionN.VOID:
                txt += "    (*) "
            else: 
                txt += "        "

            acceptance_condition_set = brief_db.acceptance_condition_db[acceptance_id]
            if not acceptance_condition_set:
                txt += "[%7s]: %s/%s\n" % (acceptance_id, "NONE", 
                                           x.storing_si_set)
            else:
                for acceptance_condition_id in acceptance_condition_set:
                    txt += "[%7s]: %s/%s\n" % (acceptance_id, 
                                               acceptance_condition_id, 
                                               x.storing_si_set)
        print(txt)

