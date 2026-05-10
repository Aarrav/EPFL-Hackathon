#include <Arduino.h>
#include <Adafruit_NeoPixel.h>

// ESP32-S3 DevKitC-1 specific pins
#define RGB_PIN 48
#define NUM_PIXELS 1

Adafruit_NeoPixel pixels(NUM_PIXELS, RGB_PIN, NEO_GRB + NEO_KHZ800);

void setup() {
    // Start Serial - since you saw "Hello from Native USB", 
    // the 'Serial' object is the correct one for your current port.
    Serial.begin(115200);

    // Wait for Serial Monitor to be ready (up to 5 seconds)
    while (!Serial && millis() < 5000) {
        delay(10);
    }

    Serial.println("\n========================================");
    Serial.println("   ESP32-S3 SYSTEM CHECK INITIALIZED   ");
    Serial.println("========================================\n");

    pixels.begin();
    pixels.setBrightness(30); // 0-255 range
}

void loop() {
    static int colorIndex = 0;
    
    // Define some colors: Red, Green, Blue, Purple, Yellow
    uint32_t colors[] = {
        pixels.Color(255, 0, 0),   // Red
        pixels.Color(0, 255, 0),   // Green
        pixels.Color(0, 0, 255),   // Blue
        pixels.Color(200, 0, 255), // Purple
        pixels.Color(255, 200, 0)  // Yellow
    };

    // Update the LED
    pixels.setPixelColor(0, colors[colorIndex]);
    pixels.show();

    // Read internal stats
    float temp_c = temperatureRead();
    uint32_t uptime = millis() / 1000;

    // Print Status Report
    Serial.printf("[SYSTEM] Uptime: %lu seconds | Chip Temp: %.2f °C | LED Index: %d\n", 
                  uptime, temp_c, colorIndex);

    // Increment color
    colorIndex++;
    if (colorIndex >= 5) colorIndex = 0;

    delay(1000); // Wait 1 second
}