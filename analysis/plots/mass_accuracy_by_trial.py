#!/usr/bin/env python

import sys
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import util


def plot(results_path, fig_paths):

    mass_responses = pd\
        .read_csv(results_path.joinpath('mass_accuracy_by_trial.csv'))\
        .groupby(['class', 'species'])\
        .get_group(('chance', 'human'))

    colors = {
        8: 'k',
        20: 'k',
        -1: 'k',
        5: 'r',
        4: 'y',
        3: 'g',
        2: 'b',
        1: 'm'
    }

    versions = ['H', 'G', 'I', 'I-all']

    fig, axes = plt.subplots(1, 4, sharey=True)

    for version, df in mass_responses.groupby('version'):
        for kappa0, df2 in df.groupby('kappa0'):
            if kappa0 != 'all':
                continue

            for num, df3 in df2.groupby('num_mass_trials'):
                if version == 'I' and num != -1:
                    ax = axes[versions.index('I-all')]
                else:
                    ax = axes[versions.index(version)]

                x = np.asarray(df3['trial'], dtype=int)
                y = df3['median']
                yl = df3['lower']
                yu = df3['upper']

                ax.fill_between(x, yl, yu, alpha=0.3, color=colors[num])
                ax.plot(x, y, color=colors[num], lw=2,
                        label="%d trials" % num,
                        marker='o', markersize=4)

    for i, ax in enumerate(axes):
        version = versions[i]
        if version == 'I-all':
            version = 'I'

        df = mass_responses.groupby('version').get_group(version)
        x = np.sort(df['trial'].unique()).astype(int)
        if version == 'H':
            ax.set_xticks([1, 5, 10, 15, 20])
            ax.set_xticklabels([1, 5, 10, 15, 20])
        else:
            ax.set_xticks(x)
            ax.set_xticklabels(x)

        ax.set_xlim(x.min(), x.max())
        ax.set_xlabel("Trial")
        ax.set_title("Experiment %d" % (versions.index(version) + 1))

        util.clear_right(ax)
        util.clear_top(ax)
        util.outward_ticks(ax)

    ax = axes[0]
    ax.set_ylim(0.5, 1)
    ax.set_ylabel("Fraction correct")

    axes[-1].legend(loc='lower center', fontsize=10, ncol=2, frameon=False)

    fig.set_figwidth(9)
    fig.set_figheight(3)
    plt.draw()
    plt.tight_layout()

    for pth in fig_paths:
        util.save(pth, close=False)


if __name__ == "__main__":
    util.make_plot(plot, sys.argv[1:])
