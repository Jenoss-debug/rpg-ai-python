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
const saveButton = document.getElementById("admin-map-save");
const saveStatus = document.getElementById("admin-map-save-status");
const MAP_API_URL = "/api/admin/cartes/terres_neutres";

if (canvas instanceof HTMLCanvasElement) {
    if (
        !(terrainTools instanceof HTMLElement)
        || !(terrainPicker instanceof HTMLElement)
        || !(variantTools instanceof HTMLElement)
        || !(variantHeading instanceof HTMLElement)
        || !(variantPicker instanceof HTMLElement)
        || !(saveButton instanceof HTMLButtonElement)
        || !(saveStatus instanceof HTMLElement)
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
    let grid;
    let mapReady = false;
    let saveInProgress = false;
    let changeVersion = 0;
    let savedVersion = null;
    let currentMode = "selection";
    let selectedTerrainCode = null;
    let selectedVariant = null;
    let leftShiftPressed = false;

    function setSaveStatus(message, state) {
        saveStatus.textContent = message;
        saveStatus.dataset.state = state;
    }

    function updateSaveButton() {
        saveButton.disabled = (
            !mapReady
            || saveInProgress
            || changeVersion === savedVersion
        );
    }

    function setEditorControlsEnabled(enabled) {
        for (const button of modeButtons) {
            button.disabled = !enabled;
        }
        for (const button of terrainPicker.querySelectorAll("button")) {
            button.disabled = !enabled;
        }
    }

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
        if (
            !mapReady
            || !cell
            || !selectedTerrainCode
            || selectedVariant === null
        ) {
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
            changeVersion += 1;
            updateSaveButton();
            setSaveStatus(
                saveInProgress
                    ? "Modifications apportées pendant la sauvegarde."
                    : "Modifications non enregistrées.",
                saveInProgress ? "pending" : ""
            );
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
        button.disabled = true;
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
    setEditorControlsEnabled(false);

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

    function createMapGrid(columns, rows) {
        return createHexGrid(canvas, {
            columns,
            rows,
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
    }

    coordinatesToggle?.addEventListener("change", () => {
        grid?.setCoordinatesVisible(coordinatesToggle.checked);
    });

    function decodeMapData(data) {
        if (
            !data
            || data.code !== "terres_neutres"
            || !Number.isInteger(data.largeur)
            || data.largeur < 1
            || !Number.isInteger(data.hauteur)
            || data.hauteur < 1
            || !Array.isArray(data.cases)
        ) {
            throw new Error("Les informations reçues pour la carte sont invalides.");
        }

        const cells = new Map();
        for (const cell of data.cases) {
            if (
                !cell
                || !Number.isInteger(cell.x)
                || !Number.isInteger(cell.y)
                || cell.x < 0
                || cell.x >= data.largeur
                || cell.y < 0
                || cell.y >= data.hauteur
            ) {
                throw new Error("La carte contient des coordonnées invalides.");
            }

            const colors = variantColors.get(cell.terrain_code);
            if (!colors?.has(cell.variant)) {
                throw new Error(
                    "La carte contient un terrain ou une variante inconnue."
                );
            }

            const key = getCellKey(cell);
            if (cells.has(key)) {
                throw new Error("La carte contient des coordonnées dupliquées.");
            }
            cells.set(key, {
                terrainCode: cell.terrain_code,
                variant: cell.variant
            });
        }
        return cells;
    }

    async function loadMap() {
        try {
            const response = await fetch(MAP_API_URL, {
                credentials: "same-origin",
                headers: { Accept: "application/json" }
            });
            if (!response.ok) {
                throw new Error(`Erreur HTTP ${response.status}.`);
            }

            const mapData = await response.json();
            const loadedCells = decodeMapData(mapData);
            paintedCells.clear();
            for (const [key, paint] of loadedCells) {
                paintedCells.set(key, paint);
            }

            grid = createMapGrid(mapData.largeur, mapData.hauteur);
            canvas.setAttribute(
                "aria-label",
                `Carte ${mapData.nom}, quadrillage hexagonal de `
                + `${mapData.largeur} colonnes et ${mapData.hauteur} lignes`
            );
            mapReady = true;
            savedVersion = changeVersion;
            setEditorControlsEnabled(true);
            updateSaveButton();
            setSaveStatus(
                "Carte chargée. Aucune modification à enregistrer.",
                "success"
            );
        } catch (error) {
            setEditorControlsEnabled(false);
            updateSaveButton();
            const detail = error instanceof Error
                ? error.message
                : "Erreur inconnue.";
            setSaveStatus(
                `Échec du chargement : ${detail} L'éditeur reste désactivé.`,
                "error"
            );
        }
    }

    saveButton.addEventListener("click", async () => {
        if (
            !mapReady
            || saveInProgress
            || changeVersion === savedVersion
        ) {
            return;
        }

        const saveVersion = changeVersion;
        const cases = Array.from(paintedCells, ([key, paint]) => {
            const [x, y] = key.split(";").map(Number);
            return {
                x,
                y,
                terrain_code: paint.terrainCode,
                variant: paint.variant
            };
        });

        saveInProgress = true;
        saveButton.textContent = "Enregistrement…";
        updateSaveButton();
        setSaveStatus("Enregistrement en cours…", "pending");

        try {
            const response = await fetch(MAP_API_URL, {
                method: "PUT",
                credentials: "same-origin",
                headers: {
                    Accept: "application/json",
                    "Content-Type": "application/json"
                },
                body: JSON.stringify(cases)
            });
            if (!response.ok) {
                throw new Error(`Erreur HTTP ${response.status}.`);
            }

            savedVersion = saveVersion;
            setSaveStatus(
                changeVersion === saveVersion
                    ? "Carte enregistrée."
                    : "Sauvegarde terminée; des modifications restent à enregistrer.",
                changeVersion === saveVersion ? "success" : "pending"
            );
        } catch (error) {
            const detail = error instanceof Error
                ? error.message
                : "Erreur inconnue.";
            setSaveStatus(
                `Échec de l'enregistrement : ${detail}`,
                "error"
            );
        } finally {
            saveInProgress = false;
            saveButton.textContent = "Enregistrer";
            updateSaveButton();
        }
    });

    loadMap();
}
