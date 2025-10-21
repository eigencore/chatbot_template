from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.webhooks import whatsapp_webhook_router
from app.core.settings import settings
from app.db.orm import init_db_pool, close_db_pool, AsyncPGORM

DB_URL = f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"


# async def lifespan(app: FastAPI):
#     global orm
    
#     await init_db_pool(DB_URL)
#     orm = AsyncPGORM()
    
#     try:
#         yield
#     finally:
#         await close_db_pool()

app = FastAPI(title=settings.APP_NAME) #, lifespan=lifespan)

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# custom_orm: AsyncPGORM | None = None

app.include_router(whatsapp_webhook_router)



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
