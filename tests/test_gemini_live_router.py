import asyncio

from google.genai import types

from services.gemini_live_service import gemini_live_service


async def main():

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
            "Introduce yourself briefly and ask the candidate if they "
            "are ready to begin."
        )
    )

    try:
        async with gemini_live_service.connect(config) as (session, model):

            print(f"\nConnected model: {model}")
            print("Sending interview test...")

            await session.send_realtime_input(
                text="Please introduce yourself as my ATSWA interviewer."
            )

            audio_received = False
            transcription_received = False

            async def receive_response():
                nonlocal audio_received, transcription_received

                async for message in session.receive():

                    content = message.server_content

                    if not content:
                        continue

                    if content.output_transcription:
                        transcription_received = True
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
                        return

            await asyncio.wait_for(
                receive_response(),
                timeout=45
            )

            print("\n\nAudio received:", audio_received)
            print("Transcription received:", transcription_received)
            print(
                "Remembered model:",
                gemini_live_service.last_successful_model
            )

            if not audio_received:
                raise RuntimeError("Gemini did not return audio.")

            if not transcription_received:
                raise RuntimeError("Gemini did not return transcription.")

            print("\nGemini Live router test successful.")

    except Exception as error:
        print(
            f"\nGemini Live router test failed: "
            f"{type(error).__name__}: {error}"
        )
        raise

    finally:
        await gemini_live_service.close()


if __name__ == "__main__":
    asyncio.run(main())
