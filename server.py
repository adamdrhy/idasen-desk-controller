#import modules
import asyncio
import json
from flask import Flask, send_from_directory, request
from flask_sock import Sock
from idasen import IdasenDesk
import os

#preset positions (in meters)
MAC_ADDRESS = "E8:77:15:32:3C:1D"
POSITIONS = {"sit": 0.66, "stand": 1.02}

#configure Flask app and WebSocket
app = Flask(__name__, static_folder=".")
sock = Sock(app)

desk = IdasenDesk(MAC_ADDRESS) #connect to desk

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/eye.svg")
def eye_icon():
    return send_from_directory(".", "eye.svg")

@sock.route("/ws")
def height_stream(ws):
    async def stream():
        await desk.connect()
        try:
            while True:
                #handle incoming WebSocket message
                try:
                    message = ws.receive(timeout=0.01)
                    if message:
                        data = json.loads(message)
                        if data.get("action") == "move":
                            target = data.get("target")
                            if target in POSITIONS:
                                print(f"Moving to: {target} ({POSITIONS[target]} m)")
                                await desk.move_to_target(POSITIONS[target])
                except Exception:
                    pass #timeout or invalid message

                #send current height (in cm)
                try:
                    height = await desk.get_height()
                    ws.send(str(height * 100))
                except Exception:
                    break
        finally:
            await desk.disconnect()

    asyncio.run(stream())

@app.route("/backlight", methods=["POST"])
def backlight_control():
    data = request.json
    state = data.get("on") #expects true or false
    try:
        with open("/sys/class/backlight/10-0045/bl_power", "w") as f:
            f.write("0" if state else "1") #0=on, 1=off
        return {"status": "ok", "backlight": state}
    except Exception as e:
        return {"status": "error", "error": str(e)}, 500

#run server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
