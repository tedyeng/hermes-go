/**
 * Calculate distance between two coordinates in meters using Haversine formula.
 */
export function calculateDistance(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371e3; // Earth radius in meters
  const phi1 = (lat1 * Math.PI) / 180;
  const phi2 = (lat2 * Math.PI) / 180;
  const deltaPhi = ((lat2 - lat1) * Math.PI) / 180;
  const deltaLambda = ((lon2 - lon1) * Math.PI) / 180;

  const a =
    Math.sin(deltaPhi / 2) * Math.sin(deltaPhi / 2) +
    Math.cos(phi1) * Math.cos(phi2) * Math.sin(deltaLambda / 2) * Math.sin(deltaLambda / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return Math.round(R * c);
}

/**
 * Format distance value to human readable string.
 */
export function formatDistance(meters: number): string {
  if (meters < 1000) {
    return `${meters}m`;
  }
  return `${(meters / 1000).toFixed(1)}km`;
}

/**
 * Get color hex depending on YouBike availability.
 * Green: Rich (> 50% capacity or > 8 bikes)
 * Amber: Low (between 1 and 8 bikes)
 * Red: Empty/Critical (0 bikes or suspended)
 */
export function getBikesStatusColor(available: number, _capacity: number, serviceStatus: number = 1): string {
  if (serviceStatus === 0) {
    return "#EF4444"; // Red for suspended
  }
  if (available === 0) {
    return "#EF4444"; // Red
  }
  if (available <= 3) {
    return "#F59E0B"; // Amber for low
  }
  return "#10B981"; // Green for active
}

/**
 * Format bus ETA in seconds to minutes.
 */
export function formatEta(seconds: number | null | undefined, status: number = 0): string {
  if (status !== 0) {
    // Stop status: 1: no service, 2: not start, 3: end, 4: bypass
    switch (status) {
      case 1:
        return "尚未營運";
      case 2:
        return "交管不停";
      case 3:
        return "末班車已過";
      case 4:
        return "今日停駛";
      default:
        return "未發車";
    }
  }
  
  if (seconds === null || seconds === undefined || seconds < 0) {
    return "未發車";
  }
  
  if (seconds <= 60) {
    return "即將到站";
  }
  
  const minutes = Math.floor(seconds / 60);
  return `${minutes} 分鐘`;
}
