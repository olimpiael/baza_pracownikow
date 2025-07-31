#!/usr/bin/env python3
import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://127.0.0.1:8000/ws/room/test/"
    
    try:
        print(f"Connecting to {uri}")
        async with websockets.connect(uri) as websocket:
            print("Connected successfully!")
            
            # Send test message
            test_message = {
                "type": "test",
                "message": "Hello WebSocket!"
            }
            await websocket.send(json.dumps(test_message))
            print("Sent test message")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"Received response: {response}")
            except asyncio.TimeoutError:
                print("No response received within 5 seconds")
                
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket())
