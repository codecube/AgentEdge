/*
 * ENS160+AHT21 Sensor Reader for Agent Edge
 *
 * Reads temperature, humidity (AHT21) and eCO2, TVOC, AQI (ENS160)
 * via I2C and outputs JSON over serial at 9600 baud every 2 seconds.
 *
 * Libraries required:
 *   - ScioSense_ENS160
 *   - Adafruit_AHTX0
 *
 * Wiring: SDA/SCL (I2C) + VCC + GND
 * ENS160 default I2C address: 0x53
 * AHT21 default I2C address: 0x38
 */

#include <Wire.h>
#include <ScioSense_ENS160.h>
#include <Adafruit_AHTX0.h>

ScioSense_ENS160 ens160(ENS160_I2CADDR_1);  // 0x53
Adafruit_AHTX0 aht;

void setup() {
  Serial.begin(9600);
  Wire.begin();

  if (!aht.begin()) {
    Serial.println("{\"error\":\"AHT21 not found\"}");
    while (1) delay(10);
  }

  if (!ens160.begin()) {
    Serial.println("{\"error\":\"ENS160 not found\"}");
    while (1) delay(10);
  }
  ens160.setMode(ENS160_OPMODE_STD);
}

void loop() {
  sensors_event_t humidity_event, temp_event;
  aht.getEvent(&humidity_event, &temp_event);

  float t = temp_event.temperature;
  float h = humidity_event.relative_humidity;

  // Feed AHT21 readings to ENS160 for compensation
  ens160.set_envdata(t, h);
  ens160.measure();

  int eco2 = ens160.geteCO2();
  int tvoc = ens160.getTVOC();
  int aqi  = ens160.getAQI();

  if (isnan(t) || isnan(h)) {
    Serial.println("{\"temp\":null,\"humidity\":null,\"eco2\":null,\"tvoc\":null,\"aqi\":null}");
  } else {
    Serial.print("{\"temp\":");
    Serial.print(t, 1);
    Serial.print(",\"humidity\":");
    Serial.print(h, 1);
    Serial.print(",\"eco2\":");
    Serial.print(eco2);
    Serial.print(",\"tvoc\":");
    Serial.print(tvoc);
    Serial.print(",\"aqi\":");
    Serial.print(aqi);
    Serial.println("}");
  }

  delay(5000);
}
