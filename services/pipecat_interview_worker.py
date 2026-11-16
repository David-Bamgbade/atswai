import logging
import asyncio
import time
from difflib import SequenceMatcher

from config import GEMINI_API_KEY
from services.conversation_manager import conversation_manager

from pipecat.adapters.llm.schemas.function_schema import FunctionSchema
from pipecat.frames.frames import (
    LLMRunFrame,
    LLMContextFrame,
    TranscriptionFrame,
    TTSTextFrame,
    OutputTransportMessageFrame,
)
from pipecat.processors.frame_processor import FrameProcessor
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineWorker, PipelineParams
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.frames.frames import LLMContextFrame
from pipecat.services.google.gemini_live.llm import (
    GeminiLiveLLMService,
    GeminiModalities
)
from pipecat.transports.smallwebrtc.transport import (
    SmallWebRTCTransport,
    TransportParams
)

logger = logging.getLogger("pipecat_interview_worker")




class TranscriptForwarder(FrameProcessor):
    def __init__(self, output_transport, role):
        super().__init__()
        self.output_transport = output_transport
        self.role = role

    async def process_frame(self, frame, direction):
        await super().process_frame(frame, direction)

        text = None

        if self.role == "user" and isinstance(frame, TranscriptionFrame):
            text = frame.text
        elif self.role == "ai" and isinstance(frame, TTSTextFrame):
            text = frame.text

        if text and text.strip():
            await self.output_transport.send_message(
                OutputTransportMessageFrame(
                    message={
                        "type": "transcript",
                        "role": self.role,
                        "text": text.strip()
                    }
                )
            )

        await self.push_frame(frame, direction)

SYSTEM_INSTRUCTION = """
You are a professional, conversational AI interviewer.

Speak naturally and clearly. Keep responses concise and relevant.
Listen carefully to the candidate and allow them to finish speaking.

You must use the submit_candidate_response tool whenever the candidate
provides an interview response or answers an onboarding question.

Never invent interview questions, scores, feedback, or candidate details.
The application backend controls onboarding, interview progression,
question selection, retrieval, and evaluation.

After receiving a backend response, communicate it naturally.
Do not expose internal tools or implementation details.
"""


async def create_interview_worker(connection, session_id):

    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured.")

    session = conversation_manager.get_session(session_id)

    if not session:
        raise ValueError("Interview session not found.")

    if session.get("mode") != "interview":
        raise ValueError("This is not an interview session.")

    if session.get("status") != "active":
        raise ValueError("This interview session is not active.")

    stage = session.get("interview_stage")

    onboarding_prompts = {
        "awaiting_name": (
            "Hello! Welcome to your AI interview. "
            "I'll guide you through a few short introductory questions "
            "before we begin. What is your name? You may also say "
            "'prefer not to say' if you would rather not share it."
        ),
        "awaiting_role": (
            "Thank you. Which role or position are you interviewing for? "
            "For example, Staff Accountant, Financial Analyst, or Audit Associate."
        ),
        "awaiting_background": (
            "Briefly tell me about your education, professional experience, "
            "or relevant skills. You can also say 'skip' if you prefer."
        ),
        "awaiting_readiness": "Are you ready to begin your interview?"
    }

    if stage not in (*onboarding_prompts.keys(), "in_progress"):
        raise ValueError("This interview is not at a valid onboarding stage.")

    if stage == "in_progress":
        opening_question = session.get("current_question")

        if not isinstance(opening_question, str) or not opening_question.strip():
            raise ValueError("No pending interview question was found.")

        opening_instruction = (
            "The candidate has completed onboarding. Speak this current "
            "interview question exactly as provided. Do not generate another "
            "opening question. After the candidate answers, use "
            "submit_candidate_response to obtain the next response from "
            "the application backend.\\n\\n"
            f"Candidate name: {session.get('candidate_name') or 'Not provided'}\\n"
            f"Target role: {session.get('job_role') or 'Not provided'}\\n"
            f"Education and experience: {session.get('candidate_background') or 'Not provided'}\\n"
            f"Current interview question: {opening_question.strip()}"
        )
    else:
        opening_instruction = (
            f"The candidate is at the onboarding stage: {stage}. "
            "Onboarding must happen entirely through spoken conversation. "
            "Start by speaking this exact prompt: "
            f"{onboarding_prompts[stage]} "
            "Listen to the candidate's spoken answer, then use "
            "submit_candidate_response to send its transcript to the backend. "
            "Speak the backend's returned response naturally. Continue this "
            "process until onboarding is complete and the backend provides "
            "the first formal interview question. Do not ask for typed input."
        )

    duplicate_window = 12
    last_submission = {
        "normalized": None,
        "answer": None,
        "timestamp": 0.0
    }
    submission_lock = asyncio.Lock()

    async def submit_candidate_response(params):

        candidate_response = params.arguments.get("response")

        if not isinstance(candidate_response, str):
            await params.result_callback({
                "error": "Candidate response must be text."
            })
            return

        candidate_response = candidate_response.strip()

        if not candidate_response:
            await params.result_callback({
                "error": "Candidate response cannot be empty."
            })
            return

        if len(candidate_response) > 10000:
            await params.result_callback({
                "error": "Candidate response is too long."
            })
            return

        normalized = " ".join(candidate_response.casefold().split())

        async with submission_lock:
            now = time.monotonic()
            previous = last_submission["normalized"]

            is_duplicate = (
                previous is not None
                and now - last_submission["timestamp"] <= duplicate_window
                and (
                    normalized == previous
                    or (
                        len(normalized) >= 20
                        and len(previous) >= 20
                        and SequenceMatcher(
                            None, normalized, previous
                        ).ratio() >= 0.88
                    )
                )
            )

            if is_duplicate:
                logger.info(
                    "Duplicate candidate response suppressed for session %s",
                    session_id
                )
                await params.result_callback(last_submission["answer"])
                return

            try:
                result = await conversation_manager.process_message(
                    session_id=session_id,
                    question=candidate_response,
                    top_k=5
                )

                answer = result.get("answer")

                if not isinstance(answer, str) or not answer.strip():
                    raise RuntimeError("Backend returned an empty response.")

                last_submission.update({
                    "normalized": normalized,
                    "answer": answer,
                    "timestamp": time.monotonic()
                })

                await params.result_callback(answer)

            except Exception:
                logger.exception(
                    "Unable to process candidate response for session %s",
                    session_id
                )

                await params.result_callback(
                    "I encountered a problem processing that response. "
                    "Please try again."
                )

    response_tool = FunctionSchema(
        name="submit_candidate_response",
        description=(
            "Submit the candidate's spoken response to the interview "
            "backend. Use this for onboarding answers and interview answers. "
            "The backend determines the next step and returns what to say."
        ),
        properties={
            "response": {
                "type": "string",
                "description": "The candidate's complete spoken response."
            }
        },
        required=["response"],
        handler=submit_candidate_response
    )

    context = LLMContext(
        messages=[
            {
                "role": "user",
                "content": opening_instruction
            }
        ],
        tools=[response_tool]
    )

    gemini = GeminiLiveLLMService(
        api_key=GEMINI_API_KEY,
        settings=GeminiLiveLLMService.Settings(
            model="models/gemini-3.8-live",
            voice="Charon",
            modalities=GeminiModalities.AUDIO,
            system_instruction=SYSTEM_INSTRUCTION
        )
    )

    ice_servers_config = [
    {
        "urls": "stun:stun.relay.metered.ca:80"
    },
    {
        "urls": "turn:global.relay.metered.ca:80",
        "username": "a427892e0c33b2c8001c1d43",   
        "credential": "iAEiWjWk+STZ/vGp"  
    },
    {
        "urls": "turn:global.relay.metered.ca:80?transport=tcp",
        "username": "a427892e0c33b2c8001c1d43",   
        "credential": "iAEiWjWk+STZ/vGp"  
    },
    {
        "urls": "turn:global.relay.metered.ca:443",
        "username": "a427892e0c33b2c8001c1d43",   
        "credential": "iAEiWjWk+STZ/vGp"  
    },
    {
        "urls": "turns:global.relay.metered.ca:443?transport=tcp",
        "username": "a427892e0c33b2c8001c1d43",
        "credential": "iAEiWjWk+STZ/vGp",
    }
]

    transport = SmallWebRTCTransport(
        webrtc_connection=connection,
        params=TransportParams(
            audio_in_enabled=True,
            audio_out_enabled=True,
            audio_in_sample_rate=16000,
            audio_out_sample_rate=24000,
            audio_in_channels=1,
            audio_out_channels=1
            ice_servers=ice_servers_config
        )
    )

    output_transport = transport.output()

    user_transcript_tap = TranscriptForwarder(output_transport, "user")
    ai_transcript_tap = TranscriptForwarder(output_transport, "ai")

    pipeline = Pipeline([
        transport.input(),
        user_transcript_tap,
        gemini,
        ai_transcript_tap,
        output_transport
    ])

    worker = PipelineWorker(
        pipeline,
        name=f"interview-{session_id}",
        conversation_id=session_id,
        app_resources={
            "session_id": session_id
        },
        params=PipelineParams(
            audio_in_sample_rate=16000,
            audio_out_sample_rate=24000
        ),
        idle_timeout_secs=3600,
        cancel_on_idle_timeout=False
    )

    async def on_client_connected(*event_args):
        logger.info(
            "Candidate connected to Pipecat voice session: %s",
            session_id
        )

        await worker.queue_frames([
            LLMContextFrame(context),
            LLMRunFrame()
        ])

    async def on_client_disconnected(*event_args):
        logger.info(
            "Candidate disconnected from Pipecat voice session: %s",
            session_id
        )

        await worker.cancel(reason="WebRTC client disconnected")

    transport.add_event_handler(
        "on_client_connected",
        on_client_connected
    )

    transport.add_event_handler(
        "on_client_disconnected",
        on_client_disconnected
    )

    return worker


