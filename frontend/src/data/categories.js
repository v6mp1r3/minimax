export const categories = [
  {
    id: "education",
    title: "Educație și studii",
    description: "Erasmus, burse, universitate și echivalarea diplomelor.",
    icon: "education",
    color: "mint",
    topics: ["Erasmus", "Înscriere la universitate", "Echivalarea diplomelor", "Burse și finanțare"],
  },
  {
    id: "health",
    title: "Sănătate",
    description: "Înregistrarea la medic, asigurare și acces la servicii.",
    icon: "health",
    color: "pink",
    topics: ["Înregistrare la medic", "Asigurare medicală", "Servicii medicale"],
  },
  {
    id: "travel",
    title: "Călătorii și relocare",
    description: "Vize, ședere și documente de călătorie.",
    icon: "travel",
    color: "blue",
    topics: ["Viză", "Permis de ședere", "Relocare în străinătate"],
  },
  {
    id: "public",
    title: "Acte și servicii publice",
    description: "Buletin, pașaport, stare civilă și servicii publice.",
    icon: "public",
    color: "mint",
    topics: ["Buletin", "Pașaport", "Stare civilă", "Alte servicii publice"],
  },
  {
    id: "career",
    title: "Muncă și carieră",
    description: "Angajare, acte de muncă și calificări.",
    icon: "career",
    color: "orange",
    topics: ["Angajare", "Contract de muncă", "Recunoașterea calificărilor"],
  },
  {
    id: "business",
    title: "Afaceri și finanțe",
    description: "Înregistrare firmă, autorizații și acte fiscale.",
    icon: "business",
    color: "purple",
    topics: ["Deschiderea unei firme", "Acte fiscale", "Autorizații"],
  },
  {
    id: "daily",
    title: "Viață cotidiană",
    description: "Închiriere, schimbarea domiciliului și utilități.",
    icon: "daily",
    color: "blue",
    topics: ["Închiriere", "Schimbarea domiciliului", "Utilități"],
  },
];

// The backend classifies each question; map its category to the ones shown in the UI.
export const backendCategory = {
  education: "education",
  health: "health",
  relocation: "travel",
  auto: "public",
  rent: "daily",
  employment: "career",
  business: "business",
};
export const categoryById = (id) => categories.find((c) => c.id === id) || null;

export const examples = [
  "Vreau să plec cu Erasmus în Franța",
  "Cum mă înregistrez la medic?",
  "Mi-am pierdut buletinul",
];
