from ortools.sat.python import cp_model
import pandas as pd
from collections import defaultdict
import sys

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

class Variables(object):
    pass


class Input(object):
    pass


class Options(object):
    pass

class Sampler:
    options = Options()
    def __init__(self, previous_aggregated_results, true_case_numbers, options):
        """Create sampler.

        Args:
            previous_aggregated_results (pd.DataFrame): Pandas dataframe of results acquired in previous period with columns: `area`, `n`
            target_aggregated_results (pd.DataFrame): Pandas dataframe with columns: `area`, `n`
            options (dict): parameters.
        """
        self.input = Input()
        self.input.previous_aggregated_results = previous_aggregated_results
        self.input.true_case_numbers = true_case_numbers


        self.options.seconds_per_cherrypick = options['seconds_per_cherrypick']
        self.options.seconds_per_box_load = options['seconds_per_box_load']
        self.options.total_time_available = options['total_time_available']
        self.options.area_loss_weighting = options['area_loss_weighting']
        self.options.maximise_samples_weighting = options['maximise_samples_weighting']
        self.options.priority_sample_weighting = options['priority_sample_weighting']
        self.options.max_samples = options['max_samples']
        self.options.max_boxes = options['max_boxes']
        self.options.max_plates = options['max_plates']
        self.options.max_search_time = options['max_search_time']

    def make_picks(self, candidates):
        self.input.candidate_samples = candidates
        self.input.unique_box_names = candidates.box.unique().tolist()
        self.input.unique_plate_names = candidates.plate.unique().tolist()

        self.model = cp_model.CpModel()
        self.instantiate_variables()
        self.add_time_constraint()
        self.loss = self.get_loss()

        return self.get_results(candidates)


    def instantiate_variables(self):
        self.v = Variables()

        self.v.sample_is_picked = {} # indexed by row index
        self.v.priority_sample_is_picked = {} # indexed by row index
        self.v.box_is_picked = {} # indexed by box name
        self.v.plate_is_picked = {} # indexed by box name

        self.v.sample_is_picked_by_area = defaultdict(list)

        for box_name in self.input.unique_box_names:
            self.v.box_is_picked[box_name] = self.model.NewBoolVar(f'box_{box_name}_is_picked')

        for plate_name in self.input.unique_plate_names:
            self.v.plate_is_picked[plate_name] = self.model.NewBoolVar(f'plate_{plate_name}_is_picked')

        for i,row in self.input.candidate_samples.iterrows():
            self.v.sample_is_picked[i] = self.model.NewBoolVar(f'sample_{i}_is_picked')
            self.model.Add(self.v.box_is_picked[row.box] >= self.v.sample_is_picked[i])
            self.model.Add(self.v.plate_is_picked[row.plate] >= self.v.sample_is_picked[i])
            self.v.sample_is_picked_by_area[row.area].append(self.v.sample_is_picked[i])

            # Below we assert that if a single sample on a plate is picked then all samples are picked.
            self.model.Add(  self.v.sample_is_picked[i] >= self.v.plate_is_picked[row.plate])

            if row.priority:
                self.v.priority_sample_is_picked[i] = self.v.sample_is_picked[i]

        self.instantiate_summary_variables()
        self.instantiate_geographical_variables()

    def instantiate_summary_variables(self):

        self.v.total_boxes_picked = sum(self.v.box_is_picked.values())
        self.v.total_plates_picked = sum(self.v.plate_is_picked.values())
        self.v.total_samples_picked = sum(self.v.sample_is_picked.values())
        self.v.total_priority_samples_picked = sum(self.v.priority_sample_is_picked.values())
        self.v.total_time = self.v.total_boxes_picked* self.options.seconds_per_box_load + self.v.total_samples_picked*self.options.seconds_per_cherrypick

        self.v.total_by_area = {}
        for key, value in self.v.sample_is_picked_by_area.items():
            self.v.total_by_area[key] = sum(value)




    def instantiate_geographical_variables(self):
        self.input.true_case_numbers['proportion'] = self.input.true_case_numbers['cases'] / self.input.true_case_numbers['cases'].sum()
        case_number_proportions = dict(zip(self.input.true_case_numbers['area'], self.input.true_case_numbers['proportion']))

        self.v.desired_numbers_for_eod_by_area = {} # These are actually constants for now!
        self.v.projected_numbers_for_eod_by_area = {}

        genomes_in_last_6_days_by_area = dict(zip(self.input.previous_aggregated_results['area'], self.input.previous_aggregated_results['n']))
        genomes_in_last_6_days_by_area = defaultdict(lambda: 0,genomes_in_last_6_days_by_area)
        total_in_past_6_days = self.input.previous_aggregated_results['n'].sum()
        eprint(f"Total in past 6 days: {total_in_past_6_days}")

        for area in case_number_proportions.keys():
            eprint(f"prop {area}:  {case_number_proportions[area]}")
            self.v.desired_numbers_for_eod_by_area[area] = int( (7/6) * total_in_past_6_days * case_number_proportions[area])
            # This assumes we expect to go at about the same rate as last 6 days - we could also manually specify the number we roughly expect to run today
            # Unfortunately trying to do this on the fly with a division of the number we expect to do doesn't seem to play well with the solver.


        for area in case_number_proportions.keys():
            if area in self.v.total_by_area:
                self.v.projected_numbers_for_eod_by_area[area] = genomes_in_last_6_days_by_area[area] + self.v.total_by_area[area]
            else:
                self.v.projected_numbers_for_eod_by_area[area] = genomes_in_last_6_days_by_area[area]


    def add_time_constraint(self):
        self.model.Add(self.v.total_time<self.options.total_time_available)
        self.model.Add(self.v.total_boxes_picked <= self.options.max_boxes)
        self.model.Add(self.v.total_plates_picked <= self.options.max_plates)
        self.model.Add(self.v.total_samples_picked <= self.options.max_samples)


    def get_area_loss(self):
        area_losses = {}
        for area in self.v.projected_numbers_for_eod_by_area.keys():
            possible_loss =  self.v.desired_numbers_for_eod_by_area[area] - self.v.projected_numbers_for_eod_by_area[area]
            area_loss_var = self.model.NewIntVar(0,100000000,f"positive_loss_for_{area}")
            self.model.Add(area_loss_var>=possible_loss) #this is how we implement a 0-cut off

            area_losses[area] = area_loss_var

        return sum(area_losses.values())

    def get_loss(self):
        loss = self.get_area_loss() * self.options.area_loss_weighting
        loss = loss - self.v.total_samples_picked*self.options.maximise_samples_weighting
        loss = loss - self.v.total_priority_samples_picked*self.options.priority_sample_weighting
        return loss

    def get_results(self, input_candidates):
        eprint("calling get results")
        self.model.Minimize(self.loss)
        self.solver = cp_model.CpSolver()
        self.solver.parameters.max_time_in_seconds = self.options.max_search_time
        #self.solver.parameters.linearization_level = 0
        #self.solver.parameters.num_search_workers=8
        status = self.solver.Solve(self.model)
        for area in self.v.desired_numbers_for_eod_by_area.keys():
            desired = self.solver.Value(self.v.desired_numbers_for_eod_by_area[area])
            projected = self.solver.Value(self.v.projected_numbers_for_eod_by_area[area])
            eprint(f"{area}: desired: {desired}  projected: {projected} diff:{projected-desired}")
        eprint(f"Total projected for this 7 days: {self.solver.Value(sum(self.v.projected_numbers_for_eod_by_area.values()))}")
        eprint(f"Total desired for this 7 days: {self.solver.Value(sum(self.v.desired_numbers_for_eod_by_area.values()))}")

        eprint(f"got loss {self.solver.Value(self.loss)}")

        self.input.candidate_samples
        self.input.candidate_samples['to_pick'] = [self.solver.Value(self.v.sample_is_picked[i]) for i in self.input.candidate_samples.index]
        return self.input.candidate_samples

    def get_value(self,variable):
        if isinstance(variable,dict):
            return {k: self.solver.Value(v) for k,v in variable.items()}
        else:
            return(self.solver.Value(variable))
