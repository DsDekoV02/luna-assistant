import sys
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, r"D:\LunaDrive\LunaLab\projects\luna-jarvis\python-service")
from voice.text_processor import optimize_for_voice_clone

tests = [
    "Hola Nicolas, como estas hoy?",
    "Buenos dias! Que tal todo?",
    "Hola Nicolas, soy Luna. En que puedo ayudarte?",
    "Tienes 3 mensajes nuevos y la CPU esta al 45%.",
    "El archivo main.py tiene un error en la linea 42.",
    "Hola Nicolas!!! Como estas???",
    "Bueno, entonces vamos a ver que pasa.",
]

print("Text Processor V5 Fix Verification")
print("=" * 60)
for t in tests:
    result = optimize_for_voice_clone(t)
    changed = t != result
    print(f"  {'CHANGED' if changed else 'OK'}: '{t}'")
    if changed:
        print(f"      -> '{result}'")
    print()