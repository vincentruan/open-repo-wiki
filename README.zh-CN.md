# OpenRepoWiki

![OpenRepoWiki 示例图片](assets/openrepowiki.png)

**OpenRepoWiki** 是一个能够为任意 GitHub 仓库自动生成综合 Wiki 页面的工具。我**讨厌**阅读代码，但我想学习如何构建各种东西——从网站到数据库。这就是我创建 **OpenRepoWiki** 的原因，通过它我们可以理解特定仓库中各个文件和文件夹的用途。

## 功能特性

- **自动生成 Wiki：** 创建仓库用途、功能和核心组件的摘要概述。
- **代码库分析：** 分析代码结构，识别关键文件和函数，并解释它们在项目中的作用。
- **依赖关系图：** 使用带有标注箭头的 Mermaid 图表展示每个文件夹中文件之间的关系（例如："提供配置给"、"为...转换数据"）。
- **代码块链接：** 天蓝色高亮的代码块将指向其引用的 GitHub 链接。

## 安装

### 环境要求

- Google AI Studio 或 Deepseek API 密钥（二选一）
- GitHub API 密钥（用于获取更多仓库数据请求配额）
- Amazon S3（如果只在本地使用可以忽略这些参数。如果要部署到服务器，数据库需要使用证书。）
- Docker（如果在本地部署）

### 配置（Docker）

1. 复制 `.env.example` 为 `.env`
2. 只需配置 `GitHub token` 和 `LLM 配置`
3. 运行 `docker compose up` 或 `docker compose up -d`（后台运行，隐藏输出）

### 本地开发（无 Docker）

不使用 Docker 进行本地开发时，需要连接 MySQL 或 PostgreSQL 数据库：

1. **设置环境：**
   ```bash
   cd src
   python -m venv .venv
   source .venv/bin/activate  # Windows 系统: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **配置环境变量：**
   ```bash
   cp ../.env.local.example .env
   # 编辑 .env 文件，添加数据库连接信息和 LLM_APIKEY
   ```

3. **初始化数据库：**
   ```bash
   python manage.py check_tables  # 验证表结构（可选）
   python manage.py migrate
   ```

4. **运行服务器：**
   ```bash
   python manage.py runserver
   ```

5. 在浏览器中打开 http://localhost:8000。

> [!NOTE]
> 本地开发模式下：
> - 连接到远程 MySQL 或 PostgreSQL 数据库
> - 仓库处理同步运行（大型仓库可能需要几分钟）
> - 无需 Redis 或 Celery

#### Ollama 配置指南

- 建议运行大于 14b 参数的 LLM。
- 不需要提供 API KEY
- 将 LLM_PROVIDER 设置为 Ollama（将连接到默认的 Ollama 端点）
- 使用 `ollama ls` 命令查看可用模型，将 LLM_MODELNAME 设置为对应的模型名称
- 如果使用小参数 LLM（如 8b、14b），建议将 TOKEN_PROCESSING_CHARACTER_LIMIT 设置在 10000-20000 之间（约 300-600 行代码）

**示例：**

```
LLM_PROVIDER=deepseek
LLM_APIKEY=sk-....
LLM_MODELNAME=deepseek-chat
```

### 附加信息

> [!CAUTION]
> 使用前请注意，每个仓库可能轻易消耗 100 万输入/输出 token。因此建议使用更便宜的 LLM。

- 如果在本地部署，只需配置 Docker PostgreSQL 容器、GitHub API 密钥，以及 Google AI Studio 或 Deepseek API 密钥

### 多仓库来源支持

OpenRepoWiki 支持从多种来源生成文档：

#### GitHub 仓库
输入以下任意格式的 GitHub 仓库：
- `owner/repo`（例如：`daeisbae/open-repo-wiki`）
- `https://github.com/owner/repo`
- `github.com/owner/repo`

#### 本地文件夹
输入绝对路径来扫描本地目录：
- `/home/user/my-project`
- `~/projects/my-app`（将展开为用户主目录）
- `C:\Projects\MyApp`（Windows）

适用场景：
- 未托管在任何 Git 服务上的私有项目
- 开发过程中的快速文档生成
- 离线文档生成

#### Git URL（GitLab、Bitbucket 等）
输入任何 Git 兼容的 URL 进行克隆和扫描：
- `https://gitlab.com/owner/repo`
- `https://bitbucket.org/owner/repo`
- `git@github.com:owner/repo.git`
- 自托管 Git 服务器

> [!NOTE]
> Git URL 扫描需要安装 `git` 并添加到 PATH 环境变量中。
> 仓库将被克隆到临时目录进行处理。

### MySQL 数据库支持

OpenRepoWiki 默认使用 PostgreSQL。你也可以选择使用 MySQL 作为数据库后端。

#### 配置方法

1. 在 `.env` 文件中设置数据库引擎：
   ```
   DB_ENGINE=mysql
   DB_HOST=localhost
   DB_PORT=3306
   DB_NAME=openrepowiki
   DB_USER=root
   DB_PASSWORD=your_password
   ```

2. 修改 `docker-compose.yml` 使用 MySQL 替代 PostgreSQL：
   ```yaml
   db:
     image: mysql:8.0
     environment:
       MYSQL_ROOT_PASSWORD: your_password
       MYSQL_DATABASE: openrepowiki
     ports:
       - "3306:3306"
   ```

3. 运行 `docker compose up` 启动应用。

> [!NOTE]
> 使用 MySQL 时，请确保 MySQL 服务器使用 `utf8mb4` 字符集以正确支持 Unicode。

## 需求和文档

参阅 [文档](docs/README.zh-CN.md)
