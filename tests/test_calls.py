import uuid


def test_uploads_mp3_and_returns_pending_call(client, organization_id):
    response = client.post(
        "/api/v1/calls",
        headers={"X-Organization-ID": organization_id},
        files={"file": ("customer-call.mp3", b"ID3-fake-audio", "audio/mpeg")},
    )

    assert response.status_code == 202
    payload = response.json()
    assert payload["organization_id"] == organization_id
    assert payload["original_filename"] == "customer-call.mp3"
    assert payload["status"] == "pending"


def test_rejects_non_mp3_file(client, organization_id):
    response = client.post(
        "/api/v1/calls",
        headers={"X-Organization-ID": organization_id},
        files={"file": ("notes.txt", b"not audio", "text/plain")},
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Only MP3 files are supported"


def test_does_not_return_another_tenants_call(client, organization_id):
    created = client.post(
        "/api/v1/calls",
        headers={"X-Organization-ID": organization_id},
        files={"file": ("call.mp3", b"ID3-fake-audio", "audio/mpeg")},
    ).json()

    response = client.get(
        f"/api/v1/calls/{created['id']}",
        headers={"X-Organization-ID": str(uuid.uuid4())},
    )

    assert response.status_code == 404
