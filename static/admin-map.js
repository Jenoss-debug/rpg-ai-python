import { createHexGrid } from "./hex-grid.js";
import { createSelectedCellPanel } from "./selected-cell-panel.js";
import {
    getTerrainByCode,
    getTerrainVariants,
    TERRAIN_CATALOG
} from "./terrain-catalog.js";

const canvas = document.getElementById("admin-map-grid");
const coordinatesToggle = document.getElementById("admin-map-show-coordinates");
const overlays = document.querySelector(".canvas-overlays");
const terrainTools = document.getElementById("terrain-tools");
const terrainPicker = document.getElementById("terrain-picker");
const variantTools = document.getElementById("variant-tools");
const variantHeading = document.getElementById("variant-heading");
const variantPicker = document.getElementById("variant-picker");
const modeButtons = Array.from(document.querySelectorAll("[data-map-mode]"));

if (canvas instanceof HTMLCanvasElement) {
    if (
        !(terrainTools instanceof HTMLElement)
        || !(terrainPicker instanceof HTMLElement)
        || !(variantTools instanceof HTMLElement)
        || !(variantHeading instanceof HTMLElement)
        || !(variantPicker instanceof HTMLElement)
        || modeButtons.length !== 2
    ) {
        throw new Error("The map editor controls are missing from the page.");
    }

    const updateSelectedCellPanel = createSelectedCellPanel(
        document.querySelector(".map-cell-details")
    );
    const paintedCells = new Map();
    const variantColors = new Map(
        TERRAIN_CATALOG.map((terrain) => [
            terrain.code,
            new Map(
                getTerrainVariants(terrain.code).map((variant) => [
                    variant.number,
                    variant.color
                ])
            )
        ])
    );
    let currentMode = "selection";
    let selectedTerrainCode = null;
    let selectedVariant = null;
    let leftShiftPressed = false;

    function getCellKey(cell) {
        return `${cell.x};${cell.y}`;
    }

    function getCellDetails(cell) {
        if (!cell) {
            return null;
        }

        const paint = paintedCells.get(getCellKey(cell));
        if (!paint) {
            return null;
        }

        const terrain = getTerrainByCode(paint.terrainCode);
        return {
            terrainName: terrain.name,
            entryCostLabel: `${terrain.entryCost.toLocaleString("fr-FR")} PM`,
            variant: paint.variant
        };
    }

    function paintCell(cell, event, grid) {
        if (!cell || !selectedTerrainCode || selectedVariant === null) {
            return;
        }

        const key = getCellKey(cell);
        const previousPaint = paintedCells.get(key);
        const paintChanged = (
            previousPaint?.terrainCode !== selectedTerrainCode
            || previousPaint?.variant !== selectedVariant
        );
        if (paintChanged) {
            paintedCells.set(key, {
                terrainCode: selectedTerrainCode,
                variant: selectedVariant
            });
        }

        const wasSelected = (
            grid.getSelectedCell()?.x === cell.x
            && grid.getSelectedCell()?.y === cell.y
        );
        grid.setSelectedCell(cell, event);

        if (paintChanged && wasSelected) {
            updateSelectedCellPanel(cell, getCellDetails(cell));
            grid.redraw();
        }
    }

    function setMode(mode) {
        currentMode = mode;
        terrainTools.hidden = mode !== "edition";
        for (const button of modeButtons) {
            button.setAttribute(
                "aria-pressed",
                String(button.dataset.mapMode === mode)
            );
        }
    }

    function selectVariant(number) {
        selectedVariant = number;
        for (const button of variantPicker.querySelectorAll("[data-variant]")) {
            button.setAttribute(
                "aria-pressed",
                String(Number(button.dataset.variant) === selectedVariant)
            );
        }
    }

    function selectTerrain(code) {
        const terrain = getTerrainByCode(code);
        selectedTerrainCode = terrain.code;
        variantHeading.textContent = `Variantes graphiques — ${terrain.name}`;
        for (const button of terrainPicker.querySelectorAll("[data-terrain-code]")) {
            button.setAttribute(
                "aria-pressed",
                String(button.dataset.terrainCode === selectedTerrainCode)
            );
        }

        variantPicker.replaceChildren();
        for (const variant of getTerrainVariants(terrain.code)) {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "terrain-variant";
            button.dataset.variant = String(variant.number);
            button.setAttribute("aria-label", `Variante ${variant.number}`);
            button.setAttribute("aria-pressed", "false");

            const swatch = document.createElement("span");
            swatch.className = "terrain-swatch terrain-variant-swatch";
            swatch.style.backgroundColor = variant.color;
            swatch.setAttribute("aria-hidden", "true");

            const number = document.createElement("span");
            number.textContent = String(variant.number);

            button.append(swatch, number);
            button.addEventListener("click", () => {
                selectVariant(variant.number);
            });
            variantPicker.append(button);
        }

        variantTools.hidden = false;
        selectVariant(3);
    }

    for (const terrain of TERRAIN_CATALOG) {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "terrain-choice";
        button.dataset.terrainCode = terrain.code;
        button.setAttribute("aria-pressed", "false");

        const swatch = document.createElement("span");
        swatch.className = "terrain-swatch";
        swatch.style.backgroundColor = terrain.color;
        swatch.setAttribute("aria-hidden", "true");

        const name = document.createElement("span");
        name.className = "terrain-choice-name";
        name.textContent = terrain.name;

        const cost = document.createElement("small");
        cost.className = "terrain-choice-cost";
        cost.textContent = `${terrain.entryCost.toLocaleString("fr-FR")} PM`;

        button.append(swatch, name, cost);
        button.addEventListener("click", () => {
            selectTerrain(terrain.code);
        });
        terrainPicker.append(button);
    }

    for (const button of modeButtons) {
        button.addEventListener("click", () => {
            setMode(button.dataset.mapMode);
        });
    }
    setMode("selection");

    window.addEventListener("keydown", (event) => {
        if (event.code === "ShiftLeft") {
            leftShiftPressed = true;
        }
    });
    window.addEventListener("keyup", (event) => {
        if (event.code === "ShiftLeft") {
            leftShiftPressed = false;
        }
    });
    window.addEventListener("blur", () => {
        leftShiftPressed = false;
    });

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
        interactionMode: {
            getPointerBehavior() {
                return currentMode === "edition" && leftShiftPressed
                    ? "custom"
                    : "pan";
            },
            onCellClick(cell, event, api) {
                if (currentMode === "edition" && selectedTerrainCode) {
                    paintCell(cell, event, api);
                } else {
                    api.setSelectedCell(cell, event);
                }
            },
            onPointerDown(cell, event, api) {
                paintCell(cell, event, api);
            },
            onPointerMove(cell, event, api) {
                paintCell(cell, event, api);
            },
            onPointerUp(cell, event, api) {
                if (leftShiftPressed) {
                    paintCell(cell, event, api);
                }
            }
        },
        onCellRender(context, cell) {
            const paint = paintedCells.get(getCellKey(cell));
            if (!paint) {
                return;
            }

            context.fillStyle = variantColors.get(paint.terrainCode).get(
                paint.variant
            );
            context.fill();
        },
        onSelectionChange(cell) {
            updateSelectedCellPanel(cell, getCellDetails(cell));
        }
    });

    coordinatesToggle?.addEventListener("change", () => {
        grid.setCoordinatesVisible(coordinatesToggle.checked);
    });
}
