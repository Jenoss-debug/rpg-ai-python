(() => {
    const canvas = document.getElementById("route-grid");
    const coordinatesToggle = document.getElementById("show-coordinates");
    const selectionOutput = document.getElementById("selected-coordinate");
    if (!(canvas instanceof HTMLCanvasElement)) {
        return;
    }

    const context = canvas.getContext("2d");
    if (!context) {
        return;
    }

    const MAP_SIZE = 100;
    const HEX_RADIUS = 42;
    const HEX_WIDTH = HEX_RADIUS * 2;
    const HEX_HEIGHT = Math.sqrt(3) * HEX_RADIUS;
    const COLUMN_STEP = HEX_WIDTH * 0.75;
    const ORIGIN_X = HEX_RADIUS;
    const ORIGIN_Y = HEX_HEIGHT / 2;
    const MAP_LEFT = ORIGIN_X - HEX_RADIUS;
    const MAP_RIGHT = ORIGIN_X + (MAP_SIZE - 1) * COLUMN_STEP + HEX_RADIUS;
    const MAP_TOP = ORIGIN_Y - HEX_HEIGHT / 2;
    const MAP_BOTTOM = ORIGIN_Y
        + (MAP_SIZE - 1) * HEX_HEIGHT
        + ((MAP_SIZE - 1) % 2) * HEX_HEIGHT * 0.5
        + HEX_HEIGHT / 2;
    // Adjust this value to set the lowest zoom level.
    const MIN_ZOOM = 0.1;
    const ZOOM_MAX = 3;
    const ZOOM_FACTOR = 1.15;
    const RECENTER_START_ZOOM = 0.6;
    const COORDINATE_ZOOM_THRESHOLD = 0.75;
    const DRAG_THRESHOLD = 4;

    let width = 0;
    let height = 0;
    let pixelRatio = 1;
    let zoom = 1;
    let offsetX = 0;
    let offsetY = 0;
    let hoveredCell = null;
    let selectedCell = null;
    let activePointer = null;
    let coordinatesEnabled = false;

    function sameCell(first, second) {
        return first?.x === second?.x && first?.y === second?.y;
    }

    function columnOffsetY(x) {
        return (x % 2) * HEX_HEIGHT * 0.5;
    }

    function cellCenter(x, y) {
        return {
            x: ORIGIN_X + x * COLUMN_STEP,
            y: ORIGIN_Y + y * HEX_HEIGHT + columnOffsetY(x)
        };
    }

    function constrainAxis(offset, viewSize, mapStart, mapEnd) {
        const scaledMapSize = (mapEnd - mapStart) * zoom;
        if (scaledMapSize <= viewSize) {
            return (viewSize - scaledMapSize) / 2 - mapStart * zoom;
        }

        return Math.min(
            -mapStart * zoom,
            Math.max(viewSize - mapEnd * zoom, offset)
        );
    }

    function constrainOffsets() {
        offsetX = constrainAxis(offsetX, width, MAP_LEFT, MAP_RIGHT);
        offsetY = constrainAxis(offsetY, height, MAP_TOP, MAP_BOTTOM);
    }

    function canPan() {
        return (
            (MAP_RIGHT - MAP_LEFT) * zoom > width
            || (MAP_BOTTOM - MAP_TOP) * zoom > height
        );
    }

    function recenterOffset(anchorOffset, viewSize, mapStart, mapEnd, anchorWeight) {
        const centeredOffset = (
            viewSize - (mapEnd - mapStart) * zoom
        ) / 2 - mapStart * zoom;
        return centeredOffset + (anchorOffset - centeredOffset) * anchorWeight;
    }

    function cellAt(screenX, screenY) {
        const mapX = (screenX - offsetX) / zoom;
        const mapY = (screenY - offsetY) / zoom;
        const firstColumn = Math.max(
            0,
            Math.ceil((mapX - ORIGIN_X - HEX_RADIUS) / COLUMN_STEP)
        );
        const lastColumn = Math.min(
            MAP_SIZE - 1,
            Math.floor((mapX - ORIGIN_X + HEX_RADIUS) / COLUMN_STEP)
        );

        for (let x = firstColumn; x <= lastColumn; x += 1) {
            const columnY = ORIGIN_Y + columnOffsetY(x);
            const firstRow = Math.max(
                0,
                Math.ceil((mapY - columnY - HEX_HEIGHT * 0.5) / HEX_HEIGHT)
            );
            const lastRow = Math.min(
                MAP_SIZE - 1,
                Math.floor((mapY - columnY + HEX_HEIGHT * 0.5) / HEX_HEIGHT)
            );

            for (let y = firstRow; y <= lastRow; y += 1) {
                const center = cellCenter(x, y);
                const relativeX = Math.abs(mapX - center.x);
                const relativeY = Math.abs(mapY - center.y);
                const horizontalLimit = HEX_RADIUS - relativeY / Math.sqrt(3);

                if (
                    relativeY <= HEX_HEIGHT * 0.5
                    && relativeX <= horizontalLimit
                ) {
                    return { x, y };
                }
            }
        }

        return null;
    }

    function pointerIsInsideCanvas(event) {
        const bounds = canvas.getBoundingClientRect();
        return (
            event.clientX >= bounds.left
            && event.clientX <= bounds.right
            && event.clientY >= bounds.top
            && event.clientY <= bounds.bottom
        );
    }

    function drawHexagon(centerX, centerY, cell) {
        context.beginPath();
        context.moveTo(centerX - HEX_RADIUS, centerY);
        context.lineTo(centerX - HEX_RADIUS / 2, centerY - HEX_HEIGHT / 2);
        context.lineTo(centerX + HEX_RADIUS / 2, centerY - HEX_HEIGHT / 2);
        context.lineTo(centerX + HEX_RADIUS, centerY);
        context.lineTo(centerX + HEX_RADIUS / 2, centerY + HEX_HEIGHT / 2);
        context.lineTo(centerX - HEX_RADIUS / 2, centerY + HEX_HEIGHT / 2);
        context.closePath();

        const isHovered = sameCell(cell, hoveredCell);
        const isSelected = sameCell(cell, selectedCell);
        if (isHovered) {
            context.fillStyle = "rgba(255, 255, 255, 0.1)";
            context.fill();
        } else if (isSelected) {
            context.fillStyle = "rgba(216, 173, 97, 0.2)";
            context.fill();
        }

        context.strokeStyle = isHovered
            ? "rgba(255, 255, 255, 0.9)"
            : isSelected
                ? "#d8ad61"
                : "#394452";
        context.lineWidth = 1 / zoom;
        context.stroke();

        if (
            coordinatesEnabled
            && zoom >= COORDINATE_ZOOM_THRESHOLD
        ) {
            const fontSize = Math.max(9, Math.min(14, 12 * zoom));
            context.fillStyle = "#eeeeee";
            context.font = `${fontSize / zoom}px Arial, sans-serif`;
            context.textAlign = "center";
            context.textBaseline = "middle";
            context.fillText(`${cell.x};${cell.y}`, centerX, centerY);
        }
    }

    function drawGrid() {
        const bounds = canvas.getBoundingClientRect();
        width = bounds.width;
        height = bounds.height;
        if (width <= 0 || height <= 0) {
            return;
        }

        constrainOffsets();
        pixelRatio = window.devicePixelRatio || 1;
        canvas.width = Math.round(width * pixelRatio);
        canvas.height = Math.round(height * pixelRatio);
        context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
        context.fillStyle = "#11161e";
        context.fillRect(0, 0, width, height);

        context.setTransform(
            pixelRatio * zoom,
            0,
            0,
            pixelRatio * zoom,
            pixelRatio * offsetX,
            pixelRatio * offsetY
        );
        const mapLeft = -offsetX / zoom;
        const mapTop = -offsetY / zoom;
        const mapRight = (width - offsetX) / zoom;
        const mapBottom = (height - offsetY) / zoom;
        const firstColumn = Math.max(
            0,
            Math.ceil((mapLeft - ORIGIN_X - HEX_RADIUS) / COLUMN_STEP)
        );
        const lastColumn = Math.min(
            MAP_SIZE - 1,
            Math.floor((mapRight - ORIGIN_X + HEX_RADIUS) / COLUMN_STEP)
        );

        for (let x = firstColumn; x <= lastColumn; x += 1) {
            const columnY = ORIGIN_Y + columnOffsetY(x);
            const firstRow = Math.max(
                0,
                Math.ceil((mapTop - columnY - HEX_HEIGHT * 0.5) / HEX_HEIGHT)
            );
            const lastRow = Math.min(
                MAP_SIZE - 1,
                Math.floor((mapBottom - columnY + HEX_HEIGHT * 0.5) / HEX_HEIGHT)
            );

            for (let y = firstRow; y <= lastRow; y += 1) {
                const center = cellCenter(x, y);
                drawHexagon(center.x, center.y, { x, y });
            }
        }

        if (selectionOutput) {
            selectionOutput.textContent = selectedCell
                ? `${selectedCell.x};${selectedCell.y}`
                : "Aucune";
        }
    }

    function updateHover(event) {
        const nextCell = pointerIsInsideCanvas(event)
            ? cellAt(event.offsetX, event.offsetY)
            : null;
        if (!sameCell(nextCell, hoveredCell)) {
            hoveredCell = nextCell;
            drawGrid();
        }
    }

    canvas.addEventListener("pointerdown", (event) => {
        if (event.button !== 0 || activePointer) {
            return;
        }

        event.preventDefault();
        activePointer = {
            id: event.pointerId,
            startX: event.clientX,
            startY: event.clientY,
            lastX: event.clientX,
            lastY: event.clientY,
            canDrag: canPan(),
            moved: false,
            dragging: false
        };
        canvas.setPointerCapture(event.pointerId);
    });

    canvas.addEventListener("pointermove", (event) => {
        if (activePointer?.id === event.pointerId) {
            const deltaX = event.clientX - activePointer.lastX;
            const deltaY = event.clientY - activePointer.lastY;
            activePointer.lastX = event.clientX;
            activePointer.lastY = event.clientY;

            if (
                !activePointer.moved
                && Math.hypot(
                    event.clientX - activePointer.startX,
                    event.clientY - activePointer.startY
                ) >= DRAG_THRESHOLD
            ) {
                activePointer.moved = true;
            }

            if (activePointer.canDrag && activePointer.moved) {
                activePointer.dragging = true;
            }

            if (activePointer.dragging) {
                offsetX += deltaX;
                offsetY += deltaY;
                constrainOffsets();
                hoveredCell = pointerIsInsideCanvas(event)
                    ? cellAt(event.offsetX, event.offsetY)
                    : null;
                drawGrid();
                return;
            }
        }

        updateHover(event);
    });

    canvas.addEventListener("pointerup", (event) => {
        if (activePointer?.id !== event.pointerId) {
            return;
        }

        const pointerMoved = activePointer.moved;
        activePointer = null;
        if (!pointerMoved && pointerIsInsideCanvas(event)) {
            selectedCell = cellAt(event.offsetX, event.offsetY);
        }
        hoveredCell = pointerIsInsideCanvas(event)
            ? cellAt(event.offsetX, event.offsetY)
            : null;
        drawGrid();
    });

    function cancelPointer(event) {
        if (activePointer?.id === event.pointerId) {
            activePointer = null;
            hoveredCell = null;
            drawGrid();
        }
    }

    canvas.addEventListener("pointercancel", cancelPointer);
    canvas.addEventListener("lostpointercapture", cancelPointer);
    canvas.addEventListener("pointerleave", () => {
        hoveredCell = null;
        drawGrid();
    });

    canvas.addEventListener("wheel", (event) => {
        event.preventDefault();
        if (event.deltaY === 0) {
            return;
        }

        const nextZoom = Math.min(
            ZOOM_MAX,
            Math.max(
                MIN_ZOOM,
                zoom * (event.deltaY < 0 ? ZOOM_FACTOR : 1 / ZOOM_FACTOR)
            )
        );
        if (nextZoom === zoom) {
            return;
        }

        const mapX = (event.offsetX - offsetX) / zoom;
        const mapY = (event.offsetY - offsetY) / zoom;
        zoom = nextZoom;
        const anchoredOffsetX = event.offsetX - mapX * zoom;
        const anchoredOffsetY = event.offsetY - mapY * zoom;
        const recenterProgress = Math.max(
            0,
            Math.min(
                1,
                (zoom - MIN_ZOOM) / (RECENTER_START_ZOOM - MIN_ZOOM)
            )
        );
        const anchorWeight = recenterProgress * recenterProgress
            * (3 - 2 * recenterProgress);
        offsetX = recenterOffset(
            anchoredOffsetX,
            width,
            MAP_LEFT,
            MAP_RIGHT,
            anchorWeight
        );
        offsetY = recenterOffset(
            anchoredOffsetY,
            height,
            MAP_TOP,
            MAP_BOTTOM,
            anchorWeight
        );
        constrainOffsets();
        hoveredCell = cellAt(event.offsetX, event.offsetY);
        drawGrid();
    }, { passive: false });

    if (coordinatesToggle) {
        coordinatesToggle.addEventListener("change", () => {
            coordinatesEnabled = coordinatesToggle.checked;
            drawGrid();
        });
    }

    const resizeObserver = new ResizeObserver(drawGrid);
    resizeObserver.observe(canvas);
    drawGrid();
})();
