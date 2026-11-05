"""Verify the deployed HTTP stack. Run only with compose.test.yaml's fixture provider."""

import json
import re
import sys
import time
import urllib.request
from http.cookiejar import CookieJar


def main():
    base = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8080").rstrip("/")
    client = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(CookieJar())
    )

    def request(path, data=None):
        body = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(
            base + path, data=body, headers={"Content-Type": "application/json"}
        )
        with client.open(req, timeout=10) as response:
            return response.read()

    html = request("/").decode()
    asset = re.search(r'src="([^"]+\.js)"', html)
    assert asset, "Built application script missing"
    assert request(asset[1]), "Built application script could not be served"
    assert json.loads(request("/api/health")) == {"status": "ok", "database": "ok"}
    assert b"swagger-ui" in request("/api/docs")
    assert "/api/story/create" in json.loads(request("/openapi.json"))["paths"]
    created = json.loads(request("/api/story/create", {"theme": "Docker smoke test"}))
    assert created["status"] == "pending", created
    for _ in range(60):
        job = json.loads(request(f"/api/jobs/{created['job_id']}"))
        if job["status"] in {"completed", "failed"}:
            break
        time.sleep(0.5)
    assert job["status"] == "completed", job
    story = json.loads(request(f"/api/story/{job['story_id']}/complete"))
    assert len(story["all_nodes"]) == 5, story
    assert str(story["root_node"]["id"]) in story["all_nodes"]
    for node in story["all_nodes"].values():
        for option in node["options"]:
            assert str(option["node_id"]) in story["all_nodes"], option
    print(
        "PASS: built assets, API proxy, health, docs, create/poll/read and persisted choices"
    )


if __name__ == "__main__":
    main()
