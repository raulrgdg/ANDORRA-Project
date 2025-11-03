void setup() {
  Serial.begin(115200);
  pinMode(A16, INPUT_DISABLE);
}
void loop() {
  int adc_signal = analogRead(A16);  // ton signal utile
  Serial.println(adc_signal);
  }
