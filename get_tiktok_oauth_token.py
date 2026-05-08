"""
One-time OAuth 2.0 authorization for TikTok Content Posting API.
Run this locally to get ACCESS_TOKEN + REFRESH_TOKEN, then save to .env and GitHub Secrets.

Setup before running:
1. Go to https://developers.tiktok.com → My Apps → Create App
2. Enable "Content Posting API" scope
3. Set redirect URI to: http://localhost:8080/callback
4. Copy Client Key and Client Secret to .env:
   TIKTOK_CLIENT_KEY=your_client_key
   TIKTOK_CLIENT_SECRET=your_client_secret

Usage:
    python get_tiktok_oauth_token.py
"""

import os
import re
import subprocess
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
from dotenv import load_dotenv

load_dotenv()

CLIENT_KEY = os.environ.get("TIKTOK_CLIENT_KEY", "").strip()
CLIENT_SECRET = os.environ.get("TIKTOK_CLIENT_SECRET", "").strip()
REDIRECT_URI = "http://localhost:8080/callback"
SCOPES = "video.publish,video.upload"

auth_code = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
        auth_code = params.get("code")
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"<h1>Authorization successful! You can close this tab.</h1>")

    def log_message(self, format, *args):
        pass


def main():
    if not CLIENT_KEY or not CLIENT_SECRET:
        print("ERROR: TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET must be set in .env")
        return

    # Build auth URL
    params = {
        "client_key": CLIENT_KEY,
        "scope": SCOPES,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "state": "videogenerator",
    }
    auth_url = "https://www.tiktok.com/v2/auth/authorize/?" + urllib.parse.urlencode(params)

    print(f"\nOpening TikTok authorization page...")
    print(f"If browser doesn't open, go to:\n{auth_url}\n")
    webbrowser.open(auth_url)

    # Wait for callback
    print("Waiting for authorization callback on http://localhost:8080...")
    server = HTTPServer(("localhost", 8080), CallbackHandler)
    server.handle_request()

    if not auth_code:
        print("ERROR: No authorization code received.")
        return

    print(f"Authorization code received.")

    # Exchange code for tokens
    resp = requests.post(
        "https://open.tiktokapis.com/v2/oauth/token/",
        data={
            "client_key": CLIENT_KEY,
            "client_secret": CLIENT_SECRET,
            "code": auth_code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    data = resp.json()

    if "access_token" not in data:
        print(f"ERROR: {data}")
        return

    access_token = data["access_token"]
    refresh_token = data.get("refresh_token", "")
    print(f"\naccess_token:  {access_token[:20]}...")
    print(f"refresh_token: {refresh_token[:20]}...")

    # Save to .env
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
        for key, val in [("TIKTOK_ACCESS_TOKEN", access_token), ("TIKTOK_REFRESH_TOKEN", refresh_token)]:
            if f"{key}=" in content:
                content = re.sub(rf"^{key}=.*$", f"{key}={val}", content, flags=re.MULTILINE)
            else:
                content += f"\n{key}={val}\n"
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("\nSaved to .env")

    # Save to GitHub Secrets
    answer = input("\nSave to GitHub Secrets? [y/N]: ").strip().lower()
    if answer == "y":
        for key, val in [("TIKTOK_ACCESS_TOKEN", access_token), ("TIKTOK_REFRESH_TOKEN", refresh_token)]:
            result = subprocess.run(
                ["gh", "secret", "set", key, "--body", val],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                print(f"  ✓ {key} saved")
            else:
                print(f"  ✗ {key}: {result.stderr.strip()}")


if __name__ == "__main__":
    main()
