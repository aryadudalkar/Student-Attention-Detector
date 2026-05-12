import requests

BASE = 'http://127.0.0.1:8000/api'

# Create students
s1 = requests.post(f'{BASE}/students/', json={'student_id': 101, 'name': 'Arpit Kumar', 'usn': '1RV22CS001'})
print('Student1:', s1.status_code, s1.json())
s2 = requests.post(f'{BASE}/students/', json={'student_id': 102, 'name': 'Rahul Sharma', 'usn': '1RV22CS002'})
print('Student2:', s2.status_code, s2.json())
s3 = requests.post(f'{BASE}/students/', json={'student_id': 103, 'name': 'Priya Singh', 'usn': '1RV22CS003'})
print('Student3:', s3.status_code, s3.json())

# Get PKs
students = requests.get(f'{BASE}/students/').json()
pk1 = [s for s in students if s['student_id']==101][0]['id']
pk2 = [s for s in students if s['student_id']==102][0]['id']
pk3 = [s for s in students if s['student_id']==103][0]['id']
print(f'PKs: {pk1}, {pk2}, {pk3}')

# Start session
r = requests.post(f'{BASE}/sessions/start/', json={'label': 'Data Structures Lecture'})
sid = r.json()['id']
print(f'Session {sid} started')

# Send attention logs
logs = []
for i in range(20):
    logs.append({'session': sid, 'student': pk1, 'attention_score': 0.82, 'label': 'Attentive', 'object_detected': 'none', 'yolo_score': 0.8, 'gaze_score': 0.85, 'head_score': 0.9, 'pitch': 3.0, 'yaw': 2.0, 'roll': 0.5})
    logs.append({'session': sid, 'student': pk2, 'attention_score': 0.35, 'label': 'Distracted (Phone)', 'object_detected': 'phone', 'yolo_score': 0.3, 'gaze_score': 0.2, 'head_score': 0.25, 'pitch': -25.0, 'yaw': 30.0, 'roll': 0.0})
    logs.append({'session': sid, 'student': pk3, 'attention_score': 0.65, 'label': 'Partially Attentive', 'object_detected': 'none', 'yolo_score': 0.6, 'gaze_score': 0.7, 'head_score': 0.6, 'pitch': -5.0, 'yaw': 10.0, 'roll': 1.0})

r2 = requests.post(f'{BASE}/logs/batch/', json={'logs': logs})
print(f'Logs: {r2.status_code} - {r2.json()}')

# End session (triggers auto-summary + auto-feedback)
r3 = requests.post(f'{BASE}/sessions/{sid}/end/')
print(f'End session: {r3.status_code}')

# Check timeline
r4 = requests.get(f'{BASE}/sessions/{sid}/timeline/')
tl = r4.json()
print(f'Timeline: {r4.status_code} - {len(tl)} buckets')
for t in tl:
    print(f"  {t['time']}: attn={t['attention_pct']}% dist={t['distraction_pct']}%")

# Check feedback
r5 = requests.get(f'{BASE}/sessions/{sid}/feedback/')
fb = r5.json()
print(f'Feedback: {r5.status_code}')
print(fb.get('overall_summary', '')[:400])
print('Peaks:', fb.get('peak_distraction_periods'))
print('Recs:', fb.get('recommendations'))

# Search students by USN
r6 = requests.get(f'{BASE}/students/?search=1RV22CS')
print(f'Search USN "1RV22CS": found {len(r6.json())} students')

# Search students by name
r7 = requests.get(f'{BASE}/students/?search=arpit')
print(f'Search name "arpit": found {len(r7.json())} students')

# Student sessions history
r8 = requests.get(f'{BASE}/students/101/sessions/')
print(f'Student 101 sessions: {r8.status_code} count={len(r8.json())}')
for s in r8.json():
    print(f"  {s['session_label']}: score={s['avg_score']} grade={s['grade']}")

# All feedbacks
r9 = requests.get(f'{BASE}/feedbacks/')
print(f'All feedbacks: {r9.status_code} count={len(r9.json())}')

print('\n=== ALL TESTS PASSED ===')
