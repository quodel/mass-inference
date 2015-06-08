#!/usr/bin/env python

"""
Creates a new version of each model likelihood for each participant. We need to
do this, because participants complete the trials in a different order -- so 
in particular, for the learning model, we have to put the trials in the right
order for each participant in order to correctly compute how the model learns.

This depends on RESULTS_PATH/model_likelihood.h5, and produces a new HDF5
database, with the same key structure as model_likelihood.h5. For each
table in the database, the columns are:

    counterfactual (bool)
        whether the counterfactual likelihood was used
    version (string)
        the experiment version
    kappa0 (float)
        true log mass ratio
    pid (string)
        unique participant id
    stimulus (string)
        stimulus name
    trial (int)
        trial number
    hypothesis (float)
        hypothesis about the mass ratio
    llh (float)
        log likelihood of the hypothesis

"""

__depends__ = ["trial_order.csv", "model_likelihood.h5"]
__parallel__ = True
__ext__ = '.h5'

import util
import pandas as pd
import os

from IPython.parallel import Client, require


def likelihood_by_trial(args):
    key, trials, old_store_pth = args
    print key

    old_store = pd.HDFStore(old_store_pth, mode='r')
    llh = old_store[key].groupby('kappa0')
    old_store.close()

    # create an empty dataframe for the results
    results = pd.DataFrame([])

    # iterate through each of the pids
    for (kappa0, pid), df in trials.groupby(['kappa0', 'pid']):
        # merge the trial order with the model likelihood
        model = pd.merge(
            llh.get_group(kappa0),
            df.reset_index())

        results = results.append(model, ignore_index=True)

    # make sure hypothesis is of type float, otherwise hdf5 will complain
    results.loc[:, 'hypothesis'] = results['hypothesis'].astype(float)

    return key, results


def run(dest, results_path, parallel):
    # load in trial order
    trial_order = pd.read_csv(os.path.join(
        results_path, 'trial_order.csv'))
    trials = trial_order\
        .groupby('mode')\
        .get_group('experimentC')\
        .drop('mode', axis=1)\
        .set_index('stimulus')\
        .sort('trial')

    # start up the ipython parallel client
    if parallel:
        rc = Client()
        lview = rc.load_balanced_view()
        task = require('pandas as pd')(likelihood_by_trial)
    else:
        task = likelihood_by_trial

    # load model likelihoods
    old_store_pth = os.path.abspath(os.path.join(
        results_path, 'model_likelihood.h5'))
    old_store = pd.HDFStore(old_store_pth, mode='r')

    # run the tasks
    results = []
    store = pd.HDFStore(dest, mode='w')
    for key in old_store.keys():
        if key.split('/')[-1] == 'param_ref':
            store.append(key, old_store[key])
            continue

        args = [key, trials, old_store_pth]
        if parallel:
            result = lview.apply(task, args)
        else:
            result = task(args)
        results.append(result)

    # close the old hdf5 store
    old_store.close()

    # get and save results
    while len(results) > 0:
        result = results.pop(0)
        if parallel:
            key, model = result.get()
            result.display_outputs()
        else:
            key, model = result

        store.append(key, model)
    store.close()

if __name__ == "__main__":
    parser = util.default_argparser(locals())
    args = parser.parse_args()
    run(args.to, args.results_path, args.parallel)