"""API Integration tests for Resource Catalogue (CA-3).

Directly verifies:
- TC-F4-07: Resource cannot be published without required metadata
- TC-F4-08: Resource skill tag must correspond to a canonical skill in taxonomy
- TC-F4-10: Inactive resource does not appear in student search results
"""


def test_tc_f4_07_resource_missing_skill_tags_rejected(client, admin_token):
    """TC-F4-07: Verify a resource cannot be published without skill tags (BR-01, REQ-F4-08)."""
    # Resource with empty skill tags list
    payload = {
        "title": "Intro to Go",
        "description": "Learn Go programming fundamentals with hands-on exercises.",
        "item_type": "course",
        "level": "beginner",
        "source_url": "https://example.com/go-intro",
        "skill_tags": [],
    }

    response = client.post(
        "/api/v1/catalogue",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=payload,
    )

    # Must be rejected with 422 Unprocessable Entity
    assert response.status_code == 422
    data = response.json()
    assert "skill_tags" in str(data)


def test_tc_f4_07_resource_missing_title_or_invalid_url_rejected(client, admin_token):
    """TC-F4-07: Missing required fields or malformed URL are rejected."""
    # Invalid URL
    payload_bad_url = {
        "title": "Valid Title Here",
        "description": "Valid description of at least ten characters.",
        "item_type": "course",
        "level": "beginner",
        "source_url": "not-a-valid-http-url",
        "skill_tags": [{"skill_id": 1, "coverage_level": "beginner"}],
    }

    resp = client.post(
        "/api/v1/catalogue",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=payload_bad_url,
    )
    assert resp.status_code == 422


def test_tc_f4_08_unknown_skill_tag_rejected_with_suggestions(client, admin_token):
    """TC-F4-08: Unknown skill tag rejected with suggestions for closest canonical skills."""
    payload = {
        "title": "Quantum Blockchain Masterclass",
        "description": "Advanced conceptual study into quantum blockchain architectures.",
        "item_type": "course",
        "level": "advanced",
        "source_url": "https://example.com/quantum",
        "skill_tags": [{"skill_name": "Blockchain Quantum", "coverage_level": "advanced"}],
    }

    response = client.post(
        "/api/v1/catalogue",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=payload,
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert "Blockchain Quantum" in detail
    assert "canonical skill" in detail


def test_tc_f4_08_skill_alias_resolves_to_canonical(client, admin_token):
    """TC-F4-08: Tagging by known alias resolves cleanly to canonical skill (CONTRACTS.md §2)."""
    # "docker containers" is seeded as an alias to canonical "Docker" in conftest
    payload = {
        "title": "Container Orchestration with Docker",
        "description": "Comprehensive guide to working with containers.",
        "item_type": "course",
        "level": "intermediate",
        "source_url": "https://example.com/docker-containers",
        "moderation_state": "approved",
        "skill_tags": [{"skill_name": "docker containers", "coverage_level": "intermediate"}],
    }

    response = client.post(
        "/api/v1/catalogue",
        headers={"Authorization": f"Bearer {admin_token}"},
        json=payload,
    )

    assert response.status_code == 201
    data = response.json()
    assert len(data["skill_tags"]) == 1
    # Resolved canonical name
    assert data["skill_tags"][0]["skill_name"] == "Docker"
    assert data["skill_tags"][0]["skill_id"] == 1


def test_tc_f4_10_inactive_resource_excluded_from_student_results(
    client, admin_token, student1_token
):
    """TC-F4-10: Inactive resource does not appear in normal student search results (REQ-F4-12)."""
    # 1. Admin creates an approved resource
    resp_approved = client.post(
        "/api/v1/catalogue",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "title": "Active Python Programming",
            "description": "Comprehensive course covering all fundamental and intermediate Python.",
            "item_type": "course",
            "level": "intermediate",
            "source_url": "https://example.com/active-python",
            "moderation_state": "approved",
            "skill_tags": [{"skill_id": 2, "coverage_level": "intermediate"}],
        },
    )
    assert resp_approved.status_code == 201

    # 2. Admin creates an inactive resource
    resp_inactive = client.post(
        "/api/v1/catalogue",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "title": "Inactive Deprecated Python",
            "description": "Outdated resource that should not be visible to students.",
            "item_type": "course",
            "level": "beginner",
            "source_url": "https://example.com/deprecated-python",
            "moderation_state": "inactive",
            "skill_tags": [{"skill_id": 2, "coverage_level": "beginner"}],
        },
    )
    assert resp_inactive.status_code == 201

    # 3. Search as student
    student_search = client.get(
        "/api/v1/catalogue?q=Python",
        headers={"Authorization": f"Bearer {student1_token}"},
    )
    assert student_search.status_code == 200
    results = student_search.json()
    titles = [item["title"] for item in results]

    assert "Active Python Programming" in titles
    assert "Inactive Deprecated Python" not in titles

    # 4. Search as administrator includes all resources
    admin_search = client.get(
        "/api/v1/catalogue?q=Python",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert admin_search.status_code == 200
    admin_titles = [item["title"] for item in admin_search.json()]
    assert "Active Python Programming" in admin_titles
    assert "Inactive Deprecated Python" in admin_titles
