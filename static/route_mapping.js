// Route-based CI Assignment Configuration
// Maps barangays and municipalities to route names

const routeMapping = {
    // Route 1: Bayawan → Kalumboyan → Border
    "route_1_bayawan_kalumboyan": {
        name: "Bayawan → Kalumboyan → Border",
        barangays: [
            // Bayawan barangays along this route
            "Kalumboyan", "Kalamtukan", "Malabugas", "Bugay", "Nangka"
        ],
        municipalities: []
    },
    
    // Route 2: Bayawan → Candumao → Basay → Border
    "route_2_bayawan_basay": {
        name: "Bayawan → Candumao → Basay → Border",
        barangays: [
            // Basay barangays
            "Actin", "Bal-os", "Bongalonan", "Cabalayongan", "Cabatuanan", 
            "Linantayan", "Maglinao", "Nagbo-alao", "Olandao", "Poblacion"
        ],
        municipalities: ["Basay"]
    },
    
    // Route 3: Bayawan → Sipalay
    "route_3_bayawan_sipalay": {
        name: "Bayawan → Sipalay",
        barangays: [
            // Sipalay barangays
            "Cabadiangan", "Camindangan", "Canturay", "Cartagena", "Gil Montilla",
            "Mambaroto", "Maricalum", "Nauhang", "Poblacion I", "Poblacion II",
            "Poblacion III", "San Jose"
        ],
        municipalities: ["Sipalay", "Sipalay City"]
    },
    
    // Route 4: Bayawan → Santa Catalina
    "route_4_bayawan_santa_catalina": {
        name: "Bayawan → Santa Catalina",
        barangays: [
            // Santa Catalina barangays
            "Alangilan", "Amio", "Buenavista", "Caigangan", "Caranoche", "Cawitan", 
            "Fatima", "Kabulacan", "Mabuhay", "Manalongon", "Mansagomayon", 
            "Milagrosa", "Nagbalaye", "Nagbinlod", "Obat", "Poblacion", 
            "San Francisco", "San Jose", "San Miguel", "San Pedro", "Santo Rosario", "Talalak"
        ],
        municipalities: ["Santa Catalina"]
    },
    
    // Route 5: Bayawan City Center (for local barangays)
    "route_5_bayawan_center": {
        name: "Bayawan City Center",
        barangays: [
            "Ali-is", "Banaybanay", "Banga", "Boyco", "Cansumalig", "Dawis",
            "Manduao", "Mandu-ao", "Maninihon", "Minaba", "Narra", "Pagatban",
            "Poblacion", "San Isidro", "San Jose", "San Miguel", "San Roque", 
            "Suba", "Tabuan", "Tayawan", "Tinago", "Ubos", "Villareal", "Villasol"
        ],
        municipalities: ["Bayawan", "Bayawan City"]
    }
};

// Function to find route for a given address
function findRouteForAddress(address) {
    if (!address) return null;
    
    const addressLower = address.toLowerCase();
    
    // Check each route
    for (const [routeId, routeData] of Object.entries(routeMapping)) {
        // Check if any barangay matches
        for (const barangay of routeData.barangays) {
            if (addressLower.includes(barangay.toLowerCase())) {
                return routeId;
            }
        }
        
        // Check if any municipality matches
        for (const municipality of routeData.municipalities) {
            if (addressLower.includes(municipality.toLowerCase())) {
                return routeId;
            }
        }
    }
    
    return null; // No matching route found
}

// Get route display name
function getRouteName(routeId) {
    return routeMapping[routeId]?.name || routeId;
}

// Get all available routes for dropdown
function getAllRoutes() {
    return Object.entries(routeMapping).map(([id, data]) => ({
        id: id,
        name: data.name
    }));
}
