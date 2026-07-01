import time
import uuid
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

EMAIL = "24ds2000033@ds.study.iitm.ac.in"   # <-- Replace with your email

RATE_LIMIT = 11
WINDOW = 10

app = FastAPI()

# ------------------------
# CORS
# ------------------------
app.add_middleware(
    CORSMiddleware,
   allow_origins=[
    "https://app-y529sf.example.com",
    "https://exam.sanand.workers.dev",
    "https://tools-in-data-science.pages.dev",
    "https://sanand.workers.dev",
    "https://tds.s-anand.net",
],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# ------------------------
# In-memory rate limiter
# ------------------------
buckets = defaultdict(deque)


@app.middleware("http")
async def middleware(request: Request, call_next):
    # ---------- Request ID ----------
    request_id = request.headers.get("X-Request-ID")
    if not request_id:
        request_id = str(uuid.uuid4())

    request.state.request_id = request_id

    # ---------- Rate limit ----------
    client = request.headers.get("X-Client-Id", "anonymous")

    now = time.time()
    q = buckets[client]

    while q and now - q[0] >= WINDOW:
        q.popleft()

    if len(q) >= RATE_LIMIT:
        response = JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded"},
        )
        response.headers["X-Request-ID"] = request_id
        return response

    q.append(now)

    response = await call_next(request)

    # ALWAYS echo the request ID
    response.headers["X-Request-ID"] = request_id

    return response


@app.get("/ping")
async def ping(request: Request):
    return {
        "email": EMAIL,
        "request_id": request.state.request_id,
    }
