#!/usr/bin/env python

"""
Computes statistics about how long participants took to complete the experiment,
and how much the average pay was. Produces a csv file with the following columns:

    version (string)
        the experiment version
    mean_pay (float)
        what the mean payrate (dollars/hour) was across participants
    mean_time (float)
        how long it took participants to complete the experiment (mean)
    median_time (float)
        how long it took participants to complete the experiment (median)

"""

import util
import pandas as pd
from datetime import timedelta


def run(dest):
    human = util.load_human()
    versions = list(human['all']['version'].unique())
    results = {}
    for version in versions:
        hdata = human['all'].groupby('version').get_group(version)
        starttime = hdata.groupby('pid')['timestamp'].min()
        endtime = hdata.groupby('pid')['timestamp'].max()
        exptime = endtime - starttime
        medtime = timedelta(seconds=float(exptime.median()) / 1e9)
        meantime = timedelta(seconds=float(exptime.mean()) / 1e9)
        if version == "G":
            payrate = (1.0 / (exptime.astype(int) / (1e9 * 60 * 60))).mean()
        elif version == "H":
            payrate = (1.25 / (exptime.astype(int) / (1e9 * 60 * 60))).mean()
        elif version == "I":
            payrate = (0.70 / (exptime.astype(int) / (1e9 * 60 * 60))).mean()
        else:
            raise ValueError("unexpected version: %s" % version)

        results[version] = {
            "median_time": medtime,
            "mean_time": meantime,
            "mean_pay": payrate
        }

    results = pd.DataFrame.from_dict(results).T
    results.index.name = "version"

    results.to_csv(dest)


if __name__ == "__main__":
    parser = util.default_argparser(__doc__)
    args = parser.parse_args()
    run(args.dest)
