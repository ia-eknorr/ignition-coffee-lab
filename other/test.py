import asyncio
import websockets
import json
import random

async def handle_client(websocket):
    print(f"Client connected: {websocket.remote_address}")
    
    try:
        async for message in websocket:
            # Parse request to get message ID
            try:
                request = json.loads(message)
                message_id = request.get('id', 0)
            except:
                message_id = 0
            
            # Generate random number
            value = round(random.uniform(100, 200), 1)
            
            # Create response
            response = {
                "id": message_id,
                "data": {
                    "input1": value
                }
            }
            
            # Send response
            await websocket.send(json.dumps(response))
            print(f"Sent: {value}")
    
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")

async def main():
    host = '127.0.0.1'
    port = 8765
    
    print(f"Starting server on {host}:{port}")
    
    async with websockets.serve(handle_client, host, port):
        print("Server ready")
        await asyncio.Future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped")
