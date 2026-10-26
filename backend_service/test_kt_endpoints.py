import asyncio
import httpx


async def test_knowledge_cafe():
    base_url = "http://localhost:8000/api/v1"
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        # 1. Health
        health = await client.get("/health")
        print("Health status:", health.status_code, health.json())

        # 2. List Courses (public/unauthenticated)
        courses_res = await client.get("/kt/courses")
        print("Courses:", courses_res.status_code, len(courses_res.json()))
        assert courses_res.status_code == 200
        courses = courses_res.json()
        assert len(courses) >= 1
        course = courses[0]
        print(f"Course 0: {course['title']}, Domain: {course['domain']}, Lessons: {course['total_lessons']}")

        # 3. Get Course Detail
        course_detail_res = await client.get(f"/kt/courses/{course['id']}")
        assert course_detail_res.status_code == 200
        detail = course_detail_res.json()
        print(f"Detail lessons: {len(detail['lessons'])}, Lesson 0: {detail['lessons'][0]['title']}")

        # 4. Login to get token
        login_res = await client.post("/auth/login", json={"email": "engineer@contextfoundry.dev", "password": "Password123!"})
        if login_res.status_code != 200:
            signup_res = await client.post("/auth/signup", json={
                "name": "Test Engineer",
                "email": "engineer@contextfoundry.dev",
                "password": "Password123!"
            })
            token = signup_res.json()["access_token"]
        else:
            token = login_res.json()["access_token"]

        headers = {"Authorization": f"Bearer {token}"}

        # 5. Enroll / Resume
        enroll_res = await client.post(f"/kt/courses/{course['id']}/enroll", headers=headers)
        assert enroll_res.status_code == 200
        enroll_data = enroll_res.json()
        print("Enrollment:", enroll_data["enrollment"]["course_id"], "progress:", enroll_data["enrollment"]["overall_progress"])

        # 6. Get Lesson 1
        l1_id = detail["lessons"][0]["id"]
        lesson_res = await client.get(f"/kt/courses/{course['id']}/lessons/{l1_id}", headers=headers)
        assert lesson_res.status_code == 200
        lesson_data = lesson_res.json()
        print(f"Lesson 1 Title: {lesson_data['title']}, Takeaways: {len(lesson_data['takeaways'])}, Sources: {len(lesson_data['sources'])}")

        # 7. Knowledge Check Submit
        check_res = await client.post(
            f"/kt/courses/{course['id']}/lessons/{l1_id}/check",
            headers=headers,
            json={"selected_option_index": 1}
        )
        assert check_res.status_code == 200
        print("Check result:", check_res.json())

        # 8. Ask Doubt
        doubt_res = await client.post(
            f"/kt/courses/{course['id']}/lessons/{l1_id}/doubts",
            headers=headers,
            json={"question": "What is the difference between Statement and ITR journeys?"}
        )
        assert doubt_res.status_code == 200
        doubt_data = doubt_res.json()
        print("Doubt Answer snippet:", doubt_data["answer"][:120])

        # 9. Complete Lesson 1
        comp_res = await client.post(f"/kt/courses/{course['id']}/lessons/{l1_id}/complete", headers=headers)
        assert comp_res.status_code == 200
        comp_data = comp_res.json()
        print("Completed Lesson progress:", comp_data["enrollment"]["overall_progress"], "Next:", comp_data["next_lesson"]["title"])

        # 10. View Course Document
        doc_res = await client.get(f"/kt/courses/{course['id']}/documents?file=01-overview.md", headers=headers)
        assert doc_res.status_code == 200
        print("Document View:", doc_res.json()["file"], "lines:", doc_res.json()["total_lines"])

        print("\nAll 10 Knowledge Cafe backend integration checks PASSED successfully!")


if __name__ == "__main__":
    asyncio.run(test_knowledge_cafe())
