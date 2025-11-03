void setup() {
  Serial.begin(1000000);

  pinMode(23, INPUT_DISABLE);
  pinMode(21, INPUT_DISABLE);
  pinMode(19, INPUT_DISABLE);
  pinMode(17, INPUT_DISABLE);
  pinMode(15, INPUT_DISABLE);
}

void loop() {
  int adc_23 = analogRead(23);
  int adc_21 = analogRead(21);
  int adc_19 = analogRead(19);
  int adc_17 = analogRead(17);
  int adc_15 = analogRead(15);



  // Print as CSV: adc23,adc21,adc19,adc17,adc15
  Serial.print(adc_23); Serial.print(",");
  Serial.print(adc_21); Serial.print(",");
  Serial.print(adc_19); Serial.print(",");
  Serial.print(adc_17); Serial.print(",");
  Serial.println(adc_15);

}
