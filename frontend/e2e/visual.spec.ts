import { test, expect } from '@playwright/test';

test.describe('Hermes Go Web Dashboard Visual Regression Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Intercept standard startup areas list to avoid real API traffic
    await page.route('**/api/jptrain/areas', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'success',
          data: [{ code: '4', name: '関東' }]
        })
      });
    });

    // Mock initial YouBike station list load
    await page.route('**/api/ubike/nearby*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'success',
          data: [
            {
              uid: 'mock-ubike-1',
              name: 'YouBike台北101站',
              address: '信義路五段',
              capacity: 40,
              available_rent_bikes: 25,
              available_return_bikes: 15,
              service_status: 1,
              lat: 25.0338,
              lon: 121.5644
            }
          ]
        })
      });
    });

    // Navigate to local dashboard
    await page.goto('/');
    
    // Wait for the app to settle
    await page.waitForSelector('.sidebar');
  });

  test('visual comparison: YouBike main view', async ({ page }) => {
    // Wait for YouBike list item to be rendered
    await page.waitForSelector('text=YouBike台北101站');

    // Assert full dashboard screenshot with Leaflet map masked
    await expect(page).toHaveScreenshot('youbike-main-view.png', {
      mask: [page.locator('#map')]
    });
  });

  test('visual comparison: Bus nearby view', async ({ page }) => {
    // Intercept Bus nearby stop list
    await page.route('**/api/twbus/nearby*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'success',
          data: [
            {
              uid: 'mock-bus-stop-1',
              name: '捷運台北101/世貿站',
              address: '信義路五段',
              lat: 25.0338,
              lon: 121.5644,
              etas: [
                { route_name: '信義幹線', estimate_time: 120, status: 0 },
                { route_name: '281', estimate_time: 30, status: 0 }
              ]
            }
          ]
        })
      });
    });

    // Switch to Bus tab
    await page.click('text=台灣公車 ETA');
    await page.waitForSelector('text=附近的公車站牌 (即時到站)');
    await page.waitForSelector('text=捷運台北101/世貿站');

    await expect(page).toHaveScreenshot('bus-nearby-view.png', {
      mask: [page.locator('#map')]
    });
  });

  test('visual comparison: Bus route planner results', async ({ page }) => {
    // Intercept Bus route results
    await page.route('**/api/twbus/route*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'success',
          dest_coords: { lat: 25.0338, lon: 121.5644 },
          data: [
            {
              route_name: '信義幹線',
              start_stop: '台北車站',
              dest_stop: '捷運台北101/世貿站',
              stops_count: 8,
              eta: 480
            }
          ]
        })
      });
    });

    // Switch to Bus tab
    await page.click('text=台灣公車 ETA');
    await page.waitForSelector('text=附近的公車站牌 (即時到站)');
    
    // Switch to route planning mode
    await page.click('text=直達路線規劃');
    await page.waitForSelector('text=直達公車路網規劃');

    // Fill destination and click search
    const destInput = page.locator('.route-planner-input');
    await destInput.fill('Taipei 101');
    await page.click('text=開始規劃');

    await page.waitForSelector('text=公車路線 信義幹線');

    await expect(page).toHaveScreenshot('bus-route-plan-view.png', {
      mask: [page.locator('#map')]
    });
  });

  test('visual comparison: Places view', async ({ page }) => {
    // Intercept Places results
    await page.route('**/api/places/nearby*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'success',
          data: [
            {
              uid: 'mock-place-1',
              name: '鼎泰豐 101店',
              vicinity: '台北101購物中心B1',
              rating: 4.5,
              user_ratings_total: 8500,
              open_now: true,
              lat: 25.0338,
              lon: 121.5644
            }
          ]
        })
      });
    });

    // Switch to Places tab
    await page.click('text=景點美食');
    await page.waitForSelector('text=周邊美食與觀光景點');
    await page.waitForSelector('text=鼎泰豐 101店');

    await expect(page).toHaveScreenshot('places-view.png', {
      mask: [page.locator('#map')]
    });
  });

  test('visual comparison: Japan Train status warning feed', async ({ page }) => {
    // Intercept Japan Train regional warning list
    await page.route('**/api/jptrain/status*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'success',
          data: [
            {
              company: 'JR東日本',
              name: '山手線',
              status: '平常運轉',
              status_type: 'normal',
              detail_info: '',
              update_time: '10:00'
            },
            {
              company: '東京地鐵',
              name: '丸之內線',
              status: '列車延遲',
              status_type: 'delay',
              detail_info: '因號誌故障，部分列車延遲約10分鐘。',
              update_time: '10:05'
            }
          ]
        })
      });
    });

    // Switch to Japan Train tab
    await page.click('text=日本鐵道');
    await page.waitForSelector('text=運行警報概況');

    // Select region '関東'
    const select = page.locator('select');
    await select.selectOption('4');

    await page.waitForSelector('text=丸之內線');

    await expect(page).toHaveScreenshot('jp-train-status-view.png', {
      mask: [page.locator('#map')]
    });
  });

  test('visual comparison: Japan Train route planner results', async ({ page }) => {
    // Intercept Japan Train routes planning API
    await page.route('**/api/jptrain/route*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          status: 'success',
          data: [
            {
              time_required: '15',
              fare: '200',
              transfer_count: 0,
              steps: [
                { station_name: '東京', departure_time: '10:00', line_name: '中央線快速' },
                { station_name: '新宿', departure_time: '10:15', line_name: '' }
              ]
            }
          ]
        })
      });
    });

    // Switch to Japan Train tab
    await page.click('text=日本鐵道');
    await page.waitForSelector('text=運行警報概況');

    // Click submode chip
    await page.click('text=鐵道轉乘規劃');
    await page.waitForSelector('text=日本起訖鐵道規劃');

    // Fill start and end stations and click search
    const fromInput = page.locator('input[placeholder="如：東京"]');
    const toInput = page.locator('input[placeholder="如：新宿"]');
    await fromInput.fill('東京');
    await toInput.fill('新宿');
    await page.click('text=開始規劃');

    await page.waitForSelector('text=方案 1');

    await expect(page).toHaveScreenshot('jp-train-route-view.png', {
      mask: [page.locator('#map')]
    });
  });
});
