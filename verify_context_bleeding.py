
import asyncio
import websockets
import json
import base64
from PIL import Image, ImageDraw
import io

async def verify_persistence():
    # 1. Create a BSOD image simulation
    img = Image.new('RGB', (400, 200), color = (0, 120, 215)) # Blue
    draw = ImageDraw.Draw(img)
    draw.text((20, 80), ":( HAL_INITIALIZATION_FAILED", fill=(255, 255, 255))
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    image_data = f"data:image/png;base64,{img_str}"
    
    uri = "ws://localhost:8000/api/v1/ws/chat"
    session_id = "test-persistence-session"
    
    print(f"Connecting to {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            # Turn 1: Image + Question
            print("\n--- TURN 1: Image + 'what is this?' ---")
            payload1 = {
                "query": "what is this error",
                "session_id": session_id,
                "images": [image_data]
            }
            await websocket.send(json.dumps(payload1))
            
            complete = False
            while not complete:
                response = await websocket.recv()
                data = json.loads(response)
                if data['type'] == 'token':
                     print(data['content'], end="", flush=True)
                if data['type'] == 'complete':
                    complete = True
            
            # Turn 2: Text-only follow-up
            print("\n\n--- TURN 2: Text-only 'how to fix this?' ---")
            payload2 = {
                "query": "how to fix this?",
                "session_id": session_id,
                "images": []
            }
            await websocket.send(json.dumps(payload2))
            
            complete = False
            while not complete:
                response = await websocket.recv()
                data = json.loads(response)
                if data['type'] == 'token':
                     print(data['content'], end="", flush=True)
                if data['type'] == 'complete':
                    complete = True
                    
            print("\n\nVerification finished.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(verify_persistence())
