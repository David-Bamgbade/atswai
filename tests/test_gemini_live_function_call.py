import asyncio

from google.genai import types

from services.gemini_live_service import gemini_live_service


FUNCTION_NAME = "submit_candidate_response"


async def run_function_call_round_trip(session):

    audio_received = False
    transcription = []
    function_called = False

    await session.send_realtime_input(
        text="My name is David."
    )

    async for message in session.receive():

        print("\n========== RAW GEMINI LIVE MESSAGE ==========")
        print(message)

        if message.tool_call:

            for call in message.tool_call.function_calls or []:

                if call.name != FUNCTION_NAME:
                    continue

                if function_called:
                    raise RuntimeError("Unexpected repeated function call.")

                print("\nFunction called:", call.name)
                print("Function arguments:", call.args)

                arguments = call.args or {}
                transcript = arguments.get("transcript")

                if not transcript:
                    raise RuntimeError(
                        "Gemini did not provide the candidate transcript."
                    )

                print("\nReturning simulated backend response...")

                await session.send_tool_response(
                    function_responses=[
                        types.FunctionResponse(
                            id=call.id,
                            name=FUNCTION_NAME,
                            response={
                                "result": "Thank you, David. Which position are you interviewing for?"
                            }
                        )
                    ]
                )

                function_called = True

        content = message.server_content

        if not content:
            continue

        print("\nServer content:", content)

        if content.output_transcription:
            text = content.output_transcription.text
            transcription.append(text)
            print(text, end="", flush=True)

        if content.model_turn:
            for part in content.model_turn.parts:
                if part.inline_data and part.inline_data.data:
                    audio_received = True

        if content.turn_complete:

            print("\nGemini marked the turn complete.")

            if not function_called:
                raise RuntimeError(
                    "Gemini completed the turn without calling the function."
                )

            return audio_received, "".join(transcription)

    raise RuntimeError("Gemini receive stream ended unexpectedly.")

async def main():

    declaration = types.FunctionDeclaration(
        name=FUNCTION_NAME,
        behavior=types.Behavior.BLOCKING,
        description=(
            "Submit the candidate's spoken interview response "
            "to the application backend. Do not generate an "
            "interview answer independently."
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

    config = types.LiveConnectConfig(
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
            "You are the voice interface for an interview application. "
            "When the candidate speaks, call submit_candidate_response "
            "with their response. Never independently advance interview "
            "stages, generate interview questions, or evaluate answers. "
            "Wait for the function response. Then speak the answer "
            "returned by the application naturally and faithfully."
        )
    )

    try:

        async with gemini_live_service.connect(config) as (session, model):

            print("\nConnected model:", model)

            print("\nSending simulated candidate response...")

            print("\nWaiting for Gemini function call and spoken response...")

            audio_received, transcription = await asyncio.wait_for(
                run_function_call_round_trip(session),
                timeout=90
            )
            print("\n\nAudio received:", audio_received)
            print("Transcription:", transcription)

            if not audio_received:
                raise RuntimeError("Gemini returned no audio.")

            if not transcription.strip():
                raise RuntimeError("Gemini returned no transcription.")

            print("\nPASS: Gemini Live function-call round trip completed.")

    finally:
        await gemini_live_service.close()


if __name__ == "__main__":
    asyncio.run(main())

