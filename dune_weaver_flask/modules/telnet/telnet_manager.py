import telnetlib3
import threading
import time
import logging
import asyncio
from dune_weaver_flask.modules.core.state import state

logger = logging.getLogger(__name__)

# Global variables
telnet_port = None
telnet_lock = threading.RLock()
HOST = 'fluidnc.local'
IGNORE_PORTS = ['/dev/cu.debug-console', '/dev/cu.Bluetooth-Incoming-Port']
client = None



# Device information
arduino_table_name = None
arduino_driver_type = 'Unknown'
firmware_version = 'Unknown'


class TelnetClient:
    def __init__(self):
        self.host = None
        self.port = None
        self.reader = None
        self.writer = None
        self.loop = None

    def connect(self, host, port):
        self.host = host
        self.port = port
        async def myconnect():
            try:
                self.reader, self.writer = await telnetlib3.open_connection(self.host, self.port, )
                return True  # Connection successful
            except Exception as e:
                print(f"Error connecting: {e}")
                return False
        return self.run_coroutine(myconnect())

    def read_until(self, separator=b'\n'):
        async def myread():
            logger.debug(f"Reading until {separator}")
            try:
                logger.debug("Writing....")
                self.writer.write("$Startup/Show\n") 
                #await self.writer.drain()
                logger.debug("Wrote")
                #return await self.reader.readuntil(separator)
                #while True:
                #    readbyte = await self.reader.read(1024)
                #    logger.debug(f"Read byte: {readbyte}")
                readdata = await self.reader.readuntil('ok'.encode())
                logger.debug(f"Read data: {readdata}")
                return readdata
            except Exception as e:
                logger.error(f"Error in myread: {e}")
                return None
        return self.run_coroutine(myread())

    async def write(self, data):
        try:
            self.writer.write(data)
            await self.writer.drain() # Ensure data is sent
            return True
        except Exception as e:
            print(f"Error writing: {e}")
            return False

    async def close(self):
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception as e:
                print(f"Error closing: {e}")

    def run_coroutine(self, coro):  # Helper to run coroutines
        if self.loop is None:
            self.loop = asyncio.new_event_loop()  # Create a new loop if needed.
            asyncio.set_event_loop(self.loop) # Important! Set the new loop.
        return self.loop.run_until_complete(coro)

def set_client(new_client):
    global client
    logger.debug(f'Setting internal client: {new_client}')
    client = new_client

def list_serial_ports():
    """Return a list of available telnet ports."""
    # Replace with actual logic to list telnet ports
    available_ports = ["23"]  # Example: dynamically discover ports
    logger.debug(f"Available telnet ports: {available_ports}")
    return available_ports

def connect_to_serial(port=None, baudrate=115200):
    """Automatically connect to the first available telnet port or a specified port."""
    global telnet_port, arduino_table_name, arduino_driver_type, firmware_version
    try:
        if port is None:
            ports = list_serial_ports()
            if not ports:
                logger.warning("No telnet port connected")
                return False
            port = ports[0]  # Auto-select the first available port

        with telnet_lock:
            #TODO close the connection
            
            telnet_port = port
            logger.debug(f'Connecting to {HOST}:{port}, {client}')
            if not client.connect(HOST, port):
                logger.error(f"Failed to connect to telnet port {port}")
                return False
        # machine_x, machine_y = get_machine_position()
        # if not machine_x or not machine_y or machine_x != state.machine_x or machine_y != state.machine_y:
        #     logger.info(f'x, y; {machine_x}, {machine_y}')
        #     logger.info(f'State x, y; {state.machine_x}, {state.machine_y}')
        #     home()
        # else:
        #     logger.info('Machine position known, skipping home')
        
        logger.info(f"Connected to telnet port: {port}")
        time.sleep(2)  # Allow time for the connection to establish

        # Read initial startup messages from Arduino
        
        logger.debug("Reading....")
        line = client.read_until()#.decode().strip()
        logger.debug(f"Arduino: ")
        if "Table:" in line:
            arduino_table_name = line.replace("Table: ", "").strip()
        elif "Drivers:" in line:
            arduino_driver_type = line.replace("Drivers: ", "").strip()
        elif "Version:" in line:
            firmware_version = line.replace("Version: ", "").strip()

        logger.info(f"Detected Table: {arduino_table_name or 'Unknown'}")
        logger.info(f"Detected Drivers: {arduino_driver_type or 'Unknown'}")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to telnet port {port}: {e}")
        telnet_port = None

    logger.error("Max retries reached. Could not connect to a telnet port.")
    return False

# def disconnect_from_serial():
#     """Disconnect from the current telnet port."""
#     global telnet_conn, telnet_port
#     if telnet_conn:
#         logger.info("Disconnecting telnet connection")
#         reader.close()
#         writer.close()
#         telnet_conn = None
#     telnet_port = None

# def restart_serial(port, baudrate=115200):
#     """Restart the telnet connection."""
#     logger.info(f"Restarting telnet connection on port {port}")
#     disconnect_from_serial()
#     return connect_to_serial(port, baudrate)

def is_connected():
    """Return True if connected to a telnet port."""
    return reader is not None and writer is not None

def get_port():
    """Return the current telnet port."""
    return telnet_port

# def get_status_response():
#     """
#     Send a status query ('?') and return the response string if available.
#     This helper centralizes the query logic used throughout the module.
#     """
#     while True:
#         with telnet_lock:
#             writer.write("\n".encode())
#             #TODO Eager Read
#             response = telnet_conn.readuntil(b'\n').decode().strip()
#             if "MPos" in response:
#                 logger.info(f"Status response: {response}")
#                 return response
#         time.sleep(1)

# def parse_machine_position(response):
#     """
#     Parse the work position (MPos) from a status response.
#     Expected format: "<...|MPos:-994.869,-321.861,0.000|...>"
#     Returns a tuple (work_x, work_y) if found, else None.
#     """
#     if "MPos:" not in response:
#         return None
#     try:
#         wpos_section = next((part for part in response.split("|") if part.startswith("MPos:")), None)
#         if wpos_section:
#             wpos_str = wpos_section.split(":", 1)[1]
#             wpos_values = wpos_str.split(",")
#             work_x = float(wpos_values[0])
#             work_y = float(wpos_values[1])
#             return work_x, work_y
#     except Exception as e:
#         logger.error(f"Error parsing work position: {e}")
#     return None

# def parse_buffer_info(response):
#     """
#     Parse the planner and serial buffer info from a status response.
#     Expected format: "<...|Bf:15,128|...>"
#     Returns a dictionary with keys 'planner_buffer' and 'serial_buffer' if found, else None.
#     """
#     if "|Bf:" in response:
#         try:
#             buffer_section = response.split("|Bf:")[1].split("|")[0]
#             planner_buffer, serial_buffer = map(int, buffer_section.split(","))
#             return {"planner_buffer": planner_buffer, "serial_buffer": serial_buffer}
#         except ValueError:
#             logger.warning("Failed to parse buffer info from response")
#     return None

# def send_grbl_coordinates(x, y, speed=600, timeout=2, home=False):
#     """
#     Send a G-code command to FluidNC and wait up to timeout seconds for an 'ok' response.
#     If no 'ok' is received, retry every retry_interval seconds until successful.
#     """
#     logger.debug(f"Sending G-code: X{x} Y{y} at F{speed}")
#     while True:
#         with telnet_lock:
#             if home:
#                 gcode = f"$J=G91 Y{y} F{speed}"
#             else:
#                 gcode = f"G1 X{x} Y{y} F{speed}"
#             writer.write(f"{gcode}\n".encode())
#             logger.debug(f"Sent command: {gcode}")

#             start_time = time.time()
#             while time.time() - start_time < timeout:
#                 #TODO read eager
#                 response = reader.readuntil(b'\n').decode().strip()
#                 logger.debug(f"Response: {response}")
#                 if response.lower() == "ok":
#                     logger.debug("Command execution confirmed.")
#                     return  # Exit function when 'ok' is received

#             logger.warning(f"No 'ok' received for X{x} Y{y}. Retrying in 1s...")

#         time.sleep(1)

# def home(retry=0):
#     logger.info(f"Homing with speed {state.speed}")
    
#     # Check config for sensorless homing
#     with telnet_lock:
#         writer.write("$config\n".encode())
#         response = reader.readuntil(b'\n').decode().strip()
#         logger.debug(f"Config response: {response}")
                
#     if "sensorless" in response.lower():
#         logger.info("Using sensorless homing")
#         with telnet_lock:
#             writer.write("$H\n".encode())
#             writer.write("G1 Y0 F100\n".encode())
#     # we check that we actually got a valid response, if not, we try again a couple of times
#     elif "filename" in response.lower():
#         logger.info("Using brute-force homing")
#         send_grbl_coordinates(0, -110/5, state.speed, home=True)
    
#     else:
#         # we wait a bit and cal again increasing retry times
#         # if we are over the third retry, we give up
#         if retry < 3:
#             time.sleep(1)
#             home(retry+1)
#             return
#         else:
#             # after 3 retries we're still not getting a good response
#             # raise an exception
#             raise Exception("Couldn't get a valid response for homing after 3 retries")
    
#     state.current_theta = state.current_rho = 0
#     update_machine_position()

# def check_idle():
#     """
#     Continuously check if the machine is in the 'Idle' state.
#     """
#     logger.info("Checking idle")
#     while True:
#         response = get_status_response()
#         if response and "Idle" in response:
#             logger.info("Table is idle")
#             update_machine_position()
#             return True  # Exit once 'Idle' is confirmed
#         time.sleep(1)

# def get_machine_position(timeout=3):
#     """
#     Send status queries for up to `timeout` seconds to obtain a valid machine (work) position.
#     Returns a tuple (machine_x, machine_y) if a valid response is received,
#     otherwise returns (None, None) after timeout.
#     """
#     start_time = time.time()
#     while time.time() - start_time < timeout:
#         with telnet_lock:
#             writer.write('?'.encode())
#             writer.write('\n'.encode())
#             # Check if there is any response available
#             response = reader.readuntil(b'\n').decode().strip()
#             logger.debug(f"Raw status response: {response}")
#             if "MPos" in response:
#                 pos = parse_machine_position(response)
#                 if pos:
#                     machine_x, machine_y = pos
#                     logger.debug(f"Machine position: X={machine_x}, Y={machine_y}")
#                     return machine_x, machine_y
#         # Short sleep before trying again
#         time.sleep(0.1)
#     logger.warning("Timeout reached waiting for machine position")
#     return None, None

# def update_machine_position():
#     state.machine_x, state.machine_y = get_machine_position()
#     state.save()


# loop = asyncio.get_event_loop()
# coro = telnetlib3.open_connection('localhost', 6023, shell=shell)
# reader, writer = loop.run_until_complete(coro)
# loop.run_until_complete(writer.protocol.waiter_closed)