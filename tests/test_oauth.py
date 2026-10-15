"""Regression checks for the template's missing OAuth request binding."""
import base64
import hashlib
import unittest
from urllib.parse import parse_qs, urlsplit

from starlette.testclient import TestClient

import auth
import server


class OAuthTests(unittest.TestCase):
    def setUp(self):
        auth._clients.clear()
        auth._codes.clear()
        self.client = TestClient(server.mcp.streamable_http_app())
        self.redirect = "http://127.0.0.1:4567/callback"
        self.verifier = "a" * 64
        self.challenge = base64.urlsafe_b64encode(hashlib.sha256(self.verifier.encode()).digest()).rstrip(b"=").decode()
        response = self.client.post("/register", json={"redirect_uris": [self.redirect]})
        self.assertEqual(response.status_code, 201)
        self.params = {"client_id": response.json()["client_id"], "redirect_uri": self.redirect,
                       "response_type": "code", "state": "demo-state", "code_challenge_method": "S256",
                       "code_challenge": self.challenge}

    def tearDown(self):
        self.client.close()

    def code(self):
        response = self.client.post("/authorize", data={**self.params, "mode": "guest"}, follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        query = parse_qs(urlsplit(response.headers["location"]).query)
        self.assertEqual(query["state"], ["demo-state"])
        return query["code"][0]

    def exchange(self, code, **changes):
        return self.client.post("/token", data={"grant_type": "authorization_code", "code": code,
            "client_id": self.params["client_id"], "redirect_uri": self.redirect,
            "code_verifier": self.verifier, **changes})

    def test_discovery_and_guest_pkce_flow(self):
        discovery = self.client.get("/.well-known/oauth-authorization-server").json()
        self.assertEqual(discovery["code_challenge_methods_supported"], ["S256"])
        page = self.client.get("/authorize", params=self.params)
        self.assertEqual(page.status_code, 200)
        self.assertIn("Assignment deadlines", page.text)
        code = self.code()
        self.assertEqual(self.exchange(code).json()["access_token"], auth.GUEST_TOKEN)
        self.assertEqual(self.exchange(code).status_code, 400)  # One-time only.

    def test_missing_pkce_or_redirect_tampering_is_rejected_before_login(self):
        for changes in [{"code_challenge": ""}, {"code_challenge_method": "plain"},
                        {"redirect_uri": "https://unregistered.example/callback"}]:
            params = {**self.params, **changes}
            self.assertEqual(self.client.get("/authorize", params=params).status_code, 400)
            self.assertEqual(self.client.post("/authorize", data={**params, "mode": "guest"}).status_code, 400)

    def test_code_is_bound_to_client_redirect_and_verifier(self):
        for change in [{"client_id": "another-client"}, {"redirect_uri": "https://other.example"},
                       {"code_verifier": "b" * 64}]:
            self.assertEqual(self.exchange(self.code(), **change).status_code, 400)

    def test_insecure_nonlocal_redirect_registration_is_rejected(self):
        response = self.client.post("/register", json={"redirect_uris": ["http://remote.example/callback"]})
        self.assertEqual(response.status_code, 400)
