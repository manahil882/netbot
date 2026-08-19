# API Endpoints Documentation

This document outlines the REST endpoints built for thread and message history management.

All endpoints mock the `user_id` context via a FastAPI dependency for now. In production, this dependency will be swapped with a real JWT authentication checker.

---

## 1. Create a New Thread
* **Path**: `/threads`
* **Method**: `POST`
* **Request Body**:
```json
{
  "title": "Discussion about Q3 goals"
}
```
* **Success Response (201 Created)**:
```json
{
  "id": "841b9d12-ad04-4fa7-9bc9-e235e5b89999",
  "user_id": "00000000-0000-0000-0000-000000000000",
  "title": "Discussion about Q3 goals",
  "created_at": "2026-08-19T14:22:00Z",
  "updated_at": "2026-08-19T14:22:00Z"
}
```

---

## 2. List Threads for User
* **Path**: `/threads`
* **Method**: `GET`
* **Success Response (200 OK)**:
```json
[
  {
    "id": "841b9d12-ad04-4fa7-9bc9-e235e5b89999",
    "title": "Discussion about Q3 goals",
    "last_updated": "2026-08-19T14:22:00Z"
  }
]
```

---

## 3. Get Thread Message History
* **Path**: `/threads/{thread_id}`
* **Method**: `GET`
* **Path Parameters**:
  * `thread_id` (UUID)
* **Success Response (200 OK)**:
```json
[
  {
    "id": "a127f123-513d-4fa7-9bc9-ad041b9a261e",
    "thread_id": "841b9d12-ad04-4fa7-9bc9-e235e5b89999",
    "role": "user",
    "content": "What are our Q3 targets?",
    "created_at": "2026-08-19T14:22:05Z"
  },
  {
    "id": "b345f456-513d-4fa7-9bc9-ad041b9a261e",
    "thread_id": "841b9d12-ad04-4fa7-9bc9-e235e5b89999",
    "role": "assistant",
    "content": "Our targets are outlined in the roadmap PDF.",
    "created_at": "2026-08-19T14:22:07Z"
  }
]
```
* **Error Responses**:
  * `404 Not Found`: Thread does not exist.
  * `403 Forbidden`: Thread belongs to another user.

---

## 4. Append Message to Thread
* **Path**: `/threads/{thread_id}/messages`
* **Method**: `POST`
* **Path Parameters**:
  * `thread_id` (UUID)
* **Request Body**:
```json
{
  "role": "user",
  "content": "What is our fallback strategy?"
}
```
* **Success Response (201 Created)**:
```json
{
  "id": "c567f789-513d-4fa7-9bc9-ad041b9a261e",
  "thread_id": "841b9d12-ad04-4fa7-9bc9-e235e5b89999",
  "role": "user",
  "content": "What is our fallback strategy?",
  "created_at": "2026-08-19T14:22:15Z"
}
```
* **Error Responses**:
  * `404 Not Found`: Thread does not exist.
  * `403 Forbidden`: Thread belongs to another user.
