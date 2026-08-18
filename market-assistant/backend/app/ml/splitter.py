import numpy as np
import numpy.typing as npt

IntArray = npt.NDArray[np.int_]


def purged_walk_forward_splits(
    n_samples: int,
    n_splits: int,
    test_size: int,
    purge: int,
    initial_train_size: int | None = None,
) -> list[tuple[IntArray, IntArray]]:
    if initial_train_size is None:
        initial_train_size = test_size

    splits: list[tuple[IntArray, IntArray]] = []
    for k in range(n_splits):
        train_end = initial_train_size + k * test_size
        test_start = train_end + purge
        test_end = test_start + test_size
        if test_end > n_samples:
            raise ValueError(
                f"fold {k} exceeds n_samples={n_samples} (test_end={test_end}); "
                "reduce n_splits/test_size or increase n_samples"
            )
        train_idx = np.arange(0, train_end)
        test_idx = np.arange(test_start, test_end)
        splits.append((train_idx, test_idx))
    return splits
