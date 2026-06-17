# EDMS 系统部署手册

本手册供系统管理员进行 EDMS（电子文档管理系统）的安装部署操作。当前架构基于 **MySQL 8.0+** 并集成了 AI 与 WebSocket 服务。

---

## 1. 系统要求

### 1.1 硬件要求
| 组件 | 最低配置 | 推荐配置 |
| :--- | :--- | :--- |
| CPU | 2 核 | 4 核+ |
| 内存 | 4 GB | 8 GB+ |
| 磁盘空间 | 20 GB | 50 GB+ |

### 1.2 软件要求
- **容器引擎**：Docker 20.10+ 及 Docker Compose 2.0+ (容器化部署必备)。
- **数据库**：**MySQL 8.0+** (必须支持 `utf8mb4` 字符集)。
- **操作系统**：Windows、Linux (Ubuntu/CentOS) 或 macOS。

---

## 2. 部署步骤

### 步骤 1：准备环境
1. **解压部署包**。
2. **编辑配置**：在 `sources/docker/.env` 或启动目录创建 `.env` 文件。

### 步骤 2：启动服务

#### 【选项 A：Docker 一键部署（推荐）】
1. **进入目录**：`cd sources/docker`。
2. **启动**：
   - Windows: 运行 `build.bat`。
   - Linux: 运行 `./build.sh`。
   - 或者手动执行：`docker-compose up -d --build`。

#### 【选项 A-1：在 Docker 部署中启用 HTTPS 加密（可选）】
如果您需要在容器化部署中启用安全传输协议 (HTTPS)，系统已预置了 Nginx SSL 配置文件和端口绑定。具体配置步骤如下：

1. **准备 SSL 证书**：
   在 `sources/docker/certs/` 目录下放置您的 SSL 证书和私钥文件，并分别命名为：
   - 证书文件：`fullchain.pem`
   - 私钥文件：`privkey.pem`
   
   *(提示：如果您使用的是本地脚本部署中由 `mkcert` 自动生成的开发证书，可以直接将项目根目录下的 `localhost+2.pem` 重命名拷贝为 `certs/fullchain.pem`，将 `localhost+2-key.pem` 重命名拷贝为 `certs/privkey.pem`；或者直接修改 `docker-compose.yml` 里的卷挂载，将证书文件映射至根目录，例如：)*
   ```yaml
   - ../../localhost+2.pem:/etc/nginx/certs/fullchain.pem:ro
   - ../../localhost+2-key.pem:/etc/nginx/certs/privkey.pem:ro
   ```

2. **启用卷挂载配置**：
   修改 `sources/docker/docker-compose.yml`，在 `frontend` 服务的 `volumes` 部分下，取消以下两行的注释以挂载证书和 Nginx 配置文件：
   ```yaml
   - ./frontend/nginx.ssl.conf:/etc/nginx/conf.d/default.conf:ro
   - ./certs:/etc/nginx/certs:ro
   ```

3. **指定 HTTPS 端口（可选）**：
   默认使用宿主机的 `443` 端口接入 HTTPS。如需更换，可在 `sources/docker/.env` 文件中修改 `SSL_PORT` 变量。

4. **重新编译并启动容器**：
   ```bash
   docker-compose down
   docker-compose up -d --build
   ```

#### 【选项 B：手动本地部署】
1. **MySQL 初始化**：
   ```sql
   CREATE DATABASE edms_db CHARSET utf8mb4;
   ```
2. **后端启动**：
   ```bash
   cd sources/backend
   pip install -r requirements.txt
   pip install pymysql
   python wsgi.py
   ```
3. **前端启动**：
   ```bash
    cd sources/frontend
    npm install
    npm run dev
    ```

#### 【选项 C：本地开发启用 HTTPS (可选)】
为了在本地开发中使用安全的 HTTPS 协议（例如调试部分需要 Secure Context 的浏览器 API 或 WebSockets），项目支持使用 `mkcert` 自动配置本地受信任的 SSL 证书。

1. **安装 mkcert 并信任 CA（仅需首次执行一次）**：
   * 确保项目根目录下有 `mkcert.exe` 工具（若无，请从 [mkcert Releases](https://github.com/FiloSottile/mkcert/releases) 下载 Windows 对应的二进制文件并重命名放至项目根目录）。
   * 以 **管理员身份** 打开终端（PowerShell 或 CMD），进入项目根目录，执行：
     ```powershell
     .\mkcert.exe -install
     ```
     根据系统安全提示选择 **“是 (Yes)”** 信任本地 CA 根证书。

2. **启动与自动生成证书**：
   * 执行项目启动脚本（如双击根目录下的 `start_manual.bat` 或 `frontend_start.bat`）。
   * 启动脚本检测到证书未生成时，会自动调用 `mkcert.exe` 在项目根目录下生成 `localhost+2.pem` 和 `localhost+2-key.pem`。
   * 前端运行成功后，访问地址将自动升级为 **`https://localhost:5173`** 且被浏览器完全信任。

---

## 3. 配置指南 (.env 环境变量)

您必须正确配置 `.env` 文件，特别是数据库连接串：

| 变量名 | 说明 | 示例值 |
| :--- | :--- | :--- |
| WEB_PORT | 系统访问端口 | 80 |
| DATABASE_URL | MySQL 连接串 | mysql+pymysql://root:123456@db:3306/edms_db?charset=utf8mb4 |
| JWT_SECRET_KEY | 令牌签名密钥 | production-secure-key |
| AI_API_KEY | 大模型 API Key | sk-xxxxxx |
| CORS_ORIGINS | 允许的 CORS 来源 | http://localhost,http://your-domain.com |

*注意：`DATABASE_URL` 必须包含 `charset=utf8mb4` 以支持复杂富文本。*

---

## 4. 故障排查

### 4.1 数据库连接失败
- **检查驱动**：确保 URL 以 `mysql+pymysql://` 开头。
- **权限问题**：确保 MySQL 允许远程连接且账号密码正确。
- **编码报错**：确保数据库默认字符集为 `utf8mb4`。

### 4.2 实时协同断连 (WebSocket)
- 如果前端通过 Nginx 转发，请确保配置了以下 Header：
  ```nginx
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "Upgrade";
  ```

### 4.3 端口已被占用
**错误**：`Port 80 is already in use`
**解决方案**：修改 `.env` 文件中的 `WEB_PORT` 变量。

---

## 5. 维护与备份

### 5.1 数据库备份
定期使用 `mysqldump` 备份数据：
```bash
docker exec edms-mysql mysqldump -u root -p'password' edms_db > backup.sql
```

### 5.2 文件资产备份
请同步备份存放上传附件及区块链账本的持久化存储目录（通常为 `data/` 目录）。

### 5.3 数据持久化
所有持久化数据存储在挂载的目录中：
- `data/backend/` - 应用上传的文件和其他持久化数据

---

## 6. 部署后验证

1. **服务状态检查**
   ```bash
   docker ps
   ```

2. **日志验证**
   ```bash
   docker-compose logs -f
   ```

3. **前端访问测试**
   - 打开浏览器访问 http://localhost
   - 验证登录页面是否正常加载
