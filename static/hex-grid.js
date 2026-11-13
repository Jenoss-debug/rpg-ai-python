/**
 * Pages can customize gestures and pass overlay elements as interaction blockers.
 */
const INITIAL_ZOOM = 0.45;

export function createHexGrid(canvas, options = {}) {
    if (!(canvas instanceof HTMLCanvasElement)) {
        throw new TypeError("A canvas element is required.");
    }

    const context = canvas.getContext("2d");
    if (!context) {
        throw new Error("Unable to create a 2D canvas context.");
    }

    const columns = options.columns ?? 100;
    const rows = options.rows ?? 100;
    const hexRadius = options.hexRadius ?? 42;
    const minZoom = options.minZoom ?? 0.1;
    const maxZoom = options.maxZoom ?? 3;
    const zoomFactor = options.zoomFactor ?? 1.15;
    const recenterStartZoom = options.recenterStartZoom ?? 0.6;
    const coordinateZoomThreshold = options.coordinateZoomThreshold ?? 0.75;
    const dragThreshold = 4;
    const mode = options.interactionMode ?? {};
    const interactionBlockers = options.interactionBlockers ?? [];

    if (
        !Number.isInteger(columns)
        || columns < 1
        || !Number.isInteger(rows)
        || rows < 1
        || hexRadius <= 0
    ) {
        throw new RangeError("Grid dimensions and hexagon radius must be positive.");
    }
    if (
        minZoom <= 0
        || maxZoom < minZoom
        || recenterStartZoom <= minZoom
    ) {
        throw new RangeError("Zoom limits and recenter threshold are invalid.");
    }

    const hexWidth = hexRadius * 2;
    const hexHeight = Math.sqrt(3) * hexRadius;
    const columnStep = hexWidth * 0.75;
    const originX = hexRadius;
    const originY = hexHeight / 2;
    const mapLeft = originX - hexRadius;
    const mapRight = originX + (columns - 1) * columnStep + hexRadius;
    const mapTop = originY - hexHeight / 2;
    const mapBottom = originY
        + (rows - 1) * hexHeight
        + ((columns - 1) % 2) * hexHeight * 0.5
        + hexHeight / 2;

    let width = 0;
    let height = 0;
    let pixelRatio = 1;
    let zoom = Math.max(
        minZoom,
        Math.min(maxZoom, options.initialZoom ?? INITIAL_ZOOM)
    );
    let offsetX = 0;
    let offsetY = 0;
    let hoveredCell = null;
    let selectedCell = null;
    let activePointer = null;
    let coordinatesVisible = options.showCoordinates ?? false;

    function sameCell(first, second) {
        return first?.x === second?.x && first?.y === second?.y;
    }

    function columnOffsetY(x) {
        return (x % 2) * hexHeight * 0.5;
    }

    function cellCenter(x, y) {
        return {
            x: originX + x * columnStep,
            y: originY + y * hexHeight + columnOffsetY(x)
        };
    }

    function cellAt(screenX, screenY) {
        const mapX = (screenX - offsetX) / zoom;
        const mapY = (screenY - offsetY) / zoom;
        const firstColumn = Math.max(
            0,
            Math.ceil((mapX - originX - hexRadius) / columnStep)
        );
        const lastColumn = Math.min(
            columns - 1,
            Math.floor((mapX - originX + hexRadius) / columnStep)
        );

        for (let x = firstColumn; x <= lastColumn; x += 1) {
            const columnY = originY + columnOffsetY(x);
            const firstRow = Math.max(
                0,
                Math.ceil((mapY - columnY - hexHeight * 0.5) / hexHeight)
            );
            const lastRow = Math.min(
                rows - 1,
                Math.floor((mapY - columnY + hexHeight * 0.5) / hexHeight)
            );

            for (let y = firstRow; y <= lastRow; y += 1) {
                const center = cellCenter(x, y);
                const relativeX = Math.abs(mapX - center.x);
                const relativeY = Math.abs(mapY - center.y);
                const horizontalLimit = hexRadius - relativeY / Math.sqrt(3);

                if (
                    relativeY <= hexHeight * 0.5
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
            && !pointerIsOverInteractionBlocker(event)
        );
    }

    function pointerIsOverInteractionBlocker(event) {
        if (interactionBlockers.length === 0) {
            return false;
        }

        const element = document.elementFromPoint(event.clientX, event.clientY);
        return interactionBlockers.some((blocker) => blocker.contains(element));
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
        offsetX = constrainAxis(offsetX, width, mapLeft, mapRight);
        offsetY = constrainAxis(offsetY, height, mapTop, mapBottom);
    }

    function canPan() {
        return (
            (mapRight - mapLeft) * zoom > width
            || (mapBottom - mapTop) * zoom > height
        );
    }

    function recenterOffset(anchorOffset, viewSize, mapStart, mapEnd, anchorWeight) {
        const centeredOffset = (
            viewSize - (mapEnd - mapStart) * zoom
        ) / 2 - mapStart * zoom;
        return centeredOffset + (anchorOffset - centeredOffset) * anchorWeight;
    }

    function drawHexagon(centerX, centerY, cell) {
        context.beginPath();
        context.moveTo(centerX - hexRadius, centerY);
        context.lineTo(centerX - hexRadius / 2, centerY - hexHeight / 2);
        context.lineTo(centerX + hexRadius / 2, centerY - hexHeight / 2);
        context.lineTo(centerX + hexRadius, centerY);
        context.lineTo(centerX + hexRadius / 2, centerY + hexHeight / 2);
        context.lineTo(centerX - hexRadius / 2, centerY + hexHeight / 2);
        context.closePath();

        const isHovered = sameCell(cell, hoveredCell);
        const isSelected = sameCell(cell, selectedCell);
        options.onCellRender?.(context, cell, {
            centerX,
            centerY,
            radius: hexRadius,
            width: hexWidth,
            height: hexHeight
        });

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

        if (coordinatesVisible && zoom >= coordinateZoomThreshold) {
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
        const mapViewLeft = -offsetX / zoom;
        const mapViewTop = -offsetY / zoom;
        const mapViewRight = (width - offsetX) / zoom;
        const mapViewBottom = (height - offsetY) / zoom;
        const firstColumn = Math.max(
            0,
            Math.ceil((mapViewLeft - originX - hexRadius) / columnStep)
        );
        const lastColumn = Math.min(
            columns - 1,
            Math.floor((mapViewRight - originX + hexRadius) / columnStep)
        );

        for (let x = firstColumn; x <= lastColumn; x += 1) {
            const columnY = originY + columnOffsetY(x);
            const firstRow = Math.max(
                0,
                Math.ceil((mapViewTop - columnY - hexHeight * 0.5) / hexHeight)
            );
            const lastRow = Math.min(
                rows - 1,
                Math.floor((mapViewBottom - columnY + hexHeight * 0.5) / hexHeight)
            );

            for (let y = firstRow; y <= lastRow; y += 1) {
                const center = cellCenter(x, y);
                drawHexagon(center.x, center.y, { x, y });
            }
        }
    }

    function setHoveredCell(cell, event, redraw = true) {
        if (sameCell(cell, hoveredCell)) {
            return false;
        }

        hoveredCell = cell;
        options.onCellHover?.(cell, event, api);
        if (redraw) {
            drawGrid();
        }
        return true;
    }

    function updateHover(event, redraw = true) {
        const cell = pointerIsInsideCanvas(event)
            ? cellAt(event.offsetX, event.offsetY)
            : null;
        return setHoveredCell(cell, event, redraw);
    }

    function setSelectedCell(cell, event) {
        if (sameCell(cell, selectedCell)) {
            return;
        }

        selectedCell = cell;
        options.onSelectionChange?.(cell, event);
        drawGrid();
    }

    function pointerBehavior(event, cell) {
        const behavior = mode.getPointerBehavior?.(event, cell, api) ?? "pan";
        if (behavior !== "pan" && behavior !== "custom") {
            throw new Error(`Unsupported pointer behavior: ${behavior}`);
        }
        return behavior;
    }

    const api = {
        setCoordinatesVisible(visible) {
            coordinatesVisible = Boolean(visible);
            drawGrid();
        },
        setSelectedCell,
        getSelectedCell() {
            return selectedCell;
        },
        getHoveredCell() {
            return hoveredCell;
        },
        redraw: drawGrid
    };

    canvas.addEventListener("pointerdown", (event) => {
        if (event.button !== 0 || activePointer) {
            return;
        }

        event.preventDefault();
        const cell = pointerIsInsideCanvas(event)
            ? cellAt(event.offsetX, event.offsetY)
            : null;
        const behavior = pointerBehavior(event, cell);
        activePointer = {
            id: event.pointerId,
            startX: event.clientX,
            startY: event.clientY,
            lastX: event.clientX,
            lastY: event.clientY,
            behavior,
            canDrag: behavior === "pan" && canPan(),
            moved: false,
            dragging: false
        };
        canvas.setPointerCapture(event.pointerId);
        if (behavior === "custom") {
            mode.onPointerDown?.(cell, event, api);
        }
    });

    canvas.addEventListener("pointermove", (event) => {
        const isActivePointer = (
            activePointer !== null
            && activePointer.id === event.pointerId
        );
        if (isActivePointer && pointerIsOverInteractionBlocker(event)) {
            cancelPointer(event);
            return;
        }

        if (isActivePointer) {
            const cell = pointerIsInsideCanvas(event)
                ? cellAt(event.offsetX, event.offsetY)
                : null;
            const behavior = pointerBehavior(event, cell);
            let deltaX = event.clientX - activePointer.lastX;
            let deltaY = event.clientY - activePointer.lastY;

            if (behavior !== activePointer.behavior) {
                const previousBehavior = activePointer.behavior;
                activePointer.behavior = behavior;
                activePointer.canDrag = behavior === "pan" && canPan();
                activePointer.dragging = false;
                activePointer.lastX = event.clientX;
                activePointer.lastY = event.clientY;
                deltaX = 0;
                deltaY = 0;
                mode.onPointerBehaviorChange?.(
                    previousBehavior,
                    behavior,
                    cell,
                    event,
                    api
                );
            } else {
                activePointer.lastX = event.clientX;
                activePointer.lastY = event.clientY;
            }

            if (
                !activePointer.moved
                && Math.hypot(
                    event.clientX - activePointer.startX,
                    event.clientY - activePointer.startY
                ) >= dragThreshold
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
                updateHover(event, false);
                drawGrid();
                return;
            }

            if (activePointer.behavior === "custom") {
                setHoveredCell(cell, event);
                mode.onPointerMove?.(cell, event, api);
                return;
            }
        }

        updateHover(event);
    });

    canvas.addEventListener("pointerup", (event) => {
        if (!activePointer || activePointer.id !== event.pointerId) {
            return;
        }
        if (pointerIsOverInteractionBlocker(event)) {
            cancelPointer(event);
            return;
        }

        const pointer = activePointer;
        activePointer = null;
        const cell = pointerIsInsideCanvas(event)
            ? cellAt(event.offsetX, event.offsetY)
            : null;
        if (pointer.behavior === "custom") {
            mode.onPointerUp?.(cell, event, api);
        } else if (!pointer.moved && pointerIsInsideCanvas(event)) {
            if (typeof mode.onCellClick === "function") {
                mode.onCellClick(cell, event, api);
            } else {
                selectedCell = cell;
                options.onSelectionChange?.(cell, event);
            }
        }

        setHoveredCell(cell, event, false);
        drawGrid();
    });

    function cancelPointer(event) {
        if (!activePointer || activePointer.id !== event.pointerId) {
            return;
        }

        const pointer = activePointer;
        activePointer = null;
        if (pointer.behavior === "custom") {
            mode.onPointerCancel?.(event, api);
        }
        setHoveredCell(null, event, false);
        drawGrid();
    }

    canvas.addEventListener("pointercancel", cancelPointer);
    canvas.addEventListener("lostpointercapture", cancelPointer);
    canvas.addEventListener("pointerleave", (event) => {
        setHoveredCell(null, event);
    });

    canvas.addEventListener("wheel", (event) => {
        event.preventDefault();
        if (event.deltaY === 0) {
            return;
        }

        const nextZoom = Math.min(
            maxZoom,
            Math.max(
                minZoom,
                zoom * (event.deltaY < 0 ? zoomFactor : 1 / zoomFactor)
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
                (zoom - minZoom) / (recenterStartZoom - minZoom)
            )
        );
        const anchorWeight = recenterProgress * recenterProgress
            * (3 - 2 * recenterProgress);
        offsetX = recenterOffset(
            anchoredOffsetX,
            width,
            mapLeft,
            mapRight,
            anchorWeight
        );
        offsetY = recenterOffset(
            anchoredOffsetY,
            height,
            mapTop,
            mapBottom,
            anchorWeight
        );
        constrainOffsets();
        setHoveredCell(
            pointerIsInsideCanvas(event)
                ? cellAt(event.offsetX, event.offsetY)
                : null,
            event,
            false
        );
        drawGrid();
    }, { passive: false });

    const resizeObserver = new ResizeObserver(drawGrid);
    resizeObserver.observe(canvas);
    drawGrid();
    return api;
}
