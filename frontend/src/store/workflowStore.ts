import { create } from 'zustand';
import { assembliesApi } from '../api/assemblies';
import { projectsApi } from '../api/projects';
import { packagesApi } from '../api/packages';
import { ProjectPackageStatus } from '../types/packages';

export type WorkflowPackageStatus = 'none' | 'generating' | 'ready' | 'failed';

interface WorkflowState {
  projectId: string | null;
  unitCount: number;
  assemblyCount: number;
  drawingsReadyCount: number;
  packageStatus: WorkflowPackageStatus;
  loading: boolean;
  refresh: (projectId: string) => Promise<void>;
}

export const useWorkflowStore = create<WorkflowState>((set) => ({
  projectId: null,
  unitCount: 0,
  assemblyCount: 0,
  drawingsReadyCount: 0,
  packageStatus: 'none',
  loading: false,

  refresh: async (projectId: string) => {
    set({ loading: true, projectId });
    try {
      const [unitsResult, assembliesResult, pkgResult] = await Promise.allSettled([
        projectsApi.listUnits(projectId),
        assembliesApi.listAssemblies(projectId),
        packagesApi.getPackageStatus(projectId),
      ]);

      const unitCount =
        unitsResult.status === 'fulfilled' ? unitsResult.value.length : 0;
      const asmList =
        assembliesResult.status === 'fulfilled' ? assembliesResult.value : [];
      const assemblyCount      = asmList.length;
      const drawingsReadyCount = asmList.filter(a => (a.parts?.length ?? 0) > 0).length;

      let packageStatus: WorkflowPackageStatus = 'none';
      if (pkgResult.status === 'fulfilled' && pkgResult.value) {
        const ps = pkgResult.value.status;
        if (ps === ProjectPackageStatus.READY)             packageStatus = 'ready';
        else if (ps === ProjectPackageStatus.GENERATING)   packageStatus = 'generating';
        else if (ps === ProjectPackageStatus.GENERATION_FAILED) packageStatus = 'failed';
      }

      set({ unitCount, assemblyCount, drawingsReadyCount, packageStatus, loading: false });
    } catch {
      set({ loading: false });
    }
  },
}));
