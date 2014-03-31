#!/usr/bin/env python

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from mass.render.build import build
from itertools import product
import re


defaults = dict(
    # directory to load stimuli from
    cpo_path=None,

    # log10 mass ratio of type1:type0 blocks
    kappa=0.0,

    # amount of time in seconds to present the stimulus for
    presentation_time=6.0,

    # amount of time in seconds to show feedback for
    feedback_time=3.5,

    # labels for type 0 and type 1 blocks
    label0="0",
    label1="1",

    # colors of type 0 and type 1 blocks
    color0=None,
    color1=None,

    # seed for random number generator
    seed=1209,

    # amount to rotate the camera, in degrees
    camera_spin=180,

    # whether to render feedback
    feedback=True,

    # drop occluder after stimulus presentation
    occlude=False,

    # render the full stimulus as one video
    full_render=False
)


def make_options():
    options = []

    # stable example
    options.append({
        'condition': 'shared',
        'tag': 'stable_example',
        'cpo_path': 'mass-inference-stable-example-H',
        'seed': 10239,
        'full_render': True
    })

    # unstable example
    options.append({
        'condition': 'shared',
        'tag': 'unstable_example',
        'cpo_path': 'mass-inference-unstable-example-H',
        'seed': 10240,
        'full_render': True
    })

    # pretest
    options.append({
        'condition': 'shared',
        'tag': 'pretest',
        'cpo_path': 'mass-inference-training-H',
        'seed': 10241,
    })

    # mass example
    for r, cb in product(['0.1', '10'], [0, 1]):
        labels = ['red', 'blue']
        colors = ['#CA0020', '#0571B0']
        if (r == '10' and cb == 1) or (r == '0.1' and cb == 0):
            labels = labels[::-1]
            colors = colors[::-1]

        options.append({
            'condition': 'vfb-%s-cb%d' % (r, cb),
            'tag': 'mass_example',
            'cpo_path': 'mass-inference-example-H',
            'seed': 10242,
            'label0': labels[0],
            'label1': labels[1],
            'color0': colors[0],
            'color1': colors[1],
            'kappa': 1.0,
            'full_render': True
        })

    # experiment A
    for r, cb in product(['0.1', '10'], [0, 1]):
        labels = ['red', 'blue']
        colors = ['#CA0020', '#0571B0']
        if cb == 1:
            labels = labels[::-1]
            colors = colors[::-1]
        if r == '0.1':
            kappa = -1.0
        elif r == '10':
            kappa = 1.0

        options.append({
            'condition': 'vfb-%s-cb%d' % (r, cb),
            'tag': 'experimentA',
            'cpo_path': 'mass-inference-H-a',
            'seed': 10243,
            'label0': labels[0],
            'label1': labels[1],
            'color0': colors[0],
            'color1': colors[1],
            'kappa': kappa,
        })

    # experiment B
    for r, cb in product(['0.1', '10'], [0, 1]):
        labels = ['red', 'blue']
        colors = ['#CA0020', '#0571B0']
        if cb == 1:
            labels = labels[::-1]
            colors = colors[::-1]
        if r == '0.1':
            kappa = -1.0
        elif r == '10':
            kappa = 1.0

        options.append({
            'condition': 'nfb-%s-cb%d' % (r, cb),
            'tag': 'experimentB',
            'cpo_path': 'mass-inference-H-b',
            'seed': 10244,
            'label0': labels[0],
            'label1': labels[1],
            'color0': colors[0],
            'color1': colors[1],
            'kappa': kappa,
            'feedback': False
        })

    # experiment C
    for r, cb in product(['0.1', '10'], [0, 1]):
        colordict = {
            'blue': '#0000FF',
            'cyan': '#00FFFF',
            'gray1': '#808080',  # more reddish
            'gray2': '#508080',  # more bluish
            'green': '#008837',
            'orange': '#FF7000',
            'purple': '#330099',
            'red': '#CA0020',
            'yellow': '#FFFF00',
            'magenta': '#FF00FF',
        }

        labels = [
            ['blue', 'green'],
            ['orange', 'blue'],
            ['blue', 'yellow'],
            ['gray1', 'cyan'],
            ['cyan', 'magenta'],
            ['orange', 'cyan'],
            ['cyan', 'purple'],
            ['red', 'cyan'],
            ['cyan', 'yellow'],
            ['green', 'gray1'],
            ['gray2', 'magenta'],
            ['purple', 'gray2'],
            ['gray2', 'red'],
            ['magenta', 'green'],
            ['green', 'orange'],
            ['purple', 'green'],
            ['magenta', 'yellow'],
            ['orange', 'purple'],
            ['yellow', 'purple'],
            ['yellow', 'red']]

        colors = [[colordict[x[0]], colordict[x[1]]] for x in labels]

        # strip off the number at the end of some of the labels (like "gray1")
        expr = re.compile("([a-z]+)")
        labels = [[re.match(expr, x[0]).groups()[0],
                   re.match(expr, x[1]).groups()[0]]
                  for x in labels]

        if cb == 1:
            labels = [x[::-1] for x in labels]
            colors = [x[::-1] for x in colors]
        if r == '0.1':
            kappa = -1.0
        elif r == '10':
            kappa = 1.0

        label0, label1 = zip(*labels)
        color0, color1 = zip(*colors)

        options.append({
            'condition': 'vfb-%s-cb%d' % (r, cb),
            'tag': 'experimentC',
            'cpo_path': 'mass-inference-H-b',
            'seed': 10245,
            'label0': label0,
            'label1': label1,
            'color0': color0,
            'color1': color1,
            'kappa': kappa,
        })

    return options


def make_parser():
    parser = ArgumentParser(
        formatter_class=ArgumentDefaultsHelpFormatter)

    parser.add_argument(
        "-e", "--exp",
        required=True,
        help="Experiment version.")
    parser.add_argument(
        "-c", "--condition",
        default="*",
        help="Name of this condition.")
    parser.add_argument(
        "-t", "--tag",
        default="*",
        help="Short name to identify this stimulus set.")
    parser.add_argument(
        "-f", "--force",
        action="store_true",
        default=False,
        help="Force all tasks to be put on the queue.")

    return parser


def check(exp, val):
    if exp == "*":
        return True
    if exp == val:
        return True


if __name__ == "__main__":
    parser = make_parser()
    args = parser.parse_args()

    for opts in make_options():
        cond_ok = check(args.condition, opts['condition'])
        tag_ok = check(args.tag, opts['tag'])

        if cond_ok and tag_ok:
            params = defaults.copy()
            params.update(opts)
            params['exp'] = args.exp
            params['force'] = args.force
            build(**params)
