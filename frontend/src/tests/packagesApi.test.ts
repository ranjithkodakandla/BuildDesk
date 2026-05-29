import { describe, it, expect, vi } from 'vitest';
import { ProjectPackageStatus } from '../types/packages';
import { packagesApi } from '../api/packages';
import client from '../api/client';

// Mock the axios client
vi.mock('../api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    defaults: { baseURL: 'http://localhost:8000/api/v1' }
  }
}));

describe('Packages API', () => {
  it('should generate a package', async () => {
    const mockResponse = {
      package_id: '123',
      project_id: '456',
      version: '1.0',
      status: ProjectPackageStatus.READY,
      page_count: 5
    };
    
    (client.post as any).mockResolvedValueOnce({ data: mockResponse });
    
    const result = await packagesApi.generatePackage('456', { version: '1.0' });
    expect(client.post).toHaveBeenCalledWith('/projects/456/package/generate', { version: '1.0' });
    expect(result).toEqual(mockResponse);
  });

  it('should format PDF URL correctly', () => {
    const url = packagesApi.getPdfUrl('456');
    expect(url).toBe('http://localhost:8000/api/v1/projects/456/package/pdf');
  });
});
