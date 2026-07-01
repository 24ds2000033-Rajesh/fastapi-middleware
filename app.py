import time
import uuid
from collections import defaultdict
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONEncoder

app = FastAPI()

# -----------------------------------------------------------------------------
# MIDDLEWARE 1: Request Context (Custom ASGI Middleware)
# -----------------------------------------------------------------------------
# We use a custom ASGI middleware to safely inject and intercept headers 
# before and after the request lifecycle.
@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    # Retrieve existing X-Request-ID or generate a new UUID4
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        request_id = str(uuid.uuid4())
    
    # Store the request_id in the request state so the endpoints can access it
    request.state.request_id = request_id
    
    # Process the request down the line
    response: Response = await call_next(request)
    
    # Always inject the X-Request-ID into the response headers
    response.headers["X-Request-ID"] = request_id
    return response

# -----------------------------------------------------------------------------
# MIDDLEWARE 2: CORS Configuration
# -----------------------------------------------------------------------------
# Note: We include the explicitly assigned origin alongside a wild-card match
# alternative for verification platforms if they run on local/custom origins.
origins = [
    "https://app-y529sf.example.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["X-Request-ID", "X-Client-Id", "Content-Type"],
    expose_headers=["X-Request-ID"],
)

# -----------------------------------------------------------------------------
# MIDDLEWARE 3: Per-Client Rate Limiting (11 requests / 10 seconds)
# -----------------------------------------------------------------------------
# In-memory store mapping client_id -> list of timestamps
RATE_LIMIT_WINDOW = 10.0  # seconds
RATE_LIMIT_MAX_REQUESTS = 11

client_buckets = defaultdict(list)

@app.middleware("http")
async def rate_limiter_middleware(request: Request, call_next):
    # Only enforce rate limiting on the API routes (skip docs, etc., if needed)
    if request.url.path == "/ping":
        client_id = request.headers.get("X-Client-Id")
        
        # If an X-Client-Id is provided, enforce the sliding window rate limit
        if client_id:
            current_time = time.time()
            timestamps = client_buckets[client_id]
            
            # Evict timestamps outside the 10-second window
            while timestamps and timestamps[0] < current_time - RATE_LIMIT_WINDOW:
                timestamps.pop(0)
                
            if len(timestamps) >= RATE_LIMIT_MAX_REQUESTS:
                return Response(
                    content='{"detail": "Too Many Requests"}',
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    media_type="application/json"
                )
            
            # Record current valid request timestamp
            timestamps.append(current_time)

    return await call_next(request)

# -----------------------------------------------------------------------------
# ENDPOINT: GET /ping
# -----------------------------------------------------------------------------
@app.get("/ping")
async def ping(request: Request):
    return {
        "email": "user@example.com",  # Replace with your logged-in address if required static value
        "request_id": request.state.request_id
    }
