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

ADC* adc = new ADC();
#define PIN(a) a,
uint8_t adc_pins[] = {PINS};
#undef PIN
#define PIN(...) 1 +
#define PIN_COUNT (PINS 0)
#define COL_COUNT (PINS 1)

static_assert(COL_COUNT == PIN_COUNT + 1, "COL_COUNT must include timestamp");

int data[BUFFER_SIZE * COL_COUNT];
DMAMEM int after_detection[BUFFER_SIZE * 4 * COL_COUNT];
uint16_t array_index = 0;
uint32_t array_index_2 = 0;

bool detected = false;
bool saving = false;

using namespace std::chrono;
std::chrono::time_point<std::chrono::steady_clock, std::chrono::microseconds> start;

// ---------- FIX: version pointeur + taille ----------
void fill_array(int *array, size_t T, int index) {
    int base = index * COL_COUNT;
    if ((size_t)(base + COL_COUNT) > T) return; // évite overflow

    for (int i = 0; i < PIN_COUNT; ++i) {
        array[base + i] = adc->analogRead(adc_pins[i]);
        if (array[base + i] > 50 && !detected) {
            Serial.println("Analog input detected");
            start = std::chrono::time_point_cast<std::chrono::microseconds>(std::chrono::steady_clock::now());
            detected = true;
        }
    }
    array[base + PIN_COUNT] = micros(); // timestamp
}
// ----------------------------------------------------

void setup() {
    pinMode(LED_BUILTIN, OUTPUT);
    digitalWrite(LED_BUILTIN, LOW);
    if (!SD.begin(BUILTIN_SDCARD)) {
        digitalWrite(LED_BUILTIN, HIGH); // SD init failed
    }

    memset(after_detection, 0, sizeof(after_detection));
    memset(data, 0, sizeof(data));
    for(auto a : adc->adc){
        a->setAveraging(2); // no averaging
        a->setResolution(10); // 10-bit for speed
        a->setConversionSpeed(ADC_CONVERSION_SPEED::HIGH_SPEED);
        a->setSamplingSpeed(ADC_SAMPLING_SPEED::HIGH_SPEED);
    }
}

void loop() {
    if (!detected) {
        fill_array(data, BUFFER_SIZE * COL_COUNT, array_index);
        array_index = (array_index + 1) % BUFFER_SIZE;
    } else if (!saving) {
        fill_array(after_detection, BUFFER_SIZE * 4 * COL_COUNT, array_index_2);
        array_index_2++;

        if (array_index_2 >= BUFFER_SIZE * 4 || std::chrono::steady_clock::now() - start > 10ms) {
            saving = true;
        }
    } else {
        Serial.println("Started to save data");

        auto file = SD.open(("data_" + String(rtc_get()) + ".bin").c_str(), FILE_WRITE);

        // Save pre-trigger buffer (ring buffer logic)
        size_t tail_rows = BUFFER_SIZE - array_index;
        size_t head_rows = array_index;

        file.write(&data[array_index * COL_COUNT], tail_rows * COL_COUNT * sizeof(int));
        file.write(data, head_rows * COL_COUNT * sizeof(int));

        // Save post-trigger data
        size_t filled_rows = min(array_index_2, (uint32_t)(BUFFER_SIZE * 4));
        file.write(after_detection, filled_rows * COL_COUNT * sizeof(int));

        file.flush();
        delay(100); // Ensure SD write is fully completed
        file.close();

        // Reset state
        detected = false;
        saving = false;
        array_index = 0;
        array_index_2 = 0;
        memset(after_detection, 0, sizeof(after_detection));
        memset(data, 0, sizeof(data));
    }
}
