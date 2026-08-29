// Shared vocabulary for the catalogue files.
//
// A module definition is data. Everything a module needs to exist — its form,
// how it resizes, what it snaps to, and what appears on it as it grows — is
// declared here and interpreted by ModuleInstance. No module has code.
export const AXIS = { x: 0, y: 1, z: 2 };

/**
 * The shelf the UI groups by. Order is the order of the tabs, and it follows
 * how a pharmacy is actually laid out: what the pharmacist works behind, what
 * the customer walks through, then the rooms off it.
 */
export const CATEGORIES = [
  { id: 'dispensary', label: 'Dispensary', blurb: 'Behind the counter' },
  { id: 'retail', label: 'Retail floor', blurb: 'Customer side' },
  { id: 'consultation', label: 'Consultation', blurb: 'Private space' },
  { id: 'staff', label: 'Staff', blurb: 'Back of house' },
  { id: 'signage', label: 'Signage', blurb: 'Walls and fascia' },
];

export const FIXED = { mode: 'fixed' };

/** A floor-standing module. */
export const onFloor = [{ tag: 'floor', normal: [0, -1, 0] }];

/** Sits on a worktop or a shelf rather than the floor. */
export const onSurface = [
  { tag: 'counter_surface', normal: [0, -1, 0] },
  { tag: 'shelf_surface', normal: [0, -1, 0] },
  { tag: 'floor', normal: [0, -1, 0] },
];
