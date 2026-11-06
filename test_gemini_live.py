import asyncio

from google import genai
from google.genai import types
from config import GEMINI_API_KEY

MODEL = "gemini-3.8-live"


async def main():
    client = genai.Client(api_key=GEMINI_API_KEY)

    try:
        config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            output_audio_transcription=types.AudioTranscriptionConfig(),
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Kore"
                    )
                )
            ),
            system_instruction=(
                "You are a professional ATSWA examination interviewer. "
                "Introduce yourself briefly and ask the candidate if they are ready."
            )
        )

        async with client.aio.live.connect(
            model=MODEL,
            config=config
        ) as session:

            print("Connected to Gemini Live API.")
            print("Sending interview test...")

            await session.send_realtime_input(
                text="Hello. Please introduce yourself as my interviewer."
            )

            async def receive_response():
                audio_received = False

                async for message in session.receive():
                    content = message.server_content

                    if content:
                        if content.output_transcription:
                            print(
                                content.output_transcription.text,
                                end="",
                                flush=True
                            )

                        if content.model_turn:
                            for part in content.model_turn.parts:
                                if part.inline_data:
                                    audio_received = True

                        if content.turn_complete:
                            print("\nAudio received:", audio_received)
                            return

            await asyncio.wait_for(receive_response(), timeout=45)
            print("Gemini Live test successful.")

    except Exception as error:
        print(f"\nGemini Live test failed: {type(error).__name__}: {error}")

    finally:
        await client.aio.aclose()
        client.close()


if __name__ == "__main__":
    asyncio.run(main())
