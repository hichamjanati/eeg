import numpy as np
import pandas as pd

from sklearn.base import BaseEstimator, ClassifierMixin, TransformerMixin
from sklearn.multioutput import MultiOutputRegressor


def _get_coef(est):
    if hasattr(est, 'steps'):
        return est.steps[-1][1].coef_
    return est.coef_


class SparseRegressor(BaseEstimator, ClassifierMixin, TransformerMixin):
    def __init__(self, lead_field, parcel_indices, model, n_jobs=1):
        self.lead_field = lead_field
        self.parcel_indices = parcel_indices
        self.model = model
        self.n_jobs = n_jobs

    def fit(self, X, y):
        return self

    def predict(self, X):
        return (self.decision_function(X) > 0).astype(int)

    def decision_function(self, X):
        model = MultiOutputRegressor(self.model, n_jobs=self.n_jobs)
        X = X.reset_index(drop=True)

        betas = np.empty((len(X), 0)).tolist()
        for subj_idx in np.unique(X['subject_id']):
            l_used = self.lead_field[subj_idx]

            X_used = X[X['subject_id'] == subj_idx]
            X_used = X_used.iloc[:, :-2]

            norms = l_used.std(axis=0)
            l_used = l_used / norms[None, :]

            alpha_max = abs(l_used.T.dot(X_used.T)).max() / len(l_used)
            alpha = 0.3 * alpha_max
            model.estimator.alpha = alpha
            model.fit(l_used, X_used.T)  # cross validation done here

            for idx, idx_used in enumerate(X_used.index.values):
                est_coef = np.abs(_get_coef(model.estimators_[idx]))
                est_coef /= norms
                beta = pd.DataFrame(
                        np.abs(est_coef)
                        ).groupby(
                        self.parcel_indices[subj_idx]).max().transpose()
                betas[idx_used] = np.array(beta).ravel()
        betas = np.array(betas)
        return betas
