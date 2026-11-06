import asyncio

from services.interview_voice_gateway import interview_voice_gateway
from services.gemini_live_service import gemini_live_service


GREETING = (
    "Hello! Welcome to your AI interview. "
    "I'll guide you through a few short introductory questions "
    "before we begin. What is your name? You may also say "
    "'prefer not to say' if you would rather not share it."
)


async def main():

    config = interview_voice_gateway._build_config()

    config = config.model_copy(
        update={
            "system_instruction": (
                "You are the voice interface for an interview application. "
                "The application backend may provide an opening message. "
                "When it does, speak that message exactly as provided. "
                "Do not add questions or information of your own. "
                "When the candidate responds, use the backend function. "
                "After receiving the function response, speak it faithfully."
            )
        }
    )

    try:

        async with gemini_live_service.connect(config) as (session, model):

            print("\nConnected model:", model)
            print("\nSending backend-provided greeting...")

            await session.send_realtime_input(
                text=(
                    "The application backend has provided this opening "
                    "message. Speak it exactly as written, without adding "
                    "anything:\n\n" + GREETING
                )
            )

            audio_received = False
            transcription = []

            async with asyncio.timeout(60):

                async for message in session.receive():

                    content = message.server_content

                    if not content:
                        continue

                    if content.output_transcription:
                        value = content.output_transcription.text

                        if value:
                            transcription.append(value)
                            print(value, end="", flush=True)

                    if content.model_turn:

                        for part in content.model_turn.parts:

                            if part.inline_data and part.inline_data.data:
                                audio_received = True

                    if content.turn_complete:
                        break

            spoken_text = "".join(transcription)

            print("\n\nAudio received:", audio_received)
            print("Transcription:", spoken_text)

            if not audio_received:
                raise RuntimeError("No greeting audio received.")

            if not spoken_text.strip():
                raise RuntimeError("No greeting transcription received.")

            print("\nPASS: Backend greeting was spoken.")

    finally:
        await gemini_live_service.close()


if __name__ == "__main__":
    asyncio.run(main())
