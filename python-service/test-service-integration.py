"""
Luna JARVIS - Service Integration Test
Tests all Python service endpoints and WebSocket functionality.

Run: python test-service-integration.py
Requires: Python service running on localhost:8765
"""

import os
import sys
import json
import time
import asyncio
import requests
from pathlib import Path

BASE_URL = "http://localhost:8765"
WS_URL = "ws://localhost:8765/ws"


def test_http_endpoint(name, method, path, data=None, expected_status=200):
    """Test an HTTP endpoint and return result."""
    url = f"{BASE_URL}{path}"
    try:
        start = time.time()
        if method == "GET":
            resp = requests.get(url, timeout=30)
        elif method == "POST":
            resp = requests.post(url, json=data, timeout=60)
        else:
            return {"name": name, "success": False, "error": f"Unknown method: {method}"}
        
        elapsed = time.time() - start
        success = resp.status_code == expected_status
        
        return {
            "name": name,
            "success": success,
            "status": resp.status_code,
            "latency_s": round(elapsed, 2),
            "data": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text[:200],
        }
    except requests.ConnectionError:
        return {"name": name, "success": False, "error": "Connection refused - is the service running?"}
    except Exception as e:
        return {"name": name, "success": False, "error": str(e)}


def test_websocket():
    """Test WebSocket connection and messaging."""
    try:
        import websockets
    except ImportError:
        return {"name": "WebSocket", "success": False, "error": "websockets not installed"}
    
    async def _test():
        try:
            async with websockets.connect(WS_URL, timeout=10) as ws:
                # Wait for welcome message
                welcome = await asyncio.wait_for(ws.recv(), timeout=5)
                welcome_data = json.loads(welcome)
                
                if welcome_data.get("type") != "status":
                    return {"name": "WebSocket", "success": False, "error": f"Expected status, got: {welcome_data.get('type')}"}
                
                # Send a text message
                await ws.send(json.dumps({"type": "text", "content": "Hola Luna, ¿cómo estás?"}))
                
                # Collect responses
                responses = []
                try:
                    while True:
                        msg = await asyncio.wait_for(ws.recv(), timeout=30)
                        data = json.loads(msg)
                        responses.append(data)
                        # Stop after getting the final text (non-streaming)
                        if data.get("type") == "text" and not data.get("streaming"):
                            break
                except asyncio.TimeoutError:
                    pass
                
                return {
                    "name": "WebSocket",
                    "success": len(responses) > 0,
                    "welcome": welcome_data,
                    "response_count": len(responses),
                    "responses": responses[:5],  # First 5 for brevity
                }
        except Exception as e:
            return {"name": "WebSocket", "success": False, "error": str(e)}
    
    return asyncio.run(_test())


def run_all_tests():
    """Run all service integration tests."""
    print("🌙 Luna JARVIS - Service Integration Test")
    print(f"🎯 Target: {BASE_URL}")
    print("=" * 60)
    
    results = []
    
    # ── HTTP Endpoint Tests ──
    http_tests = [
        ("Root", "GET", "/"),
        ("Health", "GET", "/health"),
        ("Status", "GET", "/status"),
        ("Cache Stats", "GET", "/cache/stats"),
        ("Suggestions", "GET", "/suggestions"),
        ("Memory Search", "GET", "/memory/search?q=hola&top_k=3"),
        ("Chat", "POST", "/chat", {"message": "Hola Luna, ¿cómo estás?", "use_rag": True}),
        ("TTS", "POST", "/tts", {"text": "Hola Nicolas", "use_clone": False}),
        ("TTS Clone", "POST", "/tts", {"text": "Hola Nicolas", "use_clone": True}),
        ("Mode Set", "POST", "/mode", {"mode": "casa"}),
        ("Command: datetime", "POST", "/command", {"command": "datetime", "params": {}}),
        ("Command: systeminfo", "POST", "/command", {"command": "systeminfo", "params": {"info_type": "all"}}),
    ]
    
    print("\n📡 HTTP Endpoints:")
    print(f"{'─' * 60}")
    
    for test_def in http_tests:
        name = test_def[0]
        method = test_def[1]
        path = test_def[2]
        data = test_def[3] if len(test_def) > 3 else None
        
        result = test_http_endpoint(name, method, path, data)
        results.append(result)
        
        status = "✅" if result["success"] else "❌"
        latency = f"{result.get('latency_s', '?')}s"
        print(f"  {status} {name:<20} {latency:>6}  {result.get('error', '')[:40]}")
    
    # ── WebSocket Test ──
    print(f"\n🔌 WebSocket:")
    print(f"{'─' * 60}")
    
    ws_result = test_websocket()
    results.append(ws_result)
    
    status = "✅" if ws_result["success"] else "❌"
    print(f"  {status} WebSocket {'connected' if ws_result['success'] else ws_result.get('error', 'failed')[:50]}")
    if ws_result.get("response_count"):
        print(f"      Responses: {ws_result['response_count']}")
    
    # ── Summary ──
    print(f"\n{'=' * 60}")
    passed = sum(1 for r in results if r["success"])
    total = len(results)
    print(f"📊 Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Service is fully operational.")
    else:
        print("⚠️  Some tests failed:")
        for r in results:
            if not r["success"]:
                print(f"   ❌ {r['name']}: {r.get('error', 'unknown error')}")
    
    # Save results
    output_dir = Path(__file__).parent / "e2e_results"
    output_dir.mkdir(exist_ok=True)
    results_path = output_dir / "service_integration.json"
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "base_url": BASE_URL,
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "results": results,
        }, f, ensure_ascii=False, indent=2, default=str)
    
    print(f"\n📄 Results saved: {results_path}")
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
