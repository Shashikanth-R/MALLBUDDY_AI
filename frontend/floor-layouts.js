/**
 * Floor Layouts and Navigation Data for MallBuddy
 * Contains store coordinates, landmarks, and pathfinding logic
 */

// Data structures for mall layout, to be populated from backend
let FLOOR_LAYOUTS = {};
let STARTING_POINTS = [];
let FLOOR_CONNECTIONS = {};

const backendUrl = window.BACKEND_URL || 'http://localhost:5000';

async function fetchMallLayout() {
    try {
        const response = await fetch(`${backendUrl}/api/navigation/layout`);
        if (!response.ok) throw new Error('Failed to fetch layout');
        const layoutData = await response.json();
        
        FLOOR_LAYOUTS = layoutData.FLOOR_LAYOUTS || {};
        STARTING_POINTS = layoutData.STARTING_POINTS || [];
        FLOOR_CONNECTIONS = layoutData.FLOOR_CONNECTIONS || {};
        console.log("Loaded mall layout from backend");
    } catch (error) {
        console.error("Error fetching mall layout:", error);
    }
}

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
 * Calculate route using backend A* service with local fallback
 */
async function calculateRoute(fromLocation, toLocation) {
    try {
        const fromName = encodeURIComponent(fromLocation.name || fromLocation.id);
        const toName = encodeURIComponent(toLocation.name || toLocation.id);
        const response = await fetch(`${backendUrl}/api/navigation/?from=${fromName}&to=${toName}`);
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        const data = await response.json();
        if (data.route) {
            console.log("Using backend A* route");
            // API compatibility formatting
            const route = data.route;
            if (!route.from.x) route.from = fromLocation;
            if (!route.to.x) route.to = toLocation;
            return route;
        }
        throw new Error("Route not found in API response");
    } catch (err) {
        console.warn("Falling back to local routing:", err);
        return calculateRouteFallback(fromLocation, toLocation);
    }
}

/**
 * Calculate route between two locations locally (fallback)
 */
function calculateRouteFallback(fromLocation, toLocation) {
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
        calculateRouteFallback,
        calculateRoute,
        generateSVGPath,
        getDirectionsText,
        fetchMallLayout
    };
}
