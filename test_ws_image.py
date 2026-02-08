
import asyncio
import websockets
import json
import base64

async def test_chat_with_image():
    # Tiny white pixel
    image_data = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAAAAAA6fptVAAAACklEQVR4nGNiAAAABgDNjd8qAAAAAElFTkSuQmCC"
    
    uri = "ws://localhost:8001/api/v1/ws/chat"
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")
            
            payload = {
                "query": "What is in this image?",
                "session_id": "test-session",
                "images": [image_data]
            }
            
            await websocket.send(json.dumps(payload))
            print("Sent payload with image")
            
            while True:
                response = await websocket.recv()
                data = json.loads(response)
                print(f"Received: {data['type']}")
                if data['type'] == 'token':
                     print(f"Token: {data['content']}", end="", flush=True)
                if data['type'] == 'complete':
                    break
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_chat_with_image())
