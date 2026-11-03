import "@testing-library/jest-dom";

afterEach(() => {
  sessionStorage.clear();
  jest.restoreAllMocks();
});
