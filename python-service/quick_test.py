"""Quick voice clone + ASR test for pronunciation quality."""
import os, sys, base64, json, time, requests
sys.path.insert(0, os.path.dirname(__file__))

API_BASE = 'https://token-plan-sgp.xiaomimimo.com/v1'
API_KEY = os.environ.get('MIMO_API_KEY', '')
REF_PATH = os.path.join(os.path.dirname(__file__), '..', 'experiments', 'luna_voz_v5b_kohana_fina.wav')

with open(REF_PATH, 'rb') as f:
    ref_b64 = base64.b64encode(f.read()).decode('utf-8')

ref_data_url = f'data:audio/wav;base64,{ref_b64}'
text = 'Hola Nicolas, soy Luna. Estoy lista para ayudarte.'
headers = {'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'}

# TTS
payload = {
    'model': 'mimo-v2.5-tts-voiceclone',
    'messages': [{'role': 'assistant', 'content': text}],
    'audio': {'format': 'wav', 'voice': ref_data_url},
    'max_tokens': 4096
}

print(f'Generating: "{text}"')
start = time.time()
resp = requests.post(f'{API_BASE}/chat/completions', headers=headers, json=payload, timeout=120)
latency = (time.time() - start) * 1000
print(f'TTS Status: {resp.status_code} | Latency: {latency:.0f}ms')

if resp.status_code != 200:
    print(f'Error: {resp.text[:300]}')
    sys.exit(1)

data = resp.json()
audio_data = None
if 'message' in data and 'audio' in data['message']:
    audio_data = data['message']['audio'].get('data')
if not audio_data and 'choices' in data:
    msg = data['choices'][0].get('message', {})
    if 'audio' in msg:
        audio_data = msg['audio'].get('data')

if not audio_data:
    print('No audio data')
    sys.exit(1)

audio_bytes = base64.b64decode(audio_data)
out_path = os.path.join(os.path.dirname(__file__), '..', 'experiments', 'pronunciation_test_quick.wav')
with open(out_path, 'wb') as f:
    f.write(audio_bytes)
print(f'Audio saved: {out_path} ({len(audio_bytes)/1024:.1f} KB)')

# ASR
print('Transcribing with ASR...')
asr_payload = {
    'model': 'mimo-v2.5-asr',
    'messages': [{
        'role': 'user',
        'content': [{'type': 'input_audio', 'input_audio': {'data': audio_data, 'format': 'wav'}}]
    }],
    'max_tokens': 4096
}
asr_start = time.time()
asr_resp = requests.post(f'{API_BASE}/chat/completions', headers=headers, json=asr_payload, timeout=60)
asr_latency = (time.time() - asr_start) * 1000

if asr_resp.status_code == 200:
    transcription = asr_resp.json()['choices'][0]['message']['content']
    print(f'ASR ({asr_latency:.0f}ms): "{transcription}"')
    
    ref_words = text.lower().split()
    hyp_words = transcription.lower().split()
    d = [[0]*(len(hyp_words)+1) for _ in range(len(ref_words)+1)]
    for i in range(len(ref_words)+1): d[i][0] = i
    for j in range(len(hyp_words)+1): d[0][j] = j
    for i in range(1, len(ref_words)+1):
        for j in range(1, len(hyp_words)+1):
            if ref_words[i-1] == hyp_words[j-1]:
                d[i][j] = d[i-1][j-1]
            else:
                d[i][j] = min(d[i-1][j]+1, d[i][j-1]+1, d[i-1][j-1]+1)
    wer = d[len(ref_words)][len(hyp_words)] / max(len(ref_words), 1)
    print(f'WER: {wer:.1%}')
else:
    print(f'ASR error: {asr_resp.status_code}')

print('Done!')
