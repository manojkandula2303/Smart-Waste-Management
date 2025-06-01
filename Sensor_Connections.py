# biogas_monitor.py
import spidev
import RPi.GPIO as GPIO
import time
import requests
import json

# Configuration
API_ENDPOINT = "http://your-server-ip:5000/api/data"
SENSOR_INTERVAL = 5  # seconds

# GPIO Setup
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Pin Definitions
HEAT_COIL_PIN = 17  # GPIO17 for heat coil control
LORA_CS_PIN = 16    # GPIO16 for LoRa module
LORA_RST_PIN = 26   # GPIO26 for LoRa reset

# Initialize GPIO for heat coil
GPIO.setup(HEAT_COIL_PIN, GPIO.OUT)
GPIO.output(HEAT_COIL_PIN, GPIO.LOW)

# 1. MCP3008 ADC Setup (SPI0)

spi = spidev.SpiDev()
spi.open(0, 0)  # SPI0, CE0
spi.max_speed_hz = 1000000  # 1 MHz clock

def read_adc(channel):
    """Read MCP3008 ADC value from specified channel (0-7)"""
    adc_data = spi.xfer2([1, (8 + channel) << 4, 0])
    return ((adc_data[1] & 0x03) << 8) + adc_data[2]


# 2. Methane Sensor (MQ-4)

def read_methane():
    """Read methane concentration from MQ-4 sensor (PPM)"""
    # MCP3008 Channel 0
    raw = read_adc(0)
    
    # Convert to voltage (0-3.3V)
    voltage = (raw * 3.3) / 1023
    
    # Calibration formula (adjust based on your sensor)
    # Typical calibration: 
    #   Rs/R0 = (Vcc - Vout)/Vout
    #   PPM = a * (Rs/R0)^b
    # For simplicity, we'll use a linear approximation
    methane_ppm = (voltage - 0.1) * 500
    
    return max(0, methane_ppm)  # Ensure non-negative value


# 3. Temperature Sensor (LM35DZ)

def read_temperature():
    """Read temperature from LM35DZ sensor (°C)"""
    # MCP3008 Channel 1
    raw = read_adc(1)
    
    # Convert to voltage
    voltage = (raw * 3.3) / 1023
    
    # LM35 output: 10mV per °C
    return voltage * 100


# 4. pH Sensor

def read_ph():
    """Read pH value from pH sensor"""
    # MCP3008 Channel 2
    raw = read_adc(2)
    
    # Convert to voltage
    voltage = (raw * 3.3) / 1023
    
    # Calibration formula (adjust based on your calibration)
    # pH 7.0 = 2.5V (neutral)
    # Slope: typically 0.18 pH per volt
    ph_value = 7 + ((2.5 - voltage) / 0.18)
    
    return ph_value

# 5. Heat Coil Control

def control_heat(target_temp=30):
    """Control heat coil based on temperature reading"""
    current_temp = read_temperature()
    
    if current_temp < target_temp:
        GPIO.output(HEAT_COIL_PIN, GPIO.HIGH)  # Turn on heat coil
        return "ON"
    else:
        GPIO.output(HEAT_COIL_PIN, GPIO.LOW)   # Turn off heat coil
        return "OFF"

# 6. LoRa Communication (RA-02)

def setup_lora():
    """Initialize LoRa module"""
    # SPI1 configuration for LoRa
    lora_spi = spidev.SpiDev()
    lora_spi.open(1, 0)  # SPI1, CE0
    lora_spi.max_speed_hz = 1000000
    
    # Configure LoRa parameters
    # (This is a simplified version - use pyLoRa for full functionality)
    # Typically you would set frequency, spreading factor, etc.
    # For now, we'll just return the SPI connection
    return lora_spi

def send_lora_data(lora_spi, data):
    """Send data via LoRa module (simplified)"""
    # In a real implementation, you would use LoRa-specific commands
    # This is just a placeholder for the concept
    try:
        # Convert data to bytes
        data_bytes = json.dumps(data).encode('utf-8')
        lora_spi.xfer2(list(data_bytes))
        return True
    except:
        return False
      
# Main Data Collection Function

def collect_and_send_data():
    """Collect sensor data and send to server"""
    try:
        # Read all sensors
        methane = read_methane()
        temperature = read_temperature()
        ph = read_ph()
        
        # Control heat coil
        heat_status = control_heat(30)  # Target 30°C
        
        # Prepare data payload
        data = {
            "methane": round(methane, 2),
            "temperature": round(temperature, 2),
            "ph": round(ph, 2),
            "heat_status": heat_status,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Option 1: Send via HTTP (for WiFi)
        response = requests.post(
            API_ENDPOINT,
            json=data,
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        
        # Option 2: Send via LoRa (for long-range)
        lora_spi = setup_lora()
        send_lora_data(lora_spi, data)
        lora_spi.close()
        
        print(f"Data sent: {data}")
        return True
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

# Main Program Loop

if __name__ == "__main__":
    print("Biogas Monitoring System Started")
    
    try:
        while True:
            collect_and_send_data()
            time.sleep(SENSOR_INTERVAL)
            
    except KeyboardInterrupt:
        print("\nSystem shutdown")
    finally:
        # Cleanup
        spi.close()
        GPIO.cleanup()
