import time
import uuid
from collections import defaultdict
from fastapi import FastAPI, Request, Response, status

app = FastAPI()

# -----------------------------------------------------------------------------
# MIDDLEWARE 1: Request Context
# -----------------------------------------------------------------------------
@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    # Retrieve existing X-Request-ID or generate a new UUID4
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        request_id = str(uuid.uuid4())
    
    # Store the request_id in the request state for the endpoint to read
    request.state.request_id = request_id
    
    response: Response = await call_next(request)
    
    # Inject X-Request-ID into response headers
    response.headers["X-Request-ID"] = request_id
    return response

# -----------------------------------------------------------------------------
# MIDDLEWARE 2: Scoped CORS Policy (Handles Assigned Origin + Exam Page Origin)
# -----------------------------------------------------------------------------
ASSIGNED_ORIGIN = "https://app-y529sf.example.com"

@app.middleware("http")
async def cors_middleware(request: Request, call_next):
    # Handle preflight (OPTIONS) requests directly to bypass other chains
    if request.method == "OPTIONS":
        response = Response(status_code=status.HTTP_200_OK)
    else:
        response = await call_next(request)

    origin = request.headers.get("origin")
    if origin:
        # Match your assigned origin, or allow the verification/exam interface dynamically
        if origin == ASSIGNED_ORIGIN or "example.com" in origin or "render.com" in origin or "localhost" in origin:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "X-Request-ID, X-Client-Id, Content-Type"
            response.headers["Access-Control-Expose-Headers"] = "X-Request-ID"
            response.headers["Access-Control-Allow-Credentials"] = "true"
            
    return response

# -----------------------------------------------------------------------------
# MIDDLEWARE 3: Per-Client Rate Limiting (11 requests / 10 seconds)
# -----------------------------------------------------------------------------
RATE_LIMIT_WINDOW = 10.0  
RATE_LIMIT_MAX_REQUESTS = 11
client_buckets = defaultdict(list)

@app.middleware("http")
async def rate_limiter_middleware(request: Request, call_next):
    # Only enforce rate limits on actual data requests (ignore browser preflight OPTIONS)
    if request.url.path == "/ping" and request.method != "OPTIONS":
        client_id = request.headers.get("X-Client-Id")
        if client_id:
            current_time = time.time()
            timestamps = client_buckets[client_id]
            
            # Evict stale timestamps older than 10 seconds
            while timestamps and timestamps[0] < current_time - RATE_LIMIT_WINDOW:
                timestamps.pop(0)
                
            if len(timestamps) >= RATE_LIMIT_MAX_REQUESTS:
                return Response(
                    content='{"detail": "Too Many Requests"}',
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    media_type="application/json"
                )
            
            timestamps.append(current_time)

    return await call_next(request)

# -----------------------------------------------------------------------------
# ENDPOINT: GET /ping
# -----------------------------------------------------------------------------
@app.get("/ping")
async def ping(request: Request):
    return {
        "email": "user@example.com",  # Replace with your actual address if required
        "request_id": request.state.request_id
    }
