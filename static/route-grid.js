import { createHexGrid } from "./hex-grid.js";
import { createSelectedCellPanel } from "./selected-cell-panel.js";

const canvas = document.getElementById("route-grid");
const coordinatesToggle = document.getElementById("show-coordinates");
const overlays = document.querySelector(".canvas-overlays");

if (canvas instanceof HTMLCanvasElement) {
    const updateSelectedCellPanel = createSelectedCellPanel(
        document.querySelector(".map-cell-details")
    );
    const grid = createHexGrid(canvas, {
        columns: 100,
        rows: 100,
        hexRadius: 42,
        minZoom: 0.1,
        maxZoom: 3,
        recenterStartZoom: 0.6,
        coordinateZoomThreshold: 0.75,
        interactionBlockers: overlays ? [overlays] : [],
        showCoordinates: coordinatesToggle?.checked ?? false,
        onSelectionChange(cell) {
            updateSelectedCellPanel(cell);
        }
    });

    coordinatesToggle?.addEventListener("change", () => {
        grid.setCoordinatesVisible(coordinatesToggle.checked);
    });
}
