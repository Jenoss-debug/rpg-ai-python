export function createSelectedCellPanel(panel) {
    if (!(panel instanceof HTMLElement)) {
        throw new TypeError("A selected-cell panel element is required.");
    }

    const selectedX = panel.querySelector("#selected-cell-x");
    const selectedY = panel.querySelector("#selected-cell-y");
    const selectedTerrain = panel.querySelector("#selected-cell-terrain");
    const selectedCost = panel.querySelector("#selected-cell-cost");
    const selectedVariant = panel.querySelector("#selected-cell-variant");
    if (!(selectedX instanceof HTMLOutputElement)
        || !(selectedY instanceof HTMLOutputElement)
        || !(selectedTerrain instanceof HTMLOutputElement)
        || !(selectedCost instanceof HTMLOutputElement)
        || !(selectedVariant instanceof HTMLOutputElement)) {
        throw new Error("The selected-cell panel is missing required outputs.");
    }

    return (cell, details = null) => {
        selectedX.textContent = cell ? String(cell.x) : "—";
        selectedY.textContent = cell ? String(cell.y) : "—";
        selectedTerrain.textContent = details?.terrainName ?? "Non défini";
        selectedCost.textContent = details?.entryCostLabel ?? "—";
        selectedVariant.textContent = details?.variant == null
            ? "—"
            : String(details.variant);
    };
}
