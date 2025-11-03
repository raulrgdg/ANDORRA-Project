-> Analyse de plusieurs capteurs à l'oscillo pour voir si on peut

Voir photos pour montrer qu'on peut détecter correctement temporellement la différence entre les différents capteurs

-> 20 microseconds de temps pour pouvoir voir correctement la différence entre 2 signaux avec les distances qu'on a ici
-> F = 1/T donc 1/(20*10**-6) càd 50kHz de freq d'échantillonnage

-> il faut utiliser double buffers circulaires + carte sd pour arriver à cette fréquence car sinon limité à 11KHz

""" marche bof bof
Calcul théorique de freq en USB:
- baud rate = n bits par seconde = 1 000 000
- on envoie environ 25 * 8 bits (entre 2 et 3 par capteurs + les virgules), sachant que un caractère = 8 bits donc 200 bits par datapoint
- donc on a en théorie 1 000 000 / 200 = 5000
"""


On a besoin de booster la freq de sampling donc utilisation d'un double buffer circulaire


### taille des buffers

sachant qu'on a une freq d'échantillonnage de chaque capteur de 50kHz donc -> 50 000 points/s
-> Si on a un buffer de 20ms par exemple, on a 50 000 / 500 * 5; * 5 car 5 capteurs /500 car on a que 20ms (1000/20 -> 500 points/ms)


-> faire les kicad des différents montages testés pour les comparer et montrer les problèmes etc


### tension
Tension mesurée à l'oscillo = ordre de 150V donc les estimations avec pont diviseur sont pas trop correctes car le pont diviseur de tension absorbe une partie de la charge



## pb carte SD

-> pour pouvoir écrire sur carte sd il faut formatage FAT32 spécifique donc bizarre

-> utilisation de gparted sur ubuntu pour formatter la carte sd en fat32 (un peu bizarre car normalement le format de fat32 = max 32gb mais ici on a fat32 une carte 64gb hehehe)


## utilisation analogread+carte sd

On voit qu'avec le code optimisé on arrive seulement à 11500Hz de fréquence d'échantillonnage car analogread est lent

La ligne coupable est ici dans ta fonction fill_array :

la ligne :
array[index][i] = analogRead(adc_pins[i]);
-> donc chaque appel à analogRead() est bloquant et prend environ 7–20 µs (selon réglage ADC, résolution, averaging…). Avec 5 canaux, tu passes facilement 80–100 µs par ligne, soit ≈10–12 kHz max malheureusement

-> solution: il faut lire les ADC en DMA en parallèle -> utiliser la lib officielle ADC en non bloquant pour pouvoir lire en // les adcs rapidement.. cela permettra de lire le buffer sans blocage et d'accélérer de fou la lecture


-> En lecture ADC + DMA + double buffer, tu peux monter à >150 kS/s (par ADC)

Donc jusqu’à 300 kS/s au total sur 2 ADCs en parallèle (car on a 2 adcs sur une teensy, on pourrait utiliser les 2 en même temps)

Si tu veux 5 canaux, tu peux faire lecture alternée ou multiplexée

-> Par ex : ADC0 → canaux 15, 19, 23 et ADC1 → canaux 17, 21

### utilisation de la lib ADC

On passe de 11500 à plus de 55000 de sampling donc super rapide

Avant on utilisait analogread() pour lire les données sauf qu'à cause du multiplexage on est lent
-> on utilise mtn la lib adc de teensy pour lire les pins donc bcp plus rapide (car on fait moins d'average donc ça va plus vite)


On a 55kHz donc en pratique on a 55 * 5 = 275 kHz de sampling frequency