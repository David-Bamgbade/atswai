import json
import logging

from asgiref.wsgi import WsgiToAsgi
from app import app
from services.interview_voice_gateway import interview_voice_gateway

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("asgi")


class ErrorHandlingMiddleware:

    def __init__(self, application):
        self.application = application

    async def __call__(self, scope, receive, send):

        if scope["type"] != "http":
            return await self.application(scope, receive, send)

        response_started = False

        async def send_wrapper(message):
            nonlocal response_started

            if message["type"] == "http.response.start":
                response_started = True

            await send(message)

        try:
            await self.application(scope, receive, send_wrapper)

        except Exception:
            logger.exception("Unhandled ASGI request error")

            if not response_started:
                body = json.dumps({
                    "success": False,
                    "error": "An unexpected server error occurred. Please try again."
                }).encode("utf-8")

                await send({
                    "type": "http.response.start",
                    "status": 500,
                    "headers": [
                        (b"content-type", b"application/json"),
                        (b"content-length", str(len(body)).encode("ascii"))
                    ]
                })

                await send({
                    "type": "http.response.body",
                    "body": body
                })
            else:
                raise


class ASGIRouter:

    def __init__(self, http_application, websocket_application):
        self.http_application = http_application
        self.websocket_application = websocket_application

    async def __call__(self, scope, receive, send):

        if scope["type"] == "websocket":
            return await self.websocket_application(scope, receive, send)

        return await self.http_application(scope, receive, send)


http_app = ErrorHandlingMiddleware(WsgiToAsgi(app))

asgi_app = ASGIRouter(
    http_application=http_app,
    websocket_application=interview_voice_gateway
)
