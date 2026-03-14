# -*- coding: utf-8 -*-
"""license_api — Vercel 简化版（测试用）"""
import json
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler

LICENSE_DAYS = 7
# 测试用卡密
licenses = {
    "TEST1234567890123456789": {"used": False, "machine_id": "", "activated_at": "", "expire_days": 7},
    "f6T3TOahThjG7Q0xuFFtujdY": {"used": False, "machine_id": "", "activated_at": "", "expire_days": 7},
}

def _now_str():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

def _expire_str(activated_at, expire_days):
    dt = datetime.strptime(activated_at, "%Y-%m-%d %H:%M:%S")
    return (dt + timedelta(days=expire_days)).strftime("%Y-%m-%d")

def _days_left(activated_at, expire_days):
    expire_dt = datetime.strptime(_expire_str(activated_at, expire_days), "%Y-%m-%d")
    return int((expire_dt - datetime.utcnow()).total_seconds() // 86400)

def _ok(data):
    return json.dumps({"ok": True, **data}, ensure_ascii=False)

def _err(msg):
    return json.dumps({"ok": False, "reason": msg}, ensure_ascii=False)

def do_activate(body):
    key = (body.get("key") or "").strip()
    machine_id = (body.get("machine_id") or "").strip()
    if not key or len(key) != 24:
        return _err("卡密格式错误：应为24位")
    if not machine_id:
        return _err("缺少机器码")
    if key not in licenses:
        return _err("卡密无效")

    doc = licenses[key]
    if doc["used"]:
        if doc["machine_id"] == machine_id:
            remaining = _days_left(doc["activated_at"], doc["expire_days"])
            if remaining < 0:
                return _err("卡密已过期")
            return _ok({"reason": f"已激活，剩余{remaining}天", "days_left": remaining})
        return _err("卡密已被其他设备使用")

    now_s = _now_str()
    licenses[key] = {"used": True, "machine_id": machine_id, "activated_at": now_s, "expire_days": doc["expire_days"]}
    return _ok({"reason": f"激活成功！有效期7天", "days_left": 7})

def do_check(body):
    key = (body.get("key") or "").strip()
    machine_id = (body.get("machine_id") or "").strip()
    if not key or not machine_id:
        return _err("参数缺失")
    if key not in licenses or not licenses[key]["used"] or licenses[key]["machine_id"] != machine_id:
        return _err("授权记录不存在")
    doc = licenses[key]
    remaining = _days_left(doc["activated_at"], doc["expire_days"])
    if remaining < 0:
        return _err("授权已过期")
    return _ok({"days_left": remaining, "activated_at": doc["activated_at"]})

class handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def _send(self, body_str, status=200):
        data = body_str.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            body = json.loads(raw or b"{}")
        except:
            self._send(_err("请求解析失败"), 400)
            return
        action = body.get("action", "")
        try:
            if action == "activate":
                self._send(do_activate(body))
            elif action == "check":
                self._send(do_check(body))
            else:
                self._send(_err("未知操作"), 404)
        except Exception as e:
            self._send(_err(str(e)), 500)

    def do_GET(self):
        self._send(json.dumps({"status": "ok", "keys": len(licenses)}))
