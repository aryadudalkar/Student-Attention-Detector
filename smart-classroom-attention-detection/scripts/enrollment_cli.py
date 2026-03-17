"""
CLI tool for enrolling/managing students in the ArcFace registry.

Usage:
    python enrollment_cli.py enroll "John Doe" path/to/photo.jpg
    python enrollment_cli.py list
    python enrollment_cli.py delete 1
    python enrollment_cli.py capture "Jane Smith"
"""

import sys
import os
import cv2
from student_registry import enroll_student, list_students, delete_student, clear_all_students


def capture_student_photo(name: str):
    """
    Capture student photo from webcam.

    Press SPACE to capture, ESC to cancel.
    """
    print(f"\n[INFO] Opening webcam for {name}")
    print("[INFO] Press SPACE to capture, ESC to cancel\n")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Could not open webcam")
        return None

    frame = None
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        cv2.imshow(f"Capture Photo for {name}", frame)
        key = cv2.waitKey(1) & 0xFF

        if key == 32:  # SPACE
            cv2.destroyAllWindows()
            cap.release()

            base = os.path.dirname(__file__)
            photo_dir = os.path.join(base, "..", "student_photos")
            os.makedirs(photo_dir, exist_ok=True)
            safe_name = name.replace(" ", "_").replace("/", "_")
            photo_path = os.path.join(photo_dir, f"{safe_name}_{len(os.listdir(photo_dir))}.jpg")

            cv2.imwrite(photo_path, frame)
            print(f"[INFO] Photo saved: {photo_path}")
            return photo_path

        elif key == 27:  # ESC
            break

    cap.release()
    cv2.destroyAllWindows()
    return None


def cmd_enroll(name: str, photo_path: str, usn: str = ""):
    """Enroll student with existing photo."""
    if not os.path.exists(photo_path):
        print(f"[ERROR] Photo not found: {photo_path}")
        return

    success = enroll_student(name, photo_path, usn=usn)
    if success:
        usn_display = f" (USN: {usn})" if usn else ""
        print(f"[SUCCESS] Student '{name}'{usn_display} enrolled")
    else:
        print(f"[ERROR] Could not enroll '{name}'")


def cmd_capture(name: str, usn: str = ""):
    """Enroll student by capturing photo from webcam."""
    # Ask for USN if not provided
    if not usn:
        usn = input("\nEnter student USN (or press ENTER to skip): ").strip()

    photo_path = capture_student_photo(name)
    if photo_path:
        success = enroll_student(name, photo_path, usn=usn)
        if success:
            usn_display = f" (USN: {usn})" if usn else ""
            print(f"[SUCCESS] Student '{name}'{usn_display} enrolled")


def cmd_list():
    """List all enrolled students."""
    students = list_students()
    if not students:
        print("[INFO] No students enrolled yet")
        return

    print("\n" + "=" * 80)
    print("ENROLLED STUDENTS")
    print("=" * 80)
    for student in students:
        usn_display = student['usn'] if student['usn'] else "N/A"
        usn_id = f"#{usn_display[-3:]}" if student['usn'] else f"ID:{student['student_id']}"
        print(
            f"  {usn_id:8s}  |  {student['name']:25s}  |  USN: {usn_display:15s}  |  "
            f"{student['enrollment_date'][:10]}"
        )
    print("=" * 80 + "\n")


def cmd_delete(student_id: int):
    """Delete enrolled student."""
    delete_student(student_id)


def cmd_clear():
    """Clear all enrolled students (with confirmation)."""
    response = input(
        "[WARNING] Clear ALL students? This cannot be undone. Type 'yes' to confirm: "
    )
    if response.lower() == "yes":
        clear_all_students()
    else:
        print("[INFO] Cancelled")


def print_usage():
    """Print usage instructions."""
    print(
        """
Usage: python enrollment_cli.py <command> [args]

Commands:
  enroll <name> <photo_path> [usn]   Enroll student with photo file and optional USN
  capture <name> [usn]               Enroll student by capturing from webcam (prompts for USN if not provided)
  list                               List all enrolled students
  delete <student_id>                Delete student by ID
  clear                              Clear all students (DANGEROUS)

Examples:
  python enrollment_cli.py enroll "John Doe" path/to/photo.jpg 1234567890
  python enrollment_cli.py capture "Jane Smith"
  python enrollment_cli.py capture "Jane Smith" 1234567890
  python enrollment_cli.py list
  python enrollment_cli.py delete 1
  python enrollment_cli.py clear

Note: USN (University Serial Number) will be used to display last 3 digits as student ID.
"""
    )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    cmd = sys.argv[1].lower()

    try:
        if cmd == "enroll":
            if len(sys.argv) < 4:
                print("[ERROR] Usage: enrollment_cli.py enroll <name> <photo_path> [usn]")
                sys.exit(1)
            name = sys.argv[2]
            photo = sys.argv[3]
            usn = sys.argv[4] if len(sys.argv) > 4 else ""
            cmd_enroll(name, photo, usn=usn)

        elif cmd == "capture":
            if len(sys.argv) < 3:
                print("[ERROR] Usage: enrollment_cli.py capture <name> [usn]")
                sys.exit(1)
            name = sys.argv[2]
            usn = sys.argv[3] if len(sys.argv) > 3 else ""
            cmd_capture(name, usn=usn)

        elif cmd == "list":
            cmd_list()

        elif cmd == "delete":
            if len(sys.argv) < 3:
                print("[ERROR] Usage: enrollment_cli.py delete <student_id>")
                sys.exit(1)
            student_id = int(sys.argv[2])
            cmd_delete(student_id)

        elif cmd == "clear":
            cmd_clear()

        else:
            print(f"[ERROR] Unknown command: {cmd}")
            print_usage()
            sys.exit(1)

    except Exception as e:
        print(f"[ERROR] {e}")
        sys.exit(1)
