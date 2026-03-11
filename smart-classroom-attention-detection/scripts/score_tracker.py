"""
Per-student attention score tracker with session and weekly reporting.

Usage:
    tracker = ScoreTracker()

    # Inside the detection loop:
    tracker.update(student_id, score, label)

    # At end of session:
    path = tracker.save()
    print(tracker.get_session_summary())

    # Weekly report (aggregates all saved JSON sessions):
    print(tracker.get_weekly_report())
"""

import json
import os
from collections import defaultdict
from datetime import datetime


class ScoreTracker:
    def __init__(self, output_dir=None):
        if output_dir is None:
            # Save next to the scripts folder under attention_logs/
            output_dir = os.path.join(
                os.path.dirname(__file__), "..", "attention_logs"
            )
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

        self._scores: dict[int, list[float]] = defaultdict(list)
        self._labels: dict[int, list[str]]   = defaultdict(list)
        self._session_start = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ------------------------------------------------------------------
    # Real-time update
    # ------------------------------------------------------------------

    def update(self, student_id: int, score: float, label: str):
        """Record one attention observation for a student."""
        self._scores[student_id].append(float(score))
        self._labels[student_id].append(label)

    # ------------------------------------------------------------------
    # Session summary
    # ------------------------------------------------------------------

    def get_session_summary(self) -> dict:
        """
        Return per-student stats for the current session.

        Keys per student:
            avg_score        — mean attention score [0-1]
            total_frames     — number of observations recorded
            attentive_pct    — % frames labelled attentive (any kind)
            distracted_pct   — % frames labelled distracted (any kind)
            phone_frames     — frames where phone use was detected
            reading_frames   — frames where book reading was detected
        """
        summary = {}
        for sid, scores in self._scores.items():
            labels = self._labels[sid]
            total  = len(scores)
            if total == 0:
                continue

            avg = sum(scores) / total

            phone_frames   = sum(1 for l in labels if "Phone"    in l)
            reading_frames = sum(1 for l in labels if "Reading"  in l)
            attentive_n    = sum(1 for l in labels if "Attentive" in l)
            distracted_n   = sum(1 for l in labels if "Distracted" in l)

            summary[str(sid)] = {
                "avg_score":      round(avg, 3),
                "total_frames":   total,
                "attentive_pct":  round(attentive_n  / total * 100, 1),
                "distracted_pct": round(distracted_n / total * 100, 1),
                "phone_frames":   phone_frames,
                "reading_frames": reading_frames,
            }
        return summary

    # ------------------------------------------------------------------
    # Overlay helper (call inside your display loop)
    # ------------------------------------------------------------------

    def get_live_stats(self, student_id: int) -> dict:
        """Return rolling stats for a single student (for HUD overlay)."""
        scores = self._scores[student_id]
        labels = self._labels[student_id]
        if not scores:
            return {"avg": 0.0, "total": 0, "phone": 0, "reading": 0}

        recent = scores[-30:]  # last ~1 s at 30 fps
        return {
            "avg":     round(sum(recent) / len(recent), 2),
            "total":   len(scores),
            "phone":   sum(1 for l in labels if "Phone"   in l),
            "reading": sum(1 for l in labels if "Reading" in l),
        }

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> str:
        """
        Write session data to a JSON file and return the file path.
        File name: session_YYYYMMDD_HHMMSS.json
        """
        payload = {
            "session_start": self._session_start,
            "saved_at":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "students":      self.get_session_summary(),
        }
        filename = os.path.join(
            self.output_dir, f"session_{self._session_start}.json"
        )
        with open(filename, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        return filename

    # ------------------------------------------------------------------
    # Weekly report
    # ------------------------------------------------------------------

    def get_weekly_report(self) -> dict:
        """
        Aggregate all saved session JSON files in output_dir into a
        weekly per-student report.

        Returns:
            dict keyed by student_id with:
                weekly_avg_score  — weighted average across all sessions
                sessions_recorded — number of session files that include
                                    this student
                total_frames      — cumulative observation count
                total_phone_frames
                total_reading_frames
        """
        weekly: dict = defaultdict(lambda: {
            "weighted_sum": 0.0,
            "total_frames": 0,
            "sessions":     0,
            "phone_frames": 0,
            "reading_frames": 0,
        })

        for fname in sorted(os.listdir(self.output_dir)):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(self.output_dir, fname)
            try:
                with open(fpath, encoding="utf-8") as fh:
                    data = json.load(fh)
            except (json.JSONDecodeError, OSError):
                continue

            for sid, stats in data.get("students", {}).items():
                n = stats.get("total_frames", 0)
                if n == 0:
                    continue
                entry = weekly[sid]
                entry["weighted_sum"]   += stats.get("avg_score", 0) * n
                entry["total_frames"]   += n
                entry["sessions"]       += 1
                entry["phone_frames"]   += stats.get("phone_frames", 0)
                entry["reading_frames"] += stats.get("reading_frames", 0)

        report = {}
        for sid, e in weekly.items():
            if e["total_frames"] > 0:
                report[sid] = {
                    "weekly_avg_score":   round(
                        e["weighted_sum"] / e["total_frames"], 3
                    ),
                    "sessions_recorded":  e["sessions"],
                    "total_frames":       e["total_frames"],
                    "total_phone_frames": e["phone_frames"],
                    "total_reading_frames": e["reading_frames"],
                }
        return report

    def print_weekly_report(self):
        """Print a formatted weekly report to stdout."""
        report = self.get_weekly_report()
        if not report:
            print("No session data found.")
            return
        print("\n" + "=" * 50)
        print("  WEEKLY ATTENTION REPORT")
        print("=" * 50)
        for sid, data in sorted(report.items(), key=lambda x: int(x[0])):
            grade = _score_to_grade(data["weekly_avg_score"])
            print(
                f"  Student {sid:>3}: "
                f"avg={data['weekly_avg_score']:.3f}  "
                f"grade={grade}  "
                f"sessions={data['sessions_recorded']}  "
                f"phone_frames={data['total_phone_frames']}  "
                f"reading_frames={data['total_reading_frames']}"
            )
        print("=" * 50 + "\n")


def _score_to_grade(score: float) -> str:
    if score >= 0.85:
        return "A  (Excellent)"
    if score >= 0.70:
        return "B  (Good)"
    if score >= 0.55:
        return "C  (Average)"
    if score >= 0.40:
        return "D  (Below Average)"
    return "F  (Poor)"
