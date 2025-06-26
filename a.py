import os
import csv

FOLDER = "adc_logs"

csv = []
png = []
for file_name in os.listdir(FOLDER):
    if file_name.endswith('csv'):
        csv.append(file_name.split('.')[0].split('_')[-2:])
    else:
        png.append(file_name.split('.')[0].split('_')[-2:])


for v in csv:
    if v not in png:
        print(v)