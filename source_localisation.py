import os
import numpy as np
import pandas as pd

from scipy import sparse
from sklearn.multioutput import MultiOutputClassifier
from sklearn.neighbors import KNeighborsClassifier

from simulation.lead_correlate import LeadCorrelate
import simulation.metrics as met
from simulation.plot_signal import plot_sources_at_activation
from simulation.plot_signal import plot_samples_vs_score

from sklearn.metrics import hamming_loss
from sklearn.metrics import jaccard_score
from sklearn.metrics import make_scorer
from sklearn.model_selection import cross_validate, train_test_split


plot_data = False
data_dir = 'data_15_2'
max_parcels = 15


def learning_curve(X, y, model=None):
    # runs given model (if None KNeighbours = 3 will be used) with the data
    # with different number of max sources and different number of brain
    # parcels and plots their score depending on number of samples used.

    # number of samples selected at each run

    X_train, X_test, y_train, y_test = \
        train_test_split(X, y, test_size=0.2, random_state=42)

    n_samples_grid = np.logspace(1, np.log10(len(X_train)),
                                 num=10, base=10, dtype='int')
    scores_all = pd.DataFrame(columns=['n_parcels', 'max_sources', 'scores'])

    if model is None:
        clf = KNeighborsClassifier(3)
        model = MultiOutputClassifier(clf, n_jobs=-1)

    for n_samples_train in n_samples_grid:
        model.fit(X_train.head(n_samples_train),
                  y_train[:n_samples_train])
        score = model.score(X_test, y_test)
        scores.append(score)

    n_parcels = y_train.shape[1]
    max_sources = y_train.sum(axis=1).max()
    scores_all = scores_all.append({'n_parcels': int(n_parcels),
                                    'max_sources': int(max_sources),
                                    'scores': scores},
                                   ignore_index=True)

    return scores_all, n_samples_grid


# if plot_data:
#     plot_sources_at_activation(X_train, y_train)

lead_matrix = np.load(os.path.join(data_dir, 'lead_field.npz'))
parcel_indices_leadfield = lead_matrix['parcel_indices']
L = lead_matrix['lead_field']

X = pd.read_csv(os.path.join(data_dir, 'X.csv'))
y = sparse.load_npz(os.path.join(data_dir, 'target.npz')).toarray()

X_train, X_test, y_train, y_test = \
    train_test_split(X, y, test_size=0.2, random_state=42)

lc = LeadCorrelate(L, parcel_indices_leadfield)
lc.fit(X_train, y_train)

y_pred_test = lc.predict(X_test)
y_pred_train = lc.predict(X_train)

score_test = lc.score(X_test, y_test)
score_train = lc.score(X_train, y_train)

# calculating
hl = hamming_loss(y_test, y_pred_test)
js = jaccard_score(y_test, y_pred_test, average='samples')
print('score: hamming: {:.2f}, jaccard: {:.2f}'.format(hl, js))

scoring = {'froc_score': make_scorer(met.froc_score,
                                     needs_threshold=True),
           'afroc_score': make_scorer(met.afroc_score,
                                      needs_threshold=True),
           'jaccard': make_scorer(jaccard_score,
                                  average='samples'),
           'hamming': make_scorer(hamming_loss,
                                  greater_is_better=False)}

scores = cross_validate(lc, X_train, y_train, cv=3, scoring=scoring)

scores = pd.DataFrame(scores)
print(scores)


if plot_data:
    scores_all, n_samples_grid = learning_curve(X, y, model=None)
    plot_samples_vs_score(scores_all, n_samples_grid)

# plt.figure()
# plt.plot(max_parcels_all, y_test_score, 'ro')
# plt.plot(max_parcels_all, y_train_score, 'ro')
# plt.xlabel('max parcels')
# plt.ylabel('score (avg #errors/sample/max parcels): higher is worse')
# plt.title('Results for 15 parcels')
# plt.show()
