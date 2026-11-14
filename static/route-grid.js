import { createHexGrid } from "./hex-grid.js";
import { createSelectedCellPanel } from "./selected-cell-panel.js";
import {
    getTerrainByCode,
    getTerrainVariants,
    TERRAIN_CATALOG
} from "./terrain-catalog.js";

const canvas = document.getElementById("route-grid");
const coordinatesToggle = document.getElementById("show-coordinates");
const overlays = document.querySelector(".canvas-overlays");
const loadStatus = document.getElementById("route-map-load-status");
const MAP_API_URL = "/api/admin/cartes/terres_neutres";

if (canvas instanceof HTMLCanvasElement) {
    if (!(loadStatus instanceof HTMLElement)) {
        throw new Error("The route map status element is missing from the page.");
    }

    const updateSelectedCellPanel = createSelectedCellPanel(
        document.querySelector(".map-cell-details")
    );
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

        const paintedCells = new Map();
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

            const variants = variantColors.get(cell.terrain_code);
            if (!variants?.has(cell.variant)) {
                throw new Error(
                    "La carte contient un terrain ou une variante inconnue."
                );
            }

            const key = `${cell.x};${cell.y}`;
            if (paintedCells.has(key)) {
                throw new Error("La carte contient des coordonnées dupliquées.");
            }
            paintedCells.set(key, {
                terrainCode: cell.terrain_code,
                variant: cell.variant
            });
        }
        return paintedCells;
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
            const paintedCells = decodeMapData(mapData);
            function getCellDetails(cell) {
                if (!cell) {
                    return null;
                }

                const paint = paintedCells.get(`${cell.x};${cell.y}`);
                if (!paint) {
                    return null;
                }

                const terrain = getTerrainByCode(paint.terrainCode);
                return {
                    terrainName: terrain.name,
                    entryCostLabel: (
                        `${terrain.entryCost.toLocaleString("fr-FR")} PM`
                    ),
                    variant: paint.variant
                };
            }

            const grid = createHexGrid(canvas, {
                columns: mapData.largeur,
                rows: mapData.hauteur,
                hexRadius: 42,
                minZoom: 0.1,
                maxZoom: 3,
                recenterStartZoom: 0.6,
                coordinateZoomThreshold: 0.75,
                interactionBlockers: overlays ? [overlays] : [],
                showCoordinates: coordinatesToggle?.checked ?? false,
                onCellRender(context, cell) {
                    const paint = paintedCells.get(`${cell.x};${cell.y}`);
                    if (!paint) {
                        return;
                    }

                    context.fillStyle = variantColors.get(
                        paint.terrainCode
                    ).get(paint.variant);
                    context.fill();
                },
                onSelectionChange(cell) {
                    updateSelectedCellPanel(cell, getCellDetails(cell));
                }
            });

            coordinatesToggle?.addEventListener("change", () => {
                grid.setCoordinatesVisible(coordinatesToggle.checked);
            });
            canvas.setAttribute(
                "aria-label",
                `Carte ${mapData.nom}, quadrillage hexagonal de `
                + `${mapData.largeur} colonnes et ${mapData.hauteur} lignes`
            );
            loadStatus.textContent = `${mapData.nom} chargée.`;
            loadStatus.dataset.state = "success";
        } catch (error) {
            const detail = error instanceof Error
                ? error.message
                : "Erreur inconnue.";
            loadStatus.textContent = (
                `Impossible de charger Terres Neutres : ${detail}`
            );
            loadStatus.dataset.state = "error";
        }
    }

    loadMap();
}
