#! /usr/bin/env python

import os, sys, argparse, json
from bids import BIDSLayout
from itertools import product


# Last modified
last_modified = "Adapted from work by Anders Perrone 3/21/2017. Last modified 11/18/2022"

# Program description
prog_descrip =  """%(prog)s: sefm_eval pairs each of the pos/neg sefm and returns the pair that is most representative
                   of the average by calculating the eta squared value for each sefm pair to the average sefm.""" + last_modified

def read_bids_layout(layout, subject_list=None, collect_on_subject=False):
    """
    :param bids_input: path to input bids folder
    :param subject_list: a list of subject ids to filter on
    :param collect_on_subject: collapses all sessions, for cases with
    non-longitudinal data spread across scan sessions.
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
            subsess += [(s, 'session')]
        elif collect_on_subject:
            subsess += [(s, sessions)]
        else:
            subsess += list(product([s], sessions))

    assert len(subsess), 'bids data not found for participants. If labels ' \
            'were provided, check the participant labels for errors.  ' \
            'Otherwise check that the bids folder provided is correct.'

    return subsess


def sefm_select(bids_dir, subject, sessions, fsl_dir, task, strategy, debug):
    fmap_dir = os.path.join(bids_dir, f"sub-{subject}", f"ses-{sessions}", "fmap")

    pos = 'PA'
    neg = 'AP'

    # Add trailing slash to fsl_dir variable if it's not present
    if fsl_dir[-1] != "/":
        fsl_dir += "/"
    

    print("Pairing for subject " + subject + ": " + subject + ", " + sessions)
    if task:
        pos_func_fmaps = [file for file in os.listdir(fmap_dir) if ".nii.gz" in file and pos in file]
        neg_func_fmaps = [file for file in os.listdir(fmap_dir) if ".nii.gz" in file and neg in file]
        # pos_func_fmaps = layout.get(subject=subject, session=sessions, datatype='fmap', direction=pos, extension='.nii.gz')
        # neg_func_fmaps = layout.get(subject=subject, session=sessions, datatype='fmap', direction=neg, extension='.nii.gz')
        list_pos = [os.path.join(fmap_dir, pos_file) for pos_file in pos_func_fmaps if f'desc-{task}' in pos_file]
        list_neg = [os.path.join(fmap_dir, neg_file) for neg_file in neg_func_fmaps if f'desc-{task}' in neg_file]
        if debug:
            print("task: ", task)
            print("pos_func_maps :", pos_func_fmaps)
            print("neg_func_maps: ", neg_func_fmaps)
            print("list_pos: ", list_pos)
            print("list_neg: ", list_neg)
    else:
        pos_func_fmaps = [file for file in os.listdir(fmap_dir) if ".nii.gz" in file and pos in file]
        neg_func_fmaps = [file for file in os.listdir(fmap_dir) if ".nii.gz" in file and neg in file]
        # pos_func_fmaps = layout.get(subject=subject, session=sessions, datatype='fmap', direction=pos, extension='.nii.gz')
        # neg_func_fmaps = layout.get(subject=subject, session=sessions, datatype='fmap', direction=neg, extension='.nii.gz')
        list_pos = [os.path.join(fmap_dir, pos_file) for pos_file in pos_func_fmaps]
        list_neg = [os.path.join(fmap_dir, neg_file) for neg_file in neg_func_fmaps]
        if debug:
            print("no task")
            print("pos_func_maps :", pos_func_fmaps)
            print("neg_func_maps: ", neg_func_fmaps)
            print("list_pos: ", list_pos)
            print("list_neg: ", list_neg)


    try:
        len(list_pos) == len(list_neg)
    except:
        print("ERROR in SEFM select: There are a mismatched number of SEFMs. This should never happen!")
    
    pairs = []
    for pair in zip(list_pos, list_neg):
        pairs.append(pair)

    if not pairs:
        print("No files found with the givien parameters.")

    selected_pos = ''
    selected_neg = ''

    if strategy == 'last':
        selected_pos = pairs[-1][0]
        selected_neg = pairs[-1][1]

    elif strategy == 'eta_square':
        pass

    return selected_pos, selected_neg

def insert_edit_json(json_path, json_field, value):
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
        'fsl_dir',
        help="Required: Path to FSL directory."
    )
    parser.add_argument(
        'strategy',
        help='which strategy to use, "last", "eta_squared"'
    )
    parser.add_argument(
        '--tasks', dest='tasks', nargs="+",
        help="an optional list of tasks to loop through."
    )
    parser.add_argument(
        '--participant-label', dest='subject_list', metavar='ID', nargs='+',
        help='optional list of participant ids to run. Default is all ids '
             'found under the bids input directory.  A participant label '
             'does not include "sub-"'
    )
    parser.add_argument(
        '-a','--all-sessions', dest='collect', action='store_true',
        help='collapses all sessions into one when running a subject.'
    )
    parser.add_argument(
        '-d', '--debug', dest='debug', action='store_true', default=False,
        help='debug mode, leaves behind the "eta_temp" directory.'
    )
    parser.add_argument(
        '-v', '--version', action='version', version=last_modified,
        help="Return script's last modified date."
    )
    parser.add_argument(
        '-o', '--output_dir', default='./data/',
        help=('Directory where necessary .json files live, including '
              'dataset_description.json')
    )
    
    return parser

def main(argv=sys.argv):
    parser = generate_parser()
    args = parser.parse_args()
    bids_dir = args.bids_dir
    layout = BIDSLayout(bids_dir)
    fsl_dir = args.fsl_dir + '/bin'
    subsess = read_bids_layout(layout, subject_list=args.subject_list, collect_on_subject=args.collect)
    strategy = args.strategy
    debug = args.debug
    tasks = args.tasks
    
    if tasks:
        for task in tasks:
            for subject,sessions in subsess:
                try:
                    selected_pos, selected_neg = sefm_select(bids_dir, subject, sessions, fsl_dir, task, strategy, debug)
                    json_field = 'IntendedFor'
                    raw_func_list = layout.get(subject=subject, session=sessions, datatype='func', extension='.nii.gz')
                    func_list = [f"ses-{sessions}/func/{x.filename}" for x in raw_func_list if f"task-{task}" in x.filename]

                    selected_pos_json = f"{selected_pos.split('.nii.gz')[0]}.json"
                    selected_neg_json = f"{selected_neg.split('.nii.gz')[0]}.json"

                    if debug:
                        print("raw_func_list :", raw_func_list)
                        print("func_list: ", func_list)
                        print("selected_pos_json: ", selected_pos_json)
                        print("selected_neg_json: ", selected_neg_json)
                    else:
                        insert_edit_json(selected_pos_json, json_field, func_list)
                        insert_edit_json(selected_neg_json, json_field, func_list)

                except Exception as e:
                    print(f"Error finding {subject}, {sessions}.", e)
    else:
        
        for subject,sessions in subsess:
            try:
                selected_pos, selected_neg = sefm_select(bids_dir, subject, sessions, fsl_dir, '', strategy, debug)
                json_field = 'IntendedFor'
                raw_func_list = layout.get(subject=subject, session=sessions, datatype='func', extension='.nii.gz')
                func_list = [f"ses-{sessions}/func/{x.filename}" for x in raw_func_list]

                selected_pos_json = f"{selected_pos.split('.nii.gz')[0]}.json"
                selected_neg_json = f"{selected_neg.split('.nii.gz')[0]}.json"

                if debug:
                    print("raw_func_list :", raw_func_list)
                    print("func_list: ", func_list)
                    print("selected_pos_json: ", selected_pos_json)
                    print("selected_neg_json: ", selected_neg_json)
                else:
                    insert_edit_json(selected_pos_json, json_field, func_list)
                    insert_edit_json(selected_neg_json, json_field, func_list)
            except Exception as e:
                print(f"Error finding {subject}, {sessions}.", e)

if __name__ == "__main__":
    sys.exit(main())