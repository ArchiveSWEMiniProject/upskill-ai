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


def test_tc_f4_09_search_matches_on_skill_tag_only(client, admin_token, student1_token):
    """TC-F4-09: Search matches on skill tag even when term is not in title or description."""
    # 1. Resource with term "Docker" ONLY in the skill tag (skill_id=1 is Docker)
    resp_docker = client.post(
        "/api/v1/catalogue",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "title": "Container Orchestration Engine",
            "description": "Production clustering and deployment architectures.",
            "item_type": "course",
            "level": "intermediate",
            "source_url": "https://example.com/containers",
            "moderation_state": "approved",
            "skill_tags": [{"skill_id": 1, "coverage_level": "intermediate"}],
        },
    )
    assert resp_docker.status_code == 201

    # 2. Unrelated resource with no Docker tag
    resp_algo = client.post(
        "/api/v1/catalogue",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={
            "title": "Algorithms and Data Structures",
            "description": "Asymptotic analysis, trees, graphs, and dynamic programming.",
            "item_type": "course",
            "level": "intermediate",
            "source_url": "https://example.com/algo",
            "moderation_state": "approved",
            "skill_tags": [{"skill_id": 2, "coverage_level": "intermediate"}],
        },
    )
    assert resp_algo.status_code == 201

    # 3. Search for "Docker"
    search_resp = client.get(
        "/api/v1/catalogue?q=Docker",
        headers={"Authorization": f"Bearer {student1_token}"},
    )
    assert search_resp.status_code == 200
    results = search_resp.json()
    titles = [item["title"] for item in results]

    # Docker-tagged resource is returned, unrelated is excluded
    assert "Container Orchestration Engine" in titles
    assert "Algorithms and Data Structures" not in titles


def test_nfr_perf_04_catalogue_pagination(client, admin_token, student1_token):
    """NFR-PERF-04: Catalogue responses are paginated with limit and offset."""
    # Seed 3 items
    for i in range(1, 4):
        client.post(
            "/api/v1/catalogue",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={
                "title": f"Resource Number {i}",
                "description": f"Detailed description for resource {i}.",
                "item_type": "course",
                "level": "beginner",
                "source_url": f"https://example.com/r{i}",
                "moderation_state": "approved",
                "skill_tags": [{"skill_id": 2, "coverage_level": "beginner"}],
            },
        )

    # Page 1: limit 2, offset 0
    page1 = client.get(
        "/api/v1/catalogue?limit=2&offset=0",
        headers={"Authorization": f"Bearer {student1_token}"},
    )
    assert page1.status_code == 200
    assert len(page1.json()) == 2
    assert "X-Total-Count" in page1.headers
    assert page1.headers["X-Limit"] == "2"
    assert page1.headers["X-Offset"] == "0"

    # Page 2: limit 2, offset 2
    page2 = client.get(
        "/api/v1/catalogue?limit=2&offset=2",
        headers={"Authorization": f"Bearer {student1_token}"},
    )
    assert page2.status_code == 200
    assert len(page2.json()) >= 1
    assert page2.headers["X-Offset"] == "2"


def test_get_resources_for_skill_service(db_session):
    """Verify internal module interface get_resources_for_skill per CONTRACTS.md §5.2."""
    from backend.catalogue.models import (
        LearningItem,
        LearningItemSkill,
        LearningItemType,
        ModerationState,
        SkillLevel,
    )
    from backend.catalogue.service import get_resources_for_skill

    # Seed an approved item and an inactive item for Skill 1 (Docker)
    approved_item = LearningItem(
        title="Production Docker",
        description="Master Docker in production systems.",
        item_type=LearningItemType.COURSE,
        level=SkillLevel.INTERMEDIATE,
        source_url="https://example.com/docker-prod",
        moderation_state=ModerationState.APPROVED,
    )
    db_session.add(approved_item)
    db_session.flush()

    link1 = LearningItemSkill(
        item_id=approved_item.item_id,
        skill_id=1,
        coverage_level=SkillLevel.INTERMEDIATE,
    )
    db_session.add(link1)

    inactive_item = LearningItem(
        title="Inactive Docker",
        description="Outdated material.",
        item_type=LearningItemType.COURSE,
        level=SkillLevel.BEGINNER,
        source_url="https://example.com/docker-old",
        moderation_state=ModerationState.INACTIVE,
    )
    db_session.add(inactive_item)
    db_session.flush()

    link2 = LearningItemSkill(
        item_id=inactive_item.item_id,
        skill_id=1,
        coverage_level=SkillLevel.BEGINNER,
    )
    db_session.add(link2)
    db_session.commit()

    # Query for Skill 1
    resources = get_resources_for_skill(skill_ids=[1], db=db_session)
    assert len(resources) == 1
    assert resources[0]["title"] == "Production Docker"

    # Query with level filter
    res_inter = get_resources_for_skill(skill_ids=[1], level="intermediate", db=db_session)
    assert len(res_inter) == 1

    res_adv = get_resources_for_skill(skill_ids=[1], level="advanced", db=db_session)
    assert len(res_adv) == 0

    # Non-existent skill returns empty
    empty_res = get_resources_for_skill(skill_ids=[9999], db=db_session)
    assert empty_res == []


def test_tc_f4_13_error_sanitization_and_correlation_id(client):
    """TC-F4-13: Unhandled errors return sanitized response with correlation ID (NFR-SEC-10)."""
    # Request without correlation ID gets one generated
    resp = client.get("/api/v1/test/trigger-error")
    assert resp.status_code == 500
    assert "X-Correlation-ID" in resp.headers

    data = resp.json()
    assert data["detail"] == "An internal server error occurred"
    assert "correlation_id" in data
    assert data["correlation_id"] == resp.headers["X-Correlation-ID"]

    # Verify sensitive data was not leaked
    response_text = resp.text
    assert "secret_token" not in response_text
    assert "XYZ123" not in response_text
    assert "db_internal_id" not in response_text
    assert "Traceback" not in response_text

    # Request with custom correlation ID preserves it
    custom_id = "test-corr-id-456"
    resp_custom = client.get(
        "/api/v1/test/trigger-error",
        headers={"X-Correlation-ID": custom_id},
    )
    assert resp_custom.status_code == 500
    assert resp_custom.headers["X-Correlation-ID"] == custom_id
    assert resp_custom.json()["correlation_id"] == custom_id
