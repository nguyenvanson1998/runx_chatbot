from fastapi import FastAPI, Request
from starlette.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from chainlit.user import User
from chainlit.utils import mount_chainlit
from chainlit.server import _authenticate_user
app = FastAPI()

# Enable CORS for frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/custom-auth")
async def custom_auth(request: Request):
    user = User(identifier="Test User")
    response = await _authenticate_user(request, user)
    return JSONResponse(content={"status": "success"}, headers=response.headers)

# Mount Chainlit
mount_chainlit(app, "test_cl.py", path="/chainlit")
