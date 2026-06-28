import os, sys
sys.path.insert(0, '.')

os.environ['SUPABASE_URL'] = 'https://placeholder.supabase.co'
os.environ['SUPABASE_ANON_KEY'] = 'placeholder'
os.environ['SUPABASE_SERVICE_KEY'] = 'placeholder'

import numpy as np
import asyncio
from backend.fingerprint.phash_encoder import encode_phash, hamming_distance
from backend.fingerprint.fusion import compute_score, get_severity

print('[1] phash_encoder import: OK')
print('[2] fusion import: OK')

# Fusion self-similarity
a = np.ones(512, dtype=np.float32); a /= np.linalg.norm(a)
score = compute_score(a, a, '0000000000000000', '0000000000000000')
assert abs(score - 1.0) < 1e-3, f'Expected 1.0 got {score}'
print(f'[3] fusion self-score: {score} OK')

# Severity mapping
assert get_severity(0.97) == 'CRITICAL'
assert get_severity(0.92) == 'HIGH'
assert get_severity(0.87) == 'MEDIUM'
assert get_severity(0.80) == 'NONE'
print('[4] severity mapping: OK')

# URL classifier
from backend.hunter.url_classifier import classify_url, URLType
assert classify_url('https://youtube.com/watch?v=abc') == URLType.YOUTUBE
assert classify_url('https://instagram.com/p/abc') == URLType.SOCIAL
assert classify_url('https://example.com/image.jpg') == URLType.DIRECT
assert classify_url('https://example.com/page') == URLType.STATIC
assert classify_url('https://twitch.tv/abc') == URLType.LIVE
print('[5] url_classifier: 5/5 cases OK')

# FAISS store
os.makedirs('./data', exist_ok=True)
from backend.store.faiss_store import add_asset, search, index_size

async def test_faiss():
    vec = np.random.rand(512).astype(np.float32)
    vec /= np.linalg.norm(vec)
    fid = await add_asset(vec, 'test-uuid-abc123')
    results = await search(vec, k=1)
    assert results, 'FAISS search returned empty'
    assert results[0][0] == 'test-uuid-abc123'
    assert results[0][1] > 0.99
    sz = index_size()
    print(f'[6] FAISS: add+search OK (faiss_id={fid}, score={results[0][1]:.6f}, total={sz})')

asyncio.run(test_faiss())

# pHash on synthetic image
from PIL import Image
img = Image.new('RGB', (256, 256), color=(128, 64, 200))
ph = encode_phash(img)
assert len(ph) == 16, f'Expected 16 hex chars, got {len(ph)}: {ph}'
dist = hamming_distance(ph, ph)
assert dist == 0, f'Self-distance should be 0, got {dist}'
print(f'[7] pHash: "{ph}" self-distance=0 OK')

print()
print('=== ALL TESTS PASSED ===')
