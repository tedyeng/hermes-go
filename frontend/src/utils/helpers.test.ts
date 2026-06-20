import { calculateDistance, formatDistance, getBikesStatusColor, formatEta } from './helpers';

describe('Helpers Unit Tests', () => {
  describe('calculateDistance', () => {
    it('should calculate the distance between two coordinates correctly', () => {
      // Taipei 101 to Taipei City Hall is around 600m
      const lat1 = 25.033671;
      const lon1 = 121.564427;
      const lat2 = 25.03746;
      const lon2 = 121.563489;
      
      const distance = calculateDistance(lat1, lon1, lat2, lon2);
      expect(distance).toBeGreaterThan(300);
      expect(distance).toBeLessThan(700);
    });

    it('should return 0 for identical coordinates', () => {
      const lat = 25.033671;
      const lon = 121.564427;
      expect(calculateDistance(lat, lon, lat, lon)).toBe(0);
    });
  });

  describe('formatDistance', () => {
    it('should format distance under 1000m to meters', () => {
      expect(formatDistance(450)).toBe('450m');
      expect(formatDistance(999)).toBe('999m');
    });

    it('should format distance over 1000m to kilometers', () => {
      expect(formatDistance(1000)).toBe('1.0km');
      expect(formatDistance(2530)).toBe('2.5km');
    });
  });

  describe('getBikesStatusColor', () => {
    it('should return red (#EF4444) if service is suspended', () => {
      expect(getBikesStatusColor(15, 30, 0)).toBe('#EF4444');
    });

    it('should return red (#EF4444) if available bikes are 0', () => {
      expect(getBikesStatusColor(0, 30, 1)).toBe('#EF4444');
    });

    it('should return amber (#F59E0B) if available bikes are <= 3', () => {
      expect(getBikesStatusColor(1, 30, 1)).toBe('#F59E0B');
      expect(getBikesStatusColor(3, 30, 1)).toBe('#F59E0B');
    });

    it('should return green (#10B981) if available bikes are > 3', () => {
      expect(getBikesStatusColor(4, 30, 1)).toBe('#10B981');
      expect(getBikesStatusColor(12, 30)).toBe('#10B981'); // tests default serviceStatus = 1
    });
  });

  describe('formatEta', () => {
    it('should format normal ETA in seconds to minutes', () => {
      expect(formatEta(120, 0)).toBe('2 分鐘');
      expect(formatEta(350, 0)).toBe('5 分鐘');
    });

    it('should show "即將到站" if ETA <= 60 seconds', () => {
      expect(formatEta(30, 0)).toBe('即將到站');
      expect(formatEta(60, 0)).toBe('即將到站');
    });

    it('should return "未發車" for negative, null, or undefined seconds', () => {
      expect(formatEta(null, 0)).toBe('未發車');
      expect(formatEta(undefined, 0)).toBe('未發車');
      expect(formatEta(-5, 0)).toBe('未發車');
    });

    it('should handle alternative stop statuses', () => {
      // 1: no service, 2: not start, 3: end, 4: bypass, 5: default/others
      expect(formatEta(100, 1)).toBe('尚未營運');
      expect(formatEta(100, 2)).toBe('交管不停');
      expect(formatEta(100, 3)).toBe('末班車已過');
      expect(formatEta(100, 4)).toBe('今日停駛');
      expect(formatEta(100, 5)).toBe('未發車');
    });
  });
});
