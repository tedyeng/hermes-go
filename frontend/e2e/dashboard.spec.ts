import { test, expect } from '@playwright/test';

test.describe('Hermes Go Web Dashboard E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to local dashboard
    await page.goto('/');
  });

  test('should display main brand title and load map viewport', async ({ page }) => {
    // Assert heading text
    await expect(page.locator('.brand-title')).toHaveText('Hermes Go Dashboard');
    
    // Assert Leaflet map viewport container is rendered
    await expect(page.locator('#map')).toBeVisible();
  });

  test('should support switching tabs and rendering corresponding sidebar headers', async ({ page }) => {
    // 1. Check default YouBike mode
    await expect(page.locator('text=附近的 YouBike 站點')).toBeVisible();
    
    // 2. Click Bus tab
    await page.click('text=台灣公車 ETA');
    await expect(page.locator('text=附近的公車站牌')).toBeVisible();
    
    // 3. Click Places tab
    await page.click('text=景點美食');
    await expect(page.locator('text=周邊美食與觀光景點')).toBeVisible();
    
    // 4. Click Japan Train tab
    await page.click('text=日本鐵道');
    await expect(page.locator('text=選擇日本區域')).toBeVisible();
  });

  test('should allow entering text in search bar and submitting form', async ({ page }) => {
    const searchInput = page.locator('.search-input');
    await searchInput.fill('Taipei 101');
    
    // Intercept parse-gps API request to mock successful coordinate response
    await page.route('**/api/utils/parse-gps', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'success', lat: 25.0338, lon: 121.5644 })
      });
    });

    // Mock YouBike endpoint that gets triggered after coordinates update
    await page.route('**/api/ubike/nearby*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'success',
          data: [
            {
              uid: 'mock-station-1',
              name: 'YouBike台北101站',
              address: '信義路五段',
              capacity: 40,
              available_rent_bikes: 25,
              available_return_bikes: 15,
              service_status: 1
            }
          ]
        })
      });
    });

    // Submit search form
    await page.click('button[type="submit"]');

    // Confirm that the mocked YouBike station card is rendered in the sidebar
    await expect(page.locator('text=YouBike台北101站')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('text=可借車輛')).toBeVisible();
  });
});
