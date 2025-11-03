#include <Arduino.h>
#include "ADC.h"
#include <SD.h>

#include "chrono"
#include <SdFat.h>

#define FREQUENCY 50000
#define BUFFER_PERIOD 100

#define BUFFER_SIZE (FREQUENCY / BUFFER_PERIOD)

#define PINS \
    PIN(15)  \
    PIN(17)  \
    PIN(19)  \
    PIN(21)  \
    PIN(23)

#define PIN(a) a,
uint8_t adc_pins[] = {PINS};
#undef PIN
#define PIN(...) 1 +
#define PIN_COUNT PINS 0
#define COL_COUNT PINS 1


//ADC adc;
int data[BUFFER_SIZE][COL_COUNT];
DMAMEM int after_detection[BUFFER_SIZE * 4] [COL_COUNT];
uint16_t array_index = 0;
uint32_t array_index_2 = 0;

bool detected = false;
bool saving = false;
using namespace std::chrono;
std::chrono::time_point<std::chrono::steady_clock, std::chrono::microseconds> start;

template<size_t T, size_t K>
void fill_array(int array[T][K], int index){
    int i = 0;
    for( ; i < PIN_COUNT; i++) {
        array[index][i] = analogRead(adc_pins[i]);
        if(array[index][i] > 30 && !detected){
            Serial.println("Analog input detected");
            start = std::chrono::time_point_cast<std::chrono::microseconds>(std::chrono::steady_clock::now());
            detected = true;
        }
    }
    array[index][i] = micros();
}

void setup() {
    pinMode(LED_BUILTIN, OUTPUT);
    digitalWrite(LED_BUILTIN, LOW);
    if(!SD.begin(BUILTIN_SDCARD)){
        digitalWrite(LED_BUILTIN, HIGH);
    }
    memset(after_detection, 0, sizeof(after_detection));
// write your initialization code here
}

void loop() {
    if(!detected) {
        fill_array<BUFFER_SIZE, COL_COUNT>(data, array_index);
        array_index = (array_index + 1) % BUFFER_SIZE;
    }else if(!saving){
        fill_array<BUFFER_SIZE * 4, COL_COUNT>(after_detection, (int)array_index_2);
        array_index_2 = (array_index_2 + 1);
        if(array_index_2 >= BUFFER_SIZE * 4){
            saving = true;
        }
        if(std::chrono::steady_clock::now()-start > 10ms){
            saving = true;
        }
    }else{
        Serial.println("Started to save data");
        auto file = SD.open(("data_" + String(rtc_get()) + ".bin").c_str(), FILE_WRITE);
        file.write(&data[array_index], (BUFFER_SIZE - (array_index)) * COL_COUNT * sizeof(int));
        file.write(data, (array_index) * COL_COUNT * sizeof(int));
        file.write(after_detection, array_index_2 * COL_COUNT * sizeof(int));
        file.flush();
        delay(100);
        file.close();
        detected = false;
        saving = false;
        array_index = 0;
        array_index_2 = 0;
        memset(after_detection, 0, sizeof(after_detection));
        memset(data, 0, sizeof(data));
    }

}