#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEUtils.h>
#include <BLE2902.h>
#include <Wire.h>

// ===============================
// FLEX SENSOR PINS (ADC1 Only)
// ===============================
#define FLEX1 36  // Pin VP  -> Thumb
#define FLEX2 39  // Pin VN  -> Pinky
#define FLEX3 34  // Pin D34 -> Index
#define FLEX4 35  // Pin D35 -> Ring
#define FLEX5 32  // Pin D32 -> Middle

// ===============================
// MPU6050 CONFIG
// ===============================
uint8_t mpuAddress = 0x68;
bool mpuFound = false;
unsigned long lastMpuRetry = 0;

// Function to find & initialize MPU6050 on either 0x68 or 0x69
bool initMPU() {
  uint8_t addresses[] = {0x68, 0x69};
  for (uint8_t addr : addresses) {
    Wire.beginTransmission(addr);
    if (Wire.endTransmission() == 0) {
      mpuAddress = addr;
      // Wake up MPU6050 (write 0 to PWR_MGMT_1 register 0x6B)
      Wire.beginTransmission(mpuAddress);
      Wire.write(0x6B);
      Wire.write(0x00);
      if (Wire.endTransmission() == 0) {
        Serial.printf("SUCCESS: MPU6050 found at address 0x%02X!\n", mpuAddress);
        mpuFound = true;
        return true;
      }
    }
  }
  mpuFound = false;
  return false;
}

// ===============================
// ADC SMOOTHING (Removes Noise)
// ===============================
int readSmoothADC(int pin, int samples = 16) {
  long sum = 0;
  for (int i = 0; i < samples; i++) {
    sum += analogRead(pin);
    delayMicroseconds(50);
  }
  return (int)(sum / samples);
}

// ===============================
// BLE UUIDs
// ===============================
#define SERVICE_UUID        "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
#define CHARACTERISTIC_UUID "beb5483e-36e1-4688-b7f5-ea07361b26a8"

BLECharacteristic *pCharacteristic = nullptr;
bool deviceConnected = false;
bool oldDeviceConnected = false;

// ===============================
// BLE CALLBACKS
// ===============================
class MyServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer* pServer) {
    deviceConnected = true;
    Serial.println(">>> BLE CLIENT CONNECTED! <<<");
  }

  void onDisconnect(BLEServer* pServer) {
    deviceConnected = false;
    Serial.println(">>> BLE CLIENT DISCONNECTED! Restarting Advertising... <<<");
  }
};

// ===============================
// SETUP
// ===============================
void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("\n==================================");
  Serial.println("Starting BiGlove_ESP32 Setup...");
  Serial.println("==================================");

  // 1. Configure 12-bit ADC for Flex Sensors
  analogReadResolution(12);

  // 2. Initialize I2C for MPU6050 (SDA=21, SCL=22)
  Wire.begin(21, 22);
  Wire.setClock(100000);
  Wire.setTimeOut(50);

  // Try to find MPU at startup
  if (!initMPU()) {
    Serial.println("WARNING: MPU6050 not detected at 0x68 or 0x69.");
    Serial.println("Check: SDA=21, SCL=22, VCC=3.3V/5V, GND=GND");
  }

  // 3. Initialize BLE
  Serial.println("Initializing Bluetooth BLE...");
  BLEDevice::init("BiGlove_ESP32");
  
  BLEServer *pServer = BLEDevice::createServer();
  pServer->setCallbacks(new MyServerCallbacks());

  BLEService *pService = pServer->createService(SERVICE_UUID);
  pCharacteristic = pService->createCharacteristic(
      CHARACTERISTIC_UUID,
      BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY
  );
  pCharacteristic->addDescriptor(new BLE2902());
  pService->start();

  // 4. Start BLE Advertising
  BLEAdvertising *pAdvertising = BLEDevice::getAdvertising();
  pAdvertising->addServiceUUID(SERVICE_UUID);
  pAdvertising->setScanResponse(true);
  pAdvertising->setMinPreferred(0x06);
  pAdvertising->setMinPreferred(0x12);
  
  BLEDevice::startAdvertising();

  Serial.println("==================================");
  Serial.println("BiGlove_ESP32 BLE IS NOW ADVERTISING!");
  Serial.println("Waiting for Python script to connect...");
  Serial.println("==================================\n");
}

// ===============================
// MAIN LOOP
// ===============================
void loop() {
  // 1. Read Flex Sensors with 16x oversampling to stop noise/variation
  int f1 = readSmoothADC(FLEX1);
  int f2 = readSmoothADC(FLEX2);
  int f3 = readSmoothADC(FLEX3);
  int f4 = readSmoothADC(FLEX4);
  int f5 = readSmoothADC(FLEX5);

  // 2. If MPU was not found at boot, retry every 2 seconds
  if (!mpuFound && (millis() - lastMpuRetry > 2000)) {
    lastMpuRetry = millis();
    initMPU();
  }

  // 3. Read MPU6050
  float ax = 0.0, ay = 0.0, az = 0.0;
  float gx = 0.0, gy = 0.0, gz = 0.0;

  if (mpuFound) {
    Wire.beginTransmission(mpuAddress);
    Wire.write(0x3B);
    if (Wire.endTransmission(false) == 0) {
      if (Wire.requestFrom((uint8_t)mpuAddress, (size_t)14) == 14) {
        int16_t ax_raw = (Wire.read() << 8) | Wire.read();
        int16_t ay_raw = (Wire.read() << 8) | Wire.read();
        int16_t az_raw = (Wire.read() << 8) | Wire.read();
        Wire.read(); Wire.read(); // Skip temperature
        int16_t gx_raw = (Wire.read() << 8) | Wire.read();
        int16_t gy_raw = (Wire.read() << 8) | Wire.read();
        int16_t gz_raw = (Wire.read() << 8) | Wire.read();

        ax = ax_raw / 16384.0;
        ay = ay_raw / 16384.0;
        az = az_raw / 16384.0;
        gx = gx_raw / 131.0;
        gy = gy_raw / 131.0;
        gz = gz_raw / 131.0;
      } else {
        mpuFound = false; // Lost communication, will retry
      }
    } else {
      mpuFound = false; // Lost communication, will retry
    }
  }

  // 4. Format CSV payload
  String data = String(f1) + "," +
                String(f2) + "," +
                String(f3) + "," +
                String(f4) + "," +
                String(f5) + "," +
                String(ax, 3) + "," +
                String(ay, 3) + "," +
                String(az, 3) + "," +
                String(gx, 3) + "," +
                String(gy, 3) + "," +
                String(gz, 3);

  // Print to Serial Monitor
  Serial.println(data);

  // 5. Send over BLE if connected
  if (deviceConnected && pCharacteristic != nullptr) {
    pCharacteristic->setValue(data.c_str());
    pCharacteristic->notify();
  }

  // Handle re-advertising after disconnect
  if (!deviceConnected && oldDeviceConnected) {
    delay(500); // Give bluetooth stack time
    BLEDevice::startAdvertising();
    Serial.println("Re-advertising BiGlove_ESP32...");
    oldDeviceConnected = deviceConnected;
  }
  if (deviceConnected && !oldDeviceConnected) {
    oldDeviceConnected = deviceConnected;
  }

  delay(100); // 10 updates per second
}
