#! /usr/bin/env python

import os, sys, argparse, subprocess, json
from bids import BIDSLayout
from itertools import product


# Last modified
last_modified = "Created by Anders Perrone 3/21/2017. Last modified 13/01/2019"

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


def sefm_select(layout, subject, sessions, base_temp_dir, fsl_dir, eta_square=False):
    pos = 'PA'
    neg = 'AP'

    # Add trailing slash to fsl_dir variable if it's not present
    if fsl_dir[-1] != "/":
        fsl_dir += "/"

    # Make a temporary working directory
    temp_dir = os.path.join(base_temp_dir, subject + '_eta_temp')
    try:
        os.mkdir(temp_dir)
    except:
        print(temp_dir + " already exists")
        pass

    print("Pairing for subject " + subject + ": " + subject + ", " + sessions)
    pos_func_fmaps = layout.get(subject=subject, session=sessions, datatype='fmap', acquisition='func', direction=pos, extension='.nii.gz')
    neg_func_fmaps = layout.get(subject=subject, session=sessions, datatype='fmap', acquisition='func', direction=neg, extension='.nii.gz')
    list_pos = [os.path.join(x.dirname, x.filename) for x in pos_func_fmaps]
    list_neg = [os.path.join(y.dirname, y.filename) for y in neg_func_fmaps]

    try:
        len(list_pos) == len(list_neg)
    except:
        print("ERROR in SEFM select: There are a mismatched number of SEFMs. This should never happen!")
    
    pairs = []
    for pair in zip(list_pos, list_neg):
        pairs.append(pair)

    print(pairs)

    # tasks = {}
    # for pair in pairs:
    #     pos = pairs[0]
    #     task = pos.split("task-")[1]
    #     task = task.split("_")[0]
    
    # pos_ref = pairs[0][0]
    # neg_ref = pairs[0][1]
    
    # if eta_square:
    #     pass
    # else:
    #     best_pos = pairs[-1][0]
    #     best_neg = pairs[-1][1]

    # return dictionary with keys being the run name and values being a pair


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

    # Added by Greg Conan 2019-11-04
    parser.add_argument(
        '-o', '--output_dir', default='./data/',
        help=('Directory where necessary .json files live, including '
              'dataset_description.json')
    )
    
    return parser

def main(argv=sys.argv):
    parser = generate_parser()
    args = parser.parse_args()

    layout = BIDSLayout(args.bids_dir)
    fsl_dir = args.fsl_dir + '/bin'
    subsess = read_bids_layout(layout, subject_list=args.subject_list, collect_on_subject=args.collect)
    
    for subject,sessions in subsess:
        fmap = layout.get(subject=subject, session=sessions, datatype='fmap', extension='.nii.gz', acquisition='func')        
        # Check if there are func fieldmaps and return a list of each SEFM pos/neg pair
        if fmap:
            print("Running SEFM select")
            base_temp_dir = fmap[0].dirname
        sefm_select(layout, subject, sessions, base_temp_dir, fsl_dir)


if __name__ == "__main__":
    sys.exit(main())