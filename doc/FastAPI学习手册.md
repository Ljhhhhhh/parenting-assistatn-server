# FastAPI 学习手册

## 目录

1. [FastAPI 简介](#1-fastapi-简介)
2. [安装与设置](#2-安装与设置)
3. [第一个 FastAPI 应用](#3-第一个-fastapi-应用)
4. [路径参数](#4-路径参数)
5. [查询参数](#5-查询参数)
6. [请求体](#6-请求体)
7. [响应模型](#7-响应模型)
8. [依赖注入系统](#8-依赖注入系统)
9. [安全与认证](#9-安全与认证)
10. [中间件](#10-中间件)
11. [数据库集成](#11-数据库集成)
12. [后台任务](#12-后台任务)
13. [测试](#13-测试)
14. [部署](#14-部署)
15. [最佳实践](#15-最佳实践)

## 1. FastAPI 简介

FastAPI 是一个现代、快速（高性能）的 Web 框架，用于基于标准 Python 类型提示构建 API。

### 主要特点

- **快速**：性能非常高，与 NodeJS 和 Go 相当（归功于 Starlette 和 Pydantic）
- **快速编码**：提高功能开发速度约 200% 到 300%
- **更少的错误**：减少约 40% 的人为错误
- **直观**：强大的编辑器支持，自动补全无处不在，减少调试时间
- **简单**：设计易于使用和学习，减少阅读文档的时间
- **简短**：代码重复最小化，每个参数声明具有多个功能
- **健壮**：获取可用于生产环境的代码，自动交互式文档
- **标准化**：基于（并完全兼容）API 的开放标准：OpenAPI（以前称为 Swagger）和 JSON Schema

### 技术栈

FastAPI 建立在以下技术之上：

- **Starlette**：用于 Web 部分
- **Pydantic**：用于数据部分

## 2. 安装与设置

### 安装 FastAPI

```bash
pip install fastapi
```

### 安装 ASGI 服务器

对于生产环境，你需要一个 ASGI 服务器，如 Uvicorn 或 Hypercorn：

```bash
pip install "uvicorn[standard]"
```

### 完整安装（包含所有可选依赖）

```bash
pip install "fastapi[all]"
```

## 3. 第一个 FastAPI 应用

创建一个简单的 FastAPI 应用：

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "q": q}
```

### 运行应用

```bash
uvicorn main:app --reload
```

- `main`：文件 `main.py`
- `app`：在 `main.py` 文件中创建的 FastAPI 实例
- `--reload`：代码更改后自动重新加载（仅用于开发）

### 交互式 API 文档

FastAPI 自动生成交互式 API 文档：

- **Swagger UI**：访问 http://127.0.0.1:8000/docs
- **ReDoc**：访问 http://127.0.0.1:8000/redoc

## 4. 路径参数

路径参数是 URL 路径的一部分：

```python
@app.get("/items/{item_id}")
def read_item(item_id: int):
    return {"item_id": item_id}
```

### 路径参数类型转换

FastAPI 会根据类型注解自动转换参数类型：

```python
@app.get("/items/{item_id}")
def read_item(item_id: int):  # 自动转换为整数
    return {"item_id": item_id}
```

### 路径参数验证

使用 Pydantic 的 `Path` 进行验证：

```python
from fastapi import Path

@app.get("/items/{item_id}")
def read_item(item_id: int = Path(..., title="The ID of the item", ge=1)):
    return {"item_id": item_id}
```

### 预定义值

使用 Enum 限制可能的路径参数值：

```python
from enum import Enum

class ModelName(str, Enum):
    alexnet = "alexnet"
    resnet = "resnet"
    lenet = "lenet"

@app.get("/models/{model_name}")
def get_model(model_name: ModelName):
    if model_name is ModelName.alexnet:
        return {"model_name": model_name, "message": "Deep Learning FTW!"}
    
    if model_name.value == "lenet":
        return {"model_name": model_name, "message": "LeCNN all the images"}
    
    return {"model_name": model_name, "message": "Have some residuals"}
```

## 5. 查询参数

查询参数是 URL 中 `?` 后面的键值对：

```python
@app.get("/items/")
def read_items(skip: int = 0, limit: int = 10):
    return {"skip": skip, "limit": limit}
```

### 可选查询参数

将参数设置为可选：

```python
@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    if q:
        return {"item_id": item_id, "q": q}
    return {"item_id": item_id}
```

### 查询参数验证

使用 Pydantic 的 `Query` 进行验证：

```python
from fastapi import Query

@app.get("/items/")
def read_items(q: str = Query(None, min_length=3, max_length=50)):
    results = {"items": [{"item_id": "Foo"}, {"item_id": "Bar"}]}
    if q:
        results.update({"q": q})
    return results
```

### 多值查询参数

接收同一查询参数的多个值：

```python
@app.get("/items/")
def read_items(q: list[str] = Query(None)):
    query_items = {"q": q}
    return query_items
```

## 6. 请求体

使用 Pydantic 模型定义请求体：

```python
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    description: str = None
    price: float
    tax: float = None

@app.post("/items/")
def create_item(item: Item):
    return item
```

### 请求体 + 路径参数

同时使用请求体和路径参数：

```python
@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item):
    return {"item_id": item_id, **item.model_dump()}
```

### 请求体 + 路径参数 + 查询参数

```python
@app.put("/items/{item_id}")
def update_item(item_id: int, item: Item, q: str = None):
    result = {"item_id": item_id, **item.model_dump()}
    if q:
        result.update({"q": q})
    return result
```

### 嵌套模型

定义嵌套的 Pydantic 模型：

```python
class Image(BaseModel):
    url: str
    name: str

class Item(BaseModel):
    name: str
    description: str = None
    price: float
    tax: float = None
    tags: list[str] = []
    image: Image = None
```

## 7. 响应模型

使用 `response_model` 参数定义响应模型：

```python
@app.post("/items/", response_model=Item)
def create_item(item: Item):
    return item
```

### 响应模型过滤

使用 `response_model_exclude_unset` 过滤未设置的值：

```python
@app.get("/items/{item_id}", response_model=Item, response_model_exclude_unset=True)
def read_item(item_id: int):
    return items[item_id]
```

### 状态码

使用 `status_code` 参数设置状态码：

```python
@app.post("/items/", status_code=201)
def create_item(item: Item):
    return item
```

### 自定义响应

使用 `Response` 对象自定义响应：

```python
from fastapi import Response

@app.get("/items/{item_id}")
def read_item(item_id: int, response: Response):
    if item_id == 0:
        response.status_code = 404
    return {"item_id": item_id}
```

## 8. 依赖注入系统

FastAPI 提供了强大的依赖注入系统：

```python
from fastapi import Depends

def common_parameters(q: str = None, skip: int = 0, limit: int = 100):
    return {"q": q, "skip": skip, "limit": limit}

@app.get("/items/")
def read_items(commons: dict = Depends(common_parameters)):
    return {"commons": commons}
```

### 类作为依赖项

使用类作为依赖项：

```python
class CommonQueryParams:
    def __init__(self, q: str = None, skip: int = 0, limit: int = 100):
        self.q = q
        self.skip = skip
        self.limit = limit

@app.get("/items/")
def read_items(commons: CommonQueryParams = Depends()):
    return {"commons": commons}
```

### 子依赖项

依赖项可以有自己的依赖项：

```python
def query_extractor(q: str = None):
    return q

def query_or_default(q: str = Depends(query_extractor)):
    if q:
        return q
    return "default"

@app.get("/items/")
def read_items(query: str = Depends(query_or_default)):
    return {"q": query}
```

### 路径操作装饰器依赖项

应用于整个路径操作的依赖项：

```python
@app.get("/items/", dependencies=[Depends(verify_token), Depends(verify_key)])
def read_items():
    return [{"item": "Foo"}, {"item": "Bar"}]
```

## 9. 安全与认证

FastAPI 提供了多种安全机制：

### OAuth2 密码流

```python
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

@app.post("/token")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect username or password")
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me")
def read_users_me(token: str = Depends(oauth2_scheme)):
    user = get_current_user(token)
    return user
```

### JWT 认证

使用 JWT 令牌进行认证：

```python
from datetime import datetime, timedelta
from jose import JWTError, jwt

SECRET_KEY = "your-secret-key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
```

## 10. 中间件

中间件是处理请求和响应的组件：

```python
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

### CORS 中间件

配置 CORS（跨源资源共享）：

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 11. 数据库集成

FastAPI 可以与任何数据库集成。以下是使用 SQLAlchemy 的示例：

```python
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "postgresql://user:password@postgresserver/db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# 依赖项
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/users/")
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users
```

### SQLModel 集成

SQLModel 是 FastAPI 作者创建的库，结合了 SQLAlchemy 和 Pydantic：

```python
from sqlmodel import Field, Session, SQLModel, create_engine, select

class Hero(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str
    secret_name: str
    age: int = None

engine = create_engine("sqlite:///database.db")
SQLModel.metadata.create_all(engine)

def get_db():
    with Session(engine) as session:
        yield session

@app.post("/heroes/")
def create_hero(hero: Hero, db: Session = Depends(get_db)):
    db.add(hero)
    db.commit()
    db.refresh(hero)
    return hero
```

## 12. 后台任务

FastAPI 支持后台任务：

```python
@app.post("/send-notification/{email}")
async def send_notification(email: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(send_email_notification, email, message="Some notification")
    return {"message": "Notification sent in the background"}
```

## 13. 测试

使用 TestClient 测试 FastAPI 应用：

```python
from fastapi.testclient import TestClient

client = TestClient(app)

def test_read_main():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"Hello": "World"}
```

## 14. 部署

### 使用 Uvicorn 部署

```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 使用 Gunicorn 和 Uvicorn workers

```bash
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app
```

### Docker 部署

```dockerfile
FROM python:3.9

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
```

## 15. 最佳实践

### 项目结构

推荐的项目结构：

```
.
├── app
│   ├── __init__.py
│   ├── main.py
│   ├── api
│   │   ├── __init__.py
│   │   ├── dependencies.py
│   │   └── routes
│   │       ├── __init__.py
│   │       ├── items.py
│   │       └── users.py
│   ├── core
│   │   ├── __init__.py
│   │   ├── config.py
│   │   └── security.py
│   ├── db
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── models.py
│   ├── models
│   │   ├── __init__.py
│   │   ├── item.py
│   │   └── user.py
│   └── schemas
│       ├── __init__.py
│       ├── item.py
│       └── user.py
└── tests
    ├── __init__.py
    ├── conftest.py
    ├── test_items.py
    └── test_users.py
```

### 性能优化

- 使用异步函数处理 I/O 密集型操作
- 使用缓存减少重复计算
- 使用 `response_model` 过滤响应数据
- 使用 `BackgroundTasks` 处理耗时操作

### 安全最佳实践

- 使用 HTTPS
- 实现适当的认证和授权
- 验证所有输入
- 使用安全的密码哈希（如 bcrypt）
- 设置适当的 CORS 策略
- 使用环境变量存储敏感信息

## 参考资源

- [FastAPI 官方文档](https://fastapi.tiangolo.com/zh/)
- [FastAPI GitHub 仓库](https://github.com/tiangolo/fastapi)
- [Starlette 文档](https://www.starlette.io/)
- [Pydantic 文档](https://docs.pydantic.dev/)
- [SQLModel 文档](https://sqlmodel.tiangolo.com/)
- [Uvicorn 文档](https://www.uvicorn.org/)
