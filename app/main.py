from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import user, auth, post


# Creating FastAPI instance/object
app = FastAPI()


origins = [
    settings.CLIENT_ORIGIN,
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Including the routers in the app instance
app.include_router(auth.router, tags=['Auth'], prefix='/api/v1/auth')

app.include_router(user.router, tags=['Users'], prefix='/api/v1/users')

app.include_router(post.router, tags=['Posts'], prefix='/api/v1/posts')


@app.get('/api/v1/')
def root():
    return {'message': 'FastAPI Complete Authentication'}
