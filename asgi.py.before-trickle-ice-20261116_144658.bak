import json
import logging

from asgiref.wsgi import WsgiToAsgi
from app import app
from services.interview_voice_gateway import interview_voice_gateway
from services.pipecat_voice_manager import pipecat_voice_manager
from services.pipecat_interview_worker import create_interview_worker
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection

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

    async def handle_lifespan(self, receive, send):

        while True:
            message = await receive()

            if message["type"] == "lifespan.startup":
                try:
                    await pipecat_voice_manager.start()
                    await send({"type": "lifespan.startup.complete"})

                except Exception:
                    logger.exception("Pipecat startup failed")
                    await send({
                        "type": "lifespan.startup.failed",
                        "message": "Pipecat voice manager startup failed."
                    })
                    return

            elif message["type"] == "lifespan.shutdown":
                try:
                    await pipecat_voice_manager.stop()
                    await send({"type": "lifespan.shutdown.complete"})

                except Exception:
                    logger.exception("Pipecat shutdown failed")
                    await send({
                        "type": "lifespan.shutdown.failed",
                        "message": "Pipecat voice manager shutdown failed."
                    })
                    return

                return

    async def handle_webrtc_offer(self, receive, send):

        connection = None

        async def respond(status, payload):
            body = json.dumps(payload).encode("utf-8")

            await send({
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii"))
                ]
            })

            await send({
                "type": "http.response.body",
                "body": body
            })

        try:
            body = b""

            while True:
                message = await receive()

                if message["type"] == "http.disconnect":
                    return

                body += message.get("body", b"")

                if len(body) > 1_000_000:
                    await respond(413, {
                        "success": False,
                        "error": "Request body is too large."
                    })
                    return

                if not message.get("more_body", False):
                    break

            data = json.loads(body.decode("utf-8"))

            session_id = data.get("session_id")
            offer = data.get("offer")

            if not isinstance(session_id, str) or not session_id.strip():
                await respond(400, {
                    "success": False,
                    "error": "A valid session_id is required."
                })
                return

            if not isinstance(offer, dict):
                await respond(400, {
                    "success": False,
                    "error": "A WebRTC offer is required."
                })
                return

            if not isinstance(offer.get("sdp"), str) or offer.get("type") != "offer":
                await respond(400, {
                    "success": False,
                    "error": "Invalid WebRTC SDP offer."
                })
                return

            connection = SmallWebRTCConnection()

            await connection.initialize(
                offer["sdp"],
                offer["type"]
            )

            answer = connection.get_answer()

            if not answer:
                raise RuntimeError("WebRTC answer could not be created.")

            worker = await create_interview_worker(
                connection=connection,
                session_id=session_id
            )

            await pipecat_voice_manager.add_worker(worker)

            await respond(200, {
                "success": True,
                "answer": answer
            })

            logger.info(
                "Pipecat WebRTC worker registered for session %s",
                session_id
            )

        except (json.JSONDecodeError, UnicodeDecodeError):
            await respond(400, {
                "success": False,
                "error": "Invalid JSON request."
            })

        except ValueError as exc:
            if connection:
                try:
                    await connection.disconnect()
                except Exception:
                    logger.exception("WebRTC cleanup failed.")

            await respond(400, {
                "success": False,
                "error": str(exc)
            })

        except Exception:
            logger.exception("Pipecat WebRTC offer failed.")

            if connection:
                try:
                    await connection.disconnect()
                except Exception:
                    logger.exception("WebRTC cleanup failed.")

            await respond(500, {
                "success": False,
                "error": "Unable to start the voice interview."
            })


    async def __call__(self, scope, receive, send):

        if scope["type"] == "lifespan":
            return await self.handle_lifespan(receive, send)

        if scope["type"] == "websocket":
            return await self.websocket_application(scope, receive, send)

        if (
            scope["type"] == "http"
            and scope.get("method") == "POST"
            and scope.get("path") == "/api/voice/webrtc/offer"
        ):
            return await self.handle_webrtc_offer(receive, send)

        return await self.http_application(scope, receive, send)


http_app = ErrorHandlingMiddleware(WsgiToAsgi(app))

asgi_app = ASGIRouter(
    http_application=http_app,
    websocket_application=interview_voice_gateway
)

