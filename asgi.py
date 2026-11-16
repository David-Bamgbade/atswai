import json
import logging

from asgiref.wsgi import WsgiToAsgi
from app import app
from services.interview_voice_gateway import interview_voice_gateway
from services.pipecat_voice_manager import pipecat_voice_manager
from services.pipecat_interview_worker import create_interview_worker
from pipecat.transports.smallwebrtc.connection import SmallWebRTCConnection
from aiortc.sdp import candidate_from_sdp
from config import (
    METERED_TURN_USERNAME,
    METERED_TURN_CREDENTIAL,
    METERED_TURN_URLS,
)
from pipecat.transports.smallwebrtc.connection import IceServer

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
        self.webrtc_connections = {}

    async def handle_webrtc_candidate(self, receive, send):

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

                if len(body) > 100_000:
                    await respond(413, {
                        "success": False,
                        "error": "Candidate request is too large."
                    })
                    return

                if not message.get("more_body", False):
                    break

            data = json.loads(body.decode("utf-8"))

            pc_id = data.get("pc_id")
            session_id = data.get("session_id")
            candidate_data = data.get("candidate")

            if not isinstance(pc_id, str) or not pc_id.strip():
                await respond(400, {
                    "success": False,
                    "error": "A valid pc_id is required."
                })
                return

            if not isinstance(session_id, str) or not session_id.strip():
                await respond(400, {
                    "success": False,
                    "error": "A valid session_id is required."
                })
                return

            entry = self.webrtc_connections.get(pc_id)

            if not entry or entry["session_id"] != session_id:
                await respond(404, {
                    "success": False,
                    "error": "WebRTC connection not found."
                })
                return

            candidate = None

            if candidate_data is not None:
                if not isinstance(candidate_data, dict):
                    await respond(400, {
                        "success": False,
                        "error": "Invalid ICE candidate."
                    })
                    return

                candidate_sdp = candidate_data.get("candidate")

                if candidate_sdp:
                    if not isinstance(candidate_sdp, str):
                        await respond(400, {
                            "success": False,
                            "error": "Invalid candidate SDP."
                        })
                        return

                    candidate_sdp = candidate_sdp.removeprefix("candidate:")

                    candidate = candidate_from_sdp(candidate_sdp)
                    candidate.sdpMid = candidate_data.get("sdpMid")
                    candidate.sdpMLineIndex = candidate_data.get(
                        "sdpMLineIndex"
                    )

                    if (
                        candidate.sdpMid is None
                        and candidate.sdpMLineIndex is None
                    ):
                        await respond(400, {
                            "success": False,
                            "error": "Candidate media information is missing."
                        })
                        return

            await entry["connection"].add_ice_candidate(candidate)

            await respond(200, {"success": True})

        except (json.JSONDecodeError, UnicodeDecodeError):
            await respond(400, {
                "success": False,
                "error": "Invalid JSON request."
            })

        except (ValueError, AssertionError) as exc:
            await respond(400, {
                "success": False,
                "error": str(exc)
            })

        except Exception:
            logger.exception("Pipecat WebRTC candidate failed.")
            await respond(500, {
                "success": False,
                "error": "Unable to process ICE candidate."
            })

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

            ice_servers = [
                IceServer(urls="stun:stun.relay.metered.ca:80"),
                *[
                    IceServer(
                        urls=url,
                        username=METERED_TURN_USERNAME,
                        credential=METERED_TURN_CREDENTIAL,
                    )
                    for url in METERED_TURN_URLS
                ],
            ]

            connection = SmallWebRTCConnection(ice_servers=ice_servers)

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

            self.webrtc_connections[connection.pc_id] = {
                "connection": connection,
                "session_id": session_id
            }

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
                self.webrtc_connections.pop(connection.pc_id, None)
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
                self.webrtc_connections.pop(connection.pc_id, None)
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

        if (
            scope["type"] == "http"
            and scope.get("method") == "POST"
            and scope.get("path") == "/api/voice/webrtc/candidate"
        ):
            return await self.handle_webrtc_candidate(receive, send)

        if (
            scope["type"] == "http"
            and scope.get("method") == "GET"
            and scope.get("path") == "/api/voice/ice-servers"
        ):
            if not METERED_TURN_USERNAME or not METERED_TURN_CREDENTIAL:
                payload = {
                    "success": False,
                    "error": "TURN credentials are not configured."
                }
                status = 503
            else:
                ice_servers = [
                    {"urls": "stun:stun.relay.metered.ca:80"},
                    *[
                        {
                            "urls": url,
                            "username": METERED_TURN_USERNAME,
                            "credential": METERED_TURN_CREDENTIAL,
                        }
                        for url in METERED_TURN_URLS
                    ],
                ]

                payload = {
                    "success": True,
                    "iceServers": ice_servers
                }
                status = 200

            body = json.dumps(payload).encode("utf-8")

            await send({
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                    (b"cache-control", b"no-store"),
                ]
            })

            await send({
                "type": "http.response.body",
                "body": body
            })
            return
        return await self.http_application(scope, receive, send)


http_app = ErrorHandlingMiddleware(WsgiToAsgi(app))

asgi_app = ASGIRouter(
    http_application=http_app,
    websocket_application=interview_voice_gateway
)


