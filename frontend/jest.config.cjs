module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'jsdom',
  setupFilesAfterEnv: ['<rootDir>/jest.setup.js'],
  testPathIgnorePatterns: ['/node_modules/', '/e2e/'],
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/main.tsx',
    '!src/vite-env.d.ts',
    '!src/tests/**/*'
  ],
  moduleNameMapper: {
    // Mock CSS/static assets
    '\\.(css|less|sass|scss|png|jpg|ttf|woff|woff2)$': '<rootDir>/src/tests/mocks/fileMock.js',
    // Mock Leaflet.js
    '^leaflet$': '<rootDir>/src/tests/mocks/leafletMock.js'
  },
  transform: {
    '^.+\\.tsx?$': ['ts-jest', { tsconfig: 'tsconfig.jest.json' }]
  }
};
