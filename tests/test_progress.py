"""Tests for progress tracking."""

import json

import pytest

from dpreview_scraper.storage.progress import ProgressTracker


class TestProgressTracker:
    def test_starts_empty(self, tmp_path):
        tracker = ProgressTracker(tmp_path / "progress.json")
        assert len(tracker.completed) == 0
        assert len(tracker.failed) == 0
        assert tracker.total == 0

    def test_mark_completed(self, tmp_path):
        tracker = ProgressTracker(tmp_path / "progress.json")
        tracker.start(10)
        tracker.mark_completed("sony_a7v")
        assert tracker.is_completed("sony_a7v")
        assert not tracker.is_completed("canon_r5")

    def test_mark_failed(self, tmp_path):
        tracker = ProgressTracker(tmp_path / "progress.json")
        tracker.start(10)
        tracker.mark_failed("broken_camera")
        assert "broken_camera" in tracker.failed

    def test_completed_removes_from_failed(self, tmp_path):
        tracker = ProgressTracker(tmp_path / "progress.json")
        tracker.start(10)
        tracker.mark_failed("retry_camera")
        assert "retry_camera" in tracker.failed
        tracker.mark_completed("retry_camera")
        assert "retry_camera" not in tracker.failed
        assert tracker.is_completed("retry_camera")

    def test_get_remaining(self, tmp_path):
        tracker = ProgressTracker(tmp_path / "progress.json")
        tracker.start(3)
        tracker.mark_completed("cam_a")
        remaining = tracker.get_remaining(["cam_a", "cam_b", "cam_c"])
        assert remaining == ["cam_b", "cam_c"]

    def test_get_stats(self, tmp_path):
        tracker = ProgressTracker(tmp_path / "progress.json")
        tracker.start(10)
        tracker.mark_completed("cam_a")
        tracker.mark_completed("cam_b")
        tracker.mark_failed("cam_c")
        stats = tracker.get_stats()
        assert stats["total"] == 10
        assert stats["completed"] == 2
        assert stats["failed"] == 1
        assert stats["remaining"] == 8
        assert stats["progress_percent"] == 20.0

    def test_persistence(self, tmp_path):
        progress_file = tmp_path / "progress.json"
        tracker = ProgressTracker(progress_file)
        tracker.start(5)
        tracker.mark_completed("cam_a")
        tracker.mark_failed("cam_b")

        # Load from file again
        tracker2 = ProgressTracker(progress_file)
        assert tracker2.is_completed("cam_a")
        assert "cam_b" in tracker2.failed
        assert tracker2.total == 5

    def test_clear(self, tmp_path):
        progress_file = tmp_path / "progress.json"
        tracker = ProgressTracker(progress_file)
        tracker.start(5)
        tracker.mark_completed("cam_a")
        tracker.clear()
        assert len(tracker.completed) == 0
        assert tracker.total == 0
        assert not progress_file.exists()

    def test_save_creates_valid_json(self, tmp_path):
        progress_file = tmp_path / "progress.json"
        tracker = ProgressTracker(progress_file)
        tracker.start(3)
        tracker.mark_completed("cam_a")

        with open(progress_file) as f:
            data = json.load(f)
        assert "completed" in data
        assert "cam_a" in data["completed"]
        assert data["total"] == 3
