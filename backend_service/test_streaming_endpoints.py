import json
import requests
import time

BASE_URL = "http://localhost:8000"

def get_auth_token():
    login_res = requests.post(f"{BASE_URL}/api/v1/auth/login", json={"email": "engineer@contextfoundry.dev", "password": "Password123!"})
    if login_res.status_code != 200:
        signup_res = requests.post(f"{BASE_URL}/api/v1/auth/signup", json={
            "name": "Test Engineer",
            "email": "engineer@contextfoundry.dev",
            "password": "Password123!"
        })
        return signup_res.json()["access_token"]
    return login_res.json()["access_token"]

def parse_sse_stream(response):
    events = []
    for line in response.iter_lines(decode_unicode=True):
        if not line:
            continue
        if line.startswith("data: "):
            raw_data = line[6:]
            try:
                events.append(json.loads(raw_data))
            except Exception as e:
                print(f"Error parsing SSE json: {raw_data}, error: {e}")
    return events

def test_query_stream(token):
    print("\n--- Testing POST /api/v1/query/stream ---")
    url = f"{BASE_URL}/api/v1/query/stream"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "query": "Briefly explain the role of income-assessment-service.",
        "service": "income-assessment-service",
        "top_k": 3,
    }
    res = requests.post(url, json=payload, headers=headers, stream=True)
    assert res.status_code == 200, f"Query stream failed: {res.status_code} {res.text}"
    events = parse_sse_stream(res)
    print(f"Total SSE events received: {len(events)}")
    
    event_types = [e.get("type") for e in events]
    print(f"Event types received: {set(event_types)}")
    assert "metadata" in event_types, "Missing metadata event"
    assert "chunk" in event_types, "Missing chunk event"
    assert "done" in event_types, "Missing done event"

    metadata = next(e for e in events if e.get("type") == "metadata")
    done = next(e for e in events if e.get("type") == "done")
    chunks = [e["text"] for e in events if e.get("type") == "chunk"]
    full_text = "".join(chunks)

    print(f"Metadata: sources count={len(metadata.get('sources', []))}, model={metadata.get('model')}")
    print(f"Streamed chunks count: {len(chunks)}, full length: {len(full_text)}")
    print(f"Snippet: {full_text[:120]}...")
    print(f"Done event: latency_ms={done.get('latency_ms')}, message_id={done.get('message_id')}")

def test_doubt_stream(token):
    print("\n--- Testing POST /api/v1/kt/courses/{course_id}/lessons/{lesson_id}/doubts/stream ---")
    url = f"{BASE_URL}/api/v1/kt/courses/income-assessment-kt/lessons/01-service-overview/doubts/stream"
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "question": "What is the primary function of income-assessment-service in one sentence?",
    }
    res = requests.post(url, json=payload, headers=headers, stream=True)
    assert res.status_code == 200, f"Doubt stream failed: {res.status_code} {res.text}"
    events = parse_sse_stream(res)
    print(f"Total SSE doubt events received: {len(events)}")
    
    event_types = [e.get("type") for e in events]
    print(f"Doubt event types: {set(event_types)}")
    assert "metadata" in event_types, "Missing metadata event in doubt"
    assert "chunk" in event_types, "Missing chunk event in doubt"
    assert "done" in event_types, "Missing done event in doubt"

    done = next(e for e in events if e.get("type") == "done")
    chunks = [e["text"] for e in events if e.get("type") == "chunk"]
    print(f"Doubt answer: {''.join(chunks)}")
    print(f"Saved doubt ID: {done.get('doubt', {}).get('id')}")

def test_lesson_stream(token):
    print("\n--- Testing GET /api/v1/kt/courses/{course_id}/lessons/{lesson_id}/stream ---")
    url = f"{BASE_URL}/api/v1/kt/courses/income-assessment-kt/lessons/01-service-overview/stream"
    headers = {"Authorization": f"Bearer {token}"}
    res = requests.get(url, headers=headers, stream=True)
    assert res.status_code == 200, f"Lesson stream failed: {res.status_code} {res.text}"
    events = parse_sse_stream(res)
    print(f"Total SSE lesson events received: {len(events)}")
    
    event_types = [e.get("type") for e in events]
    print(f"Lesson event types: {set(event_types)}")
    assert "metadata" in event_types
    assert "chunk" in event_types
    assert "done" in event_types

    chunks = [e["text"] for e in events if e.get("type") == "chunk"]
    print(f"Streamed lesson length: {len(''.join(chunks))}")

if __name__ == "__main__":
    token = get_auth_token()
    test_query_stream(token)
    test_doubt_stream(token)
    test_lesson_stream(token)
    print("\nAll Streaming Backend Tests PASSED successfully!")
