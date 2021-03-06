#!/usr/bin/env python

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from datetime import datetime
from mass import DATA_PATH
from path import path
from hashlib import sha256
import dbtools
import json
import logging
import numpy as np
import pandas as pd
import sys
import os

root = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.append(os.path.join(root, 'lib'))
import datapackage as dpkg

logger = logging.getLogger('mass.experiment')


def hashids(df):
    df['pid'] = [sha256(bytes(x)).hexdigest() for x in df['pid']]
    df['assignment'] = [sha256(bytes(x)).hexdigest() for x in df['assignment']]
    return df


def str2bool(x):
    """Convert a string representation of a boolean (e.g. 'true' or
    'false') to an actual boolean.

    """
    sx = str(x)
    if sx.lower() == 'true':
        return True
    elif sx.lower() == 'false':
        return False
    else:
        return np.nan


def split_uniqueid(df, field):
    """PsiTurk outputs a field which is formatted as
    'workerid:assignmentid'. This function splits the field into two
    separate fields, 'pid' and 'assignment', and drops the old field
    from the dataframe.

    """
    workerid, assignmentid = zip(*map(lambda x: x.split(":"), df[field]))
    df['pid'] = workerid
    df['assignment'] = assignmentid
    df = df.drop([field], axis=1)
    return df


def parse_timestamp(df, field):
    """Parse JavaScript timestamps (which are in millseconds) to pandas
    datetime objects.

    """
    timestamp = pd.to_datetime(map(datetime.fromtimestamp, df[field] / 1e3))
    return timestamp


def find_bad_participants(exp, data):
    """Check participant data to make sure they pass the following
    conditions:

    1. No duplicated trials
    2. They finished the whole experiment
    3. They passed the posttest

    Returns a dictionary of failed participants that includes the
    reasons why they failed.

    """

    participants = []
    for (assignment, pid), df in data.groupby(['assignment', 'pid']):
        info = {
            'pid': pid,
            'assignment': assignment,
            'note': None,
            'timestamp': None,
            'percent': 0.0,
            'num_failed': np.nan
        }

        # go ahead and add this to our list now -- the dictionary is
        # mutable, so when we update stuff later the dictionary in the
        # list will also be updated
        participants.append(info)

        # get the time they started the experiment
        times = df['psiturk_time'].copy()
        times.sort_values(inplace=True)
        start_time = pd.to_datetime(
            datetime.fromtimestamp(times.iloc[0] / 1e3))
        info['timestamp'] = start_time

        # add condition/counterbalance
        cond = int(df['condition'].unique())
        cb = int(df['counterbalance'].unique())
        info['condition'] = cond
        info['counterbalance'] = cb

        # check for duplicated entries
        if exp == 'mass_inference-G':
            dupes = df.sort_values(by='psiturk_time')[['mode', 'trial', 'trial_phase']]\
                      .duplicated().any()
            if dupes:
                logger.warning(
                    "%s (%s, %s) has duplicate trials", pid, cond, cb)
                info['note'] = "duplicate_trials"
                continue

        # check to make sure they actually finished
        try:
            prestim = df\
                .set_index(['mode', 'trial', 'trial_phase'])\
                .groupby(level='trial_phase')\
                .get_group('prestim')
        except IndexError:
            if df['trial_phase'].isnull().all():
                incomplete = True
            else:
                raise
        else:
            if exp == 'mass_inference-G':
                num_trials = 62
            elif exp == 'mass_inference-H':
                num_trials = 62
            elif exp == 'mass_inference-I':
                num_trials = 32
            else:
                raise ValueError("unhandled experiment: %s" % exp)

            incomplete = len(prestim) != num_trials
            info['percent'] = 100 * len(prestim) / num_trials

        if incomplete:
            logger.warning(
                "%s (%s, %s) is incomplete (completed %d/32 trials [%.1f%%])",
                pid, cond, cb, len(prestim), info['percent'])
            info['note'] = "incomplete"
            continue

        # check to see if they passed the posttest
        posttest = df\
            .set_index(['mode', 'trial', 'trial_phase'])\
            .groupby(level=['mode', 'trial_phase'])\
            .get_group(('posttest', 'fall_response'))

        truth = (posttest['nfell'] > 0).astype(float)
        resp = (posttest['response'] > 4).astype(float)
        resp[posttest['response'] == 4] = np.nan
        failed = (truth != resp).sum()
        info['num_failed'] = failed

        if failed > 1:
            logger.warning(
                "%s (%s, %s) failed posttest (%d wrong)",
                pid, cond, cb, failed)
            info['note'] = "failed_posttest"
            continue

        # see if they already did (a version of) the experiment
        dbpath = DATA_PATH.joinpath("human", "workers.db")
        tbl = dbtools.Table(dbpath, "workers")
        datasets = tbl.select("dataset", where=("pid=?", pid))['dataset']
        exps = map(lambda x: path(x).namebase, datasets)
        if exp in exps:
            exps.remove(exp)
        if len(exps) > 0:
            logger.warning("%s (%s, %s) is a repeat worker", pid, cond, cb)
            info['note'] = "repeat_worker"
            continue

    return participants


def load_meta(data_path):

    """Load experiment metadata from the given path. Returns a dictionary
    containing the metadata as well as a list of fields for the trial
    data.

    """
    # load the data and pivot it, so the rows are uniqueid, columns
    # are keys, and values are, well, values
    meta = pd.read_csv(data_path.joinpath(
        "questiondata.csv"), header=None)
    meta = meta.pivot(index=0, columns=1, values=2)

    # extract condition information for all participants
    conds = split_uniqueid(
        meta[['condition', 'counterbalance']].reset_index(),
        0).set_index('pid')
    conds['condition'] = conds['condition'].astype(int)
    conds['counterbalance'] = conds['counterbalance'].astype(int)
    conds['assignment'] = conds['assignment'].astype(str)
    conds = conds.T.to_dict()

    # make sure everyone saw the same questions/possible responses
    if 'hash' in meta:
        meta = meta.drop(
            ['condition', 'counterbalance', 'hash'], axis=1).drop_duplicates()
    else:
        meta = meta.drop(['condition', 'counterbalance'], axis=1).drop_duplicates()
    if len(meta) > 1:
        print "WARNING: metadata is not unique! (%d versions found)" % len(meta)

    if 'fields' in meta:
        fields = json.loads(meta['fields'][0])
        meta = meta.drop(['fields'], axis=1)
    else:
        fields = None

    # convert the metadata to a dictionary
    meta = meta.reset_index(drop=True).T.to_dict()[0]

    return meta, conds, fields


def load_data(data_path, conds, fields=None):
    """Load experiment trial data from the given path. Returns a pandas
    DataFrame.

    """
    # load the data
    rawdata = pd.read_csv(data_path.joinpath(
        "trialdata.csv"), header=None)

    data = []
    for i, row in rawdata.iterrows():
        psiturk_id = row[0]
        psiturk_currenttrial = row[1]
        psiturk_time = row[2]
        try:
            datadict = json.loads(row[3])
        except:
            datadict = dict(zip(fields, row[3:]))
        datadict['psiturk_id'] = psiturk_id
        datadict['psiturk_currenttrial'] = psiturk_currenttrial
        datadict['psiturk_time'] = psiturk_time
        data.append(datadict)

    data = pd.DataFrame(data)

    # split apart psiturk_id into pid and assignment
    data = split_uniqueid(data, 'psiturk_id')

    # replace None and '' with np.nan
    data = data.replace([None, ''], [np.nan, np.nan])

    # set labels to NaN where the color is NaN
    data.loc[data['color0'].isnull(), 'label0'] = np.nan
    data.loc[data['color1'].isnull(), 'label1'] = np.nan

    # process other various fields to make sure they're in the right
    # data format
    data['instructions'] = map(str2bool, data['instructions'])
    data['response_time'] = data['response_time'].astype('float') / 1e3
    data['feedback_time'] = data['feedback_time'].astype('float')
    data['presentation_time'] = data['presentation_time'].astype('float')
    data['stable'] = map(str2bool, data['stable'])
    data['nfell'] = data['nfell'].astype('float')
    data['camera_start'] = data['camera_start'].astype('float')
    data['camera_spin'] = data['camera_spin'].astype('float')
    data['response'] = data['response'].astype('float')
    data['ratio'] = data['ratio'].astype('float')
    data['occlude'] = data['occlude'].astype('float')
    data['full_render'] = data['full_render'].astype('float')

    # remove instructions rows
    data = data\
        .groupby('instructions')\
        .get_group(False)

    # rename some columns
    data = data.rename(columns={
        'index': 'trial',
        'experiment_phase': 'mode'})
    # make trials be 1-indexed
    data['trial'] += 1

    # drop columns we don't care about
    data = data.drop([
        'psiturk_currenttrial',
        'instructions'], axis=1)

    def add_condition(df):
        info = conds[df.name]
        df['condition'] = info['condition']
        # sanity check -- make sure assignment and counterbalance
        # fields match
        assert (df['assignment'] == info['assignment']).all()
        assert (df['counterbalance'] == info['counterbalance']).all()
        return df

    # add a column for the condition code
    data = data.groupby('pid').apply(add_condition)

    # hack to handle bug where the mode and trial phase don't get
    # recorded somehow?
    if data_path.namebase == 'mass_inference-I':
        bad_trials = data.ix[data['mode'].isnull()]
        for pid, df in bad_trials.groupby('pid'):
            trials = df['trial']
            inc = np.asarray(trials)
            inc[1:] = inc[1:] < inc[:-1]
            inc[0] = False
            transitions, = np.nonzero(inc)
            idx = np.arange(len(inc))

            if len(transitions) > 0:
                pretest_idx = df.index[idx < transitions[0]]
                bad_trials.loc[pretest_idx, 'mode'] = 'pretest'
            if len(transitions) > 1:
                experimentA_idx = df.index[
                    (idx >= transitions[0]) & (idx < transitions[1])]
                bad_trials.loc[experimentA_idx, 'mode'] = 'experimentA'
            if len(transitions) > 2:
                experimentB_idx = df.index[
                    (idx >= transitions[1]) & (idx < transitions[2])]
                bad_trials.loc[experimentB_idx, 'mode'] = 'experimentB'
                posttest_idx = df.index[idx >= transitions[2]]
                bad_trials.loc[posttest_idx, 'mode'] = 'posttest'

        data.loc[data['mode'].isnull(), 'mode'] = bad_trials['mode']

        bad_trials = data.ix[data['trial_phase'].isnull()]
        for pid, df in bad_trials.groupby('pid'):
            prestim_idx = df[['mode', 'trial']].drop_duplicates().index

            notB = df['mode'] != 'experimentB'
            response = ~(df['response'].isnull())
            fall_idx = df.index[notB & response]
            bad_trials.loc[fall_idx, 'trial_phase'] = 'fall_response'

            mass_idx = df.index[~notB & response]
            bad_trials.loc[mass_idx, 'trial_phase'] = 'mass_response'

            prefeedback_idx = df.index[~notB & ~response]
            bad_trials.loc[prefeedback_idx, 'trial_phase'] = 'prefeedback'
            bad_trials.loc[prestim_idx, 'trial_phase'] = 'prestim'

        idx = data['trial_phase'].isnull()
        data.loc[idx, 'trial_phase'] = bad_trials['trial_phase']

    # construct a dataframe containing information about the
    # participants
    p_conds = pd\
        .DataFrame\
        .from_dict(conds).T\
        .reset_index()\
        .rename(columns={'index': 'pid'})
    p_info = pd\
        .DataFrame\
        .from_dict(find_bad_participants(data_path.namebase, data))
    participants = pd.merge(p_conds, p_info, on=['assignment', 'pid'])\
                     .sort_values(by='timestamp')\
                     .set_index('timestamp')

    # drop bad participants
    all_pids = p_info.set_index(['assignment', 'pid'])
    bad_pids = all_pids.dropna(subset=['note'])
    n_failed = (bad_pids['note'] == 'failed_posttest').sum()
    n_subj = len(all_pids)
    n_good = n_subj - len(bad_pids)
    n_completed = n_good + n_failed
    logger.info(
        "%d/%d (%.1f%%) participants completed experiment",
        n_completed, n_subj, n_completed * 100. / n_subj)
    logger.info(
        "%d/%d (%.1f%%) completed participants failed posttest",
        n_failed, n_completed, n_failed * 100. / n_completed)
    logger.info(
        "%d/%d (%.1f%%) completed participants OK",
        n_good, n_completed, n_good * 100. / n_completed)

    data = data\
        .set_index(['assignment', 'pid'])\
        .drop(bad_pids.index)\
        .reset_index()

    # extract the responses and times and make them separate columns,
    # rather than separate phases
    fields = ['psiturk_time', 'response', 'response_time']
    data = data.set_index(
        ['assignment', 'pid', 'mode', 'trial', 'trial_phase'])
    responses = data[fields].unstack('trial_phase')
    data = data.reset_index('trial_phase', drop=True).drop(fields, axis=1)

    data['fall? response'] = responses['response', 'fall_response']
    data['fall? time'] = responses['response_time', 'fall_response']
    data['mass? response'] = responses['response', 'mass_response']
    data['mass? time'] = responses['response_time', 'mass_response']
    data['timestamp'] = responses['psiturk_time', 'prestim']
    data['timestamp'] = parse_timestamp(data, 'timestamp')

    # drop duplicated rows and sort the dataframe
    data = data\
        .drop_duplicates()\
        .sortlevel()\
        .reset_index()

    # create a column for the kappa value of the feedback they saw
    if 'kappa' in data:
        data = data.drop(['kappa'], axis=1)
    data['kappa0'] = np.log10(data['ratio'])

    # update mass responses
    data.loc[:, 'mass? response'] = data['mass? response'] * 2 - 1
    data.loc[:, 'mass? correct'] = data['mass? response'] == data['kappa0']
    isnan = np.isnan(data['mass? response'])
    data.loc[isnan, 'mass? correct'] = np.nan

    # include number of mass trials
    def get_num_mass_trials(x):
        trials = x.set_index('trial')['mass? response']
        num_mass_trials = (~trials.isnull()).sum()
        x['num_mass_trials'] = num_mass_trials
        return x

    data = data.groupby(['mode', 'pid']).apply(get_num_mass_trials)

    return data, participants


def load_events(data_path):
    """Load experiment event data (e.g. window resizing and the like) from
    the given path. Returns a pandas DataFrame.

    """
    # load the data
    events = pd.read_csv(data_path.joinpath("eventdata.csv"))
    events.columns = [
        "uniqueid", "event_type", "interval", "value", "timestamp"]
    # split uniqueid into pid and assignment
    events = split_uniqueid(events, 'uniqueid')
    # parse timestamps
    events['timestamp'] = parse_timestamp(events, 'timestamp')
    # sort by pid/assignment
    events = events\
        .set_index(['assignment', 'pid', 'timestamp'])\
        .reset_index()\
        .sort_values(by=['assignment', 'pid', 'timestamp'])

    return events


def save_dpkg(dataset_path, data, meta, events, participants):
    dp = dpkg.DataPackage(name=dataset_path.name, licenses=['odc-by'])
    dp['version'] = '1.0.0'
    dp.add_contributor("Jessica B. Hamrick", "jhamrick@berkeley.edu")
    dp.add_contributor("Thomas L. Griffiths", "tom_griffiths@berkeley.edu")
    dp.add_contributor("Peter W. Battaglia", "pbatt@mit.edu")
    dp.add_contributor("Joshua B. Tenenbaum", "jbt@mit.edu")

    # add experiment data, and save it as csv
    r1 = dpkg.Resource(
        name="experiment.csv", fmt="csv",
        pth="./experiment.csv", data=data)
    r1['mediaformat'] = 'text/csv'
    dp.add_resource(r1)

    # add metadata, and save it inline as json
    r2 = dpkg.Resource(name="metadata", fmt="json", data=meta)
    r2['mediaformat'] = 'application/json'
    dp.add_resource(r2)

    # add event data, and save it as csv
    r3 = dpkg.Resource(
        name="events.csv", fmt="csv",
        pth="./events.csv", data=events)
    r3['mediaformat'] = 'text/csv'
    dp.add_resource(r3)

    # add participant info, and save it as csv
    r3 = dpkg.Resource(
        name="participants.csv", fmt="csv",
        pth="./participants.csv", data=participants)
    r3['mediaformat'] = 'text/csv'
    dp.add_resource(r3)

    # save the datapackage
    dp.save(dataset_path.dirname())
    logger.info("Saved to '%s'", dataset_path.relpath())


if __name__ == "__main__":
    parser = ArgumentParser(
        formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument(
        "-e", "--exp",
        required=True,
        help="Experiment version.")
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        default=False,
        help="Force all tasks to be put on the queue.")

    args = parser.parse_args()

    # paths to the data and where we will save it
    data_path = DATA_PATH.joinpath("human-raw", args.exp)
    dest_path = DATA_PATH.joinpath("human", "%s.dpkg" % args.exp)

    # don't do anything if the datapackage already exists
    if dest_path.exists() and not args.force:
        sys.exit(0)

    # create the directory if it doesn't exist
    if not dest_path.dirname().exists:
        dest_path.dirname().makedirs_p()

    # load the data
    meta, conds, fields = load_meta(data_path)
    data, participants = load_data(data_path, conds, fields)
    events = load_events(data_path)
    data = hashids(data)
    events = hashids(events)
    participants = hashids(participants)

    # save it
    save_dpkg(dest_path, data, meta, events, participants)
