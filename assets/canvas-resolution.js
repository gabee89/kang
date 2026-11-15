/* Preserve 900x580 world coordinates while drawing at the display's pixel density. */
window.CanvasResolution = (() => {
 const worldWidth = 900;
 const worldHeight = 580;
 function prepare(canvas, context) {
  const bounds = canvas.getBoundingClientRect();
  if (!bounds.width || !bounds.height) return;
  const density = Math.min(2, window.devicePixelRatio || 1);
  const scale = Math.min(4, Math.max(1, bounds.width * density / worldWidth));
  const width = Math.round(worldWidth * scale);
  const height = Math.round(worldHeight * scale);
  if (canvas.width !== width || canvas.height !== height) {
   canvas.width = width;
   canvas.height = height;
  }
  context.setTransform(width / worldWidth, 0, 0, height / worldHeight, 0, 0);
  context.imageSmoothingEnabled = true;
  context.imageSmoothingQuality = 'high';
 }
 return {prepare};
})();
