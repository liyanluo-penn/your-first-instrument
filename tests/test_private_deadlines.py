"""Real Postgres + signed JWTs: test ownership, persistence and rejected credentials."""
import asyncio
import json
import logging
import os
import tempfile
import threading
import time
import unittest
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import jwt
import httpx
import pgserver
import uvicorn
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from starlette.requests import Request
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

import deadline_store
import identity
import server

logging.getLogger("pgserver").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)


def context(header=None):
    headers = [] if header is None else [(b"authorization", header.encode())]
    return SimpleNamespace(request_context=SimpleNamespace(request=Request({"type": "http", "headers": headers})))


class PrivateDeadlineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="deadline-tests-")
        cls.pg = pgserver.get_server(Path(cls.temp.name) / "pgdata", cleanup_mode="stop")
        cls.key = Ed25519PrivateKey.generate()
        jwk = json.loads(jwt.algorithms.OKPAlgorithm.to_jwk(cls.key.public_key()))
        jwk["kid"] = "test-key"
        payload = json.dumps({"keys": [jwk]}).encode()

        class Keys(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        cls.keys = ThreadingHTTPServer(("127.0.0.1", 0), Keys)
        cls.thread = threading.Thread(target=cls.keys.serve_forever, daemon=True)
        cls.thread.start()
        cls.issuer = f"http://127.0.0.1:{cls.keys.server_port}"
        cls.env = patch.dict(os.environ, {"DATABASE_URL": cls.pg.get_uri(),
                             "NEON_AUTH_BASE_URL": cls.issuer + "/neondb/auth",
                             "NEON_AUTH_JWKS_URL": "", "STACK_PROJECT_ID": ""})
        cls.env.start()
        identity._keys.cache_clear()

    @classmethod
    def tearDownClass(cls):
        cls.env.stop()
        identity._keys.cache_clear()
        cls.keys.shutdown()
        cls.keys.server_close()
        cls.thread.join()
        cls.pg.cleanup()
        cls.temp.cleanup()

    def setUp(self):
        with deadline_store.db() as conn:
            conn.execute("TRUNCATE assignment_deadlines")

    def signed(self, subject="alice", **claims):
        body = {"sub": subject, "email": subject + "@example.test", "iss": self.issuer,
                "iat": int(time.time()), "exp": int(time.time()) + 300, **claims}
        return context("Bearer " + jwt.encode(body, self.key, algorithm="EdDSA", headers={"kid": "test-key"}))

    def test_guest_and_two_users_have_separate_persistent_lists(self):
        guest, alice, bob = context(), self.signed(), self.signed("bob")
        for ctx, title in [(guest, "Public demo"), (alice, "Alice homework"), (bob, "Bob homework")]:
            server.save_deadline(title, "2026-11-15T23:59:00-05:00", ctx)
        # Each tool call opens a new real database connection. Data survives it.
        for ctx, title in [(context(), "Public demo"), (self.signed(), "Alice homework"), (self.signed("bob"), "Bob homework")]:
            rows = server.list_deadlines(ctx)["deadlines"]
            self.assertEqual([r["title"] for r in rows], [title])
            self.assertEqual(rows[0]["deadline"], "2026-11-16T04:59:00+00:00")
        self.assertEqual(server.user_status(guest)["mode"], "guest")
        self.assertEqual(server.user_status(alice)["mode"], "user")

    def test_other_users_and_guests_cannot_complete_a_private_deadline(self):
        row = server.save_deadline("Private assignment", "2026-11-15T12:00:00Z", self.signed())
        for outsider in [context(), self.signed("bob")]:
            self.assertFalse(server.complete_deadline(row["id"], outsider)["completed"])
        self.assertEqual(len(server.list_deadlines(self.signed())["deadlines"]), 1)
        self.assertTrue(server.complete_deadline(row["id"], self.signed())["completed"])
        self.assertEqual(server.list_deadlines(self.signed())["deadlines"], [])
        history = server.list_deadlines(self.signed(), include_completed=True)["deadlines"]
        self.assertTrue(history[0]["completed"])

    def test_changed_email_keeps_the_same_owner(self):
        server.save_deadline("My assignment", "2026-11-15T12:00:00Z", self.signed())
        rows = server.list_deadlines(self.signed(email="new@example.test"))["deadlines"]
        self.assertEqual(len(rows), 1)

    def test_invalid_expired_and_wrong_issuer_tokens_never_write_as_guest(self):
        invalid = [context("Bearer broken"), context("Basic abc"), context(""), context("Bearer "),
                   self.signed(exp=int(time.time()) - 10), self.signed(iss="https://wrong.example"),
                   self.signed(subject="")]
        for ctx in invalid:
            with self.subTest(ctx=ctx), self.assertRaises(ValueError):
                server.save_deadline("Must not be public", "2026-11-15T12:00:00Z", ctx)
        self.assertEqual(server.list_deadlines(context())["deadlines"], [])

    def test_foreign_signature_is_rejected(self):
        token = jwt.encode({"sub": "alice", "iss": self.issuer, "exp": int(time.time()) + 300},
                           Ed25519PrivateKey.generate(), algorithm="EdDSA", headers={"kid": "test-key"})
        with self.assertRaises(ValueError):
            server.list_deadlines(context("Bearer " + token))

    def test_declared_guest_is_shared_and_invalid_input_is_not_saved(self):
        guest = context("Bearer guest-no-shelf")
        server.save_deadline("Demo", "2026-11-15T12:00:00Z", guest)
        self.assertEqual(server.list_deadlines(context())["deadlines"][0]["title"], "Demo")
        for title, due in [("", "2026-11-15T12:00:00Z"), ("x" * 201, "2026-11-15T12:00:00Z"),
                           ("bad date", "2026-02-30T12:00:00Z"), ("no zone", "2026-11-15T12:00:00")]:
            with self.assertRaises(ValueError):
                server.save_deadline(title, due, guest)
        self.assertEqual(len(server.list_deadlines(guest)["deadlines"]), 1)

    def test_sql_in_title_is_saved_as_text_and_sorting_is_by_deadline(self):
        guest = context()
        title = "Homework'); DROP TABLE assignment_deadlines; --"
        server.save_deadline(title, "2026-11-15T12:00:00Z", guest)
        server.save_deadline("Earlier", "2026-11-01T12:00:00Z", guest)
        self.assertEqual([r["title"] for r in server.list_deadlines(guest)["deadlines"]], ["Earlier", title])

    def test_real_mcp_http_transports_identity_and_persists_between_sessions(self):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        app = server.mcp.streamable_http_app()
        host = uvicorn.Server(uvicorn.Config(app, log_level="warning", access_log=False))
        thread = threading.Thread(target=lambda: host.run(sockets=[listener]), daemon=True)
        thread.start()
        try:
            limit = time.monotonic() + 10
            while not host.started and time.monotonic() < limit:
                time.sleep(0.05)
            self.assertTrue(host.started, "MCP HTTP server did not start")
            url = f"http://127.0.0.1:{port}/mcp"

            async def call(header, tool, arguments=None):
                headers = {} if header is None else {"Authorization": header}
                async with httpx.AsyncClient(headers=headers) as http:
                    async with streamable_http_client(url, http_client=http) as (reader, writer, _):
                        async with ClientSession(reader, writer) as session:
                            await session.initialize()
                            return await session.call_tool(tool, arguments or {})

            token = self.signed().request_context.request.headers["authorization"]
            saved = asyncio.run(call(token, "save_deadline", {"title": "Through MCP", "deadline": "2026-11-15T12:00:00Z"}))
            self.assertFalse(saved.isError)
            # A new protocol session still reads the same private database row.
            private = asyncio.run(call(token, "list_deadlines"))
            self.assertFalse(private.isError)
            private_data = private.structuredContent or json.loads(private.content[0].text)
            self.assertEqual(private_data["deadlines"][0]["title"], "Through MCP")
            guest = asyncio.run(call(None, "list_deadlines"))
            self.assertFalse(guest.isError)
            guest_data = guest.structuredContent or json.loads(guest.content[0].text)
            self.assertEqual(guest_data["deadlines"], [])
            broken = asyncio.run(call("Bearer broken", "save_deadline", {"title": "Must not leak", "deadline": "2026-11-15T12:00:00Z"}))
            self.assertTrue(broken.isError)
            self.assertEqual(server.list_deadlines(context())["deadlines"], [])
        finally:
            host.should_exit = True
            thread.join(timeout=10)
            listener.close()
