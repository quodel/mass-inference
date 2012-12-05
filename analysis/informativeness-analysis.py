# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <codecell>

# imports
import collections
import matplotlib.cm as cm
import matplotlib.gridspec as gridspec
import numpy as np
import pdb
import pickle
import scipy.stats
import os
import time

#import cogphysics
#import cogphysics.lib.circ as circ
#import cogphysics.lib.nplib as npl
from cogphysics import path as cppath
from cogphysics import CPOBJ_LIST_PATH
import cogphysics.lib.rvs as rvs

import cogphysics.tower.analysis_tools as tat
import cogphysics.tower.mass.model_observer as mo
import cogphysics.tower.mass.learning_analysis_tools as lat

from cogphysics.lib.corr import xcorr

# <codecell>

# global variables
normalize = rvs.util.normalize
weightedSample = rvs.util.weightedSample

cmap = lat.make_cmap("lh", (0, 0, 0), (.5, .5, .5), (1, 0, 0))

# <codecell>

######################################################################
## Load and process data
out = lat.load('stability')
rawhuman, rawhstim, raworder, rawtruth, rawipe, kappas = out

# <codecell>

ratios = 10 ** kappas
ratios[kappas < 0] = np.round(ratios[kappas < 0], decimals=2)
ratios[kappas >= 0] = np.round(ratios[kappas >= 0], decimals=1)

# human, stimuli, sort, truth, ipe = lat.order_by_trial(
#     rawhuman, rawhstim, raworder, rawtruth, rawipe)
# truth = truth[0]
# ipe = ipe[0]

stimuli = rawhstim[None, :].copy()
truth = rawtruth.copy()
ipe = rawipe.copy()

# variables
n_trial      = stimuli.shape[1]
n_kappas     = len(kappas)

# <codecell>

nthresh0 = 1
nthresh = 4
nsamps = 300
ext = ['png', 'pdf']
f_save = False
f_close = False
smooth = True
idx = int(np.nonzero(ratios==10)[0][0])

# <codecell>

feedback, ipe_samps = lat.make_observer_data(
    nthresh0, nthresh, nsamps, order=False)
model_lh, model_joint, model_theta = mo.ModelObserver(
    ipe_samps,
    feedback[:, None],
    outcomes=None,
    respond=False,
    smooth=smooth)

# <codecell>

def KL(qi, axis=-1):
    """Compute the KL divergence between qi and pi, where pi is a
    multinomial centered around idx (defined above).

    """
    pi = np.zeros(ratios.shape) + (1./n_kappas)
    pi[idx] += nsamps
    pi /= nsamps + 1
    kl = np.sum(np.log(pi / qi)*pi, axis=axis)
    return kl
    

# <codecell>

plt.close('all')

# figure out the starting stimulus (minimum entropy=most information)
fb = feedback[:, idx, 0]
lh = model_lh[idx, 1:].copy()
p = normalize(lh, axis=-1)[1]
H = KL(np.exp(p))

order = [np.argmin(H)]
nums = [stimuli[0, order[0]].split("_")[1]]
    
joint = lh[order[0]].copy()
allJoint = [joint.copy()]
allH = [H[order[0]]]

T = 48
for t in xrange(T-1):
    # calculate possible posterior values for each stimulus
    p = normalize(joint[None, :] + lh, axis=-1)[1]
    # compute entropies
    H = KL(np.exp(p))
    # choose stimulus that would result in the lowest entropy, without
    # repeating stimuli
    for s in np.argsort(H):
	num = stimuli[0, s].split("_")[1]
	if (s not in order) and (num not in nums):
	    order.append(s)
	    nums.append(num)
	    allH.append(H[s])
	    joint += lh[order[-1]]
	    allJoint.append(joint.copy())
	    break

order = np.array(order)
nums = np.array(nums)
allJoint = np.array(allJoint)
allH = np.array(allH)    

plt.figure()
plt.clf()
plt.suptitle(ratios[idx])
plt.subplot(1, 2, 1)
plt.plot(allH)
plt.ylim(0, 3)

lat.plot_theta(
    1, 2, 2,
    np.exp(normalize(allJoint, axis=-1)[1]),
    "",
    exp=1.3,
    cmap=cmap,
    fontsize=14)

# <codecell>

N = 30
yes = np.nonzero(fb[order] == 0)[0]
no = np.nonzero(fb[order] == 1)[0]
eqorder = order[np.sort(np.hstack([yes[:N/2], no[:N/2]]))]
print eqorder[:N]
print stimuli[0, eqorder[:N]]
print fb[eqorder[:N]]
print np.sum(fb[eqorder[:N]])

# <codecell>

np.random.shuffle(eqorder)
print eqorder 
exp_ipe_samps = ipe_samps[eqorder]
exp_feedback = feedback[eqorder][:, [idx]]

exp_lh, exp_joint, exp_theta = mo.ModelObserver(
    exp_ipe_samps,
    exp_feedback[:, None],
    outcomes=None,
    respond=False,
    smooth=smooth)

lat.plot_theta(
    1, 1, 1,
    np.exp(exp_theta[0]),
    "",
    exp=1.3,
    cmap=cmap,
    fontsize=14)

# <codecell>

exp_stims = ["%s~kappa-%s" % (x, kappas[idx]) for x in np.sort(stimuli[0, eqorder])]
listpath = cppath(CPOBJ_LIST_PATH, 'local')
l = os.path.join(listpath, "mass-towers-stability-learning~kappa-%s" % kappas[idx])
with open(l, "w") as fh:
    lines = "\n".join(exp_stims)
    fh.write(lines)
    

