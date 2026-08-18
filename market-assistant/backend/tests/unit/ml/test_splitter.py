import pytest

from app.ml.splitter import purged_walk_forward_splits


def test_exact_fold_indices_for_hand_computed_case():
    # n=30, n_splits=3, test_size=5, purge=2, initial_train_size defaults to test_size=5.
    # fold0: train=[0,5)   test=[7,12)
    # fold1: train=[0,10)  test=[12,17)
    # fold2: train=[0,15)  test=[17,22)
    splits = purged_walk_forward_splits(n_samples=30, n_splits=3, test_size=5, purge=2)

    assert len(splits) == 3

    train0, test0 = splits[0]
    assert list(train0) == list(range(0, 5))
    assert list(test0) == list(range(7, 12))

    train1, test1 = splits[1]
    assert list(train1) == list(range(0, 10))
    assert list(test1) == list(range(12, 17))

    train2, test2 = splits[2]
    assert list(train2) == list(range(0, 15))
    assert list(test2) == list(range(17, 22))


def test_folds_are_strictly_time_ordered_purge_gapped_and_non_overlapping():
    splits = purged_walk_forward_splits(n_samples=100, n_splits=6, test_size=8, purge=3)

    prev_train_end = -1
    prev_test_end = -1
    for train_idx, test_idx in splits:
        # Train grows monotonically (expanding window).
        assert train_idx.max() > prev_train_end or len(train_idx) == 0
        # No overlap between train and test in this fold.
        assert set(train_idx).isdisjoint(set(test_idx))
        # Exact purge gap between train end and test start.
        assert test_idx.min() - train_idx.max() - 1 == 3
        # Test folds never overlap each other and strictly advance in time.
        assert test_idx.min() > prev_test_end
        prev_train_end = train_idx.max()
        prev_test_end = test_idx.max()


def test_raises_when_last_fold_would_exceed_n_samples():
    with pytest.raises(ValueError, match="exceeds n_samples"):
        purged_walk_forward_splits(n_samples=20, n_splits=5, test_size=5, purge=2)
