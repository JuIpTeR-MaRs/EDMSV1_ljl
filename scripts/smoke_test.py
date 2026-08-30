#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
==============================================================================
 EDMS (Enterprise Document Management System) - 自动化冒烟测试套件
 Smoke Test & Health Check Suite
==============================================================================
 用于在本地开发启动 (start_manual.bat) 或 Docker 容器部署后，快速验证系统关键主干链路。
 耗时: 通常在 1~3 秒内完成
 退出码: 全部通过返回 0，存在失败返回 1
==============================================================================
"""

import sys
import os
import time
import json
import re
import base64
import argparse
from urllib import request, error
from typing import Dict, Any, Tuple, Optional

# Ensure UTF-8 output encoding across Windows / Linux consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# ==================== ANSI Terminal Styling ====================
class Style:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[91m"
    GREEN   = "\033[92m"
    YELLOW  = "\033[93m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN    = "\033[96m"
    WHITE   = "\033[97m"
    BG_GREEN = "\033[42m\033[30m"
    BG_RED   = "\033[41m\033[97m"

def init_terminal():
    """Enable ANSI colors in Windows CMD/PowerShell if supported."""
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
        except Exception:
            pass

def safe_print(text: str):
    """Print string safely without crashing on weird console encodings."""
    try:
        print(text)
    except UnicodeEncodeError:
        # Fallback to ascii representation with escaped chars
        cleaned = text.encode("ascii", "replace").decode("ascii")
        print(cleaned)

# ==================== HTTP Client Helper ====================
class HttpClient:
    def __init__(self, backend_url: str, verbose: bool = False):
        self.backend_url = backend_url.rstrip("/")
        self.verbose = verbose
        self.token: Optional[str] = None

    def set_token(self, token: str):
        self.token = token

    def request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 6.0,
        full_url: Optional[str] = None
    ) -> Tuple[int, Any, float]:
        """Execute HTTP request and return (status_code, response_json_or_text, duration_ms)"""
        url = full_url if full_url else f"{self.backend_url}{path}"
        req_headers = {"User-Agent": "EDMS-SmokeTest/1.0", "Accept": "application/json"}
        
        if self.token:
            req_headers["Authorization"] = f"Bearer {self.token}"
        if headers:
            req_headers.update(headers)

        payload_bytes = None
        if data is not None:
            req_headers["Content-Type"] = "application/json"
            payload_bytes = json.dumps(data).encode("utf-8")

        req = request.Request(url, data=payload_bytes, headers=req_headers, method=method.upper())

        start_time = time.time()
        status_code = 0
        resp_body = None

        try:
            with request.urlopen(req, timeout=timeout) as response:
                status_code = response.getcode()
                raw_content = response.read().decode("utf-8", errors="replace")
                try:
                    resp_body = json.loads(raw_content)
                except Exception:
                    resp_body = raw_content
        except error.HTTPError as e:
            status_code = e.code
            raw_content = e.read().decode("utf-8", errors="replace")
            try:
                resp_body = json.loads(raw_content)
            except Exception:
                resp_body = raw_content
        except Exception as e:
            status_code = -1
            resp_body = str(e)

        duration_ms = (time.time() - start_time) * 1000

        if self.verbose:
            safe_print(f"{Style.DIM}  [DEBUG HTTP] {method} {url} -> {status_code} ({duration_ms:.1f}ms){Style.RESET}")

        return status_code, resp_body, duration_ms

# ==================== Smart Captcha Solver ====================
def solve_captcha_from_svg(captcha_img_base64: str) -> str:
    """Extract and calculate math problem from EDMS captcha SVG."""
    try:
        if "," in captcha_img_base64:
            encoded_part = captcha_img_base64.split(",", 1)[1]
        else:
            encoded_part = captcha_img_base64
        svg_content = base64.b64decode(encoded_part).decode("utf-8", errors="ignore")
        
        # Match all text chunks in SVG <text ...>char</text>
        chars = re.findall(r">([^<]+)</text>", svg_content)
        challenge_str = "".join(chars).strip()
        
        # Match pattern "num1 +/- num2 = ?"
        match = re.search(r"(\d+)\s*([\+\-])\s*(\d+)", challenge_str)
        if match:
            num1 = int(match.group(1))
            op = match.group(2)
            num2 = int(match.group(3))
            ans = num1 + num2 if op == "+" else num1 - num2
            return str(ans)
    except Exception:
        pass
    return "0"

# ==================== Main Smoke Test Suite ====================
class SmokeTestSuite:
    def __init__(self, backend_url: str, frontend_url: str, username: str, password: str, check_frontend: bool, verbose: bool):
        self.backend_url = backend_url
        self.frontend_url = frontend_url
        self.username = username
        self.password = password
        self.check_frontend = check_frontend
        self.client = HttpClient(backend_url, verbose=verbose)
        
        self.total_tests = 0
        self.passed_tests = 0
        self.failed_tests = 0
        self.created_doc_id = None

    def log_step(self, step_idx: int, title: str):
        safe_print(f"\n{Style.BOLD}{Style.CYAN}[*] [{step_idx}/7] {title}{Style.RESET}")

    def record_result(self, name: str, passed: bool, duration_ms: float, details: str = ""):
        self.total_tests += 1
        if passed:
            self.passed_tests += 1
            icon = f"{Style.GREEN}[PASS]{Style.RESET}"
            dur = f"{Style.DIM}({duration_ms:.1f}ms){Style.RESET}"
            safe_print(f"  {icon} {name} {dur} {Style.DIM}{details}{Style.RESET}")
        else:
            self.failed_tests += 1
            icon = f"{Style.RED}[FAIL]{Style.RESET}"
            dur = f"{Style.DIM}({duration_ms:.1f}ms){Style.RESET}"
            safe_print(f"  {icon} {name} {dur}")
            if details:
                safe_print(f"    {Style.RED}└─ 原因: {details}{Style.RESET}")

    def run(self) -> bool:
        start_all = time.time()
        safe_print(f"{Style.BOLD}{Style.MAGENTA}{'=' * 72}{Style.RESET}")
        safe_print(f"{Style.BOLD}{Style.WHITE}   EDMS 企业级智能文档管理系统 —— 核心链路冒烟测试套件{Style.RESET}")
        safe_print(f"{Style.BOLD}{Style.MAGENTA}{'=' * 72}{Style.RESET}")
        safe_print(f"  {Style.BOLD}后端地址:{Style.RESET} {self.backend_url}")
        safe_print(f"  {Style.BOLD}前端地址:{Style.RESET} {self.frontend_url if self.check_frontend else '跳过测试'}")
        safe_print(f"  {Style.BOLD}测试账号:{Style.RESET} {self.username}")
        safe_print(f"{Style.DIM}{'-' * 72}{Style.RESET}")

        # -------------------------------------------------------------
        # STEP 1: Backend Health Check
        # -------------------------------------------------------------
        self.log_step(1, "后端服务探活与健康检查 (Backend Health Check)")
        code, body, dur = self.client.request("GET", "/api/health")
        if code == 200 and isinstance(body, dict) and body.get("status") == "ok":
            self.record_result("后端探活接口 (/api/health) 响应正常", True, dur, f"Status: {body.get('status')}")
        else:
            self.record_result(
                "后端探活接口异常", 
                False, 
                dur, 
                f"HTTP Code: {code}, 错误信息: {body}. 请确认后端是否已通过 backend_start.bat 或 start_manual.bat 启动并在 {self.backend_url} 监听！"
            )
            return self.summary(time.time() - start_all)

        # -------------------------------------------------------------
        # STEP 2: Frontend Reachability (Optional)
        # -------------------------------------------------------------
        if self.check_frontend:
            self.log_step(2, "前端 Web 服务可达性检查 (Frontend Reachability)")
            code, body, dur = self.client.request("GET", "", full_url=self.frontend_url, timeout=3.0)
            if code in (200, 304) or (isinstance(body, str) and ("<!DOCTYPE html>" in body or "<html" in body or "vite" in body.lower())):
                self.record_result(f"前端首页可正常访问 ({self.frontend_url})", True, dur, f"HTTP {code}")
            else:
                self.record_result(
                    "前端服务无法访问",
                    False,
                    dur,
                    f"HTTP {code}. 提示: 请确认前端 Vite 服务是否在 {self.frontend_url} 运行 (可通过 frontend_start.bat 启动)"
                )
        else:
            self.log_step(2, "前端 Web 服务可达性检查 (已跳过)")

        # -------------------------------------------------------------
        # STEP 3: Captcha & Authentication Flow
        # -------------------------------------------------------------
        self.log_step(3, "智能验证码解析与账号鉴权登录 (Captcha & Auth Flow)")
        
        # 3.1 获取验证码
        code, body, dur = self.client.request("GET", "/api/auth/captcha")
        captcha_token = None
        captcha_answer = None
        if code == 200 and isinstance(body, dict) and "captcha_img" in body and "captcha_token" in body:
            captcha_token = body["captcha_token"]
            captcha_answer = solve_captcha_from_svg(body["captcha_img"])
            self.record_result("成功获取图形验证码并自动解题", True, dur, f"计算得出算式答案: {captcha_answer}")
        else:
            self.record_result("获取验证码失败 (/api/auth/captcha)", False, dur, f"HTTP {code}, Body: {body}")
            return self.summary(time.time() - start_all)

        # 3.2 登录获取 Token
        login_payload = {
            "login_name": self.username,
            "password": self.password,
            "captcha_token": captcha_token,
            "captcha_answer": captcha_answer
        }
        code, body, dur = self.client.request("POST", "/api/auth/login", data=login_payload)
        access_token = body.get("access_token") or body.get("token") if isinstance(body, dict) else None
        if code == 200 and access_token:
            user_info = body.get("user", {})
            self.client.set_token(access_token)
            self.record_result(
                "管理员登录成功并签发 JWT Token", 
                True, 
                dur, 
                f"User: {user_info.get('login_name')} (Role: {user_info.get('role_name') or user_info.get('role', 'admin')})"
            )
        else:
            self.record_result(
                "管理员登录鉴权失败 (/api/auth/login)", 
                False, 
                dur, 
                f"HTTP {code}, Response: {body}. 请检查账号密码 (默认 admin / 123456)"
            )
            return self.summary(time.time() - start_all)

        # -------------------------------------------------------------
        # STEP 4: User Profile & Master Data
        # -------------------------------------------------------------
        self.log_step(4, "用户身份态与组织主数据读取 (Profile & Master Data)")
        
        # 4.1 获取个人资料
        code, body, dur = self.client.request("GET", "/api/auth/me")
        if code == 200 and isinstance(body, dict) and "id" in body:
            self.record_result("当前用户信息接口 (/api/auth/me) 校验通过", True, dur, f"Display Name: {body.get('full_name') or body.get('login_name')}")
        else:
            self.record_result("获取用户信息失败", False, dur, f"HTTP {code}, Body: {body}")

        # 4.2 获取部门架构
        code, body, dur = self.client.request("GET", "/api/users/departments")
        if code == 200 and isinstance(body, list):
            self.record_result("组织架构部门列表 (/api/users/departments) 正常返回", True, dur, f"部门总数: {len(body)}")
        else:
            self.record_result("获取部门列表失败", False, dur, f"HTTP {code}, Body: {body}")

        # -------------------------------------------------------------
        # STEP 5: Knowledge Spaces & Low-Code Templates
        # -------------------------------------------------------------
        self.log_step(5, "知识空间与模板体系验证 (Knowledge Spaces & Templates)")
        
        # 5.1 获取知识空间列表
        code, body, dur = self.client.request("GET", "/api/spaces")
        if code == 200 and (isinstance(body, list) or (isinstance(body, dict) and "items" in body)):
            items = body if isinstance(body, list) else body.get("items", [])
            self.record_result("知识空间列表 (/api/spaces) 正常返回", True, dur, f"空间数量: {len(items)}")
        else:
            self.record_result("获取知识空间失败", False, dur, f"HTTP {code}, Body: {body}")

        # 5.2 获取低代码模板库
        code, body, dur = self.client.request("GET", "/api/templates")
        if code == 200 and (isinstance(body, list) or (isinstance(body, dict) and ("templates" in body or "items" in body))):
            items = body if isinstance(body, list) else (body.get("items") or body.get("templates") or [])
            self.record_result("模板中心列表 (/api/templates) 正常返回", True, dur, f"可用模板数: {len(items)}")
        else:
            self.record_result("获取模板列表失败", False, dur, f"HTTP {code}, Body: {body}")

        # -------------------------------------------------------------
        # STEP 6: Document Lifecycle Full CRUD (Create -> Read -> Update -> Clean)
        # -------------------------------------------------------------
        self.log_step(6, "文档核心生命周期全链路闭环 (Document Full CRUD)")
        
        # 6.1 新建文档 (Create)
        create_payload = {
            "title": f"[SMOKE_TEST_AUTO] 冒烟测试文档_{int(time.time())}",
            "content": "<p>This is an automated smoke test verification document.</p>"
        }
        code, body, dur = self.client.request("POST", "/api/documents", data=create_payload)
        doc_id = None
        if code in (200, 201) and isinstance(body, dict) and "id" in body:
            doc_id = body["id"]
            self.created_doc_id = doc_id
            self.record_result("创建测试文档 (POST /api/documents) 成功", True, dur, f"DocID: {doc_id}, DocNumber: {body.get('doc_number')}")
        else:
            self.record_result("创建测试文档失败", False, dur, f"HTTP {code}, Body: {body}")

        # 6.2 查询文档详情 (Read)
        if doc_id:
            code, body, dur = self.client.request("GET", f"/api/documents/{doc_id}")
            if code == 200 and isinstance(body, dict) and body.get("id") == doc_id:
                self.record_result("读取文档详情 (GET /api/documents/:id) 成功", True, dur, f"Title: {body.get('title')[:25]}...")
            else:
                self.record_result("读取文档详情失败", False, dur, f"HTTP {code}, Body: {body}")

        # 6.3 更新文档元数据/标题 (Update)
        if doc_id:
            update_payload = {
                "title": f"[SMOKE_TEST_AUTO] 冒烟测试文档_已验证_{int(time.time())}"
            }
            code, body, dur = self.client.request("PATCH", f"/api/documents/{doc_id}", data=update_payload)
            if code == 200 and isinstance(body, dict) and "id" in body:
                self.record_result("更新文档属性 (PATCH /api/documents/:id) 成功", True, dur, "状态: OK")
            else:
                self.record_result("更新文档属性失败", False, dur, f"HTTP {code}, Body: {body}")

        # 6.4 目录树查询 (Tree View)
        code, body, dur = self.client.request("GET", "/api/documents/tree")
        if code == 200 and isinstance(body, dict):
            self.record_result("文档目录树结构 (/api/documents/tree) 正常生成", True, dur, f"Keys: {list(body.keys())}")
        else:
            self.record_result("获取文档目录树失败", False, dur, f"HTTP {code}, Body: {body}")

        # 6.5 清理测试数据 (Delete)
        if doc_id:
            code, body, dur = self.client.request("DELETE", f"/api/documents/{doc_id}")
            if code in (200, 204):
                self.record_result("自动清理临时文档 (DELETE /api/documents/:id) 成功", True, dur, "测试数据已归整，无残留")
                self.created_doc_id = None
            else:
                self.record_result("清理临时文档失败", False, dur, f"HTTP {code}, Body: {body}")

        # -------------------------------------------------------------
        # STEP 7: Dashboard Analytics & Notifications
        # -------------------------------------------------------------
        self.log_step(7, "控制台统计看板与通知中心 (Dashboard & Notifications)")
        
        # 7.1 统计看板数据
        code, body, dur = self.client.request("GET", "/api/dashboard/stats")
        if code == 200 and isinstance(body, dict):
            self.record_result("控制台看板统计 (/api/dashboard/stats) 正常返回", True, dur, f"TotalDocs: {body.get('total_docs', body.get('documents_count', 'N/A'))}")
        else:
            self.record_result("获取控制台统计失败", False, dur, f"HTTP {code}, Body: {body}")

        # 7.2 通知消息列表
        code, body, dur = self.client.request("GET", "/api/notifications")
        if code == 200 and (isinstance(body, list) or (isinstance(body, dict) and ("notifications" in body or "items" in body))):
            items = body if isinstance(body, list) else (body.get("items") or body.get("notifications") or [])
            self.record_result("用户通知列表 (/api/notifications) 正常返回", True, dur, f"通知数: {len(items)}, 通道畅通")
        else:
            self.record_result("获取通知列表失败", False, dur, f"HTTP {code}, Body: {body}")

        return self.summary(time.time() - start_all)

    def summary(self, total_seconds: float) -> bool:
        safe_print(f"\n{Style.BOLD}{Style.MAGENTA}{'=' * 72}{Style.RESET}")
        safe_print(f"{Style.BOLD}冒烟测试执行汇总 (Summary):{Style.RESET}")
        safe_print(f"  总检查项: {self.total_tests}")
        safe_print(f"  {Style.GREEN}[+] 通过项数: {self.passed_tests}{Style.RESET}")
        
        if self.failed_tests > 0:
            safe_print(f"  {Style.RED}[-] 失败项数: {self.failed_tests}{Style.RESET}")
            safe_print(f"  总耗时: {total_seconds:.2f}s")
            safe_print(f"\n  {Style.BG_RED} RESULT: SMOKE TEST FAILED (存在未通过项) {Style.RESET}")
            safe_print(f"\n{Style.YELLOW}[*] 故障排查建议 (Troubleshooting):{Style.RESET}")
            safe_print(f"  1. 确认后端是否已启动: 运行 {Style.CYAN}backend_start.bat{Style.RESET} 或 {Style.CYAN}start_manual.bat{Style.RESET}")
            safe_print(f"  2. 确认 MySQL 数据库是否在 127.0.0.1:3306 正常运行")
            safe_print(f"  3. 确认根目录 .env 配置的 DATABASE_URL 与 SECRET_KEY 是否正确")
            safe_print(f"  4. 如果是 Docker 环境，可带参数执行: {Style.CYAN}python smoke_test.py --backend-url http://localhost/api --frontend-url http://localhost{Style.RESET}")
            return False
        else:
            safe_print(f"  {Style.GREEN}[-] 失败项数: 0{Style.RESET}")
            safe_print(f"  总耗时: {total_seconds:.2f}s")
            safe_print(f"\n  {Style.BG_GREEN} RESULT: ALL SMOKE TESTS PASSED (核心主干链路 100% 畅通) {Style.RESET}\n")
            return True


def main():
    init_terminal()
    parser = argparse.ArgumentParser(
        description="EDMS (Enterprise Document Management System) 自动化冒烟测试脚本",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--backend-url", "-b",
        default="http://127.0.0.1:5000",
        help="后端 API 根地址 (默认: http://127.0.0.1:5000，Docker环境可设为 http://localhost/api 或 http://localhost:5000)"
    )
    parser.add_argument(
        "--frontend-url", "-f",
        default="http://localhost:5173",
        help="前端 Web 页面地址 (默认: http://localhost:5173，Docker环境可设为 http://localhost)"
    )
    parser.add_argument(
        "--username", "-u",
        default="admin",
        help="用于测试的管理员/用户登录名 (默认: admin)"
    )
    parser.add_argument(
        "--password", "-p",
        default="123456",
        help="登录密码 (默认: 123456)"
    )
    parser.add_argument(
        "--no-frontend",
        action="store_true",
        help="跳过前端 Web 服务探测，仅测试后端 API 链路"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="输出详细的 HTTP 请求与响应耗时调试信息"
    )

    args = parser.parse_args()

    suite = SmokeTestSuite(
        backend_url=args.backend_url,
        frontend_url=args.frontend_url,
        username=args.username,
        password=args.password,
        check_frontend=not args.no_frontend,
        verbose=args.verbose
    )

    success = suite.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
