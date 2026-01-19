import asyncio
import websockets
import json
import time
import math
import random

# Configuration
DEBUG = False  # Set to True for detailed output

class RoastSimulator:
    """Simulates a realistic Ethiopian light roast temperature profile"""
    
    def __init__(self):
        self.start_time = None
        self.roast_active = False
        
        # Ethiopian Light Roast Profile (10 minutes total)
        self.total_roast_time = 600      # 10 minutes in seconds
        self.charge_temp_et = 199        # Charge at 390°F (199°C)
        self.charge_temp_bt = 25         # Room temp beans initially
        
        # Key temperature milestones (BT - Bean Temperature)
        self.yellow_point_temp = 160     # 320°F (160°C) 
        self.yellow_point_time = 240     # 4 minutes
        self.first_crack_temp = 202      # 395°F (202°C)
        self.first_crack_time = 480      # 8 minutes  
        self.drop_temp = 210             # 410°F (210°C)
        self.drop_time = 600             # 10 minutes
        
        # Environmental conditions
        self.ambient_temp = 22
        
    def start_roast(self):
        """Start a new roast simulation"""
        self.start_time = time.time()
        self.roast_active = True
        print("🔥 Ethiopian Light Roast simulation started!")
        print("   Profile: 10min total, FC@8min, Drop@210°C")
        
    def stop_roast(self):
        """Stop the roast simulation"""
        self.roast_active = False
        self.start_time = None
        print("🛑 Roast simulation stopped")
        
    def reset_roast(self):
        """Reset and start a new roast"""
        self.stop_roast()
        time.sleep(0.1)  # Brief pause
        self.start_roast()
        
    def get_roast_phase(self, elapsed_time):
        """Determine current roast phase based on elapsed time"""
        if elapsed_time < 30:
            return "charge"
        elif elapsed_time < self.yellow_point_time:
            return "drying"
        elif elapsed_time < self.first_crack_time:
            return "maillard"
        elif elapsed_time < self.first_crack_time + 120:  # 2min development
            return "first_crack"
        elif elapsed_time < self.total_roast_time:
            return "development"
        else:
            return "finished"
    
    def calculate_bt_temperature(self, elapsed_time):
        """Calculate realistic BT following Ethiopian light roast profile"""
        if elapsed_time <= 0:
            return self.charge_temp_bt
        
        # Define key points for the curve
        time_points = [0, 30, self.yellow_point_time, self.first_crack_time, self.drop_time]
        temp_points = [self.charge_temp_bt, 120, self.yellow_point_temp, self.first_crack_temp, self.drop_temp]
        
        # Find which segment we're in
        for i in range(len(time_points) - 1):
            if elapsed_time <= time_points[i + 1]:
                # Linear interpolation between points
                t1, t2 = time_points[i], time_points[i + 1]
                temp1, temp2 = temp_points[i], temp_points[i + 1]
                
                progress = (elapsed_time - t1) / (t2 - t1)
                
                # Apply different curve shapes for different phases
                if i == 0:  # Charge phase - rapid initial rise
                    curve_progress = 1 - math.exp(-3 * progress)
                elif i == 1:  # Drying phase - steady rise
                    curve_progress = progress
                elif i == 2:  # Maillard phase - gradual curve
                    curve_progress = 0.5 * (1 + math.sin(math.pi * progress - math.pi/2))
                else:  # Development phase - linear
                    curve_progress = progress
                
                temp = temp1 + (temp2 - temp1) * curve_progress
                break
        else:
            # Beyond roast time
            temp = self.drop_temp
        
        # Add realistic noise
        noise = random.uniform(-0.8, 0.8)
        return round(temp + noise, 1)
    
    def calculate_et_temperature(self, bt_temp, elapsed_time):
        """Calculate realistic ET (Environment Temperature)"""
        # ET starts high and gap narrows as roast progresses
        if elapsed_time < 60:
            # Early roast - large gap due to hot drum
            et_offset = 80 + random.uniform(-5, 5)
        elif elapsed_time < 240:  # Drying phase
            et_offset = 60 + random.uniform(-3, 3)
        elif elapsed_time < 480:  # Maillard phase
            et_offset = 45 + random.uniform(-3, 3)
        else:  # Development phase
            et_offset = 35 + random.uniform(-2, 2)
        
        et_temp = bt_temp + et_offset
        
        # Ensure ET doesn't go below charge temperature
        et_temp = max(et_temp, self.charge_temp_et)
        
        # Add independent noise
        noise = random.uniform(-1.5, 1.5)
        return round(et_temp + noise, 1)
    
    def get_temperature_data(self):
        """Get current simulated temperature readings"""
        if not self.roast_active or self.start_time is None:
            # Pre-roast state - just ambient readings
            return {
                'ET': round(self.ambient_temp + random.uniform(-0.5, 0.5), 1),
                'BT': round(self.ambient_temp + random.uniform(-0.5, 0.5), 1),
                'phase': 'idle',
                'elapsed_time': 0
            }
        
        elapsed_time = time.time() - self.start_time
        
        # Check if roast is finished
        if elapsed_time > self.total_roast_time:
            phase = "finished"
            bt_temp = self.drop_temp + random.uniform(-1, 1)
            et_temp = bt_temp + 30 + random.uniform(-2, 2)  # Smaller gap at end
        else:
            phase = self.get_roast_phase(elapsed_time)
            bt_temp = self.calculate_bt_temperature(elapsed_time)
            et_temp = self.calculate_et_temperature(bt_temp, elapsed_time)
        
        return {
            'ET': et_temp,
            'BT': bt_temp,
            'phase': phase,
            'elapsed_time': round(elapsed_time, 1)
        }

# Global roast simulator instance
roast_sim = RoastSimulator()

async def handle_artisan_connection(websocket):
    """Handle WebSocket connection from Artisan"""
    client_addr = websocket.remote_address
    print(f"✅ Artisan connected: {client_addr}")
    
    # Auto-start roast when Artisan connects
    if not roast_sim.roast_active:
        roast_sim.start_roast()
    
    try:
        async for message in websocket:
            if DEBUG:
                print(f"Received: {message}")
            
            # Parse the request to get the message ID
            try:
                request = json.loads(message)
                message_id = request.get('id', 0)
                command = request.get('command', '')
                
                if DEBUG:
                    print(f"   Command: {command}, ID: {message_id}")
            except:
                message_id = 0
                command = 'unknown'
            
            # Get roast data
            roast_data = roast_sim.get_temperature_data()
            
            # Create response in Artisan's expected format
            response = {
                "id": message_id,
                "data": {
                    "input1": roast_data['ET'],    # ET
                    "input2": roast_data['BT']     # BT
                }
            }
            
            # Send response
            response_json = json.dumps(response)
            await websocket.send(response_json)
            
            # Status output with milestone indicators
            phase = roast_data['phase']
            elapsed = roast_data['elapsed_time']
            et = roast_data['ET']
            bt = roast_data['BT']
            
            # Add milestone indicators
            milestone = ""
            if abs(elapsed - roast_sim.yellow_point_time) < 5 and bt >= roast_sim.yellow_point_temp - 5:
                milestone = "🟡 YELLOW POINT"
            elif abs(elapsed - roast_sim.first_crack_time) < 5 and bt >= roast_sim.first_crack_temp - 5:
                milestone = "💥 FIRST CRACK"
            elif elapsed >= roast_sim.drop_time - 10 and phase == "development":
                milestone = "🎯 APPROACHING DROP"
            elif phase == "finished":
                milestone = "✅ ROAST COMPLETE"
            
            # Format time as MM:SS
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            time_str = f"{minutes:2d}:{seconds:02d}"
            
            print(f"[{time_str}] {phase:12} ET={et:5.1f}°C  BT={bt:5.1f}°C  {milestone}")
            
            if DEBUG:
                print(f"   Full response: {response_json}")
    
    except websockets.exceptions.ConnectionClosed:
        print(f"Artisan disconnected: {client_addr}")
        roast_sim.stop_roast()
    except Exception as e:
        print(f"Error: {e}")

async def start_websocket_server():
    """Start the WebSocket server"""
    host = '127.0.0.1'
    port = 8765
    
    print("Ethiopian Light Roast Simulator for Artisan")
    print("=" * 45)
    print(f"WebSocket server starting on {host}:{port}")
    print(f"Roast profile: Ethiopian Light (10 minutes)")
    print(f"Key milestones:")
    print(f"  • Yellow Point: 160°C @ 4:00")
    print(f"  • First Crack: 202°C @ 8:00") 
    print(f"  • Drop: 210°C @ 10:00")
    print(f"Debug mode: {'ON' if DEBUG else 'OFF'}")
    print("-" * 45)
    print("Roast phases: charge → drying → maillard → first_crack → development → finished")
    print("Commands: 'r' = restart roast, 's' = stop roast, 'q' = quit")
    print("-" * 45)
    
    # Start WebSocket server
    server = await websockets.serve(handle_artisan_connection, host, port)
    print(f"✅ Server ready - waiting for Artisan...")
    
    # Keep server running
    await server.wait_closed()

async def handle_user_commands():
    """Handle user input for controlling the roast simulation"""
    import sys
    import select
    
    while True:
        # Check for user input (non-blocking)
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            command = sys.stdin.readline().strip().lower()
            
            if command == 'r':
                roast_sim.reset_roast()
            elif command == 's':
                roast_sim.stop_roast()
            elif command == 'q':
                print("Shutting down...")
                break
        
        await asyncio.sleep(0.1)

async def main():
    """Main function"""
    try:
        # Start server and command handler concurrently
        server_task = asyncio.create_task(start_websocket_server())
        
        # Run server (command handler would need different implementation for cross-platform)
        await server_task
        
    except KeyboardInterrupt:
        print("\nServer stopped")
        roast_sim.stop_roast()

if __name__ == "__main__":
    # Run the server
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nGoodbye!")