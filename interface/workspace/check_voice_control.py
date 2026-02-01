from interface.cli import VoiceControl, get_voice_engine, NOVA_VOICE_AVAILABLE
print(f'NOVA_VOICE_AVAILABLE: {NOVA_VOICE_AVAILABLE}')
v = get_voice_engine()
print(f'Engine: {v}')
print(f'Provider: {v.tts.provider if v else None}')