#!/usr/bin/env python3
"""
Test script for the FastAPI Todo Server.

This script demonstrates how to interact with the todo API endpoints.
Run the server first with: uvicorn main:app --reload
"""

import requests

BASE_URL = "http://localhost:8000"


def test_api() -> None:
    """Test the FastAPI todo server endpoints."""
    print("🧪 Testing FastAPI Todo Server")
    print("=" * 50)

    # Test health check
    print("\n1. Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"✅ Health check: {response.status_code}")
        print(f"   Response: {response.json()}")
    except requests.exceptions.ConnectionError:
        print("❌ Server not running. Start with: uvicorn main:app --reload")
        return

    # Test root endpoint
    print("\n2. Testing root endpoint...")
    response = requests.get(f"{BASE_URL}/")
    print(f"✅ Root: {response.status_code}")
    print(f"   Message: {response.json()['message']}")

    # Test creating todos
    print("\n3. Creating test todos...")
    todos_to_create = [
        {
            "title": "Buy groceries",
            "description": "Milk, bread, eggs, cheese",
            "priority": "high",
        },
        {
            "title": "Write documentation",
            "description": "Update API documentation",
            "priority": "medium",
        },
        {
            "title": "Exercise",
            "description": "Go for a 30-minute run",
            "priority": "low",
        },
    ]

    created_todos = []
    for todo_data in todos_to_create:
        response = requests.post(f"{BASE_URL}/todos", json=todo_data)
        if response.status_code == 201:
            todo = response.json()
            created_todos.append(todo)
            print(f"✅ Created todo: {todo['title']} (ID: {todo['id']})")
        else:
            print(f"❌ Failed to create todo: {response.status_code}")

    # Test getting all todos
    print("\n4. Getting all todos...")
    response = requests.get(f"{BASE_URL}/todos")
    todos = response.json()
    print(f"✅ Found {len(todos)} todos")
    for todo in todos:
        status = "✓" if todo["completed"] else "○"
        print(f"   {status} {todo['title']} (Priority: {todo['priority']})")

    # Test getting a specific todo
    if created_todos:
        todo_id = created_todos[0]["id"]
        print(f"\n5. Getting todo {todo_id}...")
        response = requests.get(f"{BASE_URL}/todos/{todo_id}")
        if response.status_code == 200:
            todo = response.json()
            print(f"✅ Retrieved: {todo['title']}")
            print(f"   Description: {todo['description']}")
            print(f"   Priority: {todo['priority']}")
            print(f"   Completed: {todo['completed']}")
        else:
            print(f"❌ Failed to get todo: {response.status_code}")

    # Test updating a todo
    if created_todos:
        todo_id = created_todos[0]["id"]
        print(f"\n6. Updating todo {todo_id}...")
        update_data = {
            "title": "Buy groceries (Updated)",
            "description": "Milk, bread, eggs, cheese, yogurt",
            "priority": "medium",
        }
        response = requests.put(f"{BASE_URL}/todos/{todo_id}", json=update_data)
        if response.status_code == 200:
            todo = response.json()
            print(f"✅ Updated: {todo['title']}")
            print(f"   New priority: {todo['priority']}")
        else:
            print(f"❌ Failed to update todo: {response.status_code}")

    # Test marking todo as complete
    if created_todos:
        todo_id = created_todos[1]["id"]
        print(f"\n7. Marking todo {todo_id} as complete...")
        response = requests.patch(f"{BASE_URL}/todos/{todo_id}/complete")
        if response.status_code == 200:
            todo = response.json()
            print(f"✅ Toggled completion: {todo['title']}")
            print(f"   Completed: {todo['completed']}")
        else:
            print(f"❌ Failed to toggle completion: {response.status_code}")

    # Test filtering todos
    print("\n8. Testing filters...")

    # Filter by completion status
    response = requests.get(f"{BASE_URL}/todos?completed=false")
    incomplete_todos = response.json()
    print(f"✅ Incomplete todos: {len(incomplete_todos)}")

    response = requests.get(f"{BASE_URL}/todos?completed=true")
    complete_todos = response.json()
    print(f"✅ Complete todos: {len(complete_todos)}")

    # Filter by priority
    response = requests.get(f"{BASE_URL}/todos?priority=high")
    high_priority_todos = response.json()
    print(f"✅ High priority todos: {len(high_priority_todos)}")

    # Test deleting a todo
    if created_todos:
        todo_id = created_todos[-1]["id"]
        print(f"\n9. Deleting todo {todo_id}...")
        response = requests.delete(f"{BASE_URL}/todos/{todo_id}")
        if response.status_code == 200:
            print(f"✅ Deleted todo {todo_id}")
            print(f"   Message: {response.json()['message']}")
        else:
            print(f"❌ Failed to delete todo: {response.status_code}")

    # Final count
    print("\n10. Final todo count...")
    response = requests.get(f"{BASE_URL}/todos")
    final_todos = response.json()
    print(f"✅ Final count: {len(final_todos)} todos")

    print("\n" + "=" * 50)
    print("🎉 API testing complete!")
    print(f"📖 View API docs at: {BASE_URL}/docs")
    print(f"📚 View ReDoc at: {BASE_URL}/redoc")


if __name__ == "__main__":
    test_api()
