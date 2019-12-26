from ortools.sat.python import cp_model


class PharmacyPartialSolutionPrinter(cp_model.CpSolverSolutionCallback):
    """Print all solutions."""

    def __init__(self, shifts, num_rph, num_weeks, num_days, num_shifts):
        cp_model.CpSolverSolutionCallback.__init__(self)
        self._shifts = shifts
        self._num_rph = num_rph
        self._num_weeks = num_weeks
        self._num_days = num_days
        self._num_shifts = num_shifts
        self._solution_count = 0

    def on_solution_callback(self):
        print(f'Solution {self._solution_count}')

        for w in range(self._num_weeks):
            for s in range(self._num_shifts):
                for d in range(self._num_days):
                    for n in range(self._num_rph):
                        if self.Value(self._shifts[(n, w, d, s)]):
                            print(f'P{n}', end=" ")
                print()
            print()
        print()
        self._solution_count += 1

    def solution_count(self):
        return self._solution_count


def main():
    # Data
    num_rph = 3
    num_weeks = 3
    num_days = 7
    num_shifts = 2
    all_rph = range(num_rph)
    all_weeks = range(num_weeks)
    all_days = range(num_days)
    all_shifts = range(num_shifts)

    # Creates the model.
    model = cp_model.CpModel()

    # Creates shift variables.
    # shifts[(n, w, d, s)]: pharmacist 'n' works shift 's' on day 'd' in week 'w'
    # Week starts from Saturday so d = 0 is Saturday
    shifts = {}
    for n in all_rph:
        for w in all_weeks:
            for d in all_days:
                for s in all_shifts:
                    shifts[(n, w, d, s)] = model.NewBoolVar(f'shift_n{n}w{w}d{d}s{s}')

    # Constraints
    # Each shift is assigned to exactly one pharmacist in the schedule period.
    for w in all_weeks:
        for d in all_days:
            for s in all_shifts:
                model.Add(sum(shifts[(n, w, d, s)] for n in all_rph) == 1)

    # Each pharmacist works at most one shift per day.
    for n in all_rph:
        for w in all_weeks:
            for d in all_days:
                model.Add(sum(shifts[(n, w, d, s)] for s in all_shifts) <= 1)

    # A pharmacist does not have to work an evening shift and then a morning shift
    for n in all_rph:
        for w in all_weeks:
            for d in all_days[:-1]:
                model.Add(shifts[(n, w, d, 1)]+shifts[(n, w, d+1, 0)] != 2)
            if w < (num_weeks-1):
                model.Add(shifts[(n, w, 6, 1)]+shifts[(n, w+1, 0, 0)] != 2)

    # Pharmacy manager must work 5 shifts per week
    # Other pharmacists work at least 4 shifts per week and not more than 5 shifts per week
    shifts_per_week = {}
    for w in all_weeks:
        shifts_per_week[(0, w)] = sum(shifts[(0, w, d, s)] for d in all_days for s in all_shifts)
        model.Add(shifts_per_week[(0, w)] == 5)
    for n in all_rph[1:]:
        for w in all_weeks:
            shifts_per_week[(n, w)] = sum(shifts[(n, w, d, s)] for d in all_days for s in all_shifts)
            model.Add(shifts_per_week[(n, w)] >= 4)
            model.Add(shifts_per_week[(n, w)] <= 5)

    # Total shifts are evenly distributed
    # Pharmacy manager always does 5 according to above constraint so following applies to other pharmacists
    min_shifts = (num_weeks * (num_days * num_shifts - 5)) // (num_rph - 1)
    max_shifts = min_shifts + 1
    total_shifts_worked = {}
    for n in all_rph[1:]:
        total_shifts_worked[n] = sum(shifts[(n, w, d, s)] for w in all_weeks for d in all_days for s in all_shifts)
        model.Add(total_shifts_worked[n] >= min_shifts)
        model.Add(total_shifts_worked[n] <= max_shifts)

    # Morning and evening shifts are equally distributed
    eve_shifts_worked = {}
    morn_shifts_worked = {}
    for n in all_rph:
        eve_shifts_worked[n] = sum(shifts[(n, w, d, 1)] for w in all_weeks for d in all_days)
        morn_shifts_worked[n] = sum(shifts[(n, w, d, 0)] for w in all_weeks for d in all_days)
        model.Add(eve_shifts_worked[n] - morn_shifts_worked[n] <= 1)
        model.Add(morn_shifts_worked[n] - eve_shifts_worked[n] <= 1)

    # A pharmacist cannot work more than max_cont continuous days in a week
    max_cont = 3
    cont_shifts = {}
    for n in all_rph[1:]:
        for w in all_weeks:
            for start in range(num_days - max_cont):
                cont_shifts[(n, w, start)] = sum(shifts[(n, w, d, s)] 
                                                 for d in range(start,start+max_cont+1) for s in all_shifts)
                model.Add(cont_shifts[(n, w, start)] <= max_cont)
    # Applying above constraint across a week
        for w in all_weeks[:-1]:
            for start in range(num_days - max_cont, num_days):
                cont_shifts[(n, w, start)] = sum(shifts[(n, w, d, s)] 
                                                 for d in range(start,num_days) for s in all_shifts)\
                                             + sum(shifts[(n, w+1, d, s)] 
                                                   for d in range(max_cont+1-num_days+start) for s in all_shifts)
                model.Add(cont_shifts[(n, w, start)] <= max_cont)
     # Applying constraint over last week to first week if schedule is repeated
        for start in range(num_days - max_cont, num_days):
            cont_shifts[(n, all_weeks[-1], start)] = sum(shifts[(n, all_weeks[-1], d, s)] 
                                                         for d in range(start,num_days) for s in all_shifts)\
                                             + sum(shifts[(n, 0, d, s)] 
                                                   for d in range(max_cont+1-num_days+start) for s in all_shifts)
            model.Add(cont_shifts[(n, all_weeks[-1], start)] <= max_cont)

    # A pharmacy manager cannot work more than max_cont_mgr continuous days in a week
    max_cont_mgr = 7
    for w in all_weeks:
        for start in range(num_days - max_cont_mgr):
            cont_shifts[(0, w, start)] = sum(shifts[(0, w, d, s)] 
                                             for d in range(start,start+max_cont_mgr+1) for s in all_shifts)
            model.Add(cont_shifts[(0, w, start)] <= max_cont_mgr)
    # Applying above constraint across a week
    for w in all_weeks[:-1]:
        for start in range(num_days - max_cont_mgr, num_days):
            cont_shifts[(0, w, start)] = sum(shifts[(0, w, d, s)] 
                                             for d in range(start,num_days) for s in all_shifts) \
                                         + sum(shifts[(0, w+1, d, s)] 
                                               for d in range(max_cont_mgr + 1 - num_days + start) for s in all_shifts)
            model.Add(cont_shifts[(0, w, start)] <= max_cont_mgr)
    # Applying constraint over last week to first week if schedule is repeated
    for start in range(num_days - max_cont_mgr, num_days):
        cont_shifts[(0, all_weeks[-1], start)] = sum(shifts[(0, all_weeks[-1], d, s)] 
                                                     for d in range(start,num_days) for s in all_shifts) \
                                                 + sum(shifts[(0, 0, d, s)] 
                                                       for d in range(max_cont_mgr + 1 - num_days + start) for s in all_shifts)
        model.Add(cont_shifts[(0, all_weeks[-1], start)] <= max_cont_mgr)

    # A pharmacist has to have either Saturday or Sunday off
    # Meaning every pharmacist works at least once during the weekend (works for num_rph = 3)
    # weekend_shifts = {}
    # for n in all_rph:
    #     for w in all_weeks:
    #         weekend_shifts[(n, w)] = sum(shifts[(n, w, d, s)] for d in range(2) for s in all_shifts)
    #         model.Add(weekend_shifts[(n, w)] != 0)

	# Alternative weekend strategy
    # Pharmacist who works Saturday morning also works Sunday morning and same for evening
    # So essentially the third pharmacist gets the whole weekend off (works for num_rph = 3)
    for n in all_rph:
        for w in all_weeks:
            model.Add(shifts[(n, w, 0, 0)] == shifts[(n, w, 1, 0)])
            model.Add(shifts[(n, w, 0, 1)] == shifts[(n, w, 1, 1)])

    # Equal weekends off
    min_weekends = num_weeks // num_rph
    max_weekends = min_weekends + 1
    weekends_worked = {}
    for n in all_rph:
        weekends_worked[n] = sum(shifts[n, w, d, s] for w in all_weeks for d in range(2) for s in all_shifts)
        model.Add(2 * num_weeks - weekends_worked[n] >= min_weekends * 2)
        model.Add(2 * num_weeks - weekends_worked[n] <= max_weekends * 2)

    # Morning and evening shifts on the weekends are equally distributed
    # Effectively, for num_weeks = 3, a pharmacist works mornings once and evenings once on weekends
    eve_weekends_worked = {}
    morn_weekends_worked = {}
    for n in all_rph:
        eve_weekends_worked[n] = sum(shifts[(n, w, d, 1)] for w in all_weeks for d in range(2))
        morn_weekends_worked[n] = sum(shifts[(n, w, d, 0)] for w in all_weeks for d in range(2))
        model.Add(eve_weekends_worked[n] - morn_weekends_worked[n] <= 2)
        model.Add(morn_weekends_worked[n] - eve_weekends_worked[n] <= 2)

    # Shift off requests
    requests = {}
    for n in all_rph:
        for w in all_weeks:
            for d in all_days:
                for s in all_shifts:
                    requests[(n, w, d, s)] = 0
    requests[(0, 0, 0, 0)] = 1
    requests[(0, 0, 0, 1)] = 1

    # Creates the solver and sets parameters.
    solver = cp_model.CpSolver()
    solver.parameters.linearization_level = 0
    # solver.parameters.max_time_in_seconds = 10.0 # Sets a time limit of 10 seconds

    # Solving for all possible solutions. Not considering shift requests
    # solution_printer = PharmacyPartialSolutionPrinter(shifts, num_rph, num_weeks, num_days, num_shifts)
    # solver.SearchForAllSolutions(model, solution_printer)

    #Solving to minimze shifts on requested off days
    model.Minimize(sum(requests[(n, w, d, s)] * shifts[(n, w, d, s)]
                       for n in all_rph for w in all_weeks for d in all_days for s in all_shifts))

    status = solver.Solve(model)
    for w in all_weeks:
        for s in all_shifts:
            for d in all_days:
                for n in all_rph:
                    if solver.Value(shifts[(n, w, d, s)]) == 1:
                        print(f'P{n}', end=" ")
            print()
        print()
    print()

    # Statistics.
    print()
    print('Statistics')
    # print(f'  - conflicts       : {solver.NumConflicts()}')
    # print(f'  - branches        : {solver.NumBranches()}')
    print(f'  - wall time       : {solver.WallTime()}')
    # print(f'  - solutions found : {solution_printer.solution_count()}')
    print(f'  - objective value : {solver.ObjectiveValue()}')


if __name__ == '__main__':
    main()