import struct
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import savgol_filter
from scipy.optimize import least_squares
import itertools
import time
from typing import List, Tuple, Dict, Any
import json

class ImpactDetectionOptimizer:
    """
    Classe pour optimiser les paramètres de détection d'impact et de localisation TDOA
    en minimisant l'erreur de prédiction.
    """

    def __init__(self, data_file: str, actual_impact_location: np.ndarray):
        """
        Initialise l'optimiseur avec les données et la position réelle de l'impact.

        Args:
            data_file: Chemin vers le fichier de données binaires
            actual_impact_location: Position réelle de l'impact [x, y] en cm
        """
        self.data_file = data_file
        self.actual_impact_location = actual_impact_location
        self.data = None
        self.time_s = None
        self.adc_values = None
        self.FS = None

        # Paramètres de la plaque et des capteurs
        self.PLATE_WIDTH = 15
        self.PLATE_HEIGHT = 15
        self.SENSOR_COORDS_ALL = np.array([
            [3, 12],   # ADC 0
            [12, 12],  # ADC 1
            [3, 3],    # ADC 2
            [12, 3],   # ADC 3
            [7.5, 7.5], # ADC 4 (centre de la plaque - capteur virtuel ou non utilisé)
        ])

        # Vitesse de propagation par défaut
        self.V_WAVE = 300000.0  # cm/s

        # Historique des résultats d'optimisation
        self.optimization_history = []

        # Charger les données
        self._load_data()

    def _load_data(self):
        """Charge et prépare les données depuis le fichier binaire."""
        try:
            with open(self.data_file, "rb") as f:
                data_bytes = f.read()

            COL_COUNT = 6
            ELEMENT_SIZE = 4

            num_elements = len(data_bytes) // ELEMENT_SIZE
            num_rows = num_elements // COL_COUNT
            trimmed_size = num_rows * COL_COUNT * ELEMENT_SIZE
            data_bytes = data_bytes[:trimmed_size]

            data = struct.unpack("<" + "i" * (num_rows * COL_COUNT), data_bytes)
            data = np.array(data).reshape((num_rows, COL_COUNT))

            timestamps = data[:, -1]
            adc_values = data[:, :-1]
            time_s = (timestamps - timestamps[0]) / 1e6

            avg_sampling_period_us = np.mean(timestamps[1:] - timestamps[:-1])
            FS = 1e6 / avg_sampling_period_us

            self.data = data
            self.time_s = time_s
            self.adc_values = adc_values
            self.FS = FS

            # Vérifier la cohérence entre le nombre de canaux ADC et de capteurs
            num_adc_channels = adc_values.shape[1]
            num_sensors = len(self.SENSOR_COORDS_ALL)

            if num_adc_channels != num_sensors:
                print(f"ATTENTION: {num_adc_channels} canaux ADC détectés mais {num_sensors} capteurs configurés")
                print("Le 5ème canal ADC sera traité mais peut ne pas avoir de capteur physique")

            print(f"Données chargées: {len(time_s)} échantillons, FS = {FS:.2f} Hz")
            print(f"Canaux ADC: {num_adc_channels}, Capteurs: {num_sensors}")

        except Exception as e:
            print(f"Erreur lors du chargement des données: {e}")
            raise

    def calculate_sta_lta(self, signal: np.ndarray, sta_window: int, lta_window: int) -> np.ndarray:
        """Calcule le ratio STA/LTA pour un signal donné."""
        signal = np.abs(signal).astype(float)
        sta = np.zeros_like(signal)
        lta = np.zeros_like(signal)

        for i in range(len(signal)):
            start_sta = max(0, i - sta_window + 1)
            sta[i] = np.mean(signal[start_sta : i + 1])
            start_lta = max(0, i - lta_window + 1)
            lta[i] = np.mean(signal[start_lta : i + 1])

        lta[lta == 0] = 1e-9
        return sta / lta

    def find_onset_sta_lta(self, sta_lta_ratio: np.ndarray, threshold: float, lta_window: int) -> int:
        """Trouve l'index du début d'impact basé sur le ratio STA/LTA."""
        for i in range(lta_window, len(sta_lta_ratio)):
            if sta_lta_ratio[i] > threshold:
                return i
        return -1

    def refine_onset_derivative(self, signal: np.ndarray, preliminary_onset_idx: int,
                               search_back_samples: int, search_forward_samples: int,
                               savgol_win_len: int, savgol_poly_order: int,
                               deriv_threshold_factor: float) -> int:
        """Affine la détection du début d'impact en utilisant la dérivée."""
        search_start_idx = max(0, preliminary_onset_idx - search_back_samples)
        search_end_idx = min(len(signal), preliminary_onset_idx + search_forward_samples)

        if search_start_idx >= search_end_idx:
            return preliminary_onset_idx

        segment = signal[search_start_idx : search_end_idx]

        # Ajuster la longueur de fenêtre Savitzky-Golay
        if savgol_win_len % 2 == 0:
            savgol_win_len += 1
        if len(segment) < savgol_win_len:
            savgol_win_len = max(3, (len(segment) // 2) * 2 + 1)
            if savgol_win_len > len(segment):
                return preliminary_onset_idx

        try:
            smoothed_deriv = savgol_filter(segment, savgol_win_len, savgol_poly_order, deriv=1)
        except ValueError:
            return preliminary_onset_idx

        relative_prelim_idx = preliminary_onset_idx - search_start_idx
        search_range_for_peak = smoothed_deriv[: min(len(smoothed_deriv), relative_prelim_idx + savgol_win_len // 2)]

        if len(search_range_for_peak) == 0:
            return preliminary_onset_idx

        max_deriv_in_range = np.max(search_range_for_peak)
        if max_deriv_in_range <= 0:
            return preliminary_onset_idx

        idx_max_deriv_in_segment = np.argmax(search_range_for_peak)
        deriv_threshold = max_deriv_in_range * deriv_threshold_factor

        onset_relative_idx = -1
        for i in range(idx_max_deriv_in_segment, -1, -1):
            if smoothed_deriv[i] < deriv_threshold:
                onset_relative_idx = i
                break

        if onset_relative_idx == -1:
            return preliminary_onset_idx

        return search_start_idx + onset_relative_idx

    def detect_impacts(self, params: Dict[str, Any]) -> Tuple[List[float], List[float]]:
        """
        Détecte les impacts avec les paramètres donnés.

        Returns:
            Tuple de (temps STA/LTA, temps T0 affinés)
        """
        # Extraire les paramètres
        sta_window_length_s = params['sta_window_length_s']
        lta_window_length_s = params['lta_window_length_s']
        sta_lta_threshold = params['sta_lta_threshold']
        savgol_window_length = params['savgol_window_length']
        savgol_polyorder = params['savgol_polyorder']
        refinement_search_back_samples = int(params['refinement_search_back_s'] * self.FS)
        refinement_search_forward_samples = int(params['refinement_search_forward_s'] * self.FS)
        derivative_threshold_factor = params['derivative_threshold_factor']

        # Conversion des longueurs de fenêtres
        sta_window_samples = max(1, int(sta_window_length_s * self.FS))
        lta_window_samples = max(1, int(lta_window_length_s * self.FS))

        detected_sta_lta_times_s = []
        detected_t0_times_s = []

        for i in range(self.adc_values.shape[1]):
            signal = self.adc_values[:, i]
            sta_lta_ratio = self.calculate_sta_lta(signal, sta_window_samples, lta_window_samples)
            preliminary_onset_idx = self.find_onset_sta_lta(sta_lta_ratio, sta_lta_threshold, lta_window_samples)

            if preliminary_onset_idx != -1:
                detected_sta_lta_times_s.append(self.time_s[preliminary_onset_idx])
                t0_idx = self.refine_onset_derivative(
                    signal, preliminary_onset_idx,
                    refinement_search_back_samples, refinement_search_forward_samples,
                    savgol_window_length, savgol_polyorder, derivative_threshold_factor
                )
                detected_t0_times_s.append(self.time_s[t0_idx])
            else:
                detected_sta_lta_times_s.append(np.nan)
                detected_t0_times_s.append(np.nan)

        return detected_sta_lta_times_s, detected_t0_times_s

    def localize_impact_tdoa(self, detected_t0_times_s: List[float],
                            wave_speed: float) -> Tuple[np.ndarray, float]:
        """
        Localise l'impact en utilisant la méthode TDOA.

        Returns:
            Tuple de (position estimée, erreur de localisation)
        """
        # Filtrer les capteurs avec des T0s valides
        valid_sensor_indices = [i for i, t0 in enumerate(detected_t0_times_s) if not np.isnan(t0)]

        if len(valid_sensor_indices) < 3:
            return None, float('inf')

        # Vérifier que les indices sont dans les limites des coordonnées des capteurs
        max_sensor_index = len(self.SENSOR_COORDS_ALL) - 1
        valid_sensor_indices = [i for i in valid_sensor_indices if i <= max_sensor_index]

        if len(valid_sensor_indices) < 3:
            print(f"ATTENTION: Seulement {len(valid_sensor_indices)} capteurs valides après filtrage des indices")
            return None, float('inf')

        # Préparer les données pour TDOA
        active_sensor_coords = self.SENSOR_COORDS_ALL[valid_sensor_indices]
        active_t0_s = np.array(detected_t0_times_s)[valid_sensor_indices]

        # Capteur de référence
        reference_sensor_idx_in_active = np.argmin(active_t0_s)
        T0_ref = active_t0_s[reference_sensor_idx_in_active]
        X_ref, Y_ref = active_sensor_coords[reference_sensor_idx_in_active]

        def tdoa_residuals(impact_location, sensor_coords, arrival_times, wave_speed, ref_t0, ref_x, ref_y):
            xp, yp = impact_location
            residuals = []
            for i in range(len(sensor_coords)):
                xi, yi = sensor_coords[i]
                ti = arrival_times[i]

                dist_i = np.sqrt((xp - xi)**2 + (yp - yi)**2)
                dist_ref = np.sqrt((xp - ref_x)**2 + (yp - ref_y)**2)

                residuals.append((dist_i - dist_ref) - wave_speed * (ti - ref_t0))
            return np.array(residuals)

        # Optimisation
        initial_guess = np.array([self.PLATE_WIDTH / 2, self.PLATE_HEIGHT / 2])
        bounds = ([0, 0], [self.PLATE_WIDTH, self.PLATE_HEIGHT])

        try:
            result = least_squares(
                tdoa_residuals, initial_guess,
                args=(active_sensor_coords, active_t0_s, wave_speed, T0_ref, X_ref, Y_ref),
                bounds=bounds, ftol=1e-6, xtol=1e-6, gtol=1e-6
            )

            estimated_location = result.x
            localization_error = np.sqrt(np.sum((estimated_location - self.actual_impact_location)**2))

            return estimated_location, localization_error

        except Exception:
            return None, float('inf')

    def evaluate_parameters(self, params: Dict[str, Any]) -> float:
        """
        Évalue un ensemble de paramètres en calculant l'erreur de localisation.

        Returns:
            Erreur de localisation (inf si échec)
        """
        try:
            # Détecter les impacts
            detected_sta_lta_times_s, detected_t0_times_s = self.detect_impacts(params)

            # Localiser l'impact
            estimated_location, localization_error = self.localize_impact_tdoa(
                detected_t0_times_s, params['wave_speed']
            )

            return localization_error

        except Exception as e:
            print(f"Erreur lors de l'évaluation des paramètres: {e}")
            return float('inf')

    def grid_search_optimization(self, param_ranges: Dict[str, List],
                                max_iterations: int = None) -> Dict[str, Any]:
        """
        Effectue une recherche par grille intelligente pour optimiser les paramètres.

        Args:
            param_ranges: Dictionnaire des plages de valeurs pour chaque paramètre
            max_iterations: Nombre maximum d'itérations (None pour toutes les combinaisons)

        Returns:
            Dictionnaire contenant les meilleurs paramètres et l'historique
        """
        print("Début de l'optimisation par recherche par grille...")

        # Générer toutes les combinaisons de paramètres
        param_names = list(param_ranges.keys())
        param_values = list(param_ranges.values())
        total_combinations = np.prod([len(vals) for vals in param_values])

        if max_iterations is None:
            max_iterations = total_combinations

        print(f"Total des combinaisons possibles: {total_combinations}")
        print(f"Nombre d'itérations maximum: {max_iterations}")

        best_error = float('inf')
        best_params = None
        iteration = 0

        start_time = time.time()

        # Parcourir les combinaisons
        for combination in itertools.product(*param_values):
            if iteration >= max_iterations:
                break

            # Créer le dictionnaire de paramètres
            params = dict(zip(param_names, combination))

            # Évaluer les paramètres
            error = self.evaluate_parameters(params)

            # Sauvegarder l'historique
            result = {
                'iteration': iteration,
                'params': params.copy(),
                'error': error,
                'timestamp': time.time()
            }
            self.optimization_history.append(result)

            # Mettre à jour le meilleur résultat
            if error < best_error:
                best_error = error
                best_params = params.copy()
                print(f"Iteration {iteration}: Nouvelle meilleure erreur: {error:.4f} cm")
                print(f"Paramètres: {best_params}")

            iteration += 1

            # Afficher le progrès
            if iteration % 10 == 0:
                elapsed_time = time.time() - start_time
                progress = iteration / max_iterations * 100
                print(f"Progrès: {progress:.1f}% ({iteration}/{max_iterations}) - "
                      f"Temps écoulé: {elapsed_time:.1f}s")

        total_time = time.time() - start_time
        print(f"\nOptimisation terminée en {total_time:.1f} secondes")
        print(f"Meilleure erreur de localisation: {best_error:.4f} cm")
        print(f"Meilleurs paramètres: {best_params}")

        return {
            'best_params': best_params,
            'best_error': best_error,
            'total_iterations': iteration,
            'total_time': total_time,
            'optimization_history': self.optimization_history
        }

    def save_results(self, filename: str):
        """Sauvegarde les résultats d'optimisation dans un fichier JSON."""
        results = {
            'best_params': self.optimization_history[-1]['params'] if self.optimization_history else None,
            'best_error': self.optimization_history[-1]['error'] if self.optimization_history else None,
            'optimization_history': self.optimization_history,
            'data_file': self.data_file,
            'actual_impact_location': self.actual_impact_location.tolist(),
            'plate_dimensions': [self.PLATE_WIDTH, self.PLATE_HEIGHT],
            'sensor_coordinates': self.SENSOR_COORDS_ALL.tolist()
        }

        with open(filename, 'w') as f:
            json.dump(results, f, indent=2, default=str)

        print(f"Résultats sauvegardés dans {filename}")

    def plot_optimization_progress(self):
        """Affiche le progrès de l'optimisation."""
        if not self.optimization_history:
            print("Aucun historique d'optimisation disponible")
            return

        errors = [result['error'] for result in self.optimization_history]
        iterations = [result['iteration'] for result in self.optimization_history]

        plt.figure(figsize=(12, 8))

        # Progrès de l'erreur
        plt.subplot(2, 2, 1)
        plt.plot(iterations, errors, 'b-', alpha=0.7)
        plt.plot(iterations, errors, 'ro', markersize=3)
        plt.xlabel('Itération')
        plt.ylabel('Erreur de localisation (cm)')
        plt.title('Progrès de l\'optimisation')
        plt.grid(True)
        plt.yscale('log')

        # Distribution des erreurs
        plt.subplot(2, 2, 2)
        plt.hist(errors, bins=50, alpha=0.7, edgecolor='black')
        plt.xlabel('Erreur de localisation (cm)')
        plt.ylabel('Fréquence')
        plt.title('Distribution des erreurs')
        plt.grid(True)

        # Évolution des paramètres clés
        if self.optimization_history:
            sta_thresholds = [result['params']['sta_lta_threshold'] for result in self.optimization_history]
            wave_speeds = [result['params']['wave_speed'] for result in self.optimization_history]

            plt.subplot(2, 2, 3)
            plt.plot(iterations, sta_thresholds, 'g-', label='Seuil STA/LTA')
            plt.xlabel('Itération')
            plt.ylabel('Seuil STA/LTA')
            plt.title('Évolution du seuil STA/LTA')
            plt.grid(True)
            plt.legend()

            plt.subplot(2, 2, 4)
            plt.plot(iterations, wave_speeds, 'r-', label='Vitesse onde (cm/s)')
            plt.xlabel('Itération')
            plt.ylabel('Vitesse onde (cm/s)')
            plt.title('Évolution de la vitesse d\'onde')
            plt.grid(True)
            plt.legend()

        plt.tight_layout()
        plt.show()


def main():
    """Fonction principale pour exécuter l'optimisation."""

    # Configuration
    data_file = "data_1752195397.bin"
    actual_impact_location = np.array([3, 12])  # Centre de la plaque

    # Créer l'optimiseur
    optimizer = ImpactDetectionOptimizer(data_file, actual_impact_location)

    # Définir les plages de paramètres à explorer
    param_ranges = {
        'sta_window_length_s': [0.0002, 0.0005, 0.001, 0.002],  # 0.2ms à 2ms
        'lta_window_length_s': [0.003, 0.005, 0.01, 0.015],    # 3ms à 15ms
        'sta_lta_threshold': [1.5, 1.8, 2.0, 2.5, 3.0],       # Seuils STA/LTA
        'savgol_window_length': [21, 31, 41, 51],              # Longueurs de fenêtre Savitzky-Golay
        'savgol_polyorder': [2, 3, 4],                         # Ordres polynomiaux
        'refinement_search_back_s': [0.0005, 0.001, 0.002],    # Recherche en arrière
        'refinement_search_forward_s': [0.0001, 0.0002, 0.0005], # Recherche en avant
        'derivative_threshold_factor': [0.03, 0.05, 0.08, 0.1], # Facteur de seuil dérivée
        'wave_speed': [200000, 250000, 300000, 350000, 400000]  # Vitesses d'onde (cm/s)
    }

    # Lancer l'optimisation (limiter à 1000 itérations pour commencer)
    results = optimizer.grid_search_optimization(param_ranges, max_iterations=1000)

    # Sauvegarder les résultats
    optimizer.save_results("optimization_results.json")

    # Afficher le progrès
    optimizer.plot_optimization_progress()

    # Afficher les meilleurs paramètres
    print("\n=== RÉSULTATS FINAUX ===")
    print(f"Meilleure erreur de localisation: {results['best_error']:.4f} cm")
    print("Meilleurs paramètres:")
    for param, value in results['best_params'].items():
        print(f"  {param}: {value}")

    # Tester les meilleurs paramètres
    print("\n=== TEST DES MEILLEURS PARAMÈTRES ===")
    detected_sta_lta_times_s, detected_t0_times_s = optimizer.detect_impacts(results['best_params'])
    estimated_location, final_error = optimizer.localize_impact_tdoa(detected_t0_times_s, results['best_params']['wave_speed'])

    if estimated_location is not None:
        print(f"Position réelle: ({actual_impact_location[0]:.2f}, {actual_impact_location[1]:.2f}) cm")
        print(f"Position estimée: ({estimated_location[0]:.2f}, {estimated_location[1]:.2f}) cm")
        print(f"Erreur finale: {final_error:.4f} cm")
    else:
        print("Échec de la localisation avec les meilleurs paramètres")


if __name__ == "__main__":
    main()