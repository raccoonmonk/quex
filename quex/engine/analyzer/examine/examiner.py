# Project Quex (http://quex.sourceforge.net); License: MIT;
# (C) 2005-2020 Frank-Rene Schaefer; 
#_______________________________________________________________________________
from   quex.engine.analyzer.examine.recursive_recipe_accumulator  import RecursiveRecipeAccumulator
from   quex.engine.analyzer.examine.state_info                    import LinearStateInfo, \
                                                                         MouthStateInfo
from   quex.constants                                             import E_StateIndices

from   itertools import chain


class Examiner:
    """Maintainer of data and provider of operations for the linear state and
    mouth state analysis. Its purpose is to support the sequential process 
    implemented in the global '.do()' function.
    """
    def __init__(self, SM, RecipeType):
        self._sm            = SM
        self.recipe_type    = RecipeType
        self.predecessor_db = self._sm.get_predecessor_db()
        self.successor_db   = self._sm.get_successor_db(self.predecessor_db)

        self.linear_db   = {}  # map: state index --> LinearStateInfo
        self.mouth_db    = {}  # map: state index --> MouthStateInfo

    def categorize(self):
        """Separates the states of state machine into two categories:

           linear states: only ONE entry from another state (-> .linear_db).
           mouth states:  entries from MORE THAN ONE state (-> .mouth_db).

        The init state is special, in a sense that it is entered from outside
        without explicit mentioning. Therefore, it is only a linear state
        if it has NO entry from another state.

        All states in '.linear_db' and '.mouth_db' have a 'None' recipe. That
        indicates that they are NOT determined, yet.
        
        PREPARES: '.linear_db' and '.mouth_db'.
        """

        def handle(self, StateIndex, FromStateSet):
            n = len(FromStateSet) 
            assert n != 0
            if n == 1: self.linear_db[StateIndex] = LinearStateInfo()
            else:      self.mouth_db[StateIndex]  = MouthStateInfo(FromStateSet)

        from_db         = self._sm.get_from_db()
        state_index_set = set(self._sm.states.keys())

        # (*) Categorize all states, but the init state.
        init_state_index = self._sm.init_state_index
        state_index_set.remove(init_state_index)
        for si in state_index_set:
            handle(self, si, from_db[si])

        # (*) The init state has an 'unmentioned' entry from 'BEFORE_ENTRY'. 
        from_state_set = set(from_db[init_state_index])
        from_state_set.add(E_StateIndices.BEFORE_ENTRY)
        handle(self, init_state_index, from_state_set)

    def determine_required_sets_of_variables(self):
        """Determine for each state the set of concerned registers (sCR) and
        store it in the StateInfo object.
        
        REQUIRES: previous call to '.categorize()'
        """
        db = self.recipe_type.get_required_variable_superset_db(self._sm, 
                                                                self.predecessor_db, 
                                                                self.successor_db)

        for si, required_variable_set in db.items():
            self.get_state_info(si).required_variable_set = required_variable_set

    def is_operation_history_dependent(self, TheSingleEntry, RequiredVariableSet):
        """An operation upon entry into a state is 'history-dependent', if it does 
        depend on a setting of the required variables in that state.  The
        'single_entry' member of a single-entry state represents the concept of an
        operation 'op(i)' from [DOC]. Refer to [DOC] for the precise concept of
        history-dependence.

        RETURNS: True  -- if the operation is history-dependent
                 False -- if not.
        """
        for variable_id in RequiredVariableSet:
            if self.is_operation_component_history_dependent(TheSingleEntry, variable_id):
                return True
        return False

    def is_operation_component_history_dependent(self, TheSingleEntry, VariableId):
        # (1) An operation 'op(i)' that does not influence 'v' is history-dependent 
        #     (see discussion in [DOC])
        for cmd in TheSingleEntry: 
            if VariableId in cmd.assigned_variable_ids(): break
        else:
            # There is a variable that is not assigned by 'op(i)'
            # => 'op(i)' is history-dependent
            return True

        # (2) An operation that relies on a previous setting of 'v' is history-dependent
        #
        for cmd in TheSingleEntry: 
            if VariableId in cmd.required_variable_ids(): return True
        return False

    def setup_initial_springs(self):
        """Finds the states in the state machine that comply to the condition
        of a 'spring' as defined in [DOC]. It determines the recipe for
        those springs and adds them to the databases.

        RETURNS: list of state indices of initial spring states.
        """
        assert set(self.mouth_db).isdisjoint(set(self.linear_db))

        def setup_initial_state(self, si, state):
            """The initial state has a special predecessor 'BEFORE_ENTRY'. This
            predecessor carries the recipe 'R(init)'. In this function the 
            concatenation 'op(i) o R(init)' is applied. If the init state is a 
            linear state, it becomes the output recipe, else it is entered into
            its 'entry_recipe_db'.
            """
            # Setup the initial state with the INITIAL RECIPE
            info        = self.get_state_info(si)
            recipe_init = self.recipe_type.INITIAL(info.required_variable_set) 
            # The initial recipe cannot rely on stored values!
            # assert not recipe_init.snapshot_map

            recipe = self.recipe_type.accumulation(recipe_init, 
                                                   state.single_entry)
            if info.mouth_f():
                info.entry_recipe_db[E_StateIndices.BEFORE_ENTRY] = recipe
            else:
                self.set_recipe(si, recipe)

        def apply_history_indepdent_operations(self, si, state):
            """Identify whether 'op(i)' is history-independent. If so, apply 
            the accumulation 'op(i) o None' in order to determined either
            an entry recipe (mouth state) and/or the output recipe (mouth and 
            linear state).

            Setting the output recipe for a mouth state implements 'interference'
            for a history-indendent 'op(i)'.
            """

            info = self.get_state_info(si)
            if self.is_operation_history_dependent(state.single_entry, 
                                                   info.required_variable_set): 
                return

            recipe_null = self.recipe_type.NULL(info.required_variable_set) 
            recipe      = self.recipe_type.accumulation(recipe_null, 
                                                        state.single_entry)
            self.set_recipe(si, recipe)

            if info.mouth_f():
                info.entry_recipe_db.update(
                    (predecessor_si, recipe) 
                    for predecessor_si in info.entry_recipe_db
                ) 
            self.set_recipe(si, recipe)

        # (1) Determine what variables are required in each state.
        self.determine_required_sets_of_variables()
    
        # (2) Setup initial state with the special predecessor recipe R(init)
        setup_initial_state(self, self._sm.init_state_index, self._sm.get_init_state())

        # (3) Setup states with history-independent operations.
        for si, state in self._sm.states.items():
            apply_history_indepdent_operations(self, si, state)

        # (4) Initial Springs = States where the recipe could be determined 
        #                       beforehand (historically independent).
        return set(
            si for si in self._sm.states
               if self.get_state_info(si).is_determined()
        )

    def resolve(self, Springs):
        """.--->  (1) Walk along linear states from the states in the set of 
           |          Springs. Derive recipes along the walk.
           |      
           |      (2) Resolve mouth states, if possible according to their entries. 
           |          Interfere the recipes at a mouth state. Result: recipe of 
           |          the mouth state.
           |      
           |      (3) Consider the resolved mouth states are new springs.
           |
           '- no -(+) springs = empty?
                   |
                   |  yes  
                   |
                  (4) done, for now.

        RETURNS: Set of mouth states that could still not be resolved.
                 => They become subject to 'dead-lock treatment'.
        """
        springs  = Springs
        done_set = set()
        while springs:
            for si in springs:
                self.get_state_info(si).spring_f = True

            # Derive recipes along linear states starting from springs.
            mouths_ready_set = self._accumulate(springs) 
            done_set.update(springs)

            # Mouth states where all entry recipes are set
            # => Apply 'interference' to determine their recipe.
            self._interference(mouths_ready_set)

            # The determined mouths become the springs for the linear walk
            # Only take NEW springs. 
            springs = mouths_ready_set.difference(done_set)

        # Return the set of still undetermined mouth states.
        return set(si for si, mouth in self.mouth_db.items()
                      if not mouth.is_determined())

    def prepare_springs_of_horizon(self, UnresolvedMouthStateSet):
        """For the given set of unresolved mouth states, implement the 'restore
        all' recipe. That means, that the value of registers is determined at
        run-time upon entry into the state, stored in an auxiliary register
        and restored upon need in recipes.

        Using this approach to resolve unresolved mouth states is safe to
        deliver a complete solution.
        """
        if self._sm.init_state_index in UnresolvedMouthStateSet:
            # According to [DOC], if the initial state is undetermined it 
            # becomes the one and only horizon state.
            horizon = [ self._sm.init_state_index ]
        else:
            horizon = self.get_horizon(UnresolvedMouthStateSet)

        # Cautious interference: apply interference with 'undetermined' 
        # recipes in horizon states. 
        for si in horizon:
            self._prepare_cautious_recipe(si)
        self._interference(horizon)
        return horizon

    def get_state_info(self, StateIndex):
        """RETURNS: LinearStateInfo/MouthStateInfo for a given state index.
        """
        info = self.linear_db.get(StateIndex)
        if info is not None: return info
        else:                return self.mouth_db[StateIndex]

    def set_recipe(self, StateIndex, TheRecipe):
        """Assign a recipe to a state. As soon as this happens, the state is
        considered 'determined'.
        """
        self.get_state_info(StateIndex).recipe = TheRecipe
        # Since the .recipe is no longer 'None', the state is 'determined'.

    def get_recipe(self, StateIndex):
        """This function is only supposed to be called for determined states.

        ASSUMPTION: 'get_recipe()' is ONLY called for spring states. Thus,
        the state must be determined and the recipe MUST be registered either
        in '.linear_db' or '.mouth_db'.

        RETURNS: Recipe for given state index.
        """
        return self.get_state_info(StateIndex).recipe

    def get_horizon(self, UnresolvedMouthStateSet):
        """Horizon: Definition see "[DOC]".

        Brief: The horizon is a subset of dead-lock states that have at least
        one determined entry.  In "[DOC]" it is proven that such states always
        exist, if dead-lock states exist.

        RETURNS: List of indeces of horizon states.
        """
        def condition(si):
            """According to its definition in [DOC], a state is a horizon state
            if it is undetermined (a dead-lock state) and has at least one 
            determined entry. This is the case, if it has at least one undeter-
            mined and at least one determined entry.
            """
            has_determined_f   = False
            has_undetermined_f = False
            for entry_recipe in self.get_state_info(si).entry_recipe_db.values():
                if entry_recipe is None: has_undetermined_f = True
                else:                    has_determined_f   = True
                if has_determined_f and has_undetermined_f:
                    return True
            return False

        return set(
            si for si in UnresolvedMouthStateSet if condition(si)
        )

    def _accumulate(self, Springs):
        """Recursively walk along linear states. The termination criteria is 
        that one of three things hold:

            -- The state is a terminal and has no successors.
            -- The state ahead is a mouth state
            -- The state ahead has a determined recipe.

        An accumulated action is determined on each step by

                recipe = self._accumulate(recipe, DFA_State)

        """
        walker = RecursiveRecipeAccumulator(self)

        for si in Springs:
            # spring == determined state => 'get_recipe()' MUST work.
            walker.do((si, self.get_recipe(si)))

        return set(si for si in walker.mouths_touched_set
                      if self.mouth_db[si].entry_reicpes_all_determined())

    def _interference(self, CandidateSet): 
        """Perform interference of mouth states. Find for each state index the
        MouthInfo and determine the interfered recipe by '.recipe_type', i.e.
        according to the investigated behavior.

        MouthInfo.recipe:   Recipe of resolved mouth state.
        """
        for si in CandidateSet:
            mouth = self.get_state_info(si)
            mouth.recipe,        \
            mouth.homogeneity_db = self.recipe_type.interference(mouth, si)

    def _prepare_cautious_recipe(self, StateIndex):
        """[DOC] describes the process of 'cautious interference' as a type of 
        interference, where it is assumed that all variables are stored upon
        entry and restored in the output recipe. It has been shown in [DOC]
        that a safe procedure to do so is to replace undetermined entries with 
        'cautious entries' consisting of a concatination of the undetermined
        recipe with the current states 'op(i)' (i.e. '.single_entry').

        Once, all undetermined entries are occupied, ordinary interference is
        performed. 
        """
        # A horizon state MUST be a mouth state!
        mouth               = self.mouth_db[StateIndex]

        # According to [DOC] use 'op(i) o UndeterminedRecipe' as entry recipe
        # before interference.
        undetermined_recipe = self.recipe_type.UNDETERMINED(mouth.required_variable_set)
        single_entry        = self._sm.states[StateIndex].single_entry
        cautious_recipe     = self.recipe_type.accumulation(undetermined_recipe,
                                                            single_entry)

        # Replace any undetermined entry recipe with the 'cautious recipe'.
        for predecessor_si, entry in list(mouth.entry_recipe_db.items()):
            if entry is not None: continue
            mouth.entry_recipe_db[predecessor_si] = cautious_recipe

    def assert_consistency(self):
        """After termination, every state must have a recipe assigned to it.
        """
        assert all(chain(iter(self.linear_db.values()), 
                              iter(self.mouth_db.values())), 
                        lambda x: x.is_determined()), \
               repr([x.recipe for x in chain(iter(self.linear_db.values()), iter(self.mouth_db.values())) \
                     if not x.is_determined()])

