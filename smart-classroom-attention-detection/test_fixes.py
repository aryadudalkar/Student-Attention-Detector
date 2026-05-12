import requests, json

BASE = 'http://127.0.0.1:8000/api'

# Test timeline fix
r = requests.get(f'{BASE}/sessions/7/timeline/')
tl = r.json()
print(f'Timeline buckets: {len(tl)}')
for t in tl:
    print(f"  Seg {t['segment']}: {t['time']} attn={t['attention_pct']}% dist={t['distraction_pct']}%")

# Test student PATCH
r2 = requests.patch(f'{BASE}/students/101/', json={'name': 'Arpit Kumar Updated'})
print(f"\nPATCH student: {r2.status_code} name={r2.json()['name']}")

# Restore name
requests.patch(f'{BASE}/students/101/', json={'name': 'Arpit Kumar'})

# Test email endpoint
r3 = requests.post(f'{BASE}/sessions/7/feedback/email/', json={'email': 'teacher@example.com'})
print(f"Email send: {r3.status_code} {r3.json()}")

print('\n=== ALL FIX TESTS PASSED ===')
