import numpy as np
import os
from simulation.emd import emd_score


def get_true_false(true_signal, pred_signal):
    # given true and predicted signal 1d array of 0s and 1s
    # return true_positive, true_negative, false_positive, false_negative
    unique, counts = np.unique(true_signal - pred_signal, return_counts=True)
    try:
        false_positive = counts[np.where(unique == -1)][0]
    except IndexError:
        false_positive = 0

    try:
        true_negative = counts[np.where(unique == 1)][0]
    except IndexError:
        true_negative = 0

    unique, counts = np.unique(true_signal + pred_signal, return_counts=True)
    try:
        true_positive = counts[np.where(unique == 2)][0]
    except IndexError:
        true_positive = 0

    try:
        false_negative = counts[np.where(unique == 0)][0]
    except IndexError:
        false_negative = 0

    assert len(true_signal) == (true_positive + true_negative +
                                false_positive + false_negative)
    return true_positive, true_negative, false_positive, false_negative


def calc_froc(y_true, y_score):
    """compute Free response receiver operating characteristic curve (FROC)
    Note: this implementation is restricted to the binary classification
    task.

    Parameters
    ----------
    y_true : array, shape = [n_samples x n_classes]
             true binary labels
    y_score : array, shape = [n_samples x n_classes]
             target scores: probability estimates of the positive class,
             confidence values
    Returns
    -------
    ts : array
        sensitivity: true positive normalized by sum of all true
        positives
    tfp : array
        false positive: False positive rate divided by length of
        y_true
    thresholds : array, shape = [>2]
        Thresholds on y_score used to compute ts and tfp.
        *Note*: Since the thresholds are sorted from low to high values,
        they are reversed upon returning them to ensure they
        correspond to both fpr and tpr, which are sorted in reversed order
        during their calculation.

    References
    ----------
    http://www.devchakraborty.com/Receiver%20operating%20characteristic.pdf
    https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3679336/pdf/nihms458993.pdf
    """

    n_samples, n_sources = y_true.shape
    classes = np.unique(y_true)

    n_pos = float(np.sum(y_true == classes[1]))  # nb of true positive

    y_true = np.ravel(y_true)
    y_score = np.ravel(y_score)

    # FROC only for binary classification
    if classes.shape[0] != 2:
        raise ValueError("FROC is defined for binary classification only")

    thresholds, indicesList = np.unique(y_score, return_index=True)

    # sensitivity: true positive normalized by sum of all true
    # positives
    ts = np.zeros(thresholds.size, dtype=np.float)
    # false positive: False positives rate divided by length of y_true
    tfp = np.zeros(thresholds.size, dtype=np.float)

    idx = 0

    signal = np.c_[y_score, y_true]
    # take only those values which are unique at y_score
    sorted_signal = signal[indicesList, :][::-1]
    for score, value in sorted_signal:
        t_est = sorted_signal[:, 0] >= score

        tps, _, fps, _ = get_true_false(sorted_signal[:, 1], t_est)

        ts[idx] = tps
        tfp[idx] = fps

        idx += 1

    tfp = tfp / n_samples
    ts = ts / n_pos
    return ts, tfp, thresholds[::-1]


def emd_score_subjects(subjects, y_true, y_pred, data_dir):
    """
    given a list of subjects used in each sample, y_true and y_pred it
    calculates the emd score for each of the subjects and combines it into
    a single score. EMD score calculates the distance between the center of
    mass of the predicted and true parcels. The ideal EMD score is 0.0.

    Parameters
    ----------
    subjects : array of string, each element in the list corresponds to each
        sample and must be given in the correct order, the same as in y_true
        and y_pred
    y_true : array, shape = [n_samples x n_classes]
             target scores: probability estimates of the positive class,
             confidence values
    Returns
    -------
    ts : array
    """

    assert len(subjects) == len(y_true) == len(y_pred)
    assert y_true.shape == y_pred.shape
    assert os.path.exists(data_dir)
    unique_subj = np.unique(subjects)

    scores = np.empty(len(unique_subj))

    for idx, subject in enumerate(unique_subj):
        sbj_idc = np.where(subjects == subject)[0]
        score = emd_score_subj(y_true[sbj_idc], y_pred[sbj_idc],
                               data_dir, subject)
        scores[idx] = score * (len(sbj_idc) / len(subjects))  # normalize
    score = np.sum(scores)
    return score


def emd_score_subj(y_true, y_pred, data_dir, subject):

    labels_x = np.load(os.path.join(data_dir,
                                    subject + '_labels.npz'),
                       allow_pickle=True)['arr_0']
    score = emd_score(y_true, y_pred, labels_x)

    return score


def calc_afroc(y_true, y_score):
    """compute Alternative Free response receiver operating characteristic
    curve (FROC)
    Note: this implementation is restricted to the binary classification
    task.

    Parameters
    ----------
    y_true : array, shape = [n_samples x n_classes]
             true binary labels
    y_score : array, shape = [n_samples x n_classes]
             target scores: probability estimates of the positive class,
             confidence values
    Returns
    -------
    ts : array
        sensitivity: true positive normalized by sum of all true
        positives
    fpf : array
        false positive fraction
    thresholds : array, shape = [>2]
        Thresholds on y_score used to compute ts and tfp.
        *Note*: Since the thresholds are sorted from low to high values,
        they are reversed upon returning them to ensure they
        correspond to both fpr and tpr, which are sorted in reversed order
        during their calculation.

    References
    ----------
    https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3679336/pdf/nihms458993.pdf
    """

    ts, tfp, thresholds = calc_froc(y_true, y_score)
    fpf = 1 - np.e**(-tfp)
    return ts, fpf, thresholds


def froc_score(y_true, y_score):
    ''' Compute Area Under the Free response receiver operating characteristic
        Curve (FROC AUC) from prediction scores
    '''

    ts, tfp, thresholds = calc_froc(y_true, y_score)

    # Compute the area using the composite trapezoidal rule.
    area = np.trapz(y=ts, x=tfp)
    return area


def afroc_score(y_true, y_score):
    ''' Compute Area Under the Alternative Free response receiver operating
        characteristic Curve (FROC AUC) from prediction scores

        True Positive fraction vs. false positive fraction (FPF) termed the
        alternative FROC (AFROC).
        Since the AFROC curve is completelycontained within the unit square,
        since both axes are probabilities analogous to the area under the ROC
        curve, the area under the AFROC be used as a figure-of-merit for FROC
        performance
        [1] https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3679336/pdf/nihms
            458993.pdf

    '''
    ts, fpf, thresholds = calc_afroc(y_true, y_score)

    # Compute the area using the composite trapezoidal rule.
    area = np.trapz(y=ts, x=fpf)
    return area

# def plot_froc():
#     """Plots the FROC curve (Free response receiver operating
#        characteristic curve)
#     """
#     threshs = thresholds[::-1]
#     plt.figure()
#     plt.plot(tfp, ts, 'ro')
#     plt.xlabel('false positives per sample', fontsize=12)
#     plt.ylabel('sensitivity', fontsize=12)
#     thresh = threshs(5).astype(str)[::100]
#     for fp, ts, t in zip(tfp, ts, thresh):
#         plt.text(fp, ts - 0.025, t, rotation=45)
#     plt.title('FROC, max parcels: ' + str(self.n_sources_))
