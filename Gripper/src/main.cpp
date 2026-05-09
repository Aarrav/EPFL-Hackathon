#include <Arduino.h>
#include <SCServo.h>

SMS_STS st;

void setup() {
  // Uno uses Serial (Pins 0 and 1) to talk to the adapter
  // NOTE: UNPLUG the adapter from Pins 0/1 when uploading this code!
  Serial.begin(1000000); 
  st.pSerial = &Serial;
  delay(500);
}

void loop() {
  // st.WritePosEx(ID, Position, Speed, Acceleration)
  // Position is 0-4095. Speed is 0-4000.
  
  st.WritePosEx(1, 3000, 500, 50); // Move to 3000
  delay(2000);
  
  st.WritePosEx(1, 1000, 500, 50); // Move to 1000
  delay(2000);
}