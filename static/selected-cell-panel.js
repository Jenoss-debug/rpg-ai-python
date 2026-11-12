export function createSelectedCellPanel(panel) {
    if (!(panel instanceof HTMLElement)) {
        throw new TypeError("A selected-cell panel element is required.");
    }

    const selectedX = panel.querySelector("#selected-cell-x");
    const selectedY = panel.querySelector("#selected-cell-y");
    if (!(selectedX instanceof HTMLOutputElement)
        || !(selectedY instanceof HTMLOutputElement)) {
        throw new Error("The selected-cell panel is missing coordinate outputs.");
    }

    return (cell) => {
        selectedX.textContent = cell ? String(cell.x) : "—";
        selectedY.textContent = cell ? String(cell.y) : "—";
    };
}
