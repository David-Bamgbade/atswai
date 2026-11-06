import asyncio
import json
import logging
import re

from google.genai import types

from services.conversation_manager import conversation_manager
from services.gemini_live_service import gemini_live_service


logger = logging.getLogger("interview_voice_gateway")

FUNCTION_NAME = "submit_candidate_response"
INPUT_SAMPLE_RATE = 16000
OUTPUT_SAMPLE_RATE = 24000


class InterviewVoiceGateway:

    def _build_config(self):

        declaration = types.FunctionDeclaration(
            name=FUNCTION_NAME,
            behavior=types.Behavior.BLOCKING,
            description=(
                "Submit the candidate's spoken response to the "
                "interview application backend. Always use this "
                "function for candidate responses. Do not generate "
                "interview questions or evaluate answers yourself."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "transcript": types.Schema(
                        type=types.Type.STRING,
                        description="The candidate's transcribed response."
                    )
                },
                required=["transcript"]
            )
        )

        return types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Kore"
                    )
                )
            ),
            tools=[
                types.Tool(
                    function_declarations=[declaration]
                )
            ],
            system_instruction=(
                "You are the voice interface for an AI interview "
                "application. The backend controls every interview "
                "stage and provides every question and response. "
                "If the application sends you an opening or pending "
                "message, speak it exactly as provided without "
                "adding information. Listen to the candidate. When "
                "the candidate finishes speaking, call "
                "submit_candidate_response with their actual response. "
                "Do not independently advance stages, ask questions, "
                "answer questions, or evaluate the candidate. Wait "
                "for the backend function response. Speak the returned "
                "'result' naturally and faithfully. Do not invent "
                "additional information."
            )
        )

    async def _send_json(self, send, payload):

        await send({
            "type": "websocket.send",
            "text": json.dumps(payload)
        })

    async def _handle_function_call(
        self,
        call,
        session_id,
        live_session,
        send
    ):

        if call.name != FUNCTION_NAME:
            raise RuntimeError(
                f"Unexpected Gemini function: {call.name}"
            )

        arguments = call.args or {}
        transcript = arguments.get("transcript")

        if not isinstance(transcript, str) or not transcript.strip():

            await live_session.send_tool_response(
                function_responses=[
                    types.FunctionResponse(
                        id=call.id,
                        name=FUNCTION_NAME,
                        response={
                            "error": "The candidate response was empty. "
                                     "Please ask the candidate to repeat it."
                        }
                    )
                ]
            )
            return

        try:

            result = await conversation_manager.process_message(
                session_id=session_id,
                question=transcript.strip()
            )

            answer = result.get("answer")

            if not isinstance(answer, str) or not answer.strip():
                raise RuntimeError("The interview backend returned no answer.")

            session = conversation_manager.get_session(session_id)

            await self._send_json(
                send,
                {
                    "type": "backend_response",
                    "text": answer,
                    "stage": session.get("interview_stage"),
                    "session_id": session_id
                }
            )

            await live_session.send_tool_response(
                function_responses=[
                    types.FunctionResponse(
                        id=call.id,
                        name=FUNCTION_NAME,
                        response={
                            "result": answer
                        }
                    )
                ]
            )

        except Exception:
            logger.exception("Interview backend function failed")

            await live_session.send_tool_response(
                function_responses=[
                    types.FunctionResponse(
                        id=call.id,
                        name=FUNCTION_NAME,
                        response={
                            "error": (
                                "The interview application could not "
                                "process that response. Please ask the "
                                "candidate to try again."
                            )
                        }
                    )
                ]
            )

    async def _receive_gemini_events(
        self,
        live_session,
        session_id,
        send
    ):

        async for message in live_session.receive():

            if message.tool_call:

                for call in message.tool_call.function_calls or []:

                    await self._handle_function_call(
                        call=call,
                        session_id=session_id,
                        live_session=live_session,
                        send=send
                    )

            content = message.server_content

            if not content:
                continue

            if content.output_transcription:
                await self._send_json(
                    send,
                    {
                        "type": "output_transcription",
                        "text": content.output_transcription.text
                    }
                )

            if content.model_turn:

                for part in content.model_turn.parts:

                    if part.inline_data and part.inline_data.data:

                        await send({
                            "type": "websocket.send",
                            "bytes": part.inline_data.data
                        })

            if content.turn_complete:
                await self._send_json(
                    send,
                    {
                        "type": "turn_complete"
                    }
                )

    async def _forward_browser_audio(self, receive, live_session):

        while True:

            event = await receive()

            if event["type"] == "websocket.disconnect":
                return

            if event["type"] != "websocket.receive":
                continue

            audio_data = event.get("bytes")

            if audio_data:

                await live_session.send_realtime_input(
                    audio=types.Blob(
                        data=audio_data,
                        mime_type=f"audio/pcm;rate={INPUT_SAMPLE_RATE}"
                    )
                )

    async def __call__(self, scope, receive, send):

        if scope["type"] != "websocket":
            return

        match = re.fullmatch(
            r"/ws/interview/([0-9a-fA-F-]{36})",
            scope.get("path", "")
        )

        event = await receive()

        if event["type"] != "websocket.connect":
            return

        if not match:

            await send({
                "type": "websocket.close",
                "code": 4400,
                "reason": "Invalid WebSocket path."
            })
            return

        session_id = match.group(1)
        session = conversation_manager.get_session(session_id)

        if session is None:

            await send({
                "type": "websocket.close",
                "code": 4404,
                "reason": "Interview session not found."
            })
            return

        if session.get("mode") != "interview":

            await send({
                "type": "websocket.close",
                "code": 4403,
                "reason": "This is not an interview session."
            })
            return

        if session.get("status") != "active":

            await send({
                "type": "websocket.close",
                "code": 4403,
                "reason": "This interview session is no longer active."
            })
            return

        await send({
            "type": "websocket.accept"
        })

        await self._send_json(
            send,
            {
                "type": "connected",
                "session_id": session_id,
                "stage": session.get("interview_stage"),
                "input_sample_rate": INPUT_SAMPLE_RATE,
                "output_sample_rate": OUTPUT_SAMPLE_RATE,
                "input_format": "pcm_s16le_mono"
            }
        )

        try:

            async with gemini_live_service.connect(
                self._build_config()
            ) as (live_session, model):

                await self._send_json(
                    send,
                    {
                        "type": "live_ready",
                        "model": model
                    }
                )

                history = session.get("conversation_history", [])

                if history and history[-1].get("role") == "assistant":

                    pending_message = history[-1].get("content", "").strip()

                    if pending_message:

                        await live_session.send_realtime_input(
                            text=(
                                "The application backend has provided "
                                "this pending message. Speak it exactly "
                                "as written, without adding anything:\n\n"
                                + pending_message
                            )
                        )

                input_task = asyncio.create_task(
                    self._forward_browser_audio(
                        receive,
                        live_session
                    )
                )

                output_task = asyncio.create_task(
                    self._receive_gemini_events(
                        live_session,
                        session_id,
                        send
                    )
                )

                tasks = {input_task, output_task}

                try:

                    done, pending = await asyncio.wait(
                        tasks,
                        return_when=asyncio.FIRST_COMPLETED
                    )

                    for task in pending:
                        task.cancel()

                    await asyncio.gather(
                        *pending,
                        return_exceptions=True
                    )

                    for task in done:
                        task.result()

                finally:

                    for task in tasks:
                        if not task.done():
                            task.cancel()

                    await asyncio.gather(
                        *tasks,
                        return_exceptions=True
                    )

        except asyncio.CancelledError:
            raise

        except Exception:
            logger.exception("Interview voice gateway failed")

            try:
                await self._send_json(
                    send,
                    {
                        "type": "error",
                        "message": "The voice interview connection encountered an error."
                    }
                )
            except Exception:
                pass


interview_voice_gateway = InterviewVoiceGateway()

