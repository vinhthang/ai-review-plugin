"""Zero-dependency Chrome DevTools Protocol (CDP) WebSocket and HTTP client."""
import base64
import json
import os
import socket
import struct
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional


class CDPClient:
    """Zero-dependency Chrome DevTools Protocol (CDP) WebSocket and HTTP client."""

    @classmethod
    def is_available(cls, port: int = 9222) -> bool:
        """Checks if Chrome DevTools Protocol endpoint is responding on the given port."""
        try:
            url = f"http://127.0.0.1:{port}/json/version"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    @classmethod
    def find_gemini_tab(cls, port: int = 9222) -> Optional[dict]:
        """Finds target in /json/list where type == 'page', and url contains 'gemini.google.com' and '/app'."""
        try:
            url = f"http://127.0.0.1:{port}/json/list"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                targets = json.loads(resp.read().decode("utf-8"))
                if isinstance(targets, list):
                    for target in targets:
                        t_type = target.get("type", "")
                        t_url = target.get("url", "")
                        if t_type == "page" and "gemini.google.com" in t_url and "/app" in t_url:
                            return target
        except Exception:
            pass
        return None

    @classmethod
    def open_gemini_tab(cls, port: int = 9222) -> Optional[dict]:
        """Sends PUT to /json/new?https://gemini.google.com/app to open a new Gemini tab."""
        try:
            url = f"http://127.0.0.1:{port}/json/new?https://gemini.google.com/app"
            req = urllib.request.Request(url, method="PUT")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
        return None

    @classmethod
    def execute_js(cls, target: dict, js_code: str, port: int = 9222, timeout: int = 60) -> str:
        """Connects to target's webSocketDebuggerUrl, evaluates js_code, and returns the result string."""
        ws_url = target.get("webSocketDebuggerUrl")
        if not ws_url:
            t_id = target.get("id")
            if t_id:
                ws_url = f"ws://127.0.0.1:{port}/devtools/page/{t_id}"
            else:
                raise ValueError("Target does not contain webSocketDebuggerUrl or id")

        parsed = urllib.parse.urlsplit(ws_url)
        host = parsed.hostname or "127.0.0.1"
        target_port = parsed.port or port
        path = parsed.path
        if parsed.query:
            path = f"{path}?{parsed.query}"

        sock = socket.create_connection((host, target_port), timeout=timeout)
        sock.settimeout(timeout)

        try:
            sec_key = base64.b64encode(os.urandom(16)).decode("ascii")
            handshake_req = (
                f"GET {path} HTTP/1.1\r\n"
                f"Host: {host}:{target_port}\r\n"
                f"Upgrade: websocket\r\n"
                f"Connection: Upgrade\r\n"
                f"Sec-WebSocket-Key: {sec_key}\r\n"
                f"Sec-WebSocket-Version: 13\r\n\r\n"
            )
            sock.sendall(handshake_req.encode("utf-8"))

            handshake_resp = bytearray()
            while b"\r\n\r\n" not in handshake_resp:
                chunk = sock.recv(1024)
                if not chunk:
                    raise ConnectionError("Server closed connection during WebSocket handshake.")
                handshake_resp.extend(chunk)

            header_end = handshake_resp.find(b"\r\n\r\n") + 4
            status_line = bytes(handshake_resp[:header_end]).split(b"\r\n")[0].decode("utf-8", errors="replace")
            if "101" not in status_line:
                raise ConnectionError(f"WebSocket handshake failed: {status_line}")

            buf = bytearray(handshake_resp[header_end:])

            def read_exact(n: int) -> bytes:
                while len(buf) < n:
                    chunk = sock.recv(max(4096, n - len(buf)))
                    if not chunk:
                        raise ConnectionError("Socket closed prematurely while reading WebSocket frame.")
                    buf.extend(chunk)
                res = bytes(buf[:n])
                del buf[:n]
                return res

            def encode_frame(payload: bytes, opcode: int = 1) -> bytes:
                fin_and_opcode = 0x80 | (opcode & 0x0F)
                length = len(payload)
                mask_key = os.urandom(4)
                if length <= 125:
                    header = struct.pack("!BB", fin_and_opcode, 0x80 | length)
                elif length <= 65535:
                    header = struct.pack("!BBH", fin_and_opcode, 0x80 | 126, length)
                else:
                    header = struct.pack("!BBQ", fin_and_opcode, 0x80 | 127, length)
                mask_repeated = (mask_key * (length // 4 + 1))[:length]
                masked = bytes(a ^ b for a, b in zip(payload, mask_repeated))
                return header + mask_key + masked

            req_id = 1
            cmd = {
                "id": req_id,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": js_code,
                    "returnByValue": True,
                    "awaitPromise": True,
                },
            }
            sock.sendall(encode_frame(json.dumps(cmd).encode("utf-8")))

            start_time = time.time()
            while True:
                if time.time() - start_time > timeout:
                    raise TimeoutError("Timed out waiting for CDP Runtime.evaluate response")

                msg_bytes = bytearray()
                while True:
                    h = read_exact(2)
                    b1, b2 = struct.unpack("!BB", h)
                    fin = (b1 >> 7) & 1
                    opcode = b1 & 0x0F
                    masked = (b2 >> 7) & 1
                    length = b2 & 0x7F
                    if length == 126:
                        length = struct.unpack("!H", read_exact(2))[0]
                    elif length == 127:
                        length = struct.unpack("!Q", read_exact(8))[0]

                    if masked:
                        mkey = read_exact(4)
                        raw = read_exact(length)
                        mrep = (mkey * (length // 4 + 1))[:length]
                        frame_payload = bytes(a ^ b for a, b in zip(raw, mrep))
                    else:
                        frame_payload = read_exact(length)

                    if opcode == 0x9:  # Ping
                        sock.sendall(encode_frame(frame_payload, opcode=0x0A))
                        continue
                    elif opcode == 0x8:  # Close
                        raise ConnectionError("WebSocket closed by server")

                    msg_bytes.extend(frame_payload)
                    if fin:
                        break

                try:
                    data = json.loads(msg_bytes.decode("utf-8"))
                except Exception:
                    continue

                if data.get("id") == req_id:
                    if "error" in data:
                        err_msg = data["error"].get("message", str(data["error"]))
                        raise RuntimeError(f"CDP error: {err_msg}")

                    result_data = data.get("result", {})
                    if "exceptionDetails" in result_data:
                        exc = result_data["exceptionDetails"]
                        text = exc.get("text", "")
                        desc = exc.get("exception", {}).get("description", "")
                        raise RuntimeError(f"JavaScript exception: {text} {desc}".strip())

                    result_obj = result_data.get("result", {})
                    if "value" in result_obj:
                        val = result_obj["value"]
                        if isinstance(val, bool):
                            return "true" if val else "false"
                        if isinstance(val, (dict, list)):
                            return json.dumps(val)
                        return str(val) if val is not None else ""
                    elif result_obj.get("type") == "undefined":
                        return ""
                    elif "description" in result_obj:
                        return str(result_obj["description"])
                    return ""
        finally:
            sock.close()
