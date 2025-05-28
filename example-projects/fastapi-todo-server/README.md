# FastAPI Todo Server

A modern REST API server built with FastAPI for managing todo items. This server provides a complete CRUD API for todo management with automatic OpenAPI documentation.

## Features

- **Create Todos**: Add new todo items with title, description, and priority
- **List Todos**: Get all todos with optional filtering by status and priority
- **Get Todo**: Retrieve a specific todo by ID
- **Update Todo**: Modify existing todo items
- **Delete Todo**: Remove todo items
- **Mark Complete**: Toggle todo completion status
- **Health Check**: Simple endpoint to verify server status
- **Auto Documentation**: Swagger UI and ReDoc automatically generated

## API Endpoints

- `GET /` - Welcome message and API information
- `GET /health` - Health check endpoint
- `GET /todos` - List all todos (supports filtering)
- `POST /todos` - Create a new todo
- `GET /todos/{todo_id}` - Get a specific todo
- `PUT /todos/{todo_id}` - Update a todo
- `DELETE /todos/{todo_id}` - Delete a todo
- `PATCH /todos/{todo_id}/complete` - Toggle todo completion
- `GET /docs` - Swagger UI documentation
- `GET /redoc` - ReDoc documentation

## Todo Model

Each todo item has the following fields:
- `id`: Unique identifier (auto-generated)
- `title`: Todo title (required)
- `description`: Optional description
- `completed`: Completion status (default: false)
- `priority`: Priority level (low, medium, high)
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

## Usage

Start the server:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The server will run on `http://localhost:8000` by default.

### Example requests:

```bash
# Create a new todo
curl -X POST "http://localhost:8000/todos" \
  -H "Content-Type: application/json" \
  -d '{"title": "Buy groceries", "description": "Milk, bread, eggs", "priority": "medium"}'

# Get all todos
curl http://localhost:8000/todos

# Get a specific todo
curl http://localhost:8000/todos/1

# Update a todo
curl -X PUT "http://localhost:8000/todos/1" \
  -H "Content-Type: application/json" \
  -d '{"title": "Buy groceries", "description": "Milk, bread, eggs, cheese", "priority": "high"}'

# Mark todo as complete
curl -X PATCH "http://localhost:8000/todos/1/complete"

# Delete a todo
curl -X DELETE "http://localhost:8000/todos/1"

# Filter todos by status
curl "http://localhost:8000/todos?completed=false"

# Filter todos by priority
curl "http://localhost:8000/todos?priority=high"
```

## Dependencies

- FastAPI - Modern web framework
- uvicorn - ASGI server
- pydantic - Data validation
- python-dateutil - Date handling utilities
