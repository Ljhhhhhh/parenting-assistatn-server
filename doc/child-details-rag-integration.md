# 儿童详情 RAG 集成

本文档描述了一个用于持续记录和管理儿童特定详细信息，并将其直接集成到 RAG（检索增强生成）可检索知识库中的系统的实现。

## 概述

该系统允许用户：

1. 记录详细的儿童特定信息（兴趣、里程碑、日常事件、偏好）
2. 自动将此信息嵌入到向量数据库中以供检索
3. 在聊天对话期间，根据用户的查询检索相关的儿童详细信息
4. 根据需要管理（更新、删除）儿童详细信息

## 组件

### 1. 数据模型

`ChildDetail` 模型存储详细的儿童特定信息：

```python
class ChildDetail(ChildDetailBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    child_id: uuid.UUID = Field(foreign_key="child.id")
    child: Child = Relationship(back_populates="child_details")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    recorded_at: datetime = Field(default_factory=datetime.utcnow)  # 记录/观察到详细信息的时间
    embedding_id: Optional[str] = None  # 如果已嵌入，则为向量存储中的 ID
```

关键字段：
- `detail_type`: 详细信息类型（兴趣、里程碑、日常事件、偏好）
- `content`: 实际的详细信息内容
- `tags`: 用于分类的标签
- `importance`: 重要性级别 (1-10)
- `embedding_id`: 向量存储中嵌入的引用

### 2. 向量嵌入

儿童详细信息在创建或更新时会自动嵌入到向量存储中：

```python
def embed_child_detail(child_detail: ChildDetail) -> str:
    """
    将儿童详细信息嵌入到向量存储中。
    """
    # 格式化内容以进行嵌入
    content = f"Child Detail - Type: {child_detail.detail_type}\n"
    content += f"Content: {child_detail.content}\n"
    if child_detail.tags:
        content += f"Tags: {', '.join(child_detail.tags)}\n"
    
    # 创建文档
    doc = Document(
        page_content=content,
        metadata={
            "source": "child_detail",
            "child_detail_id": str(child_detail.id),
            "child_id": str(child_detail.child_id),
            "detail_type": child_detail.detail_type,
            "tags": child_detail.tags,
            "importance": child_detail.importance,
            "recorded_at": child_detail.recorded_at.isoformat() if child_detail.recorded_at else None,
        }
    )
    
    # 添加到向量存储
    ids = vectorstore.add_documents([doc])
    
    return ids[0] if ids else None
```

### 3. RAG 集成

在聊天对话期间，会根据与用户查询的相关性检索儿童详细信息：

```python
def get_child_details_for_rag(
    db: Session,
    child_id: uuid.UUID,
    query: str,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    根据与查询的相关性获取 RAG 的儿童详细信息。
    """
    # 获取查询的嵌入
    query_embedding = embedding_function.embed_query(query)
    
    # 搜索向量存储以查找相关的儿童详细信息
    search_filter = {"child_id": str(child_id), "source": "child_detail"}
    results = vectorstore.similarity_search_with_score_by_vector(
        query_embedding,
        k=limit,
        filter=search_filter
    )
    
    # 格式化结果
    child_details = []
    for doc, score in results:
        child_details.append({
            "content": doc.page_content,
            "metadata": doc.metadata,
            "relevance_score": score
        })
    
    return child_details
```

### 4. API 端点

以下 API 端点可用于管理儿童详细信息：

- `POST /api/v1/child-details/`: 创建新的儿童详细信息
- `GET /api/v1/child-details/`: 检索儿童详细信息
- `GET /api/v1/child-details/{detail_id}`: 获取特定的儿童详细信息
- `PUT /api/v1/child-details/{detail_id}`: 更新儿童详细信息
- `DELETE /api/v1/child-details/{detail_id}`: 删除儿童详细信息
- `POST /api/v1/child-details/batch`: 批量创建多个儿童详细信息

## 使用示例

### 1. 创建儿童详细信息

```http
POST /api/v1/child-details/
Content-Type: application/json
Authorization: Bearer <token>

{
  "detail_type": "interest",
  "content": "喜欢玩积木并创建塔",
  "tags": ["玩具", "发育", "运动技能"],
  "importance": 8,
  "child_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

### 2. 检索儿童详细信息

```http
GET /api/v1/child-details/?child_id=123e4567-e89b-12d3-a456-426614174000&detail_type=interest
Authorization: Bearer <token>
```

### 3. 更新儿童详细信息

```http
PUT /api/v1/child-details/123e4567-e89b-12d3-a456-426614174001
Content-Type: application/json
Authorization: Bearer <token>

{
  "content": "喜欢玩积木并创建复杂的结构",
  "importance": 9
}
```

### 4. 批量创建儿童详细信息

```http
POST /api/v1/child-details/batch
Content-Type: application/json
Authorization: Bearer <token>

[
  {
    "detail_type": "milestone",
    "content": "11 个月时迈出第一步",
    "tags": ["发育", "运动"],
    "importance": 10,
    "child_id": "123e4567-e89b-12d3-a456-426614174000"
  },
  {
    "detail_type": "preference",
    "content": "喜欢甜食而不是咸味食物",
    "tags": ["食物", "口味"],
    "importance": 6,
    "child_id": "123e4567-e89b-12d3-a456-426614174000"
  }
]
```

## 与聊天集成

当用户提出关于他们孩子的问题时，系统：

1. 检索孩子的基本信息（姓名、年龄、性别）
2. 根据查询搜索相关的儿童详细信息
3. 将这些详细信息包含在提供给语言模型的上下文中
4. 生成一个包含儿童特定信息的响应

这使得 AI 助手能够提供个性化的响应，从而考虑到孩子的独特特征和历史。

## 数据库迁移

包含一个数据库迁移以添加 `ChildDetail` 表：

```python
def upgrade():
    op.create_table(
        'childdetail',
        sa.Column('detail_type', sa.String(length=50), nullable=False),
        sa.Column('content', sa.String(), nullable=False),
        sa.Column('tags', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('importance', sa.Integer(), nullable=False),
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('child_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('recorded_at', sa.DateTime(), nullable=False),
        sa.Column('embedding_id', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['child_id'], ['child.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
```

要应用迁移，请运行：

```bash
cd backend
alembic upgrade head
```
