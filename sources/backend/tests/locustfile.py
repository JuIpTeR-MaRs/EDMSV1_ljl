import random
from locust import HttpUser, task, between

# 系统中预置的测试账号列表（默认密码均为 "123"）
TEST_USERS = [
    "admin", "zhangwei", "xiena", "wangfang", "liuyang", 
    "chenxiao", "zhaoming", "sunli", "wugang", "zhoujie", 
    "hhh", "linyuan", "lwj", "cjh", "hc"
]

class EDMSPerformanceUser(HttpUser):
    # 模拟用户在操作之间有 1 到 3 秒的思考时间
    wait_time = between(1, 3)
    
    def on_start(self):
        """用户初始化：随机选择一个预置账号登录，获取 JWT，并动态发现可用的文档和版本"""
        self.headers = {}
        self.valid_diff_targets = []  # 保存可用比对目标 (doc_id, v_from, v_to)
        
        # 随机挑选一个测试账号登录
        self.current_user = random.choice(TEST_USERS)
        
        # 1. 模拟用户登录
        r = self.client.post("/api/auth/login", json={"login_name": self.current_user, "password": "123"})
        if r.status_code == 200:
            token = r.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {token}"}
            
            # 2. 动态获取当前用户有权访问的文档列表
            doc_res = self.client.get("/api/documents?scope=all", headers=self.headers)
            if doc_res.status_code == 200:
                docs = doc_res.json().get("items", [])
                
                # 获取前几个文档的版本以供后续比对测试
                for doc in docs[:5]:
                    doc_id = doc.get("id")
                    ver_res = self.client.get(f"/api/documents/{doc_id}/versions", headers=self.headers)
                    if ver_res.status_code == 200:
                        versions = ver_res.json().get("items", [])
                        if len(versions) >= 2:
                            self.valid_diff_targets.append((doc_id, versions[1].get("id"), versions[0].get("id")))
                        elif len(versions) == 1:
                            self.valid_diff_targets.append((doc_id, versions[0].get("id"), versions[0].get("id")))
        else:
            print(f"[-] User {self.current_user} failed to authenticate. Check if backend is running.")

    @task(3)
    def view_documents_list(self):
        """高频任务：模拟普通用户查看文档列表"""
        if self.headers:
            self.client.get("/api/documents?scope=all", headers=self.headers)

    @task(1)
    def trigger_version_diff(self):
        """中频任务：模拟用户并发进行历史版本比对与轮询"""
        if self.headers and self.valid_diff_targets:
            doc_id, v_from, v_to = random.choice(self.valid_diff_targets)
            
            # 发起异步比对请求（返回 202 并携带 task_id）
            r = self.client.get(
                f"/api/documents/{doc_id}/diff?from={v_from}&to={v_to}&mode=inline",
                headers=self.headers,
                name="/api/documents/[id]/diff"
            )
            
            if r.status_code == 202:
                task_id = r.json().get("task_id")
                if task_id:
                    # 模拟前端轮询任务状态（最多轮询 3 次）
                    for _ in range(3):
                        poll_res = self.client.get(
                            f"/api/documents/tasks/{task_id}",
                            headers=self.headers,
                            name="/api/documents/tasks/[task_id]"
                        )
                        if poll_res.status_code == 200:
                            status = poll_res.json().get("status")
                            if status in ("completed", "failed"):
                                break
                        else:
                            break

    @task(2)
    def login_endpoint_stress(self):
        """核心压测任务：高频向 /api/auth/login 发送登录请求，测试登录接口自身的吞吐能力"""
        user_to_login = random.choice(TEST_USERS)
        self.client.post(
            "/api/auth/login", 
            json={"login_name": user_to_login, "password": "123"},
            name="/api/auth/login [Stress]"
        )

