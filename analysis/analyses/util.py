from ConfigParser import SafeConfigParser
from path import path
import numpy as np
import sys

from mass.analysis import load_human as _load_human
from mass.analysis import load_model as _load_model
from mass.analysis import load_all as _load_all
from mass.analysis import load_participants as _load_participants
from mass.analysis import bootcorr, beta, sigmoid


MAX_LOG = np.log(sys.float_info.max)


def normalize(logarr, axis=-1):
    """Normalize an array of log-values.

    This function is very useful if you have an array of log
    probabilities that need to be normalized, but some of the
    probabilies might be extremely small (i.e., underflow will occur if
    you try to exponentiate them). This function computes the
    normalization constants in log space, thus avoiding the need to
    exponentiate the values.

    Parameters
    ----------
    logarr: numpy.ndarray
        Array of log values
    axis: integer (default=-1)
        Axis over which to normalize

    Returns
    -------
    out: (numpy.ndarray, numpy.ndarray)
        2-tuple consisting of the log normalization constants used to
        normalize the array, and the normalized array of log values

    """

    # shape for the normalization constants (that would otherwise be
    # missing axis)
    shape = list(logarr.shape)
    shape[axis] = 1
    # get maximum value of array
    maxlogarr = logarr.max(axis=axis).reshape(shape)
    # calculate how much to shift the array up by
    shift = MAX_LOG - maxlogarr - 2 - logarr.shape[axis]
    shift[shift < 0] = 0
    # shift the array
    unnormed = logarr + shift
    # convert from logspace
    arr = np.exp(unnormed)
    # calculate shifted log normalization constants
    _lognormconsts = np.log(arr.sum(axis=axis)).reshape(shape)
    # calculate normalized array
    lognormarr = unnormed - _lognormconsts
    # unshift normalization constants
    _lognormconsts -= shift
    # get rid of the dimension we normalized over
    lognormconsts = _lognormconsts.sum(axis=axis)

    return lognormconsts, lognormarr


def load_human():
    root = path("..")
    config = SafeConfigParser()
    config.read(root.joinpath("config.ini"))
    human_version = config.get("analysis", "human_version")
    data_path = root.joinpath(
        config.get("analysis", "data_path")).relpath()
    human = _load_human(human_version, data_path)
    return human


def load_participants():
    root = path("..")
    config = SafeConfigParser()
    config.read(root.joinpath("config.ini"))
    human_version = config.get("analysis", "human_version")
    data_path = root.joinpath(
        config.get("analysis", "data_path")).relpath()
    human = _load_participants(human_version, data_path)
    return human


def load_model():
    root = path("..")
    config = SafeConfigParser()
    config.read(root.joinpath("config.ini"))
    model_version = config.get("analysis", "model_version")
    sigma = config.getfloat("analysis", "sigma")
    phi = config.getfloat("analysis", "phi")
    data_path = root.joinpath(
        config.get("analysis", "data_path")).relpath()
    ipe, fb = _load_model(model_version, data_path, sigma=sigma, phi=phi)
    return ipe, fb


def load_all():
    root = path("..")
    config = SafeConfigParser()
    config.read(root.joinpath("config.ini"))
    human_version = config.get("analysis", "human_version")
    model_version = config.get("analysis", "model_version")
    sigma = config.getfloat("analysis", "sigma")
    phi = config.getfloat("analysis", "phi")
    data_path = root.joinpath(
        config.get("analysis", "data_path")).relpath()
    data = _load_all(
        model_version=model_version,
        human_version=human_version,
        data_path=data_path,
        sigma=sigma,
        phi=phi)
    return data


def run_analysis(func, filename):
    root = path("..")
    config = SafeConfigParser()
    config.read(root.joinpath("config.ini"))
    seed = config.getint("analysis", "seed")

    func(filename, seed)


def get_params():
    root = path("..")
    config = SafeConfigParser()
    config.read(root.joinpath("config.ini"))
    sigma = config.getfloat("analysis", "sigma")
    phi = config.getfloat("analysis", "phi")
    return sigma, phi


def get_query():
    root = path("..")
    config = SafeConfigParser()
    config.read(root.joinpath("config.ini"))
    query = config.get("analysis", "query")
    return query
