#! /usr/bin/env python3

import os, sys, argparse, json
from bids import BIDSLayout
from itertools import product

# Last modified
last_modified = "Adapted from work by Anders Perrone 3/21/2017. Last modified 11/18/2022"

# Program description
prog_descrip =  """%(prog)s: sefm_eval pairs each of the pos/neg sefm and returns the pair that is most representative
                   of the average by calculating the eta squared value for each sefm pair to the average sefm.""" + last_modified

class FieldmapPairing(object):

    def __init__(self, layout, subject, session, strategy, task=None):
        # For each functional image in the layout find the fmap pair with a series number that is lower than that of the functional image
        # If the functional image was acquired before the fmap then find the fmap pair with the closest series number
        self.layout = layout
        self.subject = subject
        self.session = session
        self.task = task

        self.func = self.get_func()
        self.fmap = self.get_fmap()

        self.pairing = {f.path:[] for f in self.fmap}

        if strategy == 'closest':
            self.pair_by_closest()
        elif strategy == 'eta_squared':
            self.pair_by_eta()
        elif strategy == 'last':
            self.pair_by_last()
        elif strategy == 'task':
            self.pair_by_task()
        else:
            print('Warning: Strategy not recognized or specified')

    def get_func(self):
        if self.task:
            #print('Returning functional images for task: {}'.format(task))
            return self.layout.get(subject=self.subject, session=self.session, datatype='func', task=self.task, suffix='bold', extension='.nii.gz')
        else:
            #print('Returning all functional tasks')
            return self.layout.get(subject=self.subject, session=self.session, datatype='func', suffix='bold', extension='.nii.gz')

    def get_fmap(self):
        if self.task:
            return self.layout.get(subject=self.subject, session=self.session, acquisition=self.task, datatype='fmap', extension='.json')
        else:
            return self.layout.get(subject=self.subject, session=self.session, datatype='fmap', extension='.json')
    
    def group_fmap_by_run(self):
        # Pair all fmaps by run number
        fmap_runs = {}
        for f in self.fmap:
            f_run = f.get_entities()['run']
            if f_run in fmap_runs:
                fmap_runs[f_run].append(f)
            else:
                fmap_runs[f_run] = [f]

        for run_number, fieldmap_pairs in fmap_runs.items():
            try:
                assert(len(fieldmap_pairs) == 2)
            except AssertionError:
                sys.exit('Unpaired fieldmaps for {} {}'.format(self.subject, self.session))

        return fmap_runs

    def pair_by_eta_squared(self):
        # TODO
        return

    def pair_by_task(self):
        tasks = self.layout.get_tasks(subject=self.subject, session=self.session)
        for task in tasks:
            self.task = task
            self.func = self.get_func()
            self.fmap = self.get_fmap()
            self.pair_by_last()

    def pair_by_last(self):
        fmap_runs = self.group_fmap_by_run()
        last_fmap_pair = fmap_runs[sorted(fmap_runs.keys())[-1]]
        func_paths = [f.path for f in self.func]
        for f in last_fmap_pair:
            self.pairing[f.path] = func_paths
        return 
        
    def pair_by_closest(self):
        fmap_runs = self.group_fmap_by_run()
        # Return a hash map of functional run to field maps
        # Make map of series number to pair
        fmap_series_nums = {}
        for run in fmap_runs:
            min_series_number = min([f.get_metadata()['SeriesNumber'] for f in fmap_runs[run]])
            fmap_series_nums[min_series_number] = [f.path for f in fmap_runs[run]]

        func_series_nums = {f.get_metadata()['SeriesNumber']:f.path for f in self.func}

        fmap_keys = sorted(fmap_series_nums)
        func_keys = sorted(func_series_nums)
        fmap_iter = 0

        pairing = {}
        # Iterate over each functional image
        for func_iter in range(len(func_keys)):
            # If the current fmap iter is at the end then insert current fmaps or if the func series number is less than the series number of the next fieldmap
            if fmap_iter == len(fmap_keys) - 1 or func_keys[func_iter] < fmap_keys[fmap_iter + 1]:
                continue
            # Else insert the next fieldmap and increment the field map counter
            else:
                fmap_iter += 1
            for f in fmap_series_nums[fmap_keys[fmap_iter]]:
                self.pairing[f].append(func_series_nums[func_keys[func_iter]])
        return

    def insert_edit_json(self, json_path, json_field, value):
        with open(json_path, 'r') as f:
            data = json.load(f)
        if json_field in data and data[json_field] != value:
            print('WARNING: Replacing {}: {} with {} in {}'.format(json_field, data[json_field], value, json_path))
        else:
            print('Inserting {}: {} in {}'.format(json_field, value, json_path))
            
        data[json_field] = value
        with open(json_path, 'w') as f:    
            json.dump(data, f, indent=4)
        return

def read_bids_layout(layout, subject_list=None, session_list=None):
    """
    :param bids_input: path to input bids folder
    :param subject_list: a list of subject ids to filter on
    :param session_list: a list of session ids to filer on
    """

    subjects = layout.get_subjects()

    # filter subject list
    if isinstance(subject_list, list):
        subjects = [s for s in subjects if s in subject_list]
    elif isinstance(subject_list, dict):
        subjects = [s for s in subjects if s in subject_list.keys()]

    subsess = []
    # filter session list
    for s in subjects:
        sessions = layout.get_sessions(subject=s)
        if not sessions:
            print('WARNING: No sessions found for subject {}'.format(s))
        elif session_list:
            # Append tuple of subject and session only if the session is in the given session_list
            subsess += [(s, session) for session in sessions if session in session_list]
        else:
            subsess += list(product([s], sessions))

    assert len(subsess), 'bids data not found for participants. If labels ' \
            'were provided, check the participant labels for errors.  ' \
            'Otherwise check that the bids folder provided is correct.'

    return subsess

def generate_parser(parser=None):
    """
    Generates the command line parser for this program.
    :param parser: optional subparser for wrapping this program as a submodule.
    :return: ArgumentParser for this script/module
    """
    if not parser:
        parser = argparse.ArgumentParser(
            description=prog_descrip
        )
    parser.add_argument(
        'bids_dir',
        help='path to the input bids dataset root directory.  It is recommended to use '
             'the dcan bids gui or Dcm2Bids to convert from participant dicoms.'
    )
    parser.add_argument(
        'strategy',
        help='which strategy to use:'
            '   "last": Use the last fmap that was acquired for all functional images'
            '   "eta_squared": Calculate the variance of each fmap to an average to select the "best"'
            '   "closest": Use the previously acquired fmap for the current functional image'
    )
    parser.add_argument(
        '--participant-labels', dest='subject_list', nargs='+',
        help='Optional list of participant ids to run. Default is all ids '
             'found under the bids input directory.  A participant label '
             'does not include "sub-"'
    )
    parser.add_argument(
        '--session-labels', dest='session_list', nargs='+',
        help='Optional list of session ids to run for a given subject or all '
             'subjects if --participant-label is not specified. Default is to '
             'run on all sessions of each given subject. A session label does '
             'not include "ses-"'
    )
    return parser

def main(argv=sys.argv):
    parser = generate_parser()
    args = parser.parse_args()

    bids_dir = args.bids_dir
    layout = BIDSLayout(bids_dir)

    # Create a list of tuples for all subjects and sessions
    subsess = read_bids_layout(layout, subject_list=args.subject_list, session_list=args.session_list)

    strategy = args.strategy

    for subject,session in subsess:
        try:
            x = FieldmapPairing(layout, subject, session, strategy)
            for fieldmap, functional_list in x.pairing.items():
                print(fieldmap, 'IntendedFor',functional_list)
                x.insert_edit_json(fieldmap, 'IntendedFor',functional_list)
        except Exception as e:
            print("Error finding {subject}, {session}.", e)

if __name__ == "__main__":
    sys.exit(main())