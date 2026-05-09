from __future__ import annotations

import os


def main() -> None:
    try:
        from dotenv import load_dotenv
        from livekit import agents
        from livekit.agents import Agent, AgentServer, AgentSession, TurnHandlingOptions, inference, room_io
        from livekit.plugins import ai_coustics, silero
        from livekit.plugins.turn_detector.multilingual import MultilingualModel
    except ModuleNotFoundError as exc:  # pragma: no cover - optional integration
        raise SystemExit(
            "LiveKit dependencies are not installed yet. Install the LiveKit Agents stack before running this starter."
        ) from exc

    load_dotenv(".env")

    class JarvisAssistant(Agent):
        def __init__(self) -> None:
            super().__init__(
                instructions=(
                    "You are JARVIS, a calm, formal, dryly witty household associate. "
                    "Keep responses concise, useful, and respectful. "
                    "Prefer clear operational guidance over chatty filler."
                )
            )

    server = AgentServer()

    stt_model = os.getenv("LIVEKIT_STT_MODEL", "deepgram/nova-3")
    llm_model = os.getenv("LIVEKIT_LLM_MODEL", "openai/gpt-5.2-chat-latest")
    tts_model = os.getenv("LIVEKIT_TTS_MODEL", "cartesia/sonic-3")
    tts_voice = os.getenv("LIVEKIT_TTS_VOICE", "")

    @server.rtc_session(agent_name=os.getenv("LIVEKIT_AGENT_NAME", "jarvis-agent"))
    async def jarvis_agent(ctx: agents.JobContext) -> None:
        session = AgentSession(
            stt=inference.STT(model=stt_model, language="multi"),
            llm=inference.LLM(model=llm_model),
            tts=inference.TTS(model=tts_model, voice=tts_voice or None),
            vad=silero.VAD.load(),
            turn_handling=TurnHandlingOptions(
                turn_detection=MultilingualModel(),
            ),
        )
        await session.start(
            room=ctx.room,
            agent=JarvisAssistant(),
            room_options=room_io.RoomOptions(
                audio_input=room_io.AudioInputOptions(
                    noise_cancellation=ai_coustics.audio_enhancement(
                        model=ai_coustics.EnhancerModel.QUAIL_VF_L,
                    ),
                ),
            ),
        )
        await session.generate_reply(
            instructions="Greet the user briefly and offer practical help.",
        )

    agents.cli.run_app(server)


if __name__ == "__main__":
    main()
