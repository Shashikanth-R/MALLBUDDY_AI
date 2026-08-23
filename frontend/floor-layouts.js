/**
 * Floor Layouts and Navigation Data for MallBuddy
 * Contains store coordinates, landmarks, and pathfinding logic
 */

// Floor layout configurations
const FLOOR_LAYOUTS = {
    // Floor 1 - Fashion & Lifestyle
    "1": {
        name: "Floor 1 - Fashion & Lifestyle",
        width: 800,
        height: 500,
        background: "#F9FAFB",
        stores: [
            { id: 1, name: "Zara", unit: "105", x: 80, y: 80, width: 100, height: 70, color: "#6366F1" },
            { id: 2, name: "H&M", unit: "110", x: 200, y: 80, width: 100, height: 70, color: "#8B5CF6" },
            { id: 3, name: "Starbucks", unit: "115", x: 320, y: 80, width: 100, height: 70, color: "#10B981" }
        ],
        landmarks: [
            { name: "Main Entrance", x: 400, y: 450, type: "entrance", icon: "🚪" },
            { name: "Escalator to Floor 2", x: 700, y: 250, type: "escalator", icon: "↗️" },
            { name: "Washroom", unit: "101", x: 80, y: 380, type: "facility", icon: "🚻" },
            { name: "ATM - HDFC", unit: "102", x: 200, y: 380, type: "facility", icon: "🏧" }
        ],
        corridors: [
            // Main horizontal corridor
            { x: 50, y: 180, width: 700, height: 60 },
            // Vertical corridor to entrance
            { x: 370, y: 240, width: 60, height: 220 }
        ]
    },

    // Floor 2 - Sports & Electronics
    "2": {
        name: "Floor 2 - Sports & Electronics",
        width: 800,
        height: 500,
        background: "#F9FAFB",
        stores: [
            { id: 4, name: "Adidas", unit: "205", x: 80, y: 80, width: 100, height: 70, color: "#EF4444" },
            { id: 5, name: "Nike", unit: "210", x: 200, y: 80, width: 100, height: 70, color: "#F97316" },
            { id: 6, name: "Electronics Store", unit: "215", x: 320, y: 80, width: 120, height: 70, color: "#3B82F6" }
        ],
        landmarks: [
            { name: "Escalator from Floor 1", x: 700, y: 250, type: "escalator", icon: "↙️" },
            { name: "Escalator to Floor 3", x: 700, y: 150, type: "escalator", icon: "↗️" },
            { name: "Washroom", unit: "201", x: 80, y: 380, type: "facility", icon: "🚻" }
        ],
        corridors: [
            { x: 50, y: 180, width: 700, height: 60 },
            { x: 650, y: 140, width: 60, height: 180 }
        ]
    },

    // Floor 3 - Food Court
    "3": {
        name: "Floor 3 - Food Court",
        width: 800,
        height: 500,
        background: "#F9FAFB",
        stores: [
            { id: 7, name: "McDonald's", unit: "301", x: 80, y: 80, width: 100, height: 70, color: "#FBBF24" },
            { id: 8, name: "Pizza Hut", unit: "305", x: 200, y: 80, width: 100, height: 70, color: "#EF4444" },
            { id: 9, name: "Food Court", unit: "300", x: 350, y: 80, width: 200, height: 120, color: "#F97316" }
        ],
        landmarks: [
            { name: "Escalator from Floor 2", x: 700, y: 250, type: "escalator", icon: "↙️" },
            { name: "Escalator to Floor 4", x: 700, y: 150, type: "escalator", icon: "↗️" }
        ],
        corridors: [
            { x: 50, y: 220, width: 700, height: 60 }
        ]
    },

    // Floor 4 - Entertainment
    "4": {
        name: "Floor 4 - Entertainment",
        width: 800,
        height: 500,
        background: "#F9FAFB",
        stores: [
            { id: 10, name: "PVR Cinemas", unit: "401", x: 100, y: 60, width: 250, height: 120, color: "#7C3AED" },
            { id: 11, name: "Gaming Zone", unit: "410", x: 400, y: 60, width: 150, height: 100, color: "#EC4899" }
        ],
        landmarks: [
            { name: "Escalator from Floor 3", x: 700, y: 250, type: "escalator", icon: "↙️" }
        ],
        corridors: [
            { x: 50, y: 200, width: 700, height: 60 }
        ]
    },

    // Basement - Parking
    "B1": {
        name: "Basement - Parking",
        width: 800,
        height: 500,
        background: "#E5E7EB",
        stores: [],
        landmarks: [
            { name: "Parking Area", unit: "P1", x: 400, y: 250, type: "parking", icon: "🅿️" },
            { name: "Elevator to Floor 1", x: 700, y: 250, type: "elevator", icon: "🛗" }
        ],
        corridors: [
            { x: 50, y: 220, width: 700, height: 60 }
        ]
    }
};

// Starting point options
const STARTING_POINTS = [
    { id: "main_entrance", name: "Main Entrance", floor: "1", x: 400, y: 450, icon: "🚪" },
    { id: "parking", name: "Parking Area (B1)", floor: "B1", x: 400, y: 250, icon: "🅿️" },
    { id: "food_court", name: "Food Court (Floor 3)", floor: "3", x: 400, y: 140, icon: "🍔" },
    { id: "escalator_f1", name: "Escalator - Floor 1", floor: "1", x: 700, y: 250, icon: "↗️" },
    { id: "escalator_f2", name: "Escalator - Floor 2", floor: "2", x: 700, y: 250, icon: "↕️" }
];

// Floor connections (escalators, elevators)
const FLOOR_CONNECTIONS = {
    "B1": { up: "1", down: null, connectionPoint: { x: 700, y: 250 } },
    "1": { up: "2", down: "B1", connectionPoint: { x: 700, y: 250 } },
    "2": { up: "3", down: "1", connectionPoint: { x: 700, y: 250 } },
    "3": { up: "4", down: "2", connectionPoint: { x: 700, y: 250 } },
    "4": { up: null, down: "3", connectionPoint: { x: 700, y: 250 } }
};

/**
 * Find a store by name across all floors
 */
function findStoreByName(storeName) {
    const normalizedName = storeName.toLowerCase().trim();

    for (const [floor, layout] of Object.entries(FLOOR_LAYOUTS)) {
        const store = layout.stores.find(s =>
            s.name.toLowerCase() === normalizedName
        );
        if (store) {
            return { ...store, floor };
        }

        // Also check landmarks
        const landmark = layout.landmarks.find(l =>
            l.name.toLowerCase().includes(normalizedName)
        );
        if (landmark) {
            return { ...landmark, floor, isLandmark: true };
        }
    }
    return null;
}

/**
 * Find starting point by ID
 */
function findStartingPoint(startId) {
    return STARTING_POINTS.find(sp => sp.id === startId);
}

/**
 * Calculate center point of a store/location
 */
function getLocationCenter(location) {
    if (location.width && location.height) {
        return {
            x: location.x + location.width / 2,
            y: location.y + location.height / 2
        };
    }
    return { x: location.x, y: location.y };
}

/**
 * Calculate route between two locations
 */
function calculateRoute(fromLocation, toLocation) {
    const fromFloor = fromLocation.floor;
    const toFloor = toLocation.floor;

    const fromCenter = getLocationCenter(fromLocation);
    const toCenter = getLocationCenter(toLocation);

    const route = {
        from: fromLocation,
        to: toLocation,
        floors: [],
        totalDistance: 0,
        estimatedTime: 0,
        steps: []
    };

    if (fromFloor === toFloor) {
        // Same floor navigation
        route.floors.push({
            floor: fromFloor,
            path: generatePathOnFloor(fromCenter, toCenter, fromFloor)
        });
        route.steps.push(`Walk to ${toLocation.name} (Unit ${toLocation.unit || 'N/A'})`);
        route.totalDistance = calculateDistance(fromCenter, toCenter);
    } else {
        // Multi-floor navigation
        const floorPath = getFloorPath(fromFloor, toFloor);

        // First floor - walk to escalator
        const escalatorPoint = FLOOR_CONNECTIONS[fromFloor].connectionPoint;
        route.floors.push({
            floor: fromFloor,
            path: generatePathOnFloor(fromCenter, escalatorPoint, fromFloor)
        });
        route.steps.push(`Walk to the escalator on Floor ${fromFloor}`);

        // Intermediate floors
        for (let i = 1; i < floorPath.length - 1; i++) {
            route.steps.push(`Take escalator to Floor ${floorPath[i]}`);
        }

        // Last floor - walk from escalator to destination
        const lastFloorEscalator = FLOOR_CONNECTIONS[toFloor].connectionPoint;
        route.floors.push({
            floor: toFloor,
            path: generatePathOnFloor(lastFloorEscalator, toCenter, toFloor)
        });
        route.steps.push(`Take escalator to Floor ${toFloor}`);
        route.steps.push(`Walk to ${toLocation.name} (Unit ${toLocation.unit || 'N/A'})`);

        route.totalDistance = calculateDistance(fromCenter, escalatorPoint) +
            calculateDistance(lastFloorEscalator, toCenter) +
            (floorPath.length - 1) * 50; // estimate for floor changes
    }

    route.estimatedTime = Math.ceil(route.totalDistance / 50); // ~50m per minute walking

    return route;
}

/**
 * Generate path waypoints on a single floor
 */
function generatePathOnFloor(from, to, floor) {
    const layout = FLOOR_LAYOUTS[floor];
    if (!layout) return [from, to];

    const path = [];
    path.push(from);

    // Get corridor Y position for this floor
    const corridor = layout.corridors[0];
    if (corridor) {
        const corridorY = corridor.y + corridor.height / 2;

        // If start and end are not on the corridor, route through it
        if (from.y !== corridorY && to.y !== corridorY) {
            // Walk to corridor
            path.push({ x: from.x, y: corridorY });
            // Walk along corridor
            path.push({ x: to.x, y: corridorY });
        } else if (from.y !== corridorY) {
            // Just from point not on corridor
            path.push({ x: from.x, y: corridorY });
            path.push({ x: to.x, y: corridorY });
        } else if (to.y !== corridorY) {
            // Just to point not on corridor
            path.push({ x: to.x, y: corridorY });
        }
    }

    path.push(to);

    return path;
}

/**
 * Get the floor path between two floors
 */
function getFloorPath(fromFloor, toFloor) {
    const floorOrder = ["B1", "1", "2", "3", "4"];
    const fromIndex = floorOrder.indexOf(fromFloor);
    const toIndex = floorOrder.indexOf(toFloor);

    if (fromIndex === -1 || toIndex === -1) return [fromFloor, toFloor];

    const path = [];
    const direction = fromIndex < toIndex ? 1 : -1;

    for (let i = fromIndex; direction > 0 ? i <= toIndex : i >= toIndex; i += direction) {
        path.push(floorOrder[i]);
    }

    return path;
}

/**
 * Calculate distance between two points
 */
function calculateDistance(p1, p2) {
    return Math.sqrt(Math.pow(p2.x - p1.x, 2) + Math.pow(p2.y - p1.y, 2));
}

/**
 * Generate SVG path data from waypoints
 */
function generateSVGPath(waypoints) {
    if (!waypoints || waypoints.length < 2) return "";

    let pathData = `M ${waypoints[0].x} ${waypoints[0].y}`;

    for (let i = 1; i < waypoints.length; i++) {
        pathData += ` L ${waypoints[i].x} ${waypoints[i].y}`;
    }

    return pathData;
}

/**
 * Get step-by-step directions text
 */
function getDirectionsText(route) {
    const steps = [];

    steps.push({
        icon: "📍",
        text: `Start from ${route.from.name || route.from.id}`,
        detail: route.from.floor ? `Floor ${route.from.floor}` : ""
    });

    route.steps.forEach((step, index) => {
        let icon = "➡️";
        if (step.includes("escalator")) icon = "↗️";
        if (step.includes("elevator")) icon = "🛗";
        if (step.includes("Walk to")) icon = "🚶";

        steps.push({
            icon,
            text: step,
            detail: ""
        });
    });

    steps.push({
        icon: "🎯",
        text: `Arrive at ${route.to.name}`,
        detail: `Unit ${route.to.unit || 'N/A'}`
    });

    return steps;
}

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        FLOOR_LAYOUTS,
        STARTING_POINTS,
        FLOOR_CONNECTIONS,
        findStoreByName,
        findStartingPoint,
        calculateRoute,
        generateSVGPath,
        getDirectionsText
    };
}
