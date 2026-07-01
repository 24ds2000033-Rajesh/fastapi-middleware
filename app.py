import time
import uuid
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

EMAIL = "24ds2000033@ds.study.iitm.ac.in"

# Assigned values
RATE_LIMIT = 11
WINDOW = 10  # seconds

# Allowed origins
ALLOWED_ORIGINS = [
    "https://app-y529sf.example.com",

    # Exam page (keep this)
    "https://exam.sanand.workers.dev",
    "https://tools-in-data-science.pages.dev",
]

app = FastAPI()

# -----------------------------
# Middleware 1 - Request Context
# -----------------------------
@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID")

    if not request_id:
        request_id = str(uuid.uuid4())

    request.state.request_id = request_id

    response = await call_next(request)

    response.headers["X-Request-ID"] = request_id

    return response


# -----------------------------
# Middleware 2 - Rate Limiter
# -----------------------------
client_requests = defaultdict(deque)


@app.middleware("http")
async def rate_limiter(request: Request, call_next):
    client = request.headers.get("X-Client-Id", "anonymous")

    now = time.time()

    q = client_requests[client]

    while q and now - q[0] > WINDOW:
        q.popleft()

    if len(q) >= RATE_LIMIT:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
        )

    q.append(now)

    return await call_next(request)


# -----------------------------
# Middleware 3 - CORS
# -----------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# Endpoint
# -----------------------------
@app.get("/ping")
async def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }


@app.get("/")
async def root():
    return {"status": "ok"}
