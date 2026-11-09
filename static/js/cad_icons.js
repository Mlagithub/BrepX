/**
 * Precision vector icon registry for all 31 BrepX CAD modeling operators.
 * Implements standard engineering iconography for geometric modeling and CFD tools.
 */

export const CAD_ICONS = {
  // 3D 基础图元
  box: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" y1="22.08" x2="12" y2="12"/></svg>`,
  cylinder: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.66 3.58 3 8 3s8-1.34 8-3V5"/></svg>`,
  sphere: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="9" ry="3.5"/></svg>`,
  cone: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="19" rx="8" ry="3"/><path d="M4 19L12 3l8 16"/></svg>`,
  torus: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="12" rx="9" ry="5"/><ellipse cx="12" cy="12" rx="4" ry="2"/></svg>`,
  wedge: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 19h18L17 5H7L3 19z"/><line x1="7" y1="5" x2="7" y2="19"/></svg>`,

  // 特征成型与加工
  extrude: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 15l8-4 8 4-8 4-8-4z"/><path d="M4 15V9l8-4 8 4v6"/><path d="M12 5v10"/><path d="M9 7l3-3 3 3"/></svg>`,
  hole: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5"/></svg>`,
  fillet: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 20V12a8 8 0 0 1 8-8h8"/><line x1="4" y1="20" x2="20" y2="20"/></svg>`,
  chamfer: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 20V14L14 4h6"/><line x1="4" y1="20" x2="20" y2="20"/></svg>`,
  shell: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><rect x="7" y="7" width="10" height="10" rx="1" stroke-dasharray="2 2"/></svg>`,

  // 高阶曲面造型
  revolve: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="5" y1="2" x2="5" y2="22"/><path d="M5 6h7a5 5 0 0 1 5 5v2a5 5 0 0 1-5 5H5"/><polyline points="15 8 18 5 15 2"/></svg>`,
  sweep: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 18c4-1 6-7 10-7s5 5 7 2"/><ellipse cx="4" cy="18" rx="2" ry="4"/><ellipse cx="21" cy="13" rx="2" ry="4"/></svg>`,
  loft: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><ellipse cx="12" cy="5" rx="7" ry="2.5"/><ellipse cx="12" cy="19" rx="9" ry="3.5"/><path d="M5 5c0 6-2 8-2 14M19 5c0 6 2 8 2 14"/></svg>`,
  draft: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="20" x2="21" y2="20"/><path d="M7 20L10 4h7l-3 16"/></svg>`,
  offset: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="14" height="14" rx="2"/><path d="M7 21h12a2 2 0 0 0 2-2V7"/></svg>`,

  // 空间变换与布尔阵列
  boolean_cut: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="12" height="12" rx="2"/><circle cx="15" cy="15" r="6" stroke-dasharray="2 2"/></svg>`,
  boolean_join: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="12" r="6"/><circle cx="15" cy="12" r="6"/></svg>`,
  boolean_intersect: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="12" r="6" stroke-dasharray="2 2"/><circle cx="15" cy="12" r="6" stroke-dasharray="2 2"/><path d="M12 7a6 6 0 0 1 0 10 6 6 0 0 1 0-10z" fill="currentColor" fill-opacity="0.2"/></svg>`,
  mirror: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="2" x2="12" y2="22" stroke-dasharray="2 2"/><path d="M8 6L3 18h5V6z"/><path d="M16 6l5 12h-5V6z"/></svg>`,
  polar_array: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><circle cx="12" cy="4" r="1.5"/><circle cx="20" cy="12" r="1.5"/><circle cx="12" cy="20" r="1.5"/><circle cx="4" cy="12" r="1.5"/></svg>`,
  grid_array: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>`,
  translate: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="5 9 2 12 5 15"/><polyline points="9 5 12 2 15 5"/><polyline points="15 19 12 22 9 19"/><polyline points="19 9 22 12 19 15"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="12" y1="2" x2="12" y2="22"/></svg>`,
  rotate: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6"/><path d="M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>`,
  scale: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 3 21 3 21 9"/><polyline points="9 21 3 21 3 15"/><line x1="21" y1="3" x2="14" y2="10"/><line x1="3" y1="21" x2="10" y2="14"/></svg>`,
  section: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="12" x2="21" y2="12" stroke-dasharray="3 3"/><polyline points="16 7 21 12 16 17"/></svg>`,
  split: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 14l6-8H4v8zM20 10l-6 8h6v-8z"/><line x1="2" y1="22" x2="22" y2="2"/></svg>`,

  // 流体机械核心
  blade_runner: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="4"/><path d="M12 8c2-3 5-4 8-4-1 3-2 6-4 8M16 12c3 2 4 5 4 8-3-1-6-2-8-4M12 16c-2 3-5 4-8 4 1-3 2-6 4-8M8 12c-3-2-4-5-4-8 3 1 6 2 8 4"/></svg>`,
  volute: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 12m-3 0a3 3 0 1 0 6 0a3 3 0 1 0 -6 0"/><path d="M12 9c3 0 6 2 6 5s-3 6-7 6-8-4-8-9 4-9 10-9h8v4"/></svg>`,

  // CFD 几何清洗与修面
  cavity_extraction: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M8 8h8v8H8z" fill="currentColor" fill-opacity="0.25"/></svg>`,
  remove_fillets: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 20V12a8 8 0 0 1 8-8h8"/><line x1="6" y1="6" x2="18" y2="18" stroke="#dc2626"/></svg>`,
  remove_faces: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="7"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07" stroke="#dc2626"/></svg>`,
  heal: `<svg class="tool-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18"/><path d="M8 4l12 12-3 3-12-12 3-3z"/><line x1="2" y1="22" x2="6" y2="18"/></svg>`,
};
