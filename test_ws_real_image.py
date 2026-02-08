
import asyncio
import websockets
import json
import base64
from PIL import Image
import io

async def test_chat_with_real_image():
    # Create a 100x100 white square
    img = Image.new('RGB', (200, 200), color = (255, 255, 255))
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    image_data = f"data:image/png;base64,{img_str}"
    
    uri = "ws://localhost:8001/api/v1/ws/chat"
    try:
        async with websockets.connect(uri) as websocket:
            print(f"Connected to {uri}")
            
            payload = {
                "query": "What is in this image?",
                "session_id": "test-session-real",
                "images": [image_data]
            }
            
            await websocket.send(json.dumps(payload))
            print("Sent payload with 200x200 image")
            
            complete = False
            while not complete:
                response = await websocket.recv()
                data = json.loads(response)
                if data['type'] == 'token':
                     print(data['content'], end="", flush=True)
                if data['type'] == 'complete':
                    complete = True
                if data['type'] == 'error':
                    print(f"\nSERVER ERROR: {data['message']}")
                    complete = True
            print("\nTest finished.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_chat_with_real_image())
