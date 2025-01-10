import numpy as np
from scipy.signal import find_peaks
from sklearn.cluster import KMeans

def support_and_resistance(data, numberOfLines=13):
    highs, _ = find_peaks(data['High'].values, distance=10)
    lows, _ = find_peaks(-data['Low'].values, distance=10)
    high_prices = data['High'].iloc[highs]
    low_prices = data['Low'].iloc[lows]
    key_levels = np.array(list(high_prices) + list(low_prices)).reshape(-1, 1)
    kmeans = KMeans(n_clusters=numberOfLines, random_state=0).fit(key_levels)
    return np.sort(kmeans.cluster_centers_.flatten())

