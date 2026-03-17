// Complete Address Database: Dumaguete to Bayawan to Sipalay
// Using HYBRID approach: Known puroks + Numbered placeholders

let addressDatabase = [];

// Helper function to add barangay with specific puroks
function addBarangay(barangay, municipality, province, puroks) {
    puroks.forEach(purok => {
        addressDatabase.push({
            purok: purok,
            barangay: barangay,
            municipality: municipality,
            province: province
        });
    });
    
    // Add barangay without purok
    addressDatabase.push({
        barangay: barangay,
        municipality: municipality,
        province: province
    });
}

// Helper for barangays with numbered puroks (placeholder until real data is known)
function addBarangayNumbered(barangay, municipality, province, count = 10) {
    const puroks = [];
    for (let i = 1; i <= count; i++) {
        puroks.push(`Purok ${i}`);
    }
    addBarangay(barangay, municipality, province, puroks);
}

// DUMAGUETE CITY - All Barangays (using numbered puroks as placeholder)
const dumagueteBarangays = [
    "Bagacay", "Bajumpandan", "Balugo", "Banilad", "Bantayan", "Batinguel",
    "Bunao", "Cadawinonan", "Calindagan", "Camanjac", "Candau-ay", "Cantil-e",
    "Daro", "Junob", "Looc", "Mangnao-Canal", "Motong", "Piapi", "Pulantubig",
    "Tabuc-tubig", "Talay", "Poblacion 1", "Poblacion 2", "Poblacion 3",
    "Poblacion 4", "Poblacion 5", "Poblacion 6", "Poblacion 7", "Poblacion 8"
];
dumagueteBarangays.forEach(brgy => addBarangayNumbered(brgy, "Dumaguete City", "Negros Oriental", 10));

// SIBULAN - All Barangays
const sibulanBarangays = [
    "Agan-an", "Ajong", "Balugo", "Boloc-boloc", "Cangmating", "Enrique Villanueva",
    "Looc", "Magatas", "Maningning", "Maslog", "Poblacion", "San Antonio", "Tubigon"
];
sibulanBarangays.forEach(brgy => addBarangayNumbered(brgy, "Sibulan", "Negros Oriental", 10));

// VALENCIA - All Barangays
const valenciaBarangays = [
    "Apolong", "Balabag East", "Balabag West", "Balayagmanok", "Bong-ao",
    "Caidiocan", "Calayugan", "Dobdob", "Jawa", "Liptong", "Lunga",
    "Malabo", "Pajo", "Poblacion", "Pulangbato"
];
valenciaBarangays.forEach(brgy => addBarangayNumbered(brgy, "Valencia", "Negros Oriental", 10));

// BACONG - All Barangays
const bacongBarangays = [
    "Buntis", "Calangag", "Isugan", "Liptong", "Poblacion", "Sulangan", "Timbanga"
];
bacongBarangays.forEach(brgy => addBarangayNumbered(brgy, "Bacong", "Negros Oriental", 10));

// DAUIN - All Barangays
const dauinBarangays = [
    "Bagacay", "Bulak", "Lipayo", "Maayongtubig", "Masaplod Norte",
    "Masaplod Sur", "Poblacion", "Tunga-tunga"
];
dauinBarangays.forEach(brgy => addBarangayNumbered(brgy, "Dauin", "Negros Oriental", 10));

// ZAMBOANGUITA - All Barangays
const zamboanguitaBarangays = [
    "Basak", "Lotuban", "Maluay", "Nabago", "Najandig", "Poblacion"
];
zamboanguitaBarangays.forEach(brgy => addBarangayNumbered(brgy, "Zamboanguita", "Negros Oriental", 10));

// SIATON - All Barangays
const siatonBarangays = [
    "Apo Island", "Bonawon", "Caticugan", "Malabago", "Mantiquil", "Napacao",
    "Poblacion I", "Poblacion II", "Poblacion III", "Sumaliring"
];
siatonBarangays.forEach(brgy => addBarangayNumbered(brgy, "Siaton", "Negros Oriental", 10));

// SANTA CATALINA - All Barangays
const santaCatalinaBarangays = [
    "Alangilan", "Amio", "Buenavista", "Caigangan", "Cawitan", "Manalongon",
    "Milagrosa", "Obat", "Poblacion", "Talalak"
];
santaCatalinaBarangays.forEach(brgy => addBarangayNumbered(brgy, "Santa Catalina", "Negros Oriental", 10));

// BAYAWAN CITY - All Barangays with SPECIFIC puroks
// Villareal - Known puroks
addBarangay("Villareal", "Bayawan City", "Negros Oriental", [
    "Purok 1", "Purok 2", "Purok 3", "Purok 4", "Purok 5", 
    "Purok 6", "Purok 7", "Purok 8", "Purok 9", "Purok 10",
    "Purok Pagkakaisa", "Purok Sampaguita", "Purok Gemelina"
]);

// Manduao - Add specific puroks if known, otherwise numbered
addBarangayNumbered("Manduao", "Bayawan City", "Negros Oriental", 10);

// Villasol - Add specific puroks if known, otherwise numbered
addBarangayNumbered("Villasol", "Bayawan City", "Negros Oriental", 10);

// Other Bayawan barangays - using numbered puroks as placeholder
const otherBayawanBarangays = [
    "Ali-is", "Banaybanay", "Banga", "Boyco", "Bugay", "Cansumalig", "Dawis",
    "Kalamtukan", "Malabugas", "Maninihon", "Nangka", "Pagatban",
    "San Jose", "Suba", "Tayawan", "Tinago", "Ubos", "Poblacion"
];
otherBayawanBarangays.forEach(brgy => addBarangayNumbered(brgy, "Bayawan City", "Negros Oriental", 10));

// BASAY - All Barangays
const basayBarangays = [
    "Actin", "Bal-os", "Bongalonan", "Cabalayongan", "Maglinao", "Nagbo-alao",
    "Olandao", "Poblacion", "Tambo"
];
basayBarangays.forEach(brgy => addBarangayNumbered(brgy, "Basay", "Negros Oriental", 10));

// HINOBAAN (Negros Occidental) - All Barangays
const hinobaanBarangays = [
    "Anahaw", "Bacuyangan", "Bulwangan", "Caliban", "Damutan", "Gargato",
    "Libas", "Mabini", "Malaiba", "Nabulao", "Poblacion", "Talacagay"
];
hinobaanBarangays.forEach(brgy => addBarangayNumbered(brgy, "Hinobaan", "Negros Occidental", 10));

// CANDONI (Negros Occidental) - All Barangays
const candoniBarangays = [
    "Agboy", "Banga", "Cabia-an", "Gatuslao", "Haba", "Payauan",
    "Poblacion East", "Poblacion West"
];
candoniBarangays.forEach(brgy => addBarangayNumbered(brgy, "Candoni", "Negros Occidental", 10));

// CAUAYAN (Negros Occidental) - All Barangays
const cauayanBarangays = [
    "Abaca", "Baclao", "Bulata", "Caliling", "Guiljungan", "Mambugsay",
    "Poblacion I", "Poblacion II", "Sag-ang", "Tiling"
];
cauayanBarangays.forEach(brgy => addBarangayNumbered(brgy, "Cauayan", "Negros Occidental", 10));

// SIPALAY CITY (Negros Occidental) - All Barangays
const sipalayBarangays = [
    "Cabadiangan", "Camindangan", "Canturay", "Cartagena", "Gil Montilla",
    "Mambaroto", "Maricalum", "Nauhang", "Poblacion I", "Poblacion II",
    "Poblacion III", "San Jose"
];
sipalayBarangays.forEach(brgy => addBarangayNumbered(brgy, "Sipalay City", "Negros Occidental", 10));

console.log(`Total addresses loaded: ${addressDatabase.length}`);
console.log(`NOTE: Puroks are numbered (1-10) for most barangays. Update with actual purok names as they become known.`);
