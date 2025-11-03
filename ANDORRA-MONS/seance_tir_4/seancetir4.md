Mapping capteurs avec entrée:

#### De gauche à droite

C2 - C5 - C3 - C1 - C4




T1 - T2 -> voir mesure avec papier teensy marque


T1 -> tir proche de C1
T2 -> tir proche de C2
T3 -> tir proche de C5
T4 -> tir proche de C4



C2 -> A15
C5 -> A17
C3 -> A19
C1 -> A21
C4 -> A23





3 tirs sur la plaque 1:

Tir 1 - Tir 2 - Tir 3 -> les 3 tirs sont cohérents, 3 tirs sur les positions T1,T2,T3 voir photos avec images 



4 tirs sur la plaque 2 avec la capa:

- Tir 1: aucune donné, la carte n'envoie rien
- Tir 2, 3 et 4 OK => données cohérentes -> voir les graphiques 



### Localisation

-> utiliser les temps d'arrivée (TDoA) pour localiser l'impact est tout à fait pertinente et est une méthode couramment utilisée pour ce type de problème. Le principal défi est de déterminer précisément le moment d'arrivée de l'onde pour chaque capteur. La détection du pic n'est souvent pas la meilleure stratégie car le pic peut correspondre à une réflexion ou à la partie la plus intense de l'onde, et non au tout début de sa propagation.

Problème avec la détection de pic et solutions proposées:
Détecter un pic pour marquer le temps d'arrivée (ToA) est souvent imprécis pour les raisons suivantes :

- Forme de l'onde : L'onde générée par un impact n'est pas toujours une impulsion simple. Elle peut avoir une montée progressive, des oscillations, ou des réflexions qui brouillent le signal.

- Amplitude variable : L'amplitude du signal reçu peut varier considérablement entre les capteurs en fonction de la distance à l'impact et des caractéristiques de propagation. Un pic bas pour un capteur éloigné pourrait ne pas être le véritable début.

- Bruit de fond : Le bruit ambiant ou électronique peut créer de petits pics qui sont confondus avec le signal d'impact.


idée = une détection de seuil adaptative pour chaque capteur. L'idée est de calculer le niveau de bruit moyen (ou un multiple de l'écart-type) avant l'impact et de considérer le temps d'arrivée comme le premier point où le signal dépasse significativement ce niveau de bruit.


. Détection des Temps d'Arrivée (ToA)
C'est l'étape la plus critique et la plus délicate. Un temps d'arrivée imprécis entraînera une localisation d'impact erronée.

Problème du pic : Comme vous l'avez noté, le pic du signal ADC ne correspond pas forcément à l'arrivée initiale de l'onde. L'onde se propage et l'amplitude maximale peut être atteinte plus tard en raison de la forme de l'onde ou de réverbérations.

Approche par seuil adaptatif :

Estimation du bruit de fond : Nous prenons les premières noise_estimation_window_points (ici, 3 points) du signal pour estimer le niveau de bruit. Nous calculons la moyenne (noise_mean) et l'écart-type (noise_std) de ce segment.

Définition du seuil : Le seuil d'arrivée est calculé comme :

Seuil=noise_mean+threshold_multiplier×noise_std

Le threshold_multiplier (ici, 5) détermine à quel point le signal doit être supérieur au bruit pour être considéré comme une arrivée. Une valeur de 3 à 5 est courante pour un bon rapport signal/bruit.

Sécurité du seuil : Pour éviter que le seuil soit trop bas dans un environnement très silencieux, nous nous assurons qu'il est au moins égal à 10% de la valeur maximale du signal. Cela garantit que de petites fluctuations de bruit ne sont pas confondues avec des impacts.

Détection : Le temps d'arrivée est enregistré comme le premier instant où la valeur ADC du capteur dépasse ce seuil.

### souci = freq de sampling 

v onde dans acier = jusqu'à 6000m/s
v samping = 11kHz (0.000091s)

3200m/s en 0.000091 s -> 29cm -> en 1 freq echantillonnage temps de faire 2 fois la plaque :'( 



Il faut passer de 11kHz à 500kHz

