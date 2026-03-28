"""HTTP Routes."""

from fastapi import APIRouter

from tacto.interfaces.http.routes.chat import router as chat_router
from tacto.interfaces.http.routes.instances import router as instances_router
from tacto.interfaces.http.routes.restaurants import router as restaurants_router
from tacto.interfaces.http.routes.webhook_join import router as webhook_router

router = APIRouter()

router.include_router(webhook_router, prefix="/webhook/join", tags=["Webhook"])
router.include_router(restaurants_router, prefix="/restaurants", tags=["Restaurants"])
router.include_router(instances_router, prefix="/instances", tags=["Instances"])
router.include_router(chat_router, prefix="/chat", tags=["Chat Test"])

__all__ = ["router"]
