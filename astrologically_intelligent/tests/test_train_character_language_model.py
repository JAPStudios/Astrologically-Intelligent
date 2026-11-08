import json
import subprocess
import sys
from pathlib import Path

from src.character_language_model import CharacterLanguageModel


def test_training_cli_writes_checkpoint_and_reports_validation(tmp_path):
    app_root = Path(__file__).resolve().parents[1]
    training = tmp_path / "training.txt"
    validation = tmp_path / "validation.txt"
    checkpoint = tmp_path / "model.npz"
    training.write_text("abc " * 40, encoding="utf-8")
    validation.write_text("abc " * 12, encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(app_root / "scripts" / "train_character_language_model.py"),
            str(training),
            str(checkpoint),
            "--validation-file",
            str(validation),
            "--epochs",
            "1",
            "--steps-per-epoch",
            "2",
            "--sequence-length",
            "8",
            "--batch-size",
            "2",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["epochs_completed"] == 1
    assert report["validation_loss"] is not None
    assert checkpoint.is_file()
    assert isinstance(CharacterLanguageModel.load(checkpoint), CharacterLanguageModel)


def test_training_cli_rejects_validation_characters_outside_training_vocabulary(tmp_path):
    app_root = Path(__file__).resolve().parents[1]
    training = tmp_path / "training.txt"
    validation = tmp_path / "validation.txt"
    training.write_text("abc " * 20, encoding="utf-8")
    validation.write_text("xyz " * 20, encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(app_root / "scripts" / "train_character_language_model.py"),
            str(training),
            str(tmp_path / "model.npz"),
            "--validation-file",
            str(validation),
            "--epochs",
            "1",
            "--steps-per-epoch",
            "1",
            "--sequence-length",
            "8",
            "--batch-size",
            "2",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "outside the vocabulary" in result.stderr
