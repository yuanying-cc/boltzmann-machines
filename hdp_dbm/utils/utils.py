import numpy as np
from tqdm import tqdm

from rng import RNG


def batch_iter(X, batch_size=10):
    """Divide input data into batches.

    Examples
    --------
    >>> X = np.arange(36).reshape((12, 3))
    >>> for X_b in batch_iter(X, batch_size=5):
    ...     print X_b
    [[ 0  1  2]
     [ 3  4  5]
     [ 6  7  8]
     [ 9 10 11]
     [12 13 14]]
    [[15 16 17]
     [18 19 20]
     [21 22 23]
     [24 25 26]
     [27 28 29]]
    [[30 31 32]
     [33 34 35]]
    """
    X = np.asarray(X)
    for start_index in range(0, X.shape[0], batch_size):
        yield X[start_index:(start_index + batch_size)]


def tbatch_iter(X, batch_size=10):
    """Same as `batch_iter`, but with progress bar."""
    N = len(X)
    n_batches = N / batch_size + (N % batch_size > 0)
    for X_b in tqdm(batch_iter(X, batch_size=batch_size),
                    total=n_batches, leave=True, ncols=79):
        yield X_b


def make_k_folds(y, n_folds=3, shuffle=True, stratify=True, random_seed=None):
    """
    Split data into folds of (approximately) equal size.

    Parameters
    ----------
    y : (n_samples,) array-like
        The target variable for supervised learning problems.
        Stratification is done based upon the `y` labels.
    n_folds : int, `n_folds` > 1, optional
        Number of folds.
    stratify : bool, optional
        If True, the folds are made by preserving the percentage of samples
        for each class. Stratification is done based upon the `y` labels.

    Yields
    ------
    fold : np.ndarray
        Indices for current fold.

    Examples
    --------
    >>> import numpy as np
    >>> y = np.array([1, 1, 1, 2, 2, 2, 3, 3, 3])
    >>> for fold in make_k_folds(y, n_folds=3, shuffle=True, stratify=True, random_seed=1337):
    ...     print y[fold]
    [3 1 2]
    [3 2 1]
    [1 3 2]
    """
    n = len(y)
    rng = RNG(random_seed)

    if not stratify:
        indices = rng.permutation(n) if shuffle else np.arange(n, dtype=np.int)
        for fold in np.array_split(indices, n_folds):
            yield fold
        return

    # group indices
    labels_indices = {}
    for index, label in enumerate(y):
        if isinstance(label, np.ndarray):
            label = tuple(label.tolist())
        if not label in labels_indices:
            labels_indices[label] = []
        labels_indices[label].append(index)

    # split all indices label-wisely
    for label, indices in sorted(labels_indices.items()):
        labels_indices[label] = np.array_split(indices, n_folds)

    # collect respective splits into folds and shuffle if needed
    for k in xrange(n_folds):
        fold = np.concatenate([indices[k] for _, indices in sorted(labels_indices.items())])
        if shuffle:
            rng.shuffle(fold)
        yield fold


if __name__ == '__main__':
    # run corresponding tests
    from testing import run_tests
    run_tests(__file__)