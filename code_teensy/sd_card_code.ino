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
uint32_t detection_us = 0; // micros() at detection to ensure unique filenames

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
            detection_us = micros();
            detected = true;
        }
    }
    array[base + PIN_COUNT] = micros(); // timestamp
}
// ----------------------------------------------------

void listFiles() {
    Serial.println("Files on SD card:");
    File root = SD.open("/");
    while (true) {
        File entry = root.openNextFile();
        if (!entry) break;

        if (!entry.isDirectory()) {
            Serial.print(entry.name());
            Serial.print(" (");
            Serial.print(entry.size());
            Serial.println(" bytes)");
        }
        entry.close();
    }
    root.close();
    Serial.println("End of file list");
}

void sendFile(const char* filename) {
    File file = SD.open(filename, FILE_READ);
    if (!file) {
        Serial.print("ERROR: File not found: ");
        Serial.println(filename);
        return;
    }

    Serial.print("SENDING:");
    Serial.print(filename);
    Serial.print(":");
    Serial.println(file.size());

    // Send file in chunks
    uint8_t buffer[512];
    while (file.available()) {
        size_t bytesRead = file.read(buffer, sizeof(buffer));
        Serial.write(buffer, bytesRead);
    }

    Serial.println("END_OF_FILE");
    file.close();
}

void deleteFile(const char* filename) {
    if (!filename || !*filename) {
        Serial.println("ERROR: Invalid filename");
        return;
    }

    // Vérifier l'existence
    if (!SD.exists(filename)) {
        Serial.print("ERROR: File not found: ");
        Serial.println(filename);
        return;
    }

    // Tenter la suppression
    if (SD.remove(filename)) {
        Serial.print("DELETED:");
        Serial.println(filename);
    } else {
        Serial.print("ERROR: Delete failed: ");
        Serial.println(filename);
    }
}

void deleteAllFiles() {
    File root = SD.open("/");
    if (!root) {
        Serial.println("ERROR: Cannot open root");
        return;
    }

    uint32_t deletedCount = 0;
    while (true) {
        File entry = root.openNextFile();
        if (!entry) break;
        if (!entry.isDirectory()) {
            String name = entry.name();
            entry.close();
            if (SD.remove(name.c_str())) {
                deletedCount++;
            }
        } else {
            entry.close();
        }
    }
    root.close();
    Serial.print("DELETED_ALL:");
    Serial.println(deletedCount);
}

void handleSerialCommand() {
    if (Serial.available()) {
        String command = Serial.readStringUntil('\n');
        command.trim();

        if (command == "LIST") {
            listFiles();
        }
        else if (command == "HELP") {
            Serial.println("Available commands:");
            Serial.println("LIST - List all files on SD card");
            Serial.println("GET <filename> - Download a file");
            Serial.println("DEL <filename> - Delete a file");
            Serial.println("DELALL - Delete all files");
            Serial.println("HELP - Show this help");
        }
        else if (command.startsWith("GET ")) {
            String filename = command.substring(4);
            filename.trim();
            sendFile(filename.c_str());
        }
        else if (command.startsWith("DEL ")) {
            String filename = command.substring(4);
            filename.trim();
            deleteFile(filename.c_str());
        }
        else if (command == "DELALL") {
            deleteAllFiles();
        }
        else {
            Serial.print("Unknown command: ");
            Serial.println(command);
        }
    }
}

void setup() {
    pinMode(LED_BUILTIN, OUTPUT);
    digitalWrite(LED_BUILTIN, LOW);
    if (!SD.begin(BUILTIN_SDCARD)) {
        digitalWrite(LED_BUILTIN, HIGH); // SD init failed
    }

    Serial.begin(115200);
    while (!Serial && millis() < 5000); // Wait for serial or timeout

    Serial.println("Teensy Data Logger Ready");
    Serial.println("Commands: LIST, GET <filename>, HELP");

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
    // Handle serial commands (non-blocking)
    handleSerialCommand();

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
        // Include microseconds at detection to avoid filename collisions within the same second
        String filename = "data_" + String(rtc_get()) + "_" + String(detection_us) + ".bin";

        Serial.print("FILENAME:");
        Serial.println(filename);

        auto file = SD.open(filename.c_str(), FILE_WRITE);

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
        detection_us = 0;
        memset(after_detection, 0, sizeof(after_detection));
        memset(data, 0, sizeof(data));
    }
}
