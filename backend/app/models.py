import uuid
from datetime import datetime, date
from typing import List, Dict, Any, Optional

from pydantic import EmailStr
from sqlmodel import Field, Relationship, SQLModel, JSON


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=40)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=40)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=40)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=40)
    new_password: str = Field(min_length=8, max_length=40)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)
    children: list["Child"] = Relationship(back_populates="parent", cascade_delete=True)
    chat_histories: list["ChatHistory"] = Relationship(back_populates="user", cascade_delete=True)


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


# Child models
class ChildBase(SQLModel):
    name: str = Field(max_length=255)
    birthday: date
    gender: str = Field(max_length=10)


class ChildCreate(ChildBase):
    pass


class ChildUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=255)
    birthday: date | None = None
    gender: str | None = Field(default=None, max_length=10)


class Child(ChildBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    parent_id: uuid.UUID = Field(foreign_key="user.id")
    parent: User = Relationship(back_populates="children")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    growth_records: list["GrowthRecord"] = Relationship(back_populates="child", cascade_delete=True)
    chat_histories: list["ChatHistory"] = Relationship(back_populates="child", cascade_delete=True)
    child_details: list["ChildDetail"] = Relationship(back_populates="child", cascade_delete=True)


class ChildPublic(ChildBase):
    id: uuid.UUID
    parent_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class ChildrenPublic(SQLModel):
    data: list[ChildPublic]
    count: int


# Growth record models
class GrowthRecordBase(SQLModel):
    record_type: str = Field(max_length=50)  # e.g., feeding, sleep, diaper, etc.
    record_data: Dict[str, Any] = Field(sa_type=JSON)
    recorded_at: datetime
    notes: str | None = None


class GrowthRecordCreate(GrowthRecordBase):
    child_id: uuid.UUID


class GrowthRecordUpdate(SQLModel):
    record_type: str | None = Field(default=None, max_length=50)
    record_data: Dict[str, Any] | None = None
    recorded_at: datetime | None = None
    notes: str | None = None


class GrowthRecord(GrowthRecordBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    child_id: uuid.UUID = Field(foreign_key="child.id")
    child: Child = Relationship(back_populates="growth_records")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    attachments: List[str] | None = Field(default=None, sa_type=JSON)


class GrowthRecordPublic(GrowthRecordBase):
    id: uuid.UUID
    child_id: uuid.UUID
    created_at: datetime
    attachments: List[str] | None = None


class GrowthRecordsPublic(SQLModel):
    data: list[GrowthRecordPublic]
    count: int


# Document models
class DocumentBase(SQLModel):
    title: str = Field(max_length=255)
    description: str | None = Field(default=None)
    file_type: str = Field(max_length=20)  # e.g., pdf, docx, html
    status: str = Field(max_length=20, default="active")  # active, deleted, etc.


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(SQLModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = None
    status: str | None = Field(default=None, max_length=20)


class Document(DocumentBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    filename: str = Field(max_length=255)
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    doc_metadata: Dict[str, Any] | None = Field(default=None, sa_type=JSON)


class DocumentPublic(DocumentBase):
    id: uuid.UUID
    filename: str
    upload_timestamp: datetime
    doc_metadata: Dict[str, Any] | None = None


class DocumentsPublic(SQLModel):
    data: list[DocumentPublic]
    count: int


# Chat history models
class ChatHistoryBase(SQLModel):
    session_id: str = Field(max_length=50)
    user_query: str
    ai_response: str
    model: str = Field(max_length=50)


class ChatHistoryCreate(ChatHistoryBase):
    user_id: uuid.UUID
    child_id: uuid.UUID | None = None


class ChatHistory(ChatHistoryBase, table=True):
    __tablename__ = "chat_history"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="user.id")
    user: User = Relationship(back_populates="chat_histories")
    child_id: uuid.UUID | None = Field(default=None, foreign_key="child.id")
    child: Child | None = Relationship(back_populates="chat_histories")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    sources: List[str] | None = Field(default=None, sa_type=JSON)  # References to source documents


class ChatHistoryPublic(ChatHistoryBase):
    id: uuid.UUID
    user_id: uuid.UUID
    child_id: uuid.UUID | None = None
    created_at: datetime
    sources: List[str] | None = None


class ChatHistoriesPublic(SQLModel):
    data: list[ChatHistoryPublic]
    count: int


# Chat request/response models
class ChatRequest(SQLModel):
    question: str
    session_id: str | None = None
    child_id: uuid.UUID | None = None
    model: str = Field(default="google/gemini-flash-1.5-8b", max_length=100)
    #     deepseek/deepseek-chat-v3-0324:free


class ChatResponse(SQLModel):
    answer: str
    session_id: str
    sources: List[Dict[str, Any]] | None = None


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=40)


# Child detail models
class ChildDetailBase(SQLModel):
    detail_type: str = Field(max_length=50)  # e.g., interest, milestone, daily_event, preference
    content: str  # The actual detail content
    tags: List[str] = Field(default=[], sa_type=JSON)  # Tags for categorization
    importance: int = Field(default=5, ge=1, le=10)  # Importance level (1-10)


class ChildDetailCreate(ChildDetailBase):
    child_id: uuid.UUID
    recorded_at: Optional[datetime] = None


class ChildDetailUpdate(SQLModel):
    detail_type: Optional[str] = Field(default=None, max_length=50)
    content: Optional[str] = None
    tags: Optional[List[str]] = None
    importance: Optional[int] = Field(default=None, ge=1, le=10)


class ChildDetail(ChildDetailBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    child_id: uuid.UUID = Field(foreign_key="child.id")
    child: Child = Relationship(back_populates="child_details")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    recorded_at: datetime = Field(default_factory=datetime.utcnow)  # When the detail was recorded/observed
    embedding_id: Optional[str] = None  # ID in the vector store if embedded


class ChildDetailPublic(ChildDetailBase):
    id: uuid.UUID
    child_id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    recorded_at: datetime


class ChildDetailsPublic(SQLModel):
    data: list[ChildDetailPublic]
    count: int
