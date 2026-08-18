import pickle
from pathlib import Path
from typing import Any

DEFAULT_MODEL_ARTIFACT_DIR = Path("/data/ml_models")  # Fly volume mount point in production


def save_artifact(
    obj: Any,
    instrument_group: str,
    version: str,
    base_dir: Path | None = None,
    overwrite: bool = False,
) -> str:
    target_dir = base_dir if base_dir is not None else DEFAULT_MODEL_ARTIFACT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{instrument_group}_{version}.pkl"
    # Refuse to clobber an existing artifact: overwriting silently would replace
    # a live, gated model with an unvetted one under the same (group, version).
    if path.exists() and not overwrite:
        raise FileExistsError(
            f"artifact already exists: {path}. Bump the version or pass overwrite=True."
        )
    with open(path, "wb") as f:
        pickle.dump(obj, f)
    return str(path)


def load_artifact(path: str) -> Any:
    with open(path, "rb") as f:
        return pickle.load(f)
