#!/usr/bin/env python3
"""
FastAPI Todo Server - A modern REST API for managing todo items.

This FastAPI application provides a complete CRUD API for todo management
with automatic OpenAPI documentation, data validation, and modern async support.
"""

from datetime import datetime
from enum import Enum

from dateutil import tz
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

# Initialize FastAPI app
app = FastAPI(
    title="Todo API Server",
    description="A modern REST API for managing todo items",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)


# Enums
class Priority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


# Pydantic models
class TodoBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Todo title")
    description: str | None = Field(
        None, max_length=1000, description="Todo description"
    )
    priority: Priority = Field(Priority.medium, description="Todo priority level")


class TodoCreate(TodoBase):
    pass


class TodoUpdate(TodoBase):
    title: str | None = Field(None, min_length=1, max_length=200)
    priority: Priority | None = None


class Todo(TodoBase):
    id: int = Field(..., description="Unique todo identifier")
    completed: bool = Field(False, description="Completion status")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}


# In-memory storage (in a real app, this would be a database)
todos_db: list[Todo] = []
next_id = 1


def get_current_time():
    """Get current timestamp with timezone."""
    return datetime.now(tz.tzlocal())


def find_todo_by_id(todo_id: int) -> Todo | None:
    """Find a todo by ID."""
    return next((todo for todo in todos_db if todo.id == todo_id), None)


@app.get("/", tags=["Root"])
async def root():
    """Welcome endpoint with API information."""
    return {
        "message": "Welcome to the FastAPI Todo Server!",
        "description": "A modern REST API for managing todo items",
        "version": "1.0.0",
        "endpoints": {
            "/": "This welcome message",
            "/health": "Health check endpoint",
            "/todos": "List all todos (GET) or create new todo (POST)",
            "/todos/{todo_id}": "Get (GET), update (PUT), or delete (DELETE) a specific todo",
            "/todos/{todo_id}/complete": "Toggle todo completion status (PATCH)",
            "/docs": "Swagger UI documentation",
            "/redoc": "ReDoc documentation",
        },
        "total_todos": len(todos_db),
        "timestamp": get_current_time().isoformat(),
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": get_current_time().isoformat(),
        "total_todos": len(todos_db),
        "uptime": "Server is running",
    }


@app.get("/todos", response_model=list[Todo], tags=["Todos"])
async def get_todos(
    completed: bool | None = Query(None, description="Filter by completion status"),
    priority: Priority | None = Query(None, description="Filter by priority level"),
    limit: int | None = Query(
        None, ge=1, le=100, description="Limit number of results"
    ),
):
    """Get all todos with optional filtering."""
    filtered_todos = todos_db.copy()

    # Apply filters
    if completed is not None:
        filtered_todos = [
            todo for todo in filtered_todos if todo.completed == completed
        ]

    if priority is not None:
        filtered_todos = [todo for todo in filtered_todos if todo.priority == priority]

    # Apply limit
    if limit is not None:
        filtered_todos = filtered_todos[:limit]

    return filtered_todos


@app.post("/todos", response_model=Todo, status_code=201, tags=["Todos"])
async def create_todo(todo: TodoCreate):
    """Create a new todo item."""
    global next_id

    current_time = get_current_time()
    new_todo = Todo(
        id=next_id,
        title=todo.title,
        description=todo.description,
        priority=todo.priority,
        completed=False,
        created_at=current_time,
        updated_at=current_time,
    )

    todos_db.append(new_todo)
    next_id += 1

    return new_todo


@app.get("/todos/{todo_id}", response_model=Todo, tags=["Todos"])
async def get_todo(todo_id: int):
    """Get a specific todo by ID."""
    todo = find_todo_by_id(todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail=f"Todo with id {todo_id} not found")
    return todo


@app.put("/todos/{todo_id}", response_model=Todo, tags=["Todos"])
async def update_todo(todo_id: int, todo_update: TodoUpdate):
    """Update a specific todo."""
    todo = find_todo_by_id(todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail=f"Todo with id {todo_id} not found")

    # Update fields if provided
    if todo_update.title is not None:
        todo.title = todo_update.title
    if todo_update.description is not None:
        todo.description = todo_update.description
    if todo_update.priority is not None:
        todo.priority = todo_update.priority

    todo.updated_at = get_current_time()
    return todo


@app.delete("/todos/{todo_id}", tags=["Todos"])
async def delete_todo(todo_id: int):
    """Delete a specific todo."""
    todo = find_todo_by_id(todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail=f"Todo with id {todo_id} not found")

    todos_db.remove(todo)
    return {"message": f"Todo with id {todo_id} has been deleted"}


@app.patch("/todos/{todo_id}/complete", response_model=Todo, tags=["Todos"])
async def toggle_todo_completion(todo_id: int):
    """Toggle the completion status of a todo."""
    todo = find_todo_by_id(todo_id)
    if not todo:
        raise HTTPException(status_code=404, detail=f"Todo with id {todo_id} not found")

    todo.completed = not todo.completed
    todo.updated_at = get_current_time()
    return todo


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handle 404 errors."""
    return {
        "error": "Not Found",
        "message": "The requested resource was not found",
        "status_code": 404,
    }


@app.exception_handler(422)
async def validation_error_handler(request, exc):
    """Handle validation errors."""
    return {
        "error": "Validation Error",
        "message": "The request data is invalid",
        "details": exc.detail,
        "status_code": 422,
    }


if __name__ == "__main__":
    import uvicorn

    print("Starting FastAPI Todo Server...")
    print("Available endpoints:")
    print("  GET /                     - Welcome message")
    print("  GET /health               - Health check")
    print("  GET /todos                - List todos")
    print("  POST /todos               - Create todo")
    print("  GET /todos/{id}           - Get todo")
    print("  PUT /todos/{id}           - Update todo")
    print("  DELETE /todos/{id}        - Delete todo")
    print("  PATCH /todos/{id}/complete - Toggle completion")
    print("  GET /docs                 - Swagger UI")
    print("  GET /redoc                - ReDoc")
    print("\nServer running on http://localhost:8000")
    print("API Documentation: http://localhost:8000/docs")

    uvicorn.run(app, host="0.0.0.0", port=8000)
