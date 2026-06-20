const L = {
  map: () => ({
    setView: jest.fn().mockReturnThis(),
    on: jest.fn().mockImplementation(function(event, cb) {
      if (event === 'click') {
        global.mapClickCallback = cb;
      }
      return this;
    }),
    remove: jest.fn(),
    getZoom: jest.fn().mockReturnValue(15)
  }),
  tileLayer: () => ({
    addTo: jest.fn()
  }),
  layerGroup: () => ({
    addTo: jest.fn().mockReturnThis(),
    clearLayers: jest.fn()
  }),
  divIcon: jest.fn(),
  marker: () => ({
    addTo: jest.fn().mockReturnThis(),
    bindPopup: jest.fn().mockReturnThis(),
    on: jest.fn().mockImplementation(function(event, cb) {
      if (event === 'click') {
        global.markerClickCallback = cb;
      }
      return this;
    }),
    setLatLng: jest.fn().mockReturnThis(),
    openPopup: jest.fn()
  })
};

module.exports = L;
