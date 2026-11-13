export const TERRAIN_CATALOG = Object.freeze([
    { code: "plain", name: "Plaine", color: "#58734f", entryCost: 1 },
    { code: "desert", name: "Désert", color: "#99875d", entryCost: 1 },
    { code: "forest", name: "Forêt", color: "#395433", entryCost: 1 },
    { code: "deep_forest", name: "Forêt profonde", color: "#294025", entryCost: 1 },
    { code: "sea", name: "Mer", color: "#324f68", entryCost: 5 },
    { code: "deep_water", name: "Eau profonde", color: "#193044", entryCost: 5 },
    { code: "coal", name: "Charbon", color: "#959494", entryCost: 1 },
    { code: "cloud", name: "Nuage", color: "#e9f2f6", entryCost: 1 },
    { code: "mountain", name: "Montagne", color: "#5e5e67", entryCost: 2 },
    { code: "road", name: "Route", color: "#6f634c", entryCost: 0.5 },
    { code: "city", name: "Ville", color: "#9e8c63", entryCost: 0.5 }
].map((terrain) => Object.freeze(terrain)));

const TERRAIN_BY_CODE = new Map(
    TERRAIN_CATALOG.map((terrain) => [terrain.code, terrain])
);

const VARIANT_SHADES = [
    { number: 1, target: 255, amount: 0.35 },
    { number: 2, target: 255, amount: 0.16 },
    { number: 3 },
    { number: 4, target: 0, amount: 0.2 }
];

function getColorChannels(color) {
    const match = /^#([\da-f]{6})$/i.exec(color);
    if (!match) {
        throw new RangeError(`Invalid terrain color: ${color}`);
    }

    return [0, 2, 4].map((offset) => (
        Number.parseInt(match[1].slice(offset, offset + 2), 16)
    ));
}

function shadeChannel(channel, target, amount) {
    return Math.round(channel + (target - channel) * amount)
        .toString(16)
        .padStart(2, "0");
}

function makeShade(channels, target, amount) {
    return `#${channels.map((channel) => (
        shadeChannel(channel, target, amount)
    )).join("")}`;
}

export function getTerrainByCode(code) {
    const terrain = TERRAIN_BY_CODE.get(code);
    if (!terrain) {
        throw new RangeError(`Unknown terrain code: ${code}`);
    }
    return terrain;
}

export function getTerrainVariants(code) {
    const terrain = getTerrainByCode(code);
    const channels = getColorChannels(terrain.color);

    return VARIANT_SHADES.map((shade) => ({
        number: shade.number,
        color: shade.number === 3
            ? terrain.color
            : makeShade(channels, shade.target, shade.amount)
    }));
}
