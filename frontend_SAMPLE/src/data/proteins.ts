import type { Protein } from "../types";

export const proteins: Protein[] = [
  { id: "protein-EGFR", name: "EGFR", fullName: "Epidermal Growth Factor Receptor", type: "Receptor Tyrosine Kinase" },
  { id: "protein-HER2", name: "HER2", fullName: "Human Epidermal Growth Factor Receptor 2", type: "Receptor Tyrosine Kinase" },
  { id: "protein-BRAF", name: "BRAF", fullName: "B-Raf Proto-Oncogene", type: "Serine/Threonine Kinase" },
  { id: "protein-KRAS", name: "KRAS", fullName: "KRAS Proto-Oncogene", type: "GTPase" },
  { id: "protein-ALK", name: "ALK", fullName: "Anaplastic Lymphoma Kinase", type: "Receptor Tyrosine Kinase" },
  { id: "protein-CDK4", name: "CDK4", fullName: "Cyclin Dependent Kinase 4", type: "Serine/Threonine Kinase" },
  { id: "protein-VEGFR", name: "VEGFR", fullName: "Vascular Endothelial Growth Factor Receptor", type: "Receptor Tyrosine Kinase" },
  { id: "protein-TP53", name: "TP53", fullName: "Tumor Protein P53", type: "Tumor Suppressor" },
];
