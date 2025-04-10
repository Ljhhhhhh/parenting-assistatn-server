# Full-Stack-FastAPI-Template 学习手册

## 目录

1. [项目简介](#1-项目简介)
2. [技术栈](#2-技术栈)
3. [项目结构](#3-项目结构)
4. [后端架构](#4-后端架构)
5. [前端架构](#5-前端架构)
6. [开发环境配置](#6-开发环境配置)
7. [Docker 与容器化](#7-docker-与容器化)
8. [数据库与迁移](#8-数据库与迁移)
9. [认证与授权](#9-认证与授权)
10. [API 开发](#10-api-开发)
11. [测试](#11-测试)
12. [部署](#12-部署)
13. [CI/CD](#13-cicd)
14. [最佳实践](#14-最佳实践)

## 1. 项目简介

Full-Stack-FastAPI-Template 是一个现代化的全栈 Web 应用模板，由 FastAPI 的创建者 Sebastián Ramírez (tiangolo) 开发。该模板提供了一个完整的开发框架，包含前端和后端，使用最新的技术栈和最佳实践，帮助开发者快速构建高质量的 Web 应用。

### 主要特点

- 完整的全栈解决方案，包含前端和后端
- 基于 Docker 的开发和生产环境
- 自动化的 API 文档
- 内置用户认证和授权系统
- 数据库集成和迁移工具
- 前端与后端的无缝集成
- CI/CD 配置
- 自动 HTTPS 配置

## 2. 技术栈

### 后端技术栈

- **FastAPI**: 高性能的 Python Web 框架
- **SQLModel**: 结合了 SQLAlchemy 和 Pydantic 的 ORM
- **Pydantic**: 数据验证和设置管理
- **PostgreSQL**: SQL 数据库
- **Alembic**: 数据库迁移工具
- **JWT**: 用于认证的 JSON Web Token
- **Pytest**: 测试框架

### 前端技术栈

- **React**: 用于构建用户界面的 JavaScript 库
- **TypeScript**: JavaScript 的类型超集
- **Vite**: 现代前端构建工具
- **Chakra UI**: React 组件库
- **TanStack Query**: 数据获取和缓存库
- **TanStack Router**: 路由库
- **Playwright**: 端到端测试工具

### 基础设施

- **Docker**: 容器化平台
- **Docker Compose**: 多容器 Docker 应用定义和运行工具
- **Traefik**: 反向代理和负载均衡器
- **GitHub Actions**: CI/CD 工具

## 3. 项目结构

Full-Stack-FastAPI-Template 的项目结构清晰明了，主要分为以下几个部分：

```
.
├── .github/            # GitHub Actions 配置
├── backend/            # 后端代码
├── frontend/           # 前端代码
├── scripts/            # 实用脚本
├── .env                # 环境变量
├── docker-compose.yml  # Docker Compose 配置
└── ...
```

### 后端结构

```
backend/
├── app/
│   ├── api/            # API 路由
│   ├── core/           # 核心配置
│   ├── crud/           # CRUD 操作
│   ├── db/             # 数据库设置
│   ├── models/         # 数据模型
│   ├── schemas/        # Pydantic 模式
│   ├── tests/          # 测试
│   └── main.py         # 主应用入口
├── alembic/            # 数据库迁移
└── ...
```

### 前端结构

```
frontend/
├── src/
│   ├── assets/         # 静态资源
│   ├── client/         # 生成的 API 客户端
│   ├── components/     # React 组件
│   ├── hooks/          # 自定义 hooks
│   ├── routes/         # 路由和页面
│   └── ...
├── tests/              # Playwright 测试
└── ...
```

## 4. 后端架构

### FastAPI 应用结构

FastAPI 应用的入口点是 `backend/app/main.py`，它初始化 FastAPI 应用并包含所有路由。

```python
# backend/app/main.py
from fastapi import FastAPI
from app.api.main import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

app.include_router(api_router, prefix=settings.API_V1_STR)
```

### 配置管理

配置通过 `backend/app/core/config.py` 管理，使用 Pydantic 的 `BaseSettings` 类：

```python
# backend/app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str
    # 其他配置...

settings = Settings()
```

### 数据库模型

数据库模型使用 SQLModel 定义，它结合了 SQLAlchemy 和 Pydantic：

```python
# backend/app/models.py
from sqlmodel import Field, SQLModel
import uuid

class User(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False
    # 其他字段...
```

### 依赖注入

FastAPI 的依赖注入系统用于提供数据库会话、当前用户等：

```python
# backend/app/api/deps.py
from fastapi import Depends, HTTPException
from sqlmodel import Session
from app.core.db import engine

def get_db():
    with Session(engine) as session:
        yield session

def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    # 验证 token 并返回用户
    ...
```

## 5. 前端架构

### React 应用结构

前端使用 React 和 TypeScript，通过 Vite 构建：

```tsx
// frontend/src/main.tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { RouterProvider, createRouter } from '@tanstack/react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { routeTree } from './routeTree.gen';

const queryClient = new QueryClient();
const router = createRouter({ routeTree });

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </React.StrictMode>,
);
```

### API 客户端

前端使用自动生成的 API 客户端与后端通信：

```tsx
// 使用生成的 API 客户端
import { UsersService } from '../client';

// 获取用户列表
const { data, isLoading } = useQuery({
  queryKey: ['users'],
  queryFn: () => UsersService.readUsers(),
});
```

### 路由

使用 TanStack Router 进行路由管理：

```tsx
// frontend/src/routes/_layout.tsx
import { createFileRoute } from '@tanstack/react-router';
import { Layout } from '../components/Layout';

export const Route = createFileRoute('/_layout')({
  component: Layout,
});
```

### UI 组件

使用 Chakra UI 构建用户界面：

```tsx
// frontend/src/components/UserList.tsx
import {
  Box,
  Heading,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
} from '@chakra-ui/react';

export const UserList = ({ users }) => (
  <Box>
    <Heading>Users</Heading>
    <Table>
      <Thead>
        <Tr>
          <Th>Email</Th>
          <Th>Is Active</Th>
          <Th>Is Superuser</Th>
        </Tr>
      </Thead>
      <Tbody>
        {users.map((user) => (
          <Tr key={user.id}>
            <Td>{user.email}</Td>
            <Td>{user.is_active ? 'Yes' : 'No'}</Td>
            <Td>{user.is_superuser ? 'Yes' : 'No'}</Td>
          </Tr>
        ))}
      </Tbody>
    </Table>
  </Box>
);
```

## 6. 开发环境配置

### 本地开发环境

Full-Stack-FastAPI-Template 使用 Docker Compose 设置本地开发环境：

```bash
# 启动开发环境
docker compose watch
```

这将启动以下服务：

- 后端 API (http://localhost:8000)
- 前端开发服务器 (http://localhost:5173)
- PostgreSQL 数据库
- Adminer 数据库管理工具 (http://localhost:8080)
- Traefik 代理 (http://localhost:8090)
- MailCatcher 邮件测试工具 (http://localhost:1080)

### 环境变量

开发环境的配置存储在 `.env` 文件中：

```
# .env
DOMAIN=localhost
STACK_NAME=fastapi-project
PROJECT_NAME=FastAPI Project
SECRET_KEY=changethis
FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD=changethis
POSTGRES_PASSWORD=changethis
POSTGRES_SERVER=db
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_DB=app
```

### 前端开发

前端开发可以在 Docker 容器内进行，也可以在本地进行：

```bash
# 本地前端开发
cd frontend
npm install
npm run dev
```

### 后端开发

后端开发同样可以在 Docker 容器内进行，也可以在本地进行：

```bash
# 本地后端开发
cd backend
uv sync
source .venv/bin/activate
fastapi dev app/main.py
```

## 7. Docker 与容器化

### Docker Compose 配置

项目使用 Docker Compose 管理容器：

```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    image: '${DOCKER_IMAGE_BACKEND}:${TAG-latest}'
    depends_on:
      - db
    env_file:
      - .env
    environment:
      - DOMAIN=${DOMAIN}
      - FRONTEND_HOST=${FRONTEND_HOST}
      # 其他环境变量...

  frontend:
    image: '${DOCKER_IMAGE_FRONTEND}:${TAG-latest}'
    env_file:
      - .env
    environment:
      - VITE_API_URL=${FRONTEND_HOST}

  db:
    image: postgres:15
    volumes:
      - app-db-data:/var/lib/postgresql/data/pgdata
    env_file:
      - .env
    environment:
      - PGDATA=/var/lib/postgresql/data/pgdata
      # 其他环境变量...

volumes:
  app-db-data:
```

### 开发环境覆盖

`docker-compose.override.yml` 文件包含开发环境特定的配置：

```yaml
# docker-compose.override.yml
version: '3.8'
services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    volumes:
      - ./backend/app:/app/app
    command: fastapi run --reload app/main.py

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm run dev

  # 其他服务...
```

## 8. 数据库与迁移

### 数据库设置

项目使用 PostgreSQL 作为数据库，通过 SQLModel 进行 ORM 操作：

```python
# backend/app/core/db.py
from sqlmodel import create_engine, SQLModel, Session
from app.core.config import settings

engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)

def get_session():
    with Session(engine) as session:
        yield session
```

### 数据库迁移

使用 Alembic 进行数据库迁移：

```bash
# 创建迁移
alembic revision --autogenerate -m "Add column last_name to User model"

# 应用迁移
alembic upgrade head
```

### 初始数据

项目包含初始数据脚本，用于创建第一个超级用户：

```python
# backend/app/initial_data.py
from sqlmodel import Session
from app.core.db import engine
from app.models import User
from app.core.config import settings
from app.core.security import get_password_hash

def init_db(session: Session) -> None:
    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
        )
        user = create_user(session=session, user_create=user_in)
```

## 9. 认证与授权

### JWT 认证

项目使用 JWT 进行认证：

```python
# backend/app/core/security.py
from datetime import datetime, timedelta
from jose import jwt
from app.core.config import settings

def create_access_token(subject: str, expires_delta: timedelta = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt
```

### 用户认证

用户认证通过 `/login/access-token` 端点实现：

```python
# backend/app/api/routes/login.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from app.core.security import create_access_token
from app.core.config import settings
from datetime import timedelta

router = APIRouter()

@router.post("/login/access-token")
def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": create_access_token(
            user.id, expires_delta=access_token_expires
        ),
        "token_type": "bearer",
    }
```

### 权限控制

使用依赖项进行权限控制：

```python
# backend/app/api/deps.py
def get_current_active_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=403, detail="The user doesn't have enough privileges"
        )
    return current_user
```

## 10. API 开发

### 路由组织

API 路由组织在 `backend/app/api/routes/` 目录下：

```python
# backend/app/api/main.py
from fastapi import APIRouter
from app.api.routes import items, login, users, utils

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)
```

### CRUD 操作

CRUD 操作封装在 `backend/app/crud.py` 中：

```python
# backend/app/crud.py
from sqlmodel import Session, select
from app.models import User, UserCreate

def get_user(session: Session, user_id: str) -> User | None:
    return session.exec(select(User).where(User.id == user_id)).first()

def get_user_by_email(session: Session, email: str) -> User | None:
    return session.exec(select(User).where(User.email == email)).first()

def create_user(session: Session, user_create: UserCreate) -> User:
    db_user = User(
        email=user_create.email,
        hashed_password=get_password_hash(user_create.password),
        is_superuser=user_create.is_superuser,
    )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user
```

### 响应模型

使用 Pydantic 模型定义 API 响应：

```python
# backend/app/models.py
from pydantic import BaseModel, EmailStr

class UserBase(BaseModel):
    email: EmailStr
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = None

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    password: str | None = None

class UserPublic(UserBase):
    id: str
```

## 11. 测试

### 后端测试

使用 Pytest 进行后端测试：

```python
# backend/app/tests/test_users.py
from fastapi.testclient import TestClient
from sqlmodel import Session
from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_create_user(db: Session):
    data = {
        "email": "test@example.com",
        "password": "password",
        "full_name": "Test User",
    }
    response = client.post(
        f"{settings.API_V1_STR}/users/",
        headers={"Authorization": f"Bearer {superuser_token}"},
        json=data,
    )
    assert response.status_code == 201
    created_user = response.json()
    assert created_user["email"] == data["email"]
    assert created_user["full_name"] == data["full_name"]
```

### 前端测试

使用 Playwright 进行端到端测试：

```typescript
// frontend/tests/login.spec.ts
import { test, expect } from '@playwright/test';

test('login page works', async ({ page }) => {
  await page.goto('/login');
  await page.fill('input[name="email"]', 'admin@example.com');
  await page.fill('input[name="password"]', 'admin');
  await page.click('button[type="submit"]');
  await expect(page).toHaveURL('/');
});
```

### 运行测试

```bash
# 运行后端测试
cd backend
bash ./scripts/test.sh

# 运行前端测试
cd frontend
npx playwright test
```

## 12. 部署

### 部署准备

部署前需要准备：

1. 一个远程服务器
2. 配置域名 DNS 记录指向服务器 IP
3. 在服务器上安装 Docker

### Traefik 配置

部署使用 Traefik 作为反向代理：

```bash
# 创建 Traefik 公共网络
docker network create traefik-public

# 设置环境变量
export USERNAME=admin
export PASSWORD=changethis
export HASHED_PASSWORD=$(openssl passwd -apr1 $PASSWORD)
export DOMAIN=fastapi-project.example.com
export EMAIL=admin@example.com

# 启动 Traefik
docker compose -f docker-compose.traefik.yml up -d
```

### 部署应用

```bash
# 设置环境变量
export ENVIRONMENT=production
export DOMAIN=fastapi-project.example.com

# 部署应用
docker compose -f docker-compose.yml up -d
```

### 多环境部署

项目支持多环境部署，如 staging 和 production：

- `staging`: 部署到 `api.staging.fastapi-project.example.com` 和 `dashboard.staging.fastapi-project.example.com`
- `production`: 部署到 `api.fastapi-project.example.com` 和 `dashboard.fastapi-project.example.com`

## 13. CI/CD

### GitHub Actions

项目包含 GitHub Actions 配置，用于自动化测试和部署：

```yaml
# .github/workflows/test.yml
name: Test

on:
  push:
    branches: [master]
  pull_request:
    branches: [master]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install uv
          uv sync
      - name: Test with pytest
        run: |
          pytest
```

### 自动部署

GitHub Actions 配置自动部署到不同环境：

- 推送到 `master` 分支时部署到 `staging` 环境
- 发布 release 时部署到 `production` 环境

### 自托管 Runner

使用自托管 GitHub Actions runner 进行部署：

```bash
# 创建 GitHub Actions 用户
sudo adduser github

# 添加 Docker 权限
sudo usermod -aG docker github

# 安装 GitHub Actions runner
# 按照 GitHub 提供的说明进行操作
```

## 14. 最佳实践

### 代码风格

项目使用 pre-commit 钩子确保代码质量：

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: check-added-large-files
      - id: check-toml
      - id: check-yaml

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.3
    hooks:
      - id: ruff
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-eslint
    rev: v8.53.0
    hooks:
      - id: eslint
        files: \.(js|ts|tsx)$
        types: [file]
        additional_dependencies:
          - eslint@8.53.0
          - typescript@5.2.2
          # 其他依赖...

  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.0.3
    hooks:
      - id: prettier
        types_or: [javascript, jsx, ts, tsx, json, css, markdown]
```

### 安全最佳实践

- 使用环境变量存储敏感信息
- 使用 JWT 进行安全认证
- 密码哈希存储
- HTTPS 加密通信
- 定期更新依赖

### 性能优化

- 使用 Docker 多阶段构建减小镜像大小
- 数据库索引优化
- 前端代码分割和懒加载
- 使用缓存减少数据库查询

### 文档

- 自动生成的 API 文档 (Swagger UI)
- 详细的 README 文件
- 代码注释
- 部署和开发指南

## 总结

Full-Stack-FastAPI-Template 是一个功能完备的全栈 Web 应用模板，提供了从开发到部署的完整解决方案。它使用现代化的技术栈，遵循最佳实践，帮助开发者快速构建高质量的 Web 应用。

通过使用这个模板，你可以专注于业务逻辑的实现，而不必担心基础架构的搭建和配置。无论是个人项目还是企业应用，Full-Stack-FastAPI-Template 都是一个优秀的起点。
